#!/usr/bin/python

import socket  # Networking support
import signal  # Signal support (server shutdown on signal receive)
import sys  # Current time
from rabbit_manager import RabbitManager
import time
from http.server import BaseHTTPRequestHandler
from io import BytesIO
import uuid
import threading
import json
import urllib
from io import StringIO
#from urllib import request, response, parse
from WebOb import request

class HTTPRequest(BaseHTTPRequestHandler):
    def __init__(self, request_text):
        self.rfile = BytesIO(request_text)
        self.raw_requestline = self.rfile.readline()
        self.error_code = self.error_message = None
        self.parse_request()



class Server:
    connections = {}
    is_start = False

    def __init__(self, port=9595, host=''):
        self.rabbit = RabbitManager(self.on_response)
        connection_thread = threading.Thread(
            target=self.rabbit.run
        )
        connection_thread.daemon = True
        connection_thread.start()
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind((host, port))

    def activate_server(self):
        if self.is_start is False:
            signal.signal(signal.SIGINT, self.stop)
            self._wait_for_connections()
        else:
            print('Server already started')

    def shutdown(self):
        print("Shutting down the server")
        response = 'Server shutdown'.encode()
        for key, conn in self.connections.items():
            try:
                conn.send(response)
                conn.close()
                print("Close connection")
            except Exception as e:
                print("Warning: could not shut down the socket. Maybe it was already closed.")

    def _gen_headers(self, code):
        h = ''
        if (code == 200):
            h = 'HTTP/1.1 200 OK\n'
        elif (code == 404):
            h = 'HTTP/1.1 404 Not Found\n'
        current_date = time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime())
        h += 'Date: ' + current_date + '\n'
        h += 'Server: Simple-Python-HTTP-Server\n'
        h += 'Connection: close\n\n'  # signal that the conection wil be closed after complting the request
        return h

    def _wait_for_connections(self):
        print('Start http-server\n')
        while True:
            self.socket.listen(110)
            conn, addr = self.socket.accept()
            print("Got connection from:", addr)
            connection_key = str(uuid.uuid1())
            self.connections[connection_key] = conn
            connection_thread = threading.Thread(
                target=self.send_answer, args=(connection_key, )
            )
            connection_thread.daemon = True
            connection_thread.start()

    def send_answer(self, connection_key):
        conn = self.connections.get(connection_key)
        data = conn.recv(1024)  # receive data from client
        #request.

        headers = HTTPRequest(data)

        if hasattr(headers, 'path') is False:
            response_headers = self._gen_headers(404)
            server_response = response_headers.encode()
            conn.send(server_response)
            conn.close()
            return

        parseUrl = urllib.parse.urlparse(headers.path)
        get_params = urllib.parse.parse_qs(parseUrl.query)
        action = get_params.get('action', False)

        if(parseUrl.path == '/favicon.ico' or action is False):
            print('return favicon')
            response_headers = self._gen_headers(404)
            server_response = response_headers.encode()
            conn.send(server_response)
            conn.close()
            return

        task = {'connection_id': connection_key, 'data': action}
        self.rabbit.publish(task)
        sys.exit(0)

    def on_response(self, ch, method, props, body):
        conn = self.connections.pop(props.correlation_id, False)
        if conn:
            response = self._gen_headers(200)
            io = StringIO(body.decode())
            response += json.load(io) + ' ' + time.strftime('%H_%M_%S') + ' '
            conn.send(response.encode())
            conn.close()
            print("Closing connection with client")

    def stop(self):
        print('Stopping server...')
        self.rabbit.stop()
        self.shutdown()
        sys.exit(0)

s = Server(9595)
s.activate_server()


