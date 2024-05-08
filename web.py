"""""""""""""""""""""""""""""""""""""""
# ATCSC-Task_1_Project                #
#  web.py                             #
#  classes and processing of website  #
"""""""""""""""""""""""""""""""""""""""

from abc import abstractmethod
from hashlib import md5
import os
import ssl
import threading
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from string import Template
from urllib import parse
from main import DataHandler

# Creates a general understanding throughout the program that instance_data_handler is a DataHandler Object, ---
# because this metadata is not well communicated between threads
# Also storing as a file- 'global' object for accessibility
instance_data_handler: DataHandler


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""


class Web:
    """Core of the web server, handles all requests and interfaces with main"""

    def __init__(self, handler: DataHandler):
        global instance_data_handler
        instance_data_handler = handler  # storing the handler to be accessible
        self.httpd = ThreadedHTTPServer(("0.0.0.0", 4443), WebInterface)  # Create server

        # comment these lines to downgrade to http
        context = self._get_ssl_context("cert.pem", "key.pem")  # load certificates and ciphers
        self.httpd.socket = context.wrap_socket(self.httpd.socket, server_side=True)  # wrap http with TLS to make https

    @staticmethod
    def _get_ssl_context(cert_file, keyfile):
        """Load certificates, defines protocol and ciphers for HTTPS"""
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(cert_file, keyfile)
        context.set_ciphers("@SECLEVEL=1:ALL")
        return context

    def listen(self):
        """the web thread runs listen() asymmetrically (this is main for the web thread)"""
        global instance_data_handler
        # general info + data handler test (Proves information can be sent and received from main)
        print("Server started https://%s:%s\nSTART test" % ("127.0.0.1", 4443))
        print("%s\nEND test" % instance_data_handler.ping(threading.current_thread()))

        try:
            self.httpd.serve_forever()
        except KeyboardInterrupt:
            pass  # probably the most used pass in all of python

        # close server on interrupt
        self.httpd.server_close()
        del self.httpd
        print("Server stopped.")


class WebInterface(BaseHTTPRequestHandler):
    """
    Request handler for the web server, supports only GET and POST requests.
    One instance is created per request and is immediately deleted afterward.
    Acts as 'context' for serve actions (where 'self' is provided as a parameter).
    """

    # Defaults for whether in-page popup elements are served
    invalid_pass = False
    submitted = False

    # ExtraExtraSauce md5 in hex-string (0-9,a-f)
    admin_password = "170ac01abbaa03b17bfa0bdd6f2f0863"

    title = "Pizzaaaaaa Yoooooo"

    def do_GET(self):
        """do_GET is called by HTTPServer (or descendants ThreadedHTTPServer) whenever it receives a http-GET request"""
        # redirect all pages like "https://0.0.0.0:port/dir/to/path/" to "https://0.0.0.0:path/dir/to/path" (remove '/')
        if self.path.endswith("/") and len(self.path) > 1:
            print("Redirect to " + self.path.rstrip("/"))
            self.send_response(307)
            self.send_header('Location', self.path.rstrip("/"))
            self.end_headers()
        else:
            # A list of handlers that will be used to serve site-wide. The more handlers made available, the longer
            # it will take for the server to decide on 404, I've made a bunch, but have decided on only using these
            _ = [DirectoryHandler,
                 CSSHandler,
                 JSHandler,
                 JPEGHandler,
                 ICOHandler,
                 NotFoundHandler]  # The final Handler runs 404 responses
            # for all available handlers
            for __ in _:
                ___ = __(self)  # allows path override behavior.
                if ___.valid:  # check to see if it is valid for a given request, serve it if it is.
                    ___.serve()
                    break  # it's unlikely that multiple handlers will support the same request but this is just in case
                    # also reduces thread lifetime

    def do_POST(self):
        """
        do_POST is called by HTTPServer (or descendants ThreadedHTTPServer) whenever it is receiving a http-POST request
        since this is only performed on 2 pages ('/admin' and '/new') it can handle requests itself
        """
        global instance_data_handler

        length = int(self.headers.get('content-length'))
        field_data = self.rfile.read(length)
        fields = parse.parse_qs(str(field_data, "UTF-8"))
        if self.path == "/admin" and len(fields) == 1:  # if getting an admin access request (single value for password)
            passwd = fields.get("password1")[0].encode("UTF-8")  # get and encode the given password (field 'password1')
            password_md5 = md5(passwd).hexdigest()  # find md5 hash
            if password_md5 == self.admin_password:  # compare to set password
                _ = AdminHandler(self, instance_data_handler)  # initiate dedicated Handler for the admins console
            else:
                self.invalid_pass = True  # indicates that the handler must display a message about the invalid password
                _ = DirectoryHandler(self)  # initiate standard DirectoryHandler, to send back to auth prompt
            _.serve()  # send page
        elif self.path == "/new":  # if getting an order submitting request
            instance_data_handler.add_order(fields)  # enqueue form data for main to interpret
            self.submitted = True  # indicates that the next handler must display a message that the order has been sent
            self.do_GET()  # invokes standard processing in the most lazy way possible, so it just mocks a GET request:)


