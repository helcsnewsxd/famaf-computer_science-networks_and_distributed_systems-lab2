# encoding: utf-8
# Revisión 2019 (a Python 3 y base64): Pablo Ventura
# Copyright 2014 Carlos Bederián
# $Id: connection.py 455 2011-05-01 00:32:09Z carlos $

import socket
from base64 import b64encode
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
    """
    Inicialización de los atributos de Connection
    """
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

  def mk_command(self):
    """
    Crea la estructura del comando a enviar para
    facilitar el codigo y su lectura
    """
    return f"{self.status} {error_messages[self.status]}"

  def _recv(self):
    """
    Recibe datos y acumula en el buffer interno.
    """
    data = self.socket.recv(4096).decode("ascii")
    self.buffer += data

    if len(data) == 0:
      self.connected = False
      self.status = BAD_REQUEST

  def read_line(self):
    """
    Espera datos hasta obtener una línea completa delimitada por el
    terminador del protocolo.

    Devuelve la línea, eliminando el terminador y los espacios en blanco
    al principio y al final.
    """
    if EOL not in self.buffer and self.status == CODE_OK:
      self._recv()
      ret = ""
      if EOL in self.buffer:
        response, self.buffer = self.buffer.split(EOL, 1)
        ret = response.strip()
      else:
        self.status = BAD_EOL
      return ret

  def send(self, message: bytes or str, encoding='ascii', with_eol=True):
    """
    Envía el mensaje 'message' al cliente con el encoding solicitado,
    seguido por el terminador de línea del protocolo.
    Si se da un timeout, puede abortar con una excepción socket.timeout.
    También puede fallar con otras excepciones de socket.
    """
    if encoding not in ('ascii', 'b64'):
      self.status = INTERNAL_ERROR
    else:
      if encoding == 'ascii':
        message = message.encode('ascii')
      else:
        message = b64encode(message)
      while message:
        bytes_sent = self.socket.send(message)
        assert bytes_sent > 0
        message = message[bytes_sent:]

      # Completar el mensaje con un fin de línea
      if with_eol:
        self.send(EOL, with_eol=False)

  def close(self):
    """
    Desconecta el cliente del server
    """
    self.connected = False
    self.socket.close()

  def check_error(self):
    """
    En caso de que se haya producido algún error, lo chequea con
    self.status, imprime el mensaje de error y termina en caso necesario
    """

    if self.status != CODE_OK:
      self.send(self.mk_command())
      # Si es error que comienza en 1, se cierra conexión.
      # Caso contrario, no se atiende el pedido pero se sigue la conexión
      if fatal_status(self.status):
        self.close()

  def get_file_listing(self, data):
    """
    Este comando devuelve la lista de los archivos
    dentro del directorio del servidor
    """
    result = os.listdir(self.dir)
    buffer = self.mk_command() + EOL
    for archivo in result:
      buffer += archivo + EOL
    self.send(buffer)

  def get_metadata(self, file):
    """
    Devuelve el tamaño del archivo en bytes elegido por el cliente.
    El archivo debe estar en el directorio del servidor.
    """
    command = file.rsplit(' ')
    if len(command) != 2:
      self.status = INVALID_ARGUMENTS
    else:
      filename = command[1]
      if filename not in os.listdir(self.dir):
        self.status = FILE_NOT_FOUND
      else:
        size = os.path.getsize(self.dir + os.path.sep + filename)
        buffer = self.mk_command() + EOL + str(size)
        self.send(buffer)

  def get_slice(self, file):
    """
    Devuelve el fragmento de un archivo pedido en base64.
    El archivo debe estar en el directorio del servidor.
    """
    # Tengo que parsear cada parte de file
    command = file.rsplit(' ')
    if len(command) != 4:
      print("MAL ARGUMENTOS")
      self.status = INVALID_ARGUMENTS
    else:
      filename, offset, size = command[1], command[2], command[3]
      if filename not in os.listdir(self.dir):
        self.status = FILE_NOT_FOUND
      elif not offset.isnumeric() or not size.isnumeric():
        self.status = INVALID_ARGUMENTS
      elif not int(offset) + int(size) <= os.path.getsize(self.dir + os.path.sep + filename) \
              or int(offset) < 0:
        self.status = BAD_OFFSET
      else:
        buffer = self.mk_command()
        # Abro archivo
        with open(self.dir + os.path.sep + filename, 'rb') as file_data:
          # uso seek para ir al offset
          file_data.seek(int(offset))
          # leo sólo el size pedido y lo codifico
          fragment = file_data.read(int(size))
          # envío la respuesta
          self.send(buffer)
          self.send(fragment, encoding='b64')

  def quit(self, data):
    """
    Cierra la conexión a pedido del cliente
    """
    buffer = self.mk_command()
    self.send(buffer)
    self.close()

  def operation(self, data):
    """
    Elige la operación a la cual dirigir el pedido
    en base a la switch table
    """
    print(data)
    do_oper = self.switch_table.get(data.split(' ')[0], None)
    if do_oper is None:
      self.status = INVALID_COMMAND
    else:
      do_oper(data)

  def handle(self):
    """
    Atiende eventos de la conexión hasta que termina.
    """
    # El directorio del servidor no existe
    if not os.path.exists(self.dir):
      self.status = INTERNAL_ERROR
      self.check_error()

    while self.connected is True:
      data = self.read_line()
      self.check_error()
      # Si no debo procesar este pedido, no entro y vuelvo a OK
      # Si debo cortar, se ve en la guarda del while
      # Si está todo bien, entro a la operación
      if self.connected is True and self.status is CODE_OK:
        self.operation(data)
        self.check_error()
      self.status = CODE_OK
