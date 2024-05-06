import os
import ssl
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from string import Template
import abc
from urllib import parse
import hashlib

from main import DataHandler

instance_data_handler: DataHandler


class Web:

    def __init__(self, handler: DataHandler):
        self.handler = handler
        global instance_data_handler
        instance_data_handler = handler
        self.httpd = HTTPServer(("0.0.0.0", 4443), WebInterface)
        context = self._get_ssl_context("cert.pem", "key.pem")
        self.httpd.socket = context.wrap_socket(self.httpd.socket, server_side=True)

    @staticmethod
    def _get_ssl_context(certfile, keyfile):
        """Load certificates and define protocol and ciphers for HTTPS"""
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(certfile, keyfile)
        context.set_ciphers("@SECLEVEL=1:ALL")
        return context

    def begin_listen(self):

        print("Server started https://%s:%s" % ("127.0.0.1", 4443), f"handler test: {self.handler.test}")

        try:
            self.httpd.serve_forever()
        except KeyboardInterrupt:
            pass

        self.httpd.server_close()
        print("Server stopped.")


class WebInterface(BaseHTTPRequestHandler):
    invalidpass = False
    # ExtraExtraSauce
    admin_password = "170ac01abbaa03b17bfa0bdd6f2f0863"
    title = "Pizzaaaaaa Yoooooo"

    def do_GET(self):

        print(f"---{self.path}---")
        if self.path.endswith("/") and len(self.path) > 1:
            print("Redirect to " + self.path.rstrip("/"))
            self.send_response(307)
            self.send_header('Location', self.path.rstrip("/"))
            self.end_headers()
        else:
            _ = [HTMLHandler,
                 CSSHandler,
                 JSHandler,
                 DirectoryHandler,
                 JPEGHandler,
                 PNGHandler,
                 ICOHandler,
                 MP4Handler,
                 NotFoundHandler]
            for __ in _:
                ___ = __(self, self.path)
                if ___.valid:
                    ___.serve()
                    break
        print(f"---{self.path}---")

    def do_POST(self):
        global instance_data_handler
        if self.path == "/admin":
            length = int(self.headers.get('content-length'))
            field_data = self.rfile.read(length)
            fields = parse.parse_qs(str(field_data, "UTF-8"))
            passwd = fields.get("password1")[0].encode("UTF-8")
            md5 = hashlib.md5(passwd).hexdigest()
            print(md5)
            if md5 == self.admin_password:
                _ = AdminHandler(self, instance_data_handler)
            else:
                self.invalidpass = True
                _ = DirectoryHandler(self, self.path)
            _.serve()
        elif self.path == "/new":
            length = int(self.headers.get('content-length'))
            field_data = self.rfile.read(length)
            fields = parse.parse_qs(str(field_data, "UTF-8"))
            instance_data_handler.add_order(fields)
            self.do_GET()


class Handler:
    _data = ""

    def __init__(self, context: WebInterface, path: str):
        self.context = context
        self._path = path

    @property
    def valid(self):
        return self.validate()

    @property
    @abc.abstractmethod
    def content(self):
        pass

    @property
    def path(self):
        return self._path

    @property
    def full_path(self):
        cwd = os.getcwd()
        path = os.path.join(cwd, "webroot", (self.path.replace("/", "\\")).lstrip("\\"))
        return path

    @abc.abstractmethod
    def handle(self):
        raise NotImplementedError

    @abc.abstractmethod
    def validate(self):
        raise NotImplementedError

    @staticmethod
    def build(data, value_map):
        page = data
        build = Template(page)
        return build.substitute(value_map)

    def submit(self, data, code=404):

        self.context.send_response(code)
        self.context.send_header("Content-type", self.content)
        self.context.end_headers()
        self.context.wfile.write(data)

    @staticmethod
    def load_binary(filename):
        """load file as binary"""
        with open(filename, 'rb') as file_handle:
            return file_handle.read()

    @staticmethod
    def load_string(filename):
        """load file as string"""
        with open(filename, 'r') as file_handle:
            return file_handle.read()

    def serve(self):
        if self.validate():
            print(
                f"Serving '{self.path}'{f" as '{self.context.path}'" if self.path != self.context.path else ""} from '{self.full_path}' to {self.context.client_address} using handler '{self.__class__.__name__}'")
            self.handle()
        else:
            raise HandlerValidationError(self)


