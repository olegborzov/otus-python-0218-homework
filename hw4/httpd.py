# -*- coding: utf-8 -*-

"""
HTTP server with implemented methods GET and HEAD
"""


import os
import sys
import socket
import logging
import logging.handlers
import argparse
import threading
import multiprocessing
import re
from urllib.parse import unquote
from typing import Tuple

from http_response import generate_response
from config import *


class HTTPRequestParser:
    methods = ["GET", "HEAD"]

    @classmethod
    def parse(cls, request: str, root_dir: str) -> (int, str, str):
        """
        :param request: request str from client
        :param root_dir: path to dir with site files
        :return: (code, method, uri)
        """
        try:
            method, uri, *_ = request.split(" ")

            code = cls.validate_method(method)
            if code != OK:
                uri = cls.get_error_file_path(code)
                return code, method, uri

            code, uri = cls.validate_uri(uri, root_dir)
            if code != OK:
                uri = cls.get_error_file_path(code)

            return code, method, uri
        except ValueError:
            return INTERNAL_ERROR, "", ""

    @classmethod
    def validate_method(cls, method: str) -> int:
        if method not in cls.methods:
            return METHOD_NOT_ALLOWED
        return OK

    @classmethod
    def unquote_uri(cls, uri: str) -> str:
        global HEXTOBYTE
        if HEXTOBYTE is None:
            HEXTOBYTE = {
                ("%" + a + b).encode(): bytes([int(a + b, 16)])
                for a in HEXDIG for b in HEXDIG
            }

        uri_encoded = uri.encode()
        for match, sub in HEXTOBYTE.items():
            uri_encoded = uri_encoded.replace(match, sub)

        return uri_encoded.decode(errors="replace")

    @classmethod
    def normalize_uri(cls, uri: str, root_dir: str) -> (int, str):
        if "../" in uri:
            return FORBIDDEN, uri

        # Split ? and #
        uri_path = uri.split("#")[0].split("?")[0]

        # Validate uri
        uri_pattern = r"^\/[\/\.a-zA-Z0-9\-\_\%]+$"
        if not re.match(uri_pattern, uri_path):
            return BAD_REQUEST, uri

        uri_path = cls.unquote_uri(uri_path).lstrip("/")
        uri_path = os.path.join(root_dir, uri_path)
        return OK, uri_path

    @classmethod
    def validate_uri(cls, uri: str, root_dir: str) -> (int, str):
        try:
            code, uri_path = cls.normalize_uri(uri, root_dir)
            if code != OK:
                return code, uri_path

            # Check if path is dir
            if os.path.isdir(uri_path) and not uri_path.endswith("/"):
                uri_path += "/"

            if uri_path.endswith("/"):
                uri_path = os.path.join(uri_path, "index.html")
                if not os.path.isfile(uri_path):
                    return FORBIDDEN, uri_path

            # Check if path exists
            if not os.path.isfile(uri_path):
                return NOT_FOUND, uri_path

            return OK, uri_path
        except (TypeError, ValueError):
            return INTERNAL_ERROR, uri

    @classmethod
    def get_error_file_path(cls, code: int) -> str:
        error_file_name = "{}.html".format(code)
        dir_path = os.path.dirname(os.path.abspath(__file__))
        dir_path = os.path.abspath(os.path.join(dir_path, "error_pages"))
        file_path = os.path.abspath(os.path.join(dir_path, error_file_name))
        return file_path


class HTTPServer:
    def __init__(self, host: str = "localhost", port: str = 8099,
                 doc_root: str = "www", max_connections: int = 5,
                 chunk_size: int = CHUNK_SIZE):
        self.host = host
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
            logging.error("Server don't start", exc_info=True)
            self.shutdown()
            sys.exit(1)

        logging.info("Server started on {}:{}".format(self.host, self.port))
        self.socket.listen(self.max_connections)

    def shutdown(self):
        try:
            self.socket.shutdown(socket.SHUT_RDWR)
            logging.info("Server's socket closed")
        except OSError:
            return

    def listen(self):
        try:
            while True:
                client_socket = None
                client_addr = ""
                try:
                    client_socket, client_addr = self.socket.accept()
                    logging.debug("Request from {}".format(client_addr))
                    client_handler = threading.Thread(
                        target=self.handle,
                        args=(client_socket, client_addr)
                    )
                    client_handler.start()
                except OSError:
                    logging.warning("Can't handle request from {}".format(
                        client_addr
                    ))
                    if client_socket:
                        client_socket.close()
        finally:
            self.shutdown()

    def handle(self, client_socket: socket.socket, client_addr: Tuple):
        try:
            request = self.receive(client_socket)
            if not request:
                logging.warning("Empty request from {}".format(client_addr))
                return
            logging.debug("Request from {}. Status_line: {}".format(
                client_addr, request.split("\n")[0]
            ))

            code, method, uri = HTTPRequestParser.parse(request, self.root)
            if code != OK:
                uri = "error_pages/{}.html".format(code)

            response = generate_response(code, method, uri)
            client_socket.sendall(response)
            logging.debug("Send response to {}: {}, {}, {}".format(
                client_addr, code, method, uri
            ))
        except ConnectionError:
            err_msg = "Can't send response to {}".format(client_addr)
            logging.exception(err_msg)
        finally:
            client_socket.close()

    def receive(self, client_socket: socket.socket) -> str:
        result = ""
        try:
            while True:
                chunk = client_socket.recv(self.chunk_size)
                result += chunk.decode()
                if "\r\n\r\n" in result:
                    break
                if not chunk:
                    break
        except ConnectionError:
            pass

        return result


def set_logging(logging_level: int = logging.INFO):
    # Stream handler
    stream_handler = logging.StreamHandler()

    logging.basicConfig(
        handlers=[stream_handler],
        level=logging_level,
        format='%(asctime)s %(levelname)s '
               '{%(pathname)s:%(lineno)d}: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )


def parse_args():
    parser = argparse.ArgumentParser(description='HTTP server OTUS')

    parser.add_argument(
        '-hs', '--host', type=str, default="localhost",
        help='listened host, default - localhost'
    )
    parser.add_argument(
        '-p', '--port', type=int, default=8099,
        help='listened port, default - 8099'
    )
    parser.add_argument(
        '-w', '--workers', type=int, default=5,
        help='server workers count, default - 5'
    )
    parser.add_argument(
        '-r', '--root', type=str, default='doc_root',
        help='DIRECTORY_ROOT with site files, default - doc_root'
    )

    return parser.parse_args()


if __name__ == '__main__':
    set_logging(logging.DEBUG)
    args = parse_args()
    server = HTTPServer(host=args.host, port=args.port, doc_root=args.root)
    server.start()

    workers = []
    try:
        for i in range(args.workers):
            worker = multiprocessing.Process(target=server.listen)
            workers.append(worker)
            worker.start()
            logging.info("{} worker started".format(i+1))
        for worker in workers:
            worker.join()
    except KeyboardInterrupt:
        for worker in workers:
            if worker:
                worker.terminate()
    finally:
        logging.info("Server shutdown")
        server.shutdown()
