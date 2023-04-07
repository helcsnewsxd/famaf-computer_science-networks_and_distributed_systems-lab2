# encoding: utf-8
# Revisión 2019 (a Python 3 y base64): Pablo Ventura
# Copyright 2014 Carlos Bederián
# $Id: connection.py 455 2011-05-01 00:32:09Z carlos $

import socket
from base64 import b64encode
import logging
import time
import os
from constants import *


class Connection(object):
    """
    Conexión punto a punto entre el servidor y un cliente.
    Se encarga de satisfacer los pedidos del cliente hasta
    que termina la conexión.
    """

    def __init__(self, nsocket, directory):
        # FALTA: Inicializar atributos de Connection
        self.socket = nsocket
        self.dir = directory
        self.status = CODE_OK
        self.buffer = ''
        self.connected = True

        self.switch_table = {
            COMMANDS[0]: self.get_file_listing,
            COMMANDS[1]: self.get_metadata,
            COMMANDS[2]: self.get_slice,
            COMMANDS[3]: self.quit,
        }

    def _recv(self, timeout=None):
        """
        Recibe datos y acumula en el buffer interno.
        """
        self.socket.settimeout(timeout)
        data = self.socket.recv(4096).decode("ascii")
        self.buffer += data

        if len(data) == 0:
            self.connected = False
            self.status = BAD_REQUEST

    def check_error(self):
      """
      En caso de que se haya producido algún error, lo chequea con
      self.status, imprime el mensaje de error y termina en caso necesario
      """

      # Si es error que comienza en 1, se manda error y se cierra conexión
      if fatal_status(self.status):
        self.connected = False
        logging.error(
            f"{self.status} {error_messages[self.status]}\r\n")
        self.socket.close()
      # Si es error que comienza en 2, se manda warning pero no se cierra conexión
      elif not self.status == CODE_OK and not fatal_status(self.status):
        self.connected = False
        logging.warning(
            f"{self.status} {error_messages[self.status]}\r\n")
        # ERROR, NO DEBERÍA CERRARSE LA CONEXIÓN, SOLO TIRAR WARNING DE PARTE DEL SERVER. NO SE COMO HACER PARA QUE EL CLIENTE RECIBA QUE NO EXISTE EL DIR
        self.socket.close()
      elif self.status == CODE_OK:  # Si no hay error, se manda OK
        self.socket.send(b'0 OK \r\n')

    def get_file_listing(self, data):

      self.check_error()

      if os.path.exists(self.dir) and self.connected:
        result = os.listdir(self.dir)
        for archivo in result:
          self.socket.send(archivo.encode("ascii")+b'\r\n')
        self.socket.send(b'\r\n')
      else:
        self.status = FILE_NOT_FOUND

    def get_metadata(self, file):
        if not file in os.listdir(self.dir):
            self.status = FILE_NOT_FOUND
        buffer = str(CODE_OK) + ' ' + error_messages[CODE_OK] + EOL
        size = os.path.getsize(self.dir + os.path.sep + file)
        buffer = buffer + str(size) + EOL
        return buffer

    # HACER
    def get_slice(self):
        """
        ARGUMENTOS: FILENAME OFFSET SIZE
        OPERACIÓN: Se devuelve el fragmento del archivo pedido
        RESPUESTA: 0 OK\r\n{Fragmento en base64}\r\n
        """
        pass

    # HACER
    def quit(self):
        """
        ARGUMENTOS: No recibe
        OPERACIÓN: Cerrar la conexión
        RESPUESTA: 0 OK
        """
        buffer = str(CODE_OK) + ' ' + error_messages[CODE_OK] + EOL
        self.connected = False
        return (buffer)

    def read_line(self, timeout=None):
        """
        Espera datos hasta obtener una línea completa delimitada por el
        terminador del protocolo.

        Devuelve la línea, eliminando el terminador y los espacios en blanco
        al principio y al final.
        """
        if EOL not in self.buffer:
            self._recv(timeout)
        comando = self.buffer.split(EOL, 1)
        if "\n" in comando[0]:
            self.status = BAD_EOL
        # Handlea el primer comando y lo remueve del buffer
        self.buffer = self.buffer.replace(EOL.join(comando), "", 1)
        data = comando[0]
        return data

    def operation(self, data):
        """
        Elige la operación a la cual dirigir el pedido
        en base a la switch table
        """
        do_oper = self.switch_table.get(data.split(' ')[0], None)
        print(
            f"============ EL PARSEO DEL COMANDO QUE HAGO ES {data.split(' ')[0]}")
        if do_oper is None:
            print("============ EL COMANDO NO CORRESPONDE Y ES INVÁLIDO")
            self.status = INVALID_COMMAND
        else:
            print("============ ME VOY A LA FUNCIÓN CORRESPONDIENTE")
            do_oper(data)
        self.check_error()

    def handle(self):
        """
        Atiende eventos de la conexión hasta que termina.
        """
        while self.connected:
            while self.status is CODE_OK:
                data = self.read_line()
                print(f"============ COMANDO QUE RECIBO -> {data}")
                self.operation(data)
            self.check_error()
            # self.send()
        self.socket.close()