class HTMLHandler(Handler):
    content = "text/html"

    def __init__(self, context: WebInterface, path: str):
        super().__init__(context, path)

    def substitute(self, data):
        structured_template = StructTemp(data)
        structured_data = structured_template.substitute(StructureMap(self.context))
        var_replaced_template = VarTemp(structured_data)
        var_replaced_data = var_replaced_template.substitute(DefaultMap(self.context))
        return var_replaced_data

    def handle(self):
        data = self.load_string(self.full_path)
        self.submit(code=200, data=bytes(self.substitute(data), "utf-8"))

    def validate(self):
        if (self.path.endswith(".html")) and os.path.isfile(self.full_path):
            return True
        else:
            return False


class AdminHandler(HTMLHandler):
    def __init__(self, context: WebInterface, *args):
        super().__init__(context, "/admin/admin.htm")
        self.data_handler = args[0]

    def substitute(self, data):
        structured_template = StructTemp(data)
        structured_data = structured_template.substitute(StructureMap(self.context))
        var_replaced_template = VarTemp(structured_data)
        var_replaced_data = var_replaced_template.substitute(DefaultMap(self.context))
        metr_replaced_template = MetrTemp(var_replaced_data)
        metr_replaced_data = metr_replaced_template.substitute(self.data_handler.metrics)
        recr_replaced_template = RecrTemp(metr_replaced_data)
        recr_replaced_data = recr_replaced_template.substitute(RecrMap(self.data_handler))
        return recr_replaced_data

    def handle(self):
        data = self.load_string(self.full_path)
        self.submit(code=200, data=bytes(self.substitute(data), "utf-8"))

    def validate(self):
        if (self.path.endswith(".htm")) and os.path.isfile(self.full_path):
            return True
        else:
            return False


class DirectoryHandler(HTMLHandler):
    def __init__(self, context: WebInterface, path: str):
        super().__init__(context, (path + "/" if not path.endswith("/") else "") + "index.html")


class JPEGHandler(Handler):
    content = "image/jpeg"

    def handle(self):
        data = self.load_binary(self.full_path)
        self.submit(code=200, data=data)

    def validate(self):
        if (self.path.endswith(".jpeg") or self.path.endswith(".jpg")) and os.path.isfile(self.full_path):
            return True
        else:
            return False


class PNGHandler(Handler):
    content = "image/png"

    def handle(self):
        data = self.load_binary(self.full_path)
        self.submit(code=200, data=data)

    def validate(self):
        if (self.path.endswith(".png")) and os.path.isfile(self.full_path):
            return True
        else:
            return False


class ICOHandler(Handler):
    content = "image/x-icon"

    def handle(self):
        data = self.load_binary(self.full_path)
        self.submit(code=200, data=data)

    def validate(self):
        if (self.path.endswith(".ico")) and os.path.isfile(self.full_path):
            return True
        else:
            return False


class MP4Handler(Handler):
    content = "video/mp4"

    def handle(self):
        data = self.load_binary(self.full_path)
        self.submit(code=200, data=data)

    def validate(self):
        if (self.path.endswith(".mp4")) and os.path.isfile(self.full_path):
            return True
        else:
            return False


class CSSHandler(Handler):
    content = "text/css"

    def handle(self):
        data = self.load_string(self.full_path)
        self.submit(code=200, data=bytes(data, "utf-8"))

    def validate(self):
        if (self.path.endswith(".css") or self.path.endswith(".scss")) and os.path.isfile(self.full_path):
            return True
        else:
            return False


class JSHandler(Handler):
    content = "text/javascript"

    def handle(self):
        data = self.load_string(self.full_path)
        self.submit(code=200, data=bytes(data, "utf-8"))

    def validate(self):
        if (self.path.endswith(".js")) and os.path.isfile(self.full_path):
            return True
        else:
            return False


