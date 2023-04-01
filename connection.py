# encoding: utf-8
# Revisión 2019 (a Python 3 y base64): Pablo Ventura
# Copyright 2014 Carlos Bederián
# $Id: connection.py 455 2011-05-01 00:32:09Z carlos $

import socket
from constants import *
from base64 import b64encode
import logging
import time


class Connection(object):
  """
  Conexión punto a punto entre el servidor y un cliente.
  Se encarga de satisfacer los pedidos del cliente hasta
  que termina la conexión.
  """

  def __init__(self, nw_socket, directory):
    # FALTA: Inicializar atributos de Connection
    self.socket = nw_socket
    self.directory = directory
    self.status = CODE_OK
    self.buffer = ''
    self.connected = True

    self.switch_table = {
        COMMANDS[0]: self.get_file_listing,
        COMMANDS[1]: self.get_metadata,
        COMMANDS[2]: self.get_slice,
        COMMANDS[3]: self.quit,
    }

  # HACER
  def check_error(self):
    """
    En caso de que se haya producido algún error, lo chequea con
    self.status, imprime el mensaje de error y termina en caso necesario
    """
    print("parte del error")

  # HACER
  def get_file_listing(self, data):
    """
    ARGUMENTOS: No recibe
    OPERACIÓN: Devuelve la lista de archivos en el directorio
    RESPUESTA: 0 OK\r\n{archivo1}\r\n{...\r\n}\r\n
    """
    print("buenas")
    self.socket.send(b'0 OK\r\na\r\n\r\n')

  # HACER
  def get_metadata(self, data):
    """
    ARGUMENTOS: FILENAME
    OPERACIÓN: Devuelve el tamaño del archivo en bytes
    RESPUESTA: 0 OK\r\n{Tamaño}\r\n
    """
    print("buenas2")

  # HACER
  def get_slice(self, data):
    """
    ARGUMENTOS: FILENAME OFFSET SIZE
    OPERACIÓN: Se devuelve el fragmento del archivo pedido
    RESPUESTA: 0 OK\r\n{Fragmento en base64}\r\n
    """
    print("buenas3")

  # HACER
  def quit(self, data):
    """
    ARGUMENTOS: No recibe
    OPERACIÓN: Cerrar la conexión
    RESPUESTA: 0 OK
    """
    self.status = END
    self.socket.send(b'0 OK\r\n')
    self.socket.close()

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

  def read_line(self, timeout=None):
    """
    Espera datos hasta obtener una línea completa delimitada por el
    terminador del protocolo.

    Devuelve la línea, eliminando el terminador y los espacios en blanco
    al principio y al final.
    """
    while not EOL in self.buffer and self.connected:
      if timeout is not None:
        t1 = time.clock()
      self._recv(timeout)
      if timeout is not None:
        t2 = time.clock()
        timeout -= t2 - t1
        t1 = t2
    if EOL in self.buffer:
      response, self.buffer = self.buffer.split(EOL, 1)
      return response.strip()
    else:
      self.connected = False
      return ""

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
    while self.status is CODE_OK:
      data = self.read_line()
      print(f"============ COMANDO QUE RECIBO -> {data}")
      self.check_error()
      self.operation(data)