class Handler:
    """superclass for mapping request criteria to tailored responses"""

    # final path being served.
    _path = ""

    def __init__(self, context: WebInterface, path: str = None):
        self.context = context  # by default, set context to be Webinterface for request information
        self._path = path if path is not None else context.path  # allow override but default to the path of the request

    @property
    def valid(self):
        """True if valid, false if invalid (whether this handler is equipped to respond to the request made by a user"""
        return self.validate()

    @property
    @abstractmethod
    def content(self):
        """A required constant to be set by a subclass, defines the web MIME type of content"""

    @property
    def path(self):
        """path should not be modifiable once Handler object is created"""
        return self._path

    @property
    def full_path(self):
        """
        returns full system path to a resource (from webroot)
        """
        cwd = os.getcwd()
        path = os.path.join(cwd, "webroot", (self.path.replace("/", "\\")).lstrip("\\"))
        return path

    @abstractmethod
    def handle(self):
        """Customised method that handles the request it is called when the handler serves a request see serve(self):"""
        raise NotImplementedError

    @abstractmethod
    def validate(self):
        """determines if Handler can handle request and returns boolean value"""
        raise NotImplementedError

    def build(self, data):
        """A class tool that creates the content based on resource data and a 'map' of substitutions"""
        page = data
        build = Template(page)
        return build.substitute(DefaultMap(self.context))

    def submit(self, data, code=500, headers: list[tuple] = None):
        """send headers and final data"""
        if headers is None:
            headers = []  # defaults to empty list
        self.context.send_response(code)  # send response code
        self.context.send_header("Content-type", self.content)  # send MIME type header
        for _ in headers:
            self.context.send_header(*_)  # send other headers as defined by subclasses
        self.context.end_headers()
        self.context.wfile.write(data)  # send final data ending the response

    @staticmethod
    def load_binary(filename):
        """class tool that loads a file as binary"""
        with open(filename, 'rb') as file_handle:
            return file_handle.read()

    @staticmethod
    def load_string(filename):
        """class tool that loads a file as string"""
        with open(filename, 'r') as file_handle:
            return file_handle.read()

    def serve(self):
        """validate and handle"""
        if self.validate():
            print(
                f"Serving '{self.path}'{f" as '{self.context.path}'" if self.path != self.context.path else ""} from'" +
                f" {self.full_path}' to {self.context.client_address} using handler '{self.__class__.__name__}'")
            self.handle()
        else:
            raise HandlerValidationError(self)


class HTMLHandler(Handler):
    """handles html requests"""

    # MIME type
    content = "text/html"

    def build(self, data):
        """A tool that creates the content based on resource data and a 'map' of substitutions"""

        # structure substitutions
        structured_template = StructTemp(data)
        structured_data = structured_template.substitute(StructureMap(self.context))

        # variable substitutions
        var_replaced_template = VarTemp(structured_data)
        var_replaced_data = var_replaced_template.substitute(DefaultMap(self.context))

        return var_replaced_data.replace("webroot/", "")  # page links are sent to webroot (external) files

    def handle(self):
        data = self.load_string(self.full_path)  # loads file based on full path
        self.submit(code=200, data=bytes(self.build(data), "utf-8"))  # builds and sends data as bytes response code 200

    def validate(self):
        """This handler can server a request if it is a html file and its respective file exists"""
        return (self.path.endswith(".html")) and os.path.isfile(self.full_path)