class NotFoundHandler(HTMLHandler):
    def __init__(self, context: WebInterface, path: str):
        super().__init__(context, "/errors/404.html")

    def handle(self):
        data = self.load_string(self.full_path)
        self.submit(code=200, data=bytes(self.substitute(data), "utf-8"))


class HandlerValidationError(Exception):
    def __init__(self, cause: Handler):
        super().__init__(f"Handler '{type(cause)}' is unable to create a response for {cause.path}")


class Map(dict[str, str]):
    """
    superclass to define the structure of a map
    Maps define the variable based substitutions to make on a webpage, they mock the behavior of dictionaries to
    manipulate the 'Template' class
    """

    def _insert(self, file):
        cwd = os.getcwd()
        path = os.path.join(cwd, "webroot", (file.replace("/", "\\")).lstrip("\\"))
        with open(path, 'r') as file_handle:
            return file_handle.read()

    def __init__(self, context: object):
        # create the false 'dictionary'
        super().__init__()
        # pull variable sources from calling object
        self.context = context

    # Python calls this function when retrieving dictionary items
    # "dictionary[item:str] ==> dictionary.__getitem__(item:str)"
    def __getitem__(self, item: str):
        """this executes a child class's function with the name 'item' example path in DefaultMap """
        return self.__getattribute__(item)() if not item.startswith(
            "_") else ""  # prevents retrieval of builtin attributes by bad html


class StructureMap(Map):
    def navbar(self):
        return self._insert("/common/navbar.html")

    def headers(self):
        return self._insert("/common/headers.html")

    def footers(self):
        return self._insert("/common/footers.html")


class DefaultMap(Map):
    """A default mapping 'Dictionary' to inject variables into html serverside"""

    # Inheriting the Map class's behavior in mocking dictionaries path(self) is executed when an instance of
    # DefaultMap is trying to retrieve an item e.g. DefaultMap["path"] ==> DefaultMap.path()'''
    context: WebInterface

    def path(self):
        """webAC is the RequestHandler in this context, thus self.webAC.path is the request path,
        example "/path/to/page\" """
        return self.context.path

    def welcome(self):
        return "Welcome"

    def homemessage(self):
        return "Interact with the navbar to create an order."

    def invalidpass(self):
        return "<p style=\"color:red\">Invalid code, try again</p>" if self.context.invalidpass else ""

    def menu(self):
        global instance_data_handler
        html = ""

        for _ in instance_data_handler.products["menu"]:
            var_replaced_template = VarTemp(self._insert("/common/menuitem.html"))
            html += var_replaced_template.substitute(ItemMap(_))
        return html

    def title(self):
        return self.context.title


class ItemMap(Map):
    def __init__(self, diction: dict):
        super().__init__(diction)

    def itemname(self):
        return self.context.get("name")

    def itemprice(self):
        return self.context.get("price")

    def itemid(self):
        return self.context.get("id")

    def itemdescription(self):
        return self.context.get("description")


class RecrMap(Map):
    context: DataHandler

    def __init__(self, diction: dict):
        super().__init__(diction)

    def records(self):
        __ = ""
        i = 1
        for _ in self.context.metrics.get("records"):
            ___ = ""
            for key, value in _.get("order").items():
                if value > 0:
                    ___ += f"{key}: {value}\n"

            __ += f"<tr>\
<th scope='row'>{i}</th>\
<td>{_.get("member-id")}</td>\
<td>{___}</td>\
<td>{_.get("delivery")}</td>\
<td>{_.get("subtotal")}</td>\
<td>{("{:.0%}".format(_.get("discount")))}</td>\
<td>{_.get("total")}</td>\
<td>{time.strftime('%Y-%m-%d %H:%M', time.gmtime(_.get("time") + 3600 * 8))}</td>\
</tr>"
            i += 1
        return __


class StructTemp(Template):
    """Template class for inserting large portions aka files, headers, navbar, etc"""
    delimiter = "$s-"


class VarTemp(Template):
    """Template class for inserting variables, like titles, numbers, usernames etc"""
    delimiter = "$v-"


class MetrTemp(Template):
    """Template class for inserting metrics information."""
    delimiter = "$m-"


class RecrTemp(Template):
    """Template class for inserting records information"""
    delimiter = "$r-"
