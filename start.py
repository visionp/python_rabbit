import logging

import sys
import socket
import uuid
import time
import threading
import signal


loglevel = logging.DEBUG

logger = logging.getLogger()
logger.setLevel(loglevel)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(module)s:%(lineno)s - %(message)s')

ch = logging.StreamHandler()
ch.setLevel(loglevel)
ch.setFormatter(formatter)
logger.addHandler(ch)


class HTTPServer(object):
    timeout = 30
    host = 'localhost'
    port = 10113
    connections = 10
    connection_id = None
    connections_list = {}

    """
        Инициализация сервера
    """
    def __init__(self):
        logging.error("Init server (%s, %s)" % (self.host, self.port))
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind((self.host, self.port))
        self.sock.listen(self.connections)

        # Ctrl+C disconnect socket
        signal.signal(signal.SIGINT, self.signal_handler)

    """
        запуск сервера
    """
    def run(self):
        logging.error("Start server")

        # start response tread
        thread_response = threading.Thread(target=self._response_event)
        thread_response.start()

        # start tread timeout connection
        # thread = threading.Thread(target=self._timeout)
        # thread.start()

        while True:
            logging.error("Waiting connect ....")
            client_socket, client_addr = self.sock.accept()

            self.connection_id = str(uuid.uuid4())

            HTTPServer.connections_list[self.connection_id] = {
                'client_socket': client_socket,
                'client_addr': client_addr,
                'connection_time': int(time.time())
            }
            data = client_socket.recv(1024)
            thread = threading.Thread(name=self.connection_id, target=self._read_request, args=(self.connection_id,))
            thread.start()

    """
        обработчик ожидания данных от клиента
    """
    def _read_request(self, connection_id):

        time.sleep(6)
        logging.error("Waiting client(%s) data" % self.connection_id)

        connection = HTTPServer.connections_list.get(connection_id, None)

        if not connection:
            return False

        client_socket = connection.get('client_socket', None)
        resp = self._gen_headers(200) + 'aaaa'
        client_socket.send(resp.encode())
        client_socket.close()
        sys.exit(0)
    """
        обработчик завершение времени ожидания
    """
    def _timeout(self):
        while True:
            for id in list(HTTPServer.connections_list):
                client = HTTPServer.connections_list.get(id, None)
                if client:
                    delta = int(time.time()) - client.get('connection_time')

                    if delta > self.timeout:
                        logging.error("Client %s send timeout" % id)
                        self._send_timeout(id)

    """
        Удаление соединение с списка ожидающих ответа
    """
    def _delete_connect(self, id=None):
        connect = HTTPServer.connections_list.pop(id, None)
        if connect:
            client = connect.get('client_socket', None)
            if client:
                client.close()

        logging.error(HTTPServer.connections_list)

    """
        Метод для запуска в потоке что бы отвечать клиентам что ожидают ответ
    """
    def _response_event(self):
        while True:
            time.sleep(5)
            if len(HTTPServer.connections_list) == 0:
                logging.error("empty connections")
                continue
            for id in list(HTTPServer.connections_list):
                client = HTTPServer.connections_list.get(id, None)
                if client:

                    str = "{'client_id':%s, 'msg': 'all OK'}" % id
                    logging.error("Answer: %s " % str)
                    logging.error(HTTPServer.connections_list)
                    self._send_ok(id, json=str)
                    # self._send_ok2(client_socket=client.get('client_socket'), id=id)
                    # self._delete_connect(id)

    """
        Генерируем заголовки для ответа
    """
    def _gen_headers(self, code):
        h = ''

        if (code == 200):
            h = 'HTTP/1.1 200 OK\n'
        elif (code == 404):
            h = 'HTTP/1.1 404 Not Found\n'
        current_date = time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime())
        h += 'Date: ' + current_date + '\n'
        h += 'Server: Simple-Python-HTTP-Server\n'
        h += 'Connection: Close\n\n'  # signal that the conection wil be closed after complting the request
        return h

    def _send_ok(self, id,  json=None):
        answer = "HTTP/1.0 200 OK\r\n"
        answer += "Connection: Close\r\n"
        answer += "Content-Type: application/json;charset=utf-8\r\n"

        if json:
            answer += ""
            answer += json

        conn = HTTPServer.connections_list.get(id, None)
        if conn:
            client_socket = conn.get('client_socket', None)
            resp = self._gen_headers(200) + 'aaaa'
            client_socket.send(resp.encode())
            client_socket.close()
            return
            if client_socket:
                client_socket.send(answer.encode())


    def _send_ok2(self, client_socket, id="None"):
        logging.error(HTTPServer.connections_list)
        # client_socket.send(b"HTTP/1.0 200 OK\r\n")
        # client_socket.send(b"Server: OwnHands/0.1\r\n")
        # client_socket.send(b"Content-Type: text/plain\r\n")
        # client_socket.send(b"\r\n")
        # client_socket.send(b"ID: ")

        client_socket.send(self._gen_headers(200).encode())

        client_socket.close()

    """
        Отправляем сообщение время ожидания ответа истекло
        и удалем соединение с списка ожидания
    """

    def _send_timeout(self, id = None):
        answer = "HTTP/1.0 408 Request Time-out\n"
        answer += "Connection: Close\n"
        answer += "Content-Type: application/json;charset=utf-8\n"
        answer += "{'code':408, 'msg':'Request Time-out'}"

        connect = HTTPServer.connections_list.get(id, None)
        if connect:
            client_socket = connect.get('client_socket', None)
            client_socket.send(answer.encode("utf-8"))

        self._delete_connect(id)

    """
        обработчик отправки сообщения и завершения соединения
    """
    def _close_client_connection(self, client_socket):
        client_socket.close()
    """
        Ctrl+C
    """
    def signal_handler(self, signal, frame):
        for id in list(HTTPServer.connections_list):
            connection = HTTPServer.connections_list.pop(id, None)
            if connection:
                conn = connection.get('client_socket')
                logging.error(conn)
                conn.send("Server shutdown".encode())
                conn.close()

        logging.error("Finish")
        logging.error(HTTPServer.connections_list)
        self.sock.close()
        sys.exit(0)

if __name__ == "__main__":
    server = HTTPServer()
    server.run()