class AdminHandler(HTMLHandler):
    """handles admin console"""

    def __init__(self, context: WebInterface, *args):
        # rewrite url to /admin/admin.htm
        super().__init__(context, "/admin/admin.htm")
        self.data_handler = args[0]

    def build(self, data):
        """A tool that creates the content based on resource data and a 'map' of substitutions"""

        # structure substitutions
        structured_template = StructTemp(data)
        structured_data = structured_template.substitute(StructureMap(self.context))

        # variable substitutions
        var_replaced_template = VarTemp(structured_data)
        var_replaced_data = var_replaced_template.substitute(DefaultMap(self.context))

        # metrics substitutions
        metr_replaced_template = MetrTemp(var_replaced_data)
        metr_replaced_data = metr_replaced_template.substitute(self.data_handler.metrics)

        # record substitutions
        record_replaced_template = RecordTemp(metr_replaced_data)
        record_replaced_data = record_replaced_template.substitute(RecordMap(self.data_handler))

        return record_replaced_data

    def validate(self):
        """This handler can server a request if it's htm (different from html) file and its respective file exists"""
        return (self.path.endswith(".htm")) and os.path.isfile(self.full_path)


class DirectoryHandler(HTMLHandler):
    """handles directory requests"""

    def __init__(self, context: WebInterface, path: str = None):
        # rewrite path to default to /index.html, and enable rewriting
        super().__init__(context, (path if path is not None else context.path) + "/index.html")


class ImageHandler(HTMLHandler):
    """simplifies creating image handlers as they all handle the same way"""

    def handle(self):
        data = self.load_binary(self.full_path)  # loads file based on full path
        self.submit(code=200, data=data, headers=[
            ("Expires", (datetime.now() + timedelta(minutes=10)).strftime('%a, %d %b %Y %H:%M:%S %Z'))
        ])  # sends file with response code 200, and adds expiry header so that client's cache the images for 10 minutes


class JPEGHandler(ImageHandler):
    """handles jpeg requests"""

    # MIME type
    content = "image/jpeg"

    def validate(self):
        """This handler can server a request if it is a jpeg file and its respective file exists"""
        return (self.path.endswith(".jpeg") or self.path.endswith(".jpg")) and os.path.isfile(self.full_path)


class PNGHandler(ImageHandler):
    """handles png requests"""

    # MIME type
    content = "image/png"

    def validate(self):
        """This handler can server a request if it is a png file and its respective file exists"""
        return self.path.endswith(".png") and os.path.isfile(self.full_path)


class ICOHandler(ImageHandler):
    content = "image/x-icon"

    def validate(self):
        """This handler can server a request if it is an icon file and its respective file exists"""
        return self.path.endswith(".ico") and os.path.isfile(self.full_path)


class StaticFileHandler(HTMLHandler):
    """simplifies creating static file handlers as they all handle the same way"""

    def handle(self):
        data = self.load_string(self.full_path)
        self.submit(code=200, data=bytes(data, "utf-8"), headers=[
            ("Expires", (datetime.now() + timedelta(minutes=10)).strftime('%a, %d %b %Y %H:%M:%S %Z'))
        ])


class CSSHandler(StaticFileHandler):
    content = "text/css"

    def validate(self):
        return self.path.endswith(".css") and os.path.isfile(self.full_path)


class JSHandler(StaticFileHandler):
    content = "text/javascript"

    def validate(self):
        return self.path.endswith(".js") and os.path.isfile(self.full_path)


class NotFoundHandler(HTMLHandler):
    def __init__(self, context: WebInterface):
        super().__init__(context, "/errors/404.html")

    def handle(self):
        data = self.load_string(self.full_path)  # loads file based on full path
        self.submit(code=404, data=bytes(self.build(data), "utf-8"))  # builds and sends data as bytes response code 200


class HandlerValidationError(Exception):
    # if a program tries to run a handler that is unable to handle a request
    def __init__(self, cause: Handler):
        super().__init__(f"Handler '{type(cause)}' is unable to create a response for {cause.path}")


class Map(dict[str, str]):
    """
    superclass to define the structure of a map
    Maps define the variable based substitutions to make on a webpage, they mock the behavior of dictionaries to
    manipulate the 'Template' class
    """

    def __init__(self, context: object):
        # create the false 'dictionary'
        super().__init__()
        # pull variable sources from calling object
        self._context = context

    # Python calls this function when retrieving dictionary items
    # "dictionary[item:str] ==> dictionary.__getitem__(item:str)"
    def __getitem__(self, item: str):
        """this executes a child class's function with the name 'item' example path in DefaultMap """
        return self.__getattribute__(item)() if not item.startswith(
            "_") else ""  # prevents retrieval of builtin attributes by bad html

    @staticmethod
    def _load_relative(path):
        """class tool that loads a file from webroot as string"""
        cwd = os.getcwd()
        path = os.path.join(cwd, "webroot", (path.replace("/", "\\")).lstrip("\\"))
        with open(path, 'r') as file_handle:
            return file_handle.read()

    @staticmethod
    def _load_project_file(path):
        """class tool that loads a file from project root as string"""
        cwd = os.getcwd()
        path = os.path.join(cwd, (path.replace("/", "\\")).lstrip("\\"))
        with open(path, 'r') as file_handle:
            return file_handle.read()


