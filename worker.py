import pika
import json
import logging
import time  # Current time
from io import StringIO
import configparser
import os
import sys

logging.basicConfig(format=u'%(levelname)-8s [%(asctime)s] %(message)s', level=logging.INFO, filename='c:/mylog.log')
LOGGER = logging.getLogger(__name__)


class worker():
    def __init__(self):
        self.queue_name = 'server'
        self.connection = None
        self.channel = None
        self.start = False
        self.ex_name = 'worker'
        self.route = 'validate.*'

    def run(self):
        if self.start == False:
            self.connect()
            self.connection.ioloop.start()

    def connect(self):
        credentials = pika.PlainCredentials('vision', 'Opetrenk0')
        params = pika.ConnectionParameters('192.168.1.105', 5672, '/', credentials)
        self.connection = pika.SelectConnection(params, on_open_callback=self.on_open_connection)

    def open_channel(self):
        self.connection.channel(on_open_callback=self.on_open_channel)

    def queue_declare(self):
        self.result = self.channel.queue_declare(
            callback=self.on_queue_declare,
            queue=self.queue_name,
            durable=True
        )


    def on_response(self,ch,method,props,body):
        print('Got TASK')
        io = StringIO(body.decode())
        action = json.load(io).get('data')[0]

        response = 'WORKER' + ' ' + time.strftime('%H_%M_%S') + '  ' + action
        #time.sleep(2)
        response += ' ' + time.strftime('%H_%M_%S') + '    <br>\n\n\n'
        data_json = json.dumps(response)
        ch.basic_publish(exchange='',
                         routing_key=props.reply_to,
                         properties=pika.BasicProperties(correlation_id=props.correlation_id),
                         body=data_json)
        ch.basic_ack(delivery_tag=method.delivery_tag)
        print('Send result')

    def connection_close(self):
        if self.connection:
            if self.channel:
                self.channel.close()
            self.connection.close()

    def declare_exchange(self):
        print('start exchange_declare: ' + self.ex_name)
        self.channel.exchange_declare(
            callback=self.on_declare_exchange,
            exchange_type='topic',
            exchange=self.ex_name,
            durable=True
        )

    def on_open_connection(self, unused_connection):
        LOGGER.info('Connecting to channel')
        self.start = True
        self.open_channel()

    def on_open_channel(self, channel):
        LOGGER.info('channel is open')
        self.channel = channel
        self.declare_exchange()

    def on_declare_exchange(self, unused_channel):
        print('declare_exchange')
        self.queue_declare()

    def on_queue_declare(self, unused_channel):
        print('Route: ' + self.route)
        self.channel.queue_bind(
            exchange=self.ex_name,
            queue=self.queue_name,
            callback=self.start_srv,
            routing_key=self.route
        )


    def start_srv(self, q):
        print('starting...')
        self.channel.basic_consume(
            self.on_response,
            queue=self.queue_name
        )


if __name__ == "__main__":
    w = worker()
    w.run()

