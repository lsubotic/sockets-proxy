from _thread import start_new_thread
from dataclasses import dataclass
import traceback
import _thread
import argparse
import socket
import time
import re


# CONSTANTS - server socket
# LOCALHOST = ''
# SERVER_PORT = 8080  # default port value
# BUFFER_SIZE = 4096
# MAX_CONNS = 100
# TIMEOUT = 10


@dataclass
class HttpsConnectionData:
	hostname: str 
	port: int
	method: str
	headers: dict  # dict that repersents the request data as key:value
	keep_alive: bool = False	
 	
	def __init__(self):
		pass
	
	def parse_request(self, request: bytes) -> None:
		"""Parses the HTTPS request
		Returns:
			request_lines (dict): dictionary representing the request data as key:value pairs	
  		"""
		# get the remote sever and the port
		host_re = rb'Host:\s([a-z0-9\.\-]+):(\d+)'
		remote_host = re.search(host_re, request).group(1)
		port = int(re.search(host_re, request).group(2))
		self.port = port
		self.hostname = remote_host
		# split the request by each new line
		request_lines = request.split(b'\r\n')
		self.method = request_lines[0].split(b" ")[0]  # CONNECT method 	
		# go through request lines and add them as key:value pairs
		headers = {}
		for line in request_lines[1:]:
			if line == b'':
				break
			k, v = line.split(b': ')
			headers[k.decode()] = v
		# check if `keep-alive` is specified
		self.keep_alive = "Connection" in headers and headers["Connection"] == b"keep-alive"
		# update the headers
		self.headers = headers
  
	def print_data(self) -> None:
		if not self.hostname:
			print("")	
			return 
		print(f"{self.hostname}:{self.port}")
		for k, v in self.headers.items():
			print(f'{k}:', v)	
	

@dataclass
class HttpConnectionData:
	headers: dict
	hostname: str = ''
	method: str = ''
	raw_request: bytes = b''
	port: int = 80
	
	def __init__(self) -> None:
		pass	

	def parse_request(self, request: bytes) -> None:
		# empty request
		if not request:
			return

		self.raw_request = request
		request_lines = request.split(b'\r\n')
		self.method = request_lines[0].split(b" ")[0]   # ex. GET or POST method
		headers = {}
		for line in request_lines[1:]:
			if line == b'':
				break
			k, v = line.strip().split(b": ")
			headers[k.decode()] = v
		# get the hostname
		host_re = rb'Host:\s([a-z0-9\.-]+)'
		self.hostname = re.search(host_re, request).group(1)
		self.headers = headers 