class StructureMap(Map):
    # map for loading structure components
    def navbar(self): return self._load_relative("/common/navbar.htm")

    def headers(self): return self._load_relative("/common/headers.htm")

    def footers(self): return self._load_relative("/common/footers.htm")

    def documentation(self): return self._load_project_file("/readme.md")


class DefaultMap(Map):
    """A default map to inject variables into html serverside"""

    # Inheriting the Map class's behavior in mocking dictionaries path(self) is executed when an instance of
    # DefaultMap is trying to retrieve an item e.g. DefaultMap["path"] ==> DefaultMap.path()'''
    _context: WebInterface

    def path(self): return self._context.path  # request path

    def invalid_pass(self):
        """display message if returning from failed admin access attempt"""
        return "<p style=\"color:red\">Invalid code, try again</p>" if self._context.invalid_pass else ""

    def submitted(self):
        """display message if returning from successful order submission request"""
        return "<p style=\"color:red\">Submitted order.</p>" if self._context.submitted else ""

    def title(self): return self._context.title  # website title

    @staticmethod
    def welcome(): return "Welcome"

    @staticmethod
    def home_message(): return "Interact with the navbar to create an order."

    def menu(self):
        """prepares menu items from menu dictionary in main via instance data handler"""
        global instance_data_handler
        html = ""
        template = self._load_relative("/common/menuitem.htm")
        for _ in instance_data_handler.products["menu"]:  # for every item in the menu
            var_replaced_template = VarTemp(template)  # load template html for an item
            html += var_replaced_template.substitute(ItemMap(_))  # substitute item information based off of menu values
        return html  # return bulk html


class ItemMap(Map):
    """data supplied to user for product information"""

    # context is a dictionary representing a product
    _context: dict

    def __init__(self, diction: dict):
        super().__init__(diction)

    def item_name(self): return self._context.get("name")

    def item_price(self): return "{:.2f}".format(self._context.get("price"))  # format price to 2 decimal places

    def item_id(self): return self._context.get("id")

    def item_description(self): return self._context.get("description")


class RecordMap(Map):
    """data supplied to admin listing recorded orders"""

    # context is
    _context: DataHandler

    def __init__(self, data_handler: DataHandler):
        super().__init__(data_handler)

    def records(self):
        """creates a html list of table entries and formats in bootstrap for the user"""
        __ = ""  # initiate a string to add to
        for _ in enumerate(self._context.metrics.get("records")):  # for each order record
            i, _ = _  # get list index and record

            # compile order items
            ___ = ""
            for key, value in _.get("order").items():
                if value > 0:  # ignore a product if the order didn't get any
                    ___ += f"{key}: {value}<br>"

            # time from epoch
            time_local = datetime.fromtimestamp(_.get("time"))

            # Table record formatted string
            __ += ("<tr%s><th scope='row'>%s</th>"+"<td>%s</td>"*7+"</tr>") % (
                (" class=\"table-success\""
                 if datetime.fromtimestamp(_.get("time")).date() == datetime.now().date() else ""),  # highlight today's
                i,  # index column
                _.get("member-id"),  # member id column
                ___,  # products column
                _.get("delivery"),  # delivery column
                _.get("subtotal"),  # subtotal column
                ("{:.0%}".format(_.get("discount"))),  # discount column
                _.get("total"),  # total column incl tax
                time_local.strftime('%Y-%m-%d %H:%M')  # datetime column
            )
        return __  # full record list as html table


class StructTemp(Template):
    """Template class for inserting large portions aka files, headers, navbar, etc"""
    delimiter = "$s-"


class VarTemp(Template):
    """Template class for inserting variables, like titles, numbers, usernames etc"""
    delimiter = "$v-"


class MetrTemp(Template):
    """Template class for inserting metrics information."""
    delimiter = "$m-"


class RecordTemp(Template):
    """Template class for inserting records information"""
    delimiter = "$r-"
