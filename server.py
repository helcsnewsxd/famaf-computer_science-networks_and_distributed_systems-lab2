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
import threading
from queue import Queue


class Server(object):
  """
  El servidor, que crea y atiende el socket en la dirección y puerto
  especificados donde se reciben nuevas conexiones de clientes.
  """

  def __init__(self, addr=DEFAULT_ADDR, port=DEFAULT_PORT, directory=DEFAULT_DIR):
    # Creación y configuración del socket
    print(f"Serving {directory} on {addr}:{port}.")
    # Dirección y puerto donde escuchar, + directorio
    self.host = addr
    self.port = port
    self.directory = directory
    # Se crea el socket para enlazar la conexión
    self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Se configura el socket para que no espere a que una conexión
    # para volver a ser utilizado
    self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

  def serve(self):
    """
    Loop principal del servidor. Se acepta una conexión a la vez
    y se espera a que concluya antes de seguir.
    """
    # Comienza escucha del socket
    # Solo puede atender a MAX_CLIENT clientes en simultáneo
    self.socket.bind((self.host, self.port))
    self.socket.listen(MAX_CLIENT)

    # Grupo de hilos
    threads = []
    # Cola de conexiones
    connection_queue = Queue()

    # Procesa conexiones entrantes
    def handle():
      while True:
        # Obtiene una conexión de la cola
        nw_socket, client_info = connection_queue.get()
        print(f"Connection from {client_info[0]} using port {client_info[1]}")
        # Creo la conexión con el cliente
        new_connection = connection.Connection(nw_socket, self.directory)
        # Procesa pedidos del cliente
        new_connection.handle()
        # Cierra conexión luego de procesar los pedidos
        nw_socket.close()
        print(
            f"Connection from {client_info[0]} using port {client_info[1]} closed.")
        # Indica que la conexión fue procesada, da a lugar a otra conexión
        connection_queue.task_done()

    # Crea los hilos para la cantidad de clientes máxima
    for i in range(MAX_CLIENT):
      # Cada hilo ejecuta la función handle
      thr = threading.Thread(target=handle)
      # Hilo termina cuando el programa termina
      thr.daemon = True
      # Inicia el hilo
      thr.start()
      # Agrega el hilo a la lista de hilos
      threads.append(thr)

    # Espera a que se procesen todas las conexiones
    while True:
      # Acepta una conexión
      nw_socket, client_info = self.socket.accept()
      # Agrega la conexión a la cola para que sea procesada
      # por un hilo en handle()
      connection_queue.put((nw_socket, client_info))


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
