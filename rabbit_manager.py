import pika
import json
import logging
import signal
import configparser
import os
import sys

logging.basicConfig(format=u'%(levelname)-8s [%(asctime)s] %(message)s', level=logging.INFO, filename='c:/mylog.log')
LOGGER = logging.getLogger(__name__)


class RabbitManager:

    server_started = False

    def __init__(self, client_callback):
        self.client_callback = client_callback

    def run(self):
        path_ini = os.path.join(os.path.dirname(__file__), 'rabbit.ini')
        if os.path.exists(path_ini):
            cp = configparser.ConfigParser()
            cp.read(path_ini)
            section = 'auth'
            section_queue = 'queue'
            self.login = cp.get(section, 'login')
            self.password = cp.get(section, 'password')
            self.host = cp.get(section, 'host')
            self.port = int(cp.get(section, 'port'))
            self.queue_name = cp.get(section_queue, 'queue_name')
            self.ex_name = cp.get(section_queue, 'ex_name')
            self.routing_key = cp.get(section_queue, 'routing_key')

            if self.login is False \
                    or self.password is False \
                    or self.host is False \
                    or self.port is False \
                    or self.queue_name is False \
                    or self.ex_name is False:
                raise Exception('Not set all settings')
        else:
            raise Exception('Not found rabbit.ini')

        if self.server_started is False:
            self.connect()
            self.server_started = True
            self.connection.ioloop.start()

    def connect(self):
        credentials = pika.PlainCredentials(self.login, self.password)
        params = pika.ConnectionParameters(host=self.host, port=self.port, virtual_host='/', credentials=credentials)
        self.log('Start connecting to channel...')
        self.connection = pika.SelectConnection(params, on_open_callback=self.on_open_connection)

    def on_open_connection(self, connection):
        self.log('Connecting to channel: OK')
        self.connection.channel(on_open_callback=self.on_open_channel)

    def on_open_channel(self, channel):
        self.channel = channel
        self.log('Channel is open')
        self.channel.exchange_declare(
            callback=self.on_declare_exchange,
            exchange_type='topic',
            exchange=self.ex_name,
            durable=True
        )

    def on_declare_exchange(self, exchange):
        self.log('Declare exchange')
        self.channel.queue_declare(
            callback=self.on_declare_exclusive,
            queue=self.queue_name,
            durable=True
        )

    def on_declare_exclusive(self, exchange):
        self.channel.queue_declare(
            callback=self.on_queue_exclusive_declare,
            exclusive=True,
            durable=True
        )

    def on_queue_exclusive_declare(self, queue):
        self.callback_queue = queue
        self.channel.queue_bind(
            exchange=self.ex_name,
            queue=self.queue_name,
            callback=self.complete,
            routing_key=self.routing_key
        )

    def complete(self, q):
        self.log('Rabbit done')
        self.channel.basic_consume(
            self.client_callback,
            exclusive=True,
            queue=self.callback_queue.method.queue,
            no_ack=True
        )

    def publish(self, data):
        data_json = json.dumps({'data': data.get('data'), 'connection_id': data.get('connection_id')})
        self.channel.basic_publish(exchange=self.ex_name,
                                   routing_key=self.routing_key,
                                   properties=pika.BasicProperties(
                                       reply_to=self.callback_queue.method.queue,
                                       correlation_id=data.get('connection_id')
                                   ),
                                   body=data_json)
        self.log("SEND=> " + data_json)

    def stop(self):
        if(self.server_started ):
            self.log('Stopping server...')
            self.connection_close()

    def connection_close(self):
        if self.connection:
            if self.channel:
                self.channel.close()
            self.connection.close()
            self.log('Rabbit stopped!')


    def log(self, m):
        print(m)

