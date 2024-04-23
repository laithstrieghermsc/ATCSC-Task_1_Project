import os
import random
import sqlite3
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import http
from string import Template
import time
from main import DataHandler
import uuid
import ssl

class WebInterface(BaseHTTPRequestHandler):

    def DefaultMap(self):
        return {
            "test" : "Hello",
            "path" : self.path
        }

    def buildPage(self, path, Map, direct = False):
        html = self.getHTML(path, direct)
        if type(html) is int:
            return html
        build = Template(html)
        return build.substitute(Map)
    def getHTML(self, path, direct = False):
        cwd = os.getcwd()
        html = ""
        try:
            with open(os.path.join(cwd, "webroot", (path.replace("/", "\\")).lstrip("\\"))+("\\index.html" if not direct else "")) as file:
                page = file.readlines()
                for i in page:
                    html+=i
                file.close()
            return html
        except FileNotFoundError:
            return 404
    def writeWline(self, string):
        self.wfile.write(bytes(string, "utf-8"))
    def do_GET(self):
        code = 200
        page = self.buildPage(self.path, self.DefaultMap())
        if type(page) is int:
            code = page
        self.send_response(code)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        if type(page) is int:
            self.writeWline(self.buildPage("/errors/404.html", self.DefaultMap(), True))
        else:
            self.writeWline(page)

'''class session:
    public
    def __init__(self):
        sessionID = uuid.UUID()

    def _verify(self):

'''
class Web:

    def __init__(self, handler: DataHandler):
        self.handler = handler
        self.server = HTTPServer(("127.0.0.1", 4443), WebInterface)
        #context =self._get_ssl_context("cert.pem", "key.pem")
        #self.server.socket = context.wrap_socket(self.server.socket, server_side=True)

    #@staticmethod
    #def _get_ssl_context(certfile, keyfile):
    #    context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
    #    context.load_cert_chain(certfile, keyfile)
    #    context.set_ciphers("DHE-RSA-AES128-SHA:DHE-RSA-AES256-SHA:ECDHE-ECDSA-AES128-GCM-SHA256")
    #    return context
    def begin_listen(self):

        print("Server started http://%s:%s" % ("127.0.0.1", 4443), f"handler test: {self.handler.test}")

        try:
            self.server.serve_forever()
        except KeyboardInterrupt:
            print("hello")
        except:
            print(
                "Somthing stupid happened, based on the ridiculous error handling in http.server, somthing has likely stolen port 8091 or rouge radiation from the sun has perfectly hit a transistor :)")

        self.server.server_close()
        print("Server stopped.")