class HttpsConnection:
	BUFFER_SIZE = 8192
	DEFAULT_TIMEOUT = 0.5
	KEEPALIVE_TIMEOUT = 0.1 
    
	def __init__(self, browser_conn: socket, connection_data: HttpsConnectionData) -> None:
		self.browser_conn = browser_conn
		self.connection_data = connection_data 
		# this socket communicates with the remote web server
		self.remote_conn_socket = None

	def __enter__(self):
		# create a socket to connect to the remote web server and make sockets non-blocking
		self.remote_conn_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.remote_conn_socket.setblocking(0)
		self.remote_conn_socket.settimeout(7)
		self.browser_conn.setblocking(0)
		return self

	def __exit__(self, exc_type, exc_value, exc_traceback):
		self.browser_conn.close() 
		self.remote_conn_socket.close()

	def connect_to_remote_server(self) -> None:
		"""Attempts to connect to the remote server and informs the browser whether the connection was 
		successfull or not.
  		"""
		success_msg = b'HTTP/1.1 200 Connection established\r\n\r\n'
		# check if the connection is `keep-alive` 
		if 'Connection' in self.connection_data.headers and self.connection_data.headers['Connection'] == b'keep-alive':
			success_msg = b'HTTP/1.1 200\r\nConnection: keep-alive\r\n\r\n'
			print("~~Keep alive~~ ", end='')
		timeout_msg = b'HTTP/1.1 408'

		try:
			self.remote_conn_socket.connect((self.connection_data.hostname, self.connection_data.port))
			print(f"Connected to {self.connection_data.hostname}")
			# inform the browser if the connection was successfull
			self.browser_conn.send(success_msg)
		except socket.error:
			print(f"Error - Connection to {self.connection_data.hostname} timed out")
			# connection timed out
			self.browser_conn.send(timeout_msg) 
			raise socket.error
	
	def serve(self) -> None:
		"""Handles a HTTPS connection, connects to the remote server, receives data from browser and sends it to
		remote server and vice-versa, once it is concluded that there is no more data to transmit between the
		server and the browser, or the timeout is reached, the connection is closed
  		"""
		# connect to the remote web server
		self.connect_to_remote_server()
		# handle persistent connection
		if self.connection_data.keep_alive:
			self.handle_persistent_connection()	
			return
		# handle a one-time connection
		else:
			self.handle_single_https_request()

	def handle_single_https_request(self) -> None:
		# If there is no traffic between sockets for more than 0.5 each, assume that the connection is completed and close it 
		self.remote_conn_socket.settimeout(self.DEFAULT_TIMEOUT)	
		self.browser_conn.settimeout(self.DEFAULT_TIMEOUT)
		while True:
			# send data from browser to remote server
			browser_data = self.receive_from_browser()
			if browser_data:
				self.remote_conn_socket.send(browser_data)
			# send data from remote server to browser
			remote_server_data = self.receive_from_browser()
			if remote_server_data:
				self.browser_conn.send(remote_server_data)
			# if there is no data to transmit, close the connection
			if not browser_data and not remote_server_data:
				break

	def handle_persistent_connection(self):
		"""Handles `keep-alive` persistent connections. Default maximum length of a persistent connection is 60 seconds,
		Checks if there is new data to receive from Browser/Web Server with a default timeout of `KEEPALIVE_TIMEOUT`
		Once the maximum length of 60 has elapsed, or the remote Web Server closes the connection, data transmission
		is closed along with the connection
  		"""
		max_connection_length = 60  # seconds
		start_time = time.time()
		# check if there is new data to receive/send every KEEPALIVE_TIMEOUT seconds	
		self.remote_conn_socket.settimeout(self.KEEPALIVE_TIMEOUT)
		self.browser_conn.settimeout(self.KEEPALIVE_TIMEOUT)
		while True:
			try:
				browser_data = self.receive_from_browser()	
				if browser_data:
					self.remote_conn_socket.send(browser_data)
				
				remote_server_data = self.receive_from_remote_server()
				if remote_server_data:
					self.browser_conn.send(remote_server_data)

			except BrokenPipeError:
				# the remote server has closed connection
				break

			if time.time() - start_time > max_connection_length:
				break
		print(f"Keep-alive connection to {self.connection_data.hostname} closed")

	def receive_from_browser(self) -> bytes | None:
		"""This function receives data that the browser sends to the Proxy Server through the `browser_conn` socket.
		It operates with timeouts in mind, hence when a timeout of DEFAULT_TIMEOUT is reached a `socket.error` is raised and
		communication is closed
  		"""
		browser_data = b''
		while True:
			try:
				# receive data from the browser
				curr_data = self.browser_conn.recv(self.BUFFER_SIZE)
				browser_data += curr_data 
			except socket.timeout:
				return browser_data
			except socket.error:
				print("Browser socket error occured")
				return browser_data
			# if there is no more data to receive, return current data
			if not curr_data:
				return browser_data

	def receive_from_remote_server(self) -> bytes | None:
		"""This function receives data that the remote server sends to the Proxy server, through the 'remote_conn_socket', 
		that is later proxied to the browser. It operates with timeouts in mind, hence when a timeout of DEFAULT_TIMEOUT is 
		reached, a `socket.error` is raised and communication is closed 
  		"""
		server_response = b''
		while True:
			try:
				# receive server's response
				curr_data = self.remote_conn_socket.recv(self.BUFFER_SIZE)
				server_response += curr_data
			except socket.timeout:
				return server_response	
			# NOTE code below could be optimized  
			except:
				print("Remote server socket error occured")
				return server_response
			# if there is no more data to receive from the sever, return
			if not curr_data:
				return server_response


	def handle_handshake():
		"""Left for potential addition"""
		pass


