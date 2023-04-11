# Informe Laboratorio 2: Aplicación Servidor

## Resumen

En este informe describimos los resultados del trabajo realizado en el laboratorio 2 que constó en la implementación de una aplicación para la transferencia de datos en un modelo cliente-servidor. El objetivo principal del laboratorio fue implementar la conexión entre servidor y el cliente, así como la forma en que el servidor trabaja de su lado.

## Introducción

Nuestra tarea fue diseñar e implementar un servidor de archivos en Python 3 que soporte completamente un protocolo de transferencia de archivos casero HFTP, de tal forma que, el servidor sea robusto, tolerante a comandos intencionales o maliciosamente incorrectos, y capaz de poder atender múltiples conexiones simultáneamente, respondiendo con las solicitudes correspondientes.

## Desarrollo

### Implementación del servidor

El servidor se implementó usando sockets, API para establecer la conexión entre el cliente y el servidor. El trabajo se concentró en el archivo **server.py**, específicamente, en la clase *Server*, donde dividimos su implementación  en dos partes:

1. Creación del socket
    
    En el método *init* lo que hicimos primero fue inicializar self.host, self.port y self.directory con los valores respectivos. Luego, creamos un objeto de socket usando la función socket.socket() que toma como argumentos socket.AF_INET (es decir, que se utilizará IPv4 para la comunicación) y socket.SOCK_STREAM indicando la utilización del protocolo TCP para la transferencia de datos. Por último, usando socket.setsockopt, lo que hicimos fue hacer que cuando un cliente deje de atenderse, otro nuevo cliente pueda reutilizar ese socket automáticamente. Ésta última línea es importante porque permite que el puerto de escucha pueda aceptar varias conexiones entrantes, y no esperar a que éste quede liberado por un cliente que lo este usando en el momento.
    
    Luego, usamos socket.bind((addr, port)) donde se enlaza la dirección y el puerto (en el que el servidor estará escuchando conexiones entrantes) al socket creado previamente.
    
    Por último, asignamos el directorio por default que utilizará el servidor para almacenar y acceder a los archivos que se transferirán entre el mismo y el cliente.
    
    ```python
    def __init__(self, addr=DEFAULT_ADDR, port=DEFAULT_PORT, directory=DEFAULT_DIR):
        # Creación y configuración del socket
        print(f"Serving {directory} on {addr}:{port}.")
        self.host = addr
        self.port = port
        self.directory = directory
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    ```
    
2. Recepción de solicitudes
    
    En esta parte de **server.py,** en el método serve implementamos el loop principal del servidor, para que espere conexiones entrantes del cliente para procesarlas.
    
    Primero, usando socket.bind y socket.listen enlazamos el socket al puerto por default para escuchar a aquellos clientes que se conecten y soliciten información. El servidor puede manejar hasta *MAX_CLIENT* conexiones entrantes en simultáneo.
    
    ```python
    # Comienza escucha del socket
        # Solo puede atender a MAX_CLIENT clientes en simultáneo
        self.socket.bind((self.host, self.port))
        self.socket.listen(MAX_CLIENT)
    ```
    
    Luego, para que nuestra aplicación pueda responder a varias solicitudes simultáneamente, se usó una **thread pool**, que básicamente consiste en tener una lista de hilos, uno para cada cliente, en los que se procesen las solicitudes individuales de los mismos. También hicimos uso de una *Queue* para guardar de forma organizada, una cola de las conexiones a atender en cada uno de los hilos. La función *handle()* es la que maneja cada conexión entrante y la procesa. *threads* es la lista de hilos, y *connection_queue* es una cola utilizada. En el código de aquí debajo se explica en los comentarios el funcionamiento general y el sentido del mismo.
    
    ```python
    
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
    ```
    
    Notar que primero se deben crear los hilos para la cantidad de clientes necesaria, y además se deben procesar las conexiones en la lista *connection_queue* para que en *handle()* se realice la respectiva transferencia de datos.
    

### Implementación de la conexión entre el servidor y el cliente

En el archivo **connection** se implementó el cliente HFTP con los métodos necesarios para:

- Recibir comandos
- Manejar errores
- Enviar respuestas a las solicitudes respectivas

**Estructura Principal**

Para el desarrollo de esta parte, implementamos los 4 comandos disponibles en la aplicación: get_file_listing, get_metadata, get_slice y quit, y a su vez, check_error para el manejo de errores y, algunos métodos auxiliares para facilitar la lectura y comprensión del código.

**Decisiones de Implementación**

Para facilitar la implementación y uso de métodos y comandos, en *init* hicimos lo siguiente:

1. Se inicializaron los atributos importantes para la conexión con cada cliente.
    
    ```python
    		# Socket a utilizar
    		self.socket = nsocket
    		# Directorio a compartir
        self.dir = directory
    		# Estado actual de los pedidos
        self.status = CODE_OK
    		# Registro de mensajes y comandos recibidos del cliente
        self.buffer = ''
    		# Estado de la conexión
        self.connected = True
    ```
    
2. Se creó una switch_table para acceder fácil y rápidamente a los comandos disponibles.
    
    ```python
    self.switch_table = {
            COMMANDS[0]: self.get_file_listing,
            COMMANDS[1]: self.get_metadata,
            COMMANDS[2]: self.get_slice,
            COMMANDS[3]: self.quit,
        }
    ```
    
3. Formato PEP8

    Para seguir las condiciones de estilo de código pedidas por la cátedra, se ha realizado un script que formatea el código de python en PEP8 automáticamente en Visual Studio Code (cuando lo guardamos).
    El archivo se encuentra en [settings.json](.vscode/settings.json).

    Los **requisitos** para usarlo y que funcione es instalar pep8 y pylint. Para ello, se pueden ejecutar los siguientes comandos:
    ```sh
    pip install pep8
    pip install pylint
    ```

**Métodos auxiliares**

Se crearon los siguientes métodos auxiliares:

- *recv:* capta los datos recibidos durante un tiempo y los guarda en el buffer si no se presentan errores. Su funcionamiento es análogo al recv desarrollado en client.py, con la diferencia que tiene en cuenta si se produce una excepción de UnicodeError en la codificación del mensaje. Este método es usado en *read_line.*
- read_line: encargada de esperar a que lleguen los datos hasta obtener una línea completa. Ésta devuelve la linea eliminando los espacios en blanco al principio y al final. Su funcionamiento es análogo al read_line desarrollado en client.py, con la diferencia que tiene en cuenta la mala formación de una linea, devolviendo un cambio de estado en el servidor. Su uso es importante en la obtención de comandos solicitados por el cliente.
- send: encargada de enviar un mensaje al cliente. Utiliza socket.send para enviar el mensaje y devuelve un error y cambio de status del servidor en caso de que la condificación no sea la deseada.
- close: desconecta el cliente del server cambiado el estado de self.connected y cerrando el socket.
- mk_command: utilizada para facilitar los mensajes enviados por parte del cliente. Éstos mensajes luego serán guardados en el buffer.
- cnt_args_is_valid: chequea que la cantidad de argumentos sea igual a la esperada. Devuelve un booleano.
- command_args: devuelve los comandos en una lista. Es utilizada para diferenciar de un argumento pasado a los métodos, aquellas partes que son utilizadas por el método.
- list_files: modulariza el trabajo realizado por el comando get_file_listing. Devuelve una lista con los archivos de un directorio.
- file_exists: básicamente nos dice si el archivo especificado existe en el directorio del servidor.
- filename_is_valid: chequea si el nombre de un archivo es válido.
- file_path: devuelve el path completo en el que se encuentra un archivo.
- check_error: éste método es un handler de errores de la aplicación. Si se produjo un error, este es chequeado con self.status, imprimiendo el mensaje y cerrando la conexión en caso de ser un error fatal. Se utiliza el método mk_command para modularizar el trabajo de imprimir el mensaje.
    
    ```python
    def check_error(self):
        """
        En caso de que se haya producido algún error, lo chequea con
        self.status, imprime el mensaje de error y termina en caso necesario
        """
    
        if self.status != CODE_OK:
          self.send(self.mk_command())
          # Si es error que comienza en 1, se cierra conexión con quit.
          # Caso contrario, no se atiende el pedido pero se sigue la conexión
          if fatal_status(self.status):
            self.status = CODE_OK
            self.quit("quit")
    ```
    

**Comandos especiales**

Para la comunicación entre el cliente y el servidor, se implementaron los siguientes 4 comandos:

1. get_file_listing:
    
    Cada vez que un cliente solicite ver el listado de un directorio, se llama a esta función. Chequea que la cantidad de argumentos recibidos sea válida. Si lo es, guarda en el buffer el status del código en ese momento + los nombres de los archivos existentes en el directorio.
    
    ```python
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
    ```
    

Luego, utiliza send para enviar mediante el socket el mensaje de la aplicación al cliente.

