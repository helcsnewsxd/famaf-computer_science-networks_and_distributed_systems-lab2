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
        buffer = str(self.status) + '' + error_messages[self.status] + EOL
        if fatal_status(self.status):
            self.connected = False
        return buffer

    def get_file_listing(self):
        buffer = str(CODE_OK) + ' ' + error_messages[CODE_OK] + EOL
        lista = os.listdir(self.dir)
        for element in lista:
            buffer += element + EOL
        buffer += EOL
        return buffer

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