class HttpConnection:
	BUFFER_SIZE = 8192 

	def __init__(self, browser_conn: socket, request_data: HttpConnectionData) -> None:
		self.browser_conn = browser_conn
		self.request_data = request_data
		self.remote_conn_sock = None 
	
	def __enter__(self):
		self.remote_conn_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.remote_conn_sock.setblocking(0)
		self.remote_conn_sock.settimeout(1)
		return self		

	def __exit__(self, exc_type, exc_value, exc_traceback):
		self.remote_conn_sock.close()
		if self.browser_conn:
			self.browser_conn.close()
		print(f"Connection to {self.request_data.hostname} closed.")

	def connect_to_remote_server(self) -> bool:
		"""Connects to the remote server and informs the user whether the connection was successfull
		Returns:
			(bool): returns `True` or `False`, depending on whether the connecion was successfull
  		"""	
		# check for empty requests
		if not self.request_data.raw_request:
			return False 
		try:
			self.remote_conn_sock.connect((self.request_data.hostname, self.request_data.port))
			print(f"Connected to {self.request_data.hostname}")
			return True
		except socket.error:
			print(f"Error! failed to connect to {self.request_data.hostname}")
			return False 
	
	def resolve(self) -> None:
		"""Resolves the HTTP connection by connecting to the remote server, making a request and sending the servers
		response back to the client(browser)
  		"""
		# connect to remote server 
		is_connected = self.connect_to_remote_server()
		if is_connected == False:
			return
		# make a HTTP request
		self.remote_conn_sock.send(self.request_data.raw_request)
		while True:	
			try:
				data = self.remote_conn_sock.recv(self.BUFFER_SIZE)
			except socket.error:
				data = b''
			if not data:
				break
			self.browser_conn.send(data)


class ProxyServer:
	# constants
	LOCALHOST = ''
	SERVER_PORT = 8080  # default port value
	BUFFER_SIZE = 8192
	MAX_CONNS = 100
	TIMEOUT = 10
 
	server_socket: socket	

	def __init__(self, localhost = '', server_port = None | int) -> None:
		self.localhost = localhost
		self.server_port = server_port 

	def __enter__(self):
		self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		# use default values if not specified
		self.localhost = self.LOCALHOST if not self.localhost else self.localhost
		self.port = self.SERVER_PORT if not self.server_port else self.server_port
		# self.server_socket.bind(('212.200.247.102', self.SERVER_PORT))
		self.server_socket.bind((self.LOCALHOST, self.SERVER_PORT))
		print(f"Server started on {'LOCALHOST'}:{self.SERVER_PORT}.")
		return self
			
	def __exit__(self, exc_type, exc_value, exc_traceback):
		# make sure that the socket is closed
		if self.server_socket:
			self.server_socket.close() 

	def serve(self) -> None:
		"""Start a new socket server that connects with the browser to listen for new requests
		and accept them.
		"""
		print("Listening for connections...")
		# listen for connections
		self.server_socket.listen(self.MAX_CONNS)
		while True:
			try: 
				conn, addr = self.server_socket.accept()
				print(f"Accepted connection from {addr[0]}:{addr[1]}")
				request = conn.recv(self.BUFFER_SIZE)  # browser request headers
				if not request:
					conn.close()
				# TODO can be handled in a separate method `check_protocol()` that will check whether it is a http or https request
				# new thread for each connection
				if request[:7] == b'CONNECT':
					# HTTPS 
					start_new_thread(self.https_thread_helper, (conn, request))
				else:
					# HTTP
					start_new_thread(self.http_thread_helper, (conn, request))
			except KeyboardInterrupt:
				print("Proxy server shutting down...")
				self.server_socket.close()
				# end the loop
				break
			except socket.error as e:
				print("Error! Proxy server shutting down...")
				traceback.print_exc()
				break
       
	def https_thread_helper(self, conn: socket, request: bytes) -> None:
		"""Helper function that is used for wrapping each new HTTPS connection in a separate thread
		Params: 
			request (bytes): HTTPS CONNECT request received from the browser containing data necessary
				to establish a new connection with the remote host.
  		"""
		# parse the request data
		connection_data = HttpsConnectionData()
		connection_data.parse_request(request)
		# handle the HTTPS connection
		with HttpsConnection(conn, connection_data) as https_conn:
			https_conn.serve()
		# make sure to exit the thread once the connection is resolved
		_thread.exit()

	def http_thread_helper(self, conn: socket, request: bytes) -> None:
		"""Helper function that is used for wrapping each new HTTP connection in a separate thread
		Params: 
			request (bytes): HTTP request received from the browser that is forwarded to the 
			remote host.
  		"""
		# parse the request data  
		connection_data = HttpConnectionData()
		connection_data.parse_request(request)
		# handle the HTTP connection
		with HttpConnection(conn, connection_data) as http_conn:
			http_conn.resolve()
		# make sure to exit the thread
		_thread.exit()	


# start the server
with ProxyServer() as server:
	server.serve()
