#!/usr/bin/env python
# encoding: utf-8
# Revisión 2019 (a Python 3 y base64): Pablo Ventura
# Revisión 2014 Carlos Bederián
# Revisión 2011 Nicolás Wolovick
# Copyright 2008-2010 Natalia Bidart y Daniel Moisset
# $Id: server.py 656 2013-03-18 23:49:11Z bc $

import sys
import optparse
import socket
import connection
from constants import *


class Server(object):
  """
  El servidor, que crea y atiende el socket en la dirección y puerto
  especificados donde se reciben nuevas conexiones de clientes.
  """

  def __init__(self, addr=DEFAULT_ADDR, port=DEFAULT_PORT,
               directory=DEFAULT_DIR):
    # Creación y configuración del socket
    print("Serving %s on %s:%s." % (directory, addr, port))
    self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    self.socket.bind((addr, port))
    self.directory = directory

  def serve(self):
    """
    Loop principal del servidor. Se acepta una conexión a la vez
    y se espera a que concluya antes de seguir.
    """
    # Comienza escucha del socket
    # Solo puede atender a MAX_CLIENT clientes en simultáneo
    self.socket.listen(MAX_CLIENT)
    while True:
      # Acepto la conexión
      # c es el socket de conexión
      # a es (addr, port) del cliente
      nw_socket, client_info = self.socket.accept()
      print(f"Connection from {client_info[0]} using port {client_info[1]}")
      # Creo la conexión
      new_connection = connection.Connection(nw_socket, self.directory)
      # Resuelvo pedidos del cliente hasta que se vaya
      new_connection.handle()


def main():
  """Parsea los argumentos y lanza el server"""

  parser = optparse.OptionParser()
  parser.add_option(
      "-p", "--port",
      help="Número de puerto TCP donde escuchar", default=DEFAULT_PORT)
  parser.add_option(
      "-a", "--address",
      help="Dirección donde escuchar", default=DEFAULT_ADDR)
  parser.add_option(
      "-d", "--datadir",
      help="Directorio compartido", default=DEFAULT_DIR)

  options, args = parser.parse_args()
  if len(args) > 0:
    parser.print_help()
    sys.exit(1)
  try:
    port = int(options.port)
  except ValueError:
    sys.stderr.write(
        "Numero de puerto invalido: %s\n" % repr(options.port))
    parser.print_help()
    sys.exit(1)

  server = Server(options.address, port, options.datadir)
  server.serve()


if __name__ == '__main__':
  main()
