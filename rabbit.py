import pika
import json
import logging
import s
import signal
import configparser


logging.basicConfig(format = u'%(levelname)-8s [%(asctime)s] %(message)s', level = logging.INFO, filename = 'c:/mylog.log')
LOGGER = logging.getLogger(__name__)

class test():


    def __init__(self):
        self.queue_name = 'work_queue'
        self.connection = None
        self.channel = None
        self.start = False
        self.ex_name = 'worker'


    def run(self):
        if self.start == False:
            self.connect()
            self.connection.ioloop.start()

    
    def connect(self):
        credentials = pika.PlainCredentials('vision', 'Opetrenk0')
        params = pika.ConnectionParameters('192.168.1.105', 5672, '/', credentials)
        self.connection = pika.SelectConnection(params, on_open_callback = self.on_open_connection)
        

    def open_channel(self):
        self.connection.channel(on_open_callback = self.on_open_channel)


    def queue_declare(self):
        self.channel.queue_declare(callback = self.declare_exclusive, queue = self.queue_name)


    def declare_exclusive(self, unused_ch):
        self.channel.queue_declare(callback=self.on_queue_declare, exclusive=True)


    def send(self, data):
        print(data.get('connection_id'))
        data_json = json.dumps({'data': data.get('data'), 'connection_id':data.get('connection_id')})

        self.channel.basic_publish(exchange=self.ex_name,
                                   routing_key = self.queue_name,
                                   properties=pika.BasicProperties(
                                       reply_to=self.callback_queue.method.queue,
                                       correlation_id=data.get('connection_id'),
                                   ),
                                   body=data_json)

        print("SEND=> " + data_json)


    def connection_close(self):
        if self.connection:
            if self.channel:
                self.channel.close()
            self.connection.close()

        
    def declare_exchange(self):
        print('start exchange_declare')
        self.channel.exchange_declare(callback=self.on_declare_exchange, exchange_type='topic', exchange=self.ex_name)



    def on_open_connection(self, unused_connection):
        LOGGER.info('Connecting to channel')
        self.start = True
        self.open_channel()

        
    def on_open_channel(self, channel):
        LOGGER.info('channel is open')
        self.channel = channel
        self.declare_exchange()




    def on_declare_exchange(self, unused_channel):
        LOGGER.info('declare_exchange')
        print('declare_exchange')
        self.queue_declare()


    def on_queue_declare(self, queue):
        self.callback_queue = queue
        self.channel.queue_bind(exchange=self.ex_name,queue=self.queue_name, callback=self.start_srv)

    def start_srv(self, q):
        LOGGER.info('queue declare')
        # server = http_server.http_server()
        # server.run(self.send)
        self.server = s.Server(9595)
        self.server.activate_server(publish = self.send, channel = self.channel, route = self.callback_queue.method.queue)


def graceful_shutdown(sig, dummy):
    t.server.shutdown()  # shut down the server
    import sys
    sys.exit(1)


signal.signal(signal.SIGINT, graceful_shutdown)
t = test()
t.run()