1. get_metadata:
    
    Esta función devuelve el tamaño del archivo en bytes elegido por el cliente.
    
    Primero, se verifica que la cantidad de argumentos recibidos sea válida, que el archivo exista y su nombre sea válido. Estos chequeos se realizan usando los métodos auxiliares *cnt_args_is_valid* *filename_is_valid* y *file_exists*.
    
    Si todo sale bien, se usa el método *getsize* de la librería **os** para obtener el tamaño del archivo en bytes. Él tamaño se guarda en **size** para luego ser enviado al buffer.
    
    ```python
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
    ```
    
2. get_slice:
    
    Obtiene un fragmento de un archivo codificado en base64 a partir de un offset especificado. El archivo debe estar en el directorio.
    
    Primero, se verifica que la cantidad de argumentos recibidos sea válida, que el archivo exista y su nombre sea válido. Estos chequeos se realizan usando los métodos auxiliares *cnt_args_is_valid* *filename_is_valid* y *file_exists*
    
    También, se verifica que el offset sea válido, es decir, que se encuentre dentro de los límites del archivo.
    
    Si todo sale bien, se abre el archivo usando el método **open** de python, guardando “la referencia” al archivo en file_data y, usando el método *seek* y *read* se obtiene el fragmento del archivo deseado. Se usa un ciclo while para la lectura de los bytes de información para que cuando se hayan leído todos los datos, se envíe usando el método auxiliar *send* el fragmento obtenido.
    
    ```python
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
    ```
    
3. quit:
    
    Cierra la conexión a pedido del cliente. Si la cantidad de arguementos recibidos es correcta (es decir, cero argumentos) utiliza el método auxiliar *send* para enviar el buffer restante y *close* para cerrar el socket.
    
    ```python
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
    ```
    

**Handlers**

En el método handle se atienden los eventos de la conexión hasta que la misma termine. Primero, se chequea que el directorio exista haciendo el correspondiente manejo de errores con el método auxiliar *check_error*. Si el directorio existe, mientras el status de conexión sea verdadero, se leen las lineas recibidas por el cliente con el método *read_line* y se realizan las operaciones parseadas en las lineas leídas.

```python
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
```

La realización de las operaciones queda a cargo del método *operation* que se encarga de llamar a los comandos pedidos por el usuario utilizando la *switch_table* ya mencionada. También tiene un manejo de errores, que es que si no se recibió un comando, se cambia el status del servidor por INVALID_COMMAND.

```python
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
```

## Resultados

Luego de la implementación y varios errores, pudimos completar la aplicación de forma tal que su funcionamiento sea correcto no sólo ante solicitudes de un sólo cliente, si no también para múltiples clientes al mismo tiempo.

Solucionamos aquellas dificultades que se presentaron a la hora de:

- test_bad_eol: este es uno de los tests que nos falló. El problema residió en que no se consideraba el caso que haya un simbolo \n (NEWLINE) en la cadena, no haciendose un correcto manejo de errores.
- test_command_in_pieces: este test tenia un error en su implementación ya que hacía un doble quit.
- test_big_file: tuvimos problemas para realizar la codificación de los fragmentos pedidos por el cliente. Los fragmentos llegaban codificados cuando en realidad debían decodificarse al recibirse.

### Preguntas

1. Algunas estrategias que existen para implementar esta aplicación de forma tal que permita recibir solicitudes de múltiples clientes en simultáneo son:
    1. **Thread pool** esta es la estrategia por la que se optó, consiste en crear un conjunto de hilos, cada uno para cada conexión entrante, de forma tal que las solicitudes se procesen de forma independiente entre sí. Para esta estrategia hizo falta cambiar algunos detalles de la implementación del archivo server.py: tuvimos que crear los respectivos hilos para cada solicitud entrante, y tuvimos que tener una cola de solicitudes organizada para que las mismas se atiendan en el orden que llegaron. El cambio no fue abismal porque se utilizaron las librerías *Queue* y *threading* que facilitaron su desarrollo.
    2. **Preforking** en esta estrategia se crean procesos hijos cuando el servidor se inicia. Estos procesos hijos son los que albergarán a las conexiones entrantes a medida que las mismas lleguen al puerto indicado. En esta implementación, haría falta también hacer que el proceso padre espere a que todos los hijos terminen de procesar sus solicitudes, esto se puede hacer usando la librería **os** y el método *wait*.
2. localhost y 127.0.0.1 son las direcciones IP de la máquina local, es decir, la misma que estaría ejecutando el servidor. Esto significa que el servidor sólo puede ser accedido desde la máquina local. Sin embargo, si utilizamos la IP 0.0.0.0, el servidor va a escuchar conexiones que vengan desde cualquier dirección IP en la red que se encuentra el servidor.