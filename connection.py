# encoding: utf-8
# Revisión 2019 (a Python 3 y base64): Pablo Ventura
# Copyright 2014 Carlos Bederián
# $Id: connection.py 455 2011-05-01 00:32:09Z carlos $

import socket
from base64 import b64encode
import os
from constants import *


class Connection(object):
  """
  Conexión punto a punto entre el servidor y un cliente.
  Se encarga de satisfacer los pedidos del cliente hasta
  que termina la conexión.
  """

  def __init__(self, nsocket: socket, directory):
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

  # FUNCIONES AUXILIARES

  # Lectura de comandos recibidos
  def _recv(self):
    """
    Recibe datos y acumula en el buffer interno.
    """
    try:
      data = self.socket.recv(4096).decode("ascii")
      self.buffer += data

      if len(data) == 0:
        self.connected = False
        self.status = BAD_REQUEST

    except UnicodeError:
      self.status = BAD_REQUEST

  def read_line(self):
    """
    Espera datos hasta obtener una línea completa delimitada por el
    terminador del protocolo.

    Devuelve la línea, eliminando el terminador y los espacios en blanco
    al principio y al final.
    """
    ret, self.buffer = "", ""
    while EOL not in self.buffer and self.status == CODE_OK:
      self._recv()

    if EOL in self.buffer:
      response, self.buffer = self.buffer.split(EOL, 1)
      ret = response.strip()
      if NEWLINE in ret:
        self.status = BAD_EOL
        ret = ""
    else:
      self.status = BAD_EOL
    return ret

  # Envío de respuestas al cliente
  def send(self, message: bytes or str, encoding='ascii'):
    """
    Envía el mensaje 'message' al cliente con el encoding solicitado,
    seguido por el terminador de línea del protocolo en caso que sea ascii.
    Si se da un timeout, puede abortar con una excepción socket.timeout.
    También puede fallar con otras excepciones de socket.
    """
    if encoding not in ('ascii', 'b64'):
      self.status = INTERNAL_ERROR
    else:
      if encoding == 'ascii':
        message += EOL
        message = message.encode('ascii')
      else:
        message = b64encode(message)
      while len(message) > 0:
        bytes_sent = self.socket.send(message)
        assert bytes_sent > 0
        message = message[bytes_sent:]

  # Desconexión del socket
  def close(self):
    """
    Desconecta el cliente del server
    """
    self.connected = False
    self.socket.close()

  # Handler de errores del server o pedidos del cliente
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

  # Comandos de HFTP
  def mk_command(self):
    """
    Crea la estructura del comando a enviar para
    facilitar el codigo y su lectura
    """
    return f"{self.status} {error_messages[self.status]}"

  def cnt_args_is_valid(self, command, number):
    """
    Chequea que la cantidad de argumentos recibida sea
    igual a la esperada
    Es +1 ya que cuenta el nombre del comando
    """
    return len(command.rsplit(' ')) == number+1

  def command_args(self, command):
    """
    Devuelve los comandos en una lista
    """
    command_data = command.rsplit(' ')
    if len(command_data) == 1:
      return []
    else:
      return command_data[1:]

  # Directorio del servidor
  def list_files(self):
    """
    Devuelve del listado de archivos del servidor
    en el directorio en el que está
    """
    return os.listdir(self.dir)

  def file_exists(self, filename):
    """
    Responde si el archivo especificado existe en
    el directorio del servidor
    """
    return filename in self.list_files()

  def filename_is_valid(self, filename):
    """
    Chequea si el nombre de un archivo es válido
    """
    return len(set(filename)-VALID_CHARS) == 0

  def file_path(self, filename):
    """
    Devuelve el path completo del archivo recibido
    """
    return self.dir + os.path.sep + filename

  # COMANDOS DEL SERVER

  def get_file_listing(self, command):
    """
    Este comando devuelve la lista de los archivos
    dentro del directorio del servidor
    """
    if not self.cnt_args_is_valid(command, 0):
      self.status = INVALID_ARGUMENTS
    else:
      buffer = self.mk_command() + EOL
      all_files = self.list_files()
      for file in all_files:
        buffer += file + EOL
      self.send(buffer)

  def get_metadata(self, command):
    """
    Devuelve el tamaño del archivo en bytes elegido por el cliente.
    El archivo debe estar en el directorio del servidor.
    """
    if not self.cnt_args_is_valid(command, 1):
      self.status = INVALID_ARGUMENTS
    else:
      filename = self.command_args(command)[0]

      if not self.filename_is_valid(filename):
        self.status = INVALID_ARGUMENTS
      elif not self.file_exists(filename):
        self.status = FILE_NOT_FOUND
      else:
        size = os.path.getsize(self.file_path(filename))
        buffer = self.mk_command() + EOL + str(size)
        self.send(buffer)

  def get_slice(self, command):
    """
    Devuelve el fragmento de un archivo pedido en base64.
    El archivo debe estar en el directorio del servidor.
    """
    if not self.cnt_args_is_valid(command, 3):
      self.status = INVALID_ARGUMENTS
    else:
      filename, offset, size = self.command_args(command)

      if not self.filename_is_valid(filename) or not offset.isnumeric() or not size.isnumeric():
        self.status = INVALID_ARGUMENTS
      elif not self.file_exists(filename):
        self.status = FILE_NOT_FOUND
      elif int(offset) + int(size) > os.path.getsize(self.file_path(filename)) or int(offset) < 0:
        self.status = BAD_OFFSET
      else:
        offset, size = int(offset), int(size)

        buffer = self.mk_command()
        self.send(buffer)

        with open(self.dir + os.path.sep + filename, 'rb') as file_data:

          bytes_read = b''
          while size > 0:
            file_data.seek(offset)
            bytes_read += file_data.read(size)
            size -= len(bytes_read)
            offset += len(bytes_read)

          self.send(bytes_read, encoding='b64')
          self.send('')

  def quit(self, command):
    """
    Cierra la conexión a pedido del cliente
    """
    if not self.cnt_args_is_valid(command, 0):
      self.status = INVALID_ARGUMENTS
    else:
      buffer = self.mk_command()
      self.send(buffer)
      self.close()

  def operation(self, data):
    """
    Elige la operación a la cual dirigir el pedido
    en base a la switch table
    """
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
