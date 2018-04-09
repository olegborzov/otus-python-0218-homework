# Examples:
# https://github.com/Nikolay-Lysenko/otus-python-2018-02/blob/master/otus_python_homeworks/hw_4/httpd.py
# https://gist.github.com/joncardasis/cc67cfb160fa61a0457d6951eff2aeae
# TODO: Дописать HTTPResponseGenerator
# TODO: Дописать HTTPServer.handle
# TODO: Дописать считывание аргументов, main (запуск в несколько потоков)

import os
import sys
import socket
import logging

from urllib.parse import urlparse, unquote


CHUNK_SIZE = 8192

OK = 200
NOT_FOUND = 404
INTERNAL_ERROR = 405
ERRORS = {
    OK: "OK",
    NOT_FOUND: "Not Found",
    INTERNAL_ERROR: "Internal Error"
}


class HTTPResponseGenerator:
    pass


class HTTPRequestParser:
    methods = ["GET", "HEAD"]

    @classmethod
    def parse(cls, request: str, root_dir: str):
        method = ""
        uri = ""
        try:
            method, uri, _ = request.split(" ")

            cls.validate_method(method)
            norm_uri = cls.validate_uri(uri, root_dir)
            if isinstance(norm_uri, int):
                return norm_uri, method, uri

            return OK, method, norm_uri
        except ValueError:
            return INTERNAL_ERROR, method, uri

    @classmethod
    def validate_method(cls, method: str):
        if method not in cls.methods:
            raise ValueError

    @classmethod
    def validate_uri(cls, uri: str, root_dir: str):
        try:
            if "../" in uri:
                return INTERNAL_ERROR

            # Normalize uri
            uri_path = urlparse(uri).path
            uri_path = unquote(uri_path).lstrip("/")
            uri_path = os.path.join(root_dir, uri_path)

            # Check if dir
            if os.path.isdir(uri_path):
                uri_path += "/"

            if uri_path.endswith("/"):
                uri_path = os.path.join(uri_path, "index.html")

            if not os.path.isfile(uri_path):
                return NOT_FOUND

            return uri_path
        except:
            return INTERNAL_ERROR


class HTTPServer:
    def __init__(self, port: str = 80, doc_root: str = "www",
                 max_connections:int = 5, chunk_size: int = CHUNK_SIZE):
        self.host = socket.gethostname().split(".")[0]
        self.port = port
        self.root = doc_root
        self.max_connections = max_connections
        self.chunk_size = chunk_size

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def start(self):
        try:
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)

            self.socket.bind((self.host, self.port))
        except (OSError, TypeError):
            logging.exception("Server don't start", exc_info=True)
            self.shutdown()
            sys.exit(1)

        logging.debug("Server started on {}:{}".format(self.host, self.port))

        self.listen()

    def shutdown(self):
        try:
            self.socket.shutdown(socket.SHUT_RDWR)
            logging.debug("Server's socket closed")
        except OSError:
            pass

    def listen(self):
        self.socket.listen(self.max_connections)

        while True:
            client_socket = None
            try:
                client_socket, client_addr = self.socket.accept()
                logging.debug("Request from {}".format(client_addr))
                self.handle(client_socket)
            except KeyboardInterrupt:
                raise
            except OSError:
                logging.debug("Can't handle request")
                if client_socket:
                    client_socket.close()

    def handle(self, client_socket: socket.socket):
        request = self.receive(client_socket)
        logging.debug("Received request: {}".format(request))

        code, method, uri = HTTPRequestParser.parse(request, self.root)
        return

    def receive(self, client_socket: socket.socket) -> str:
        result = ""

        while True:
            chunk = client_socket.recv(self.chunk_size)
            result += chunk
            if "\r\n\r\n" in result:
                break
            if not chunk:
                logging.debug("Got empty chunk")
                break

        result = result.split("\r\n\r\n")[0]
        return result

