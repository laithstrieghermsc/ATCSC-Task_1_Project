import os
import sqlite3
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import http
from string import Template
import time
import web
#import sql
from shared import DataHandler

if __name__ == "__main__":
    handler = DataHandler("Success")
    handler.a = "hello"
    wsite = web.Web(handler)
    daemon = threading.Thread(name="http_daemon", target=wsite.begin_listen(), args=(), daemon=True)
    daemon.start()

    while True:
        print("Hello")
        time.sleep(2)