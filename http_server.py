#!/usr/bin/python
import http.server
import time


class myHandler(http.server.BaseHTTPRequestHandler):

    func = False
    connection = False

    def do_GET(self):
        html = 'test' + str(self.client_address[0]) + self.date_time_string()
        self.send_response(200)
        self.send_header('Content-type','text/html')
        self.end_headers()
        self.wfile.write(bytes(html, 'UTF-8'))
        self.sendResponse(html)
        return

    def sendResponse(self, html):
        print('send RESPONSE')
        if self:
            self.func(html)



class server(http.server.HTTPServer):

    connections = {}

    def saveConnect(self):
        return True


class http_server():

    port = 8090
    host = ''

    def run(self, func):
        try:
            self.start_server(func)
        except KeyboardInterrupt:
            print ('Shutting down the web server')
            self.stop_server()
        except:
            print('Oops, exception...')
            self.stop_server()            
            
    
    def start_server(self, func):
        myHandler.func = func
        address = (self.host, self.port)
        self.server = server(address, myHandler)
        print('Started httpserver on port %d' % self.port)
        self.server.serve_forever()
        host, port = self.server.socket.getsockname()[:2]
        print(host)
        

    def stop_server(self):
        self.server.socket.close()
        print('stop server')

    



