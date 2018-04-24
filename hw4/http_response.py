# -*- coding: utf-8 -*-
"""
HTTP response maker for methods GET and POST
"""

import os
import mimetypes
from datetime import datetime
from time import mktime
from email.utils import formatdate
from collections import OrderedDict
from typing import Union

from config import *


def generate_response(code: int, method: str, uri: str) -> bytes:
    """
    :return: response in byte format
    """
    response = "{status_line}\r\n{headers}\r\n\r\n".format(
        status_line=generate_start_line(code),
        headers=generate_headers(uri)
    )
    response = response.encode(encoding="UTF-8")

    body = generate_body(code, method, uri)
    if body:
        response += body

    return response


def generate_start_line(code: int) -> str:
    return "{proto} {code} {msg}".format(
        proto=PROTOCOL,
        code=code,
        msg=ERRORS[code]
    )


def generate_headers(uri: str) -> str:
    headers = OrderedDict({
        "Date": get_date(),
        "Server": "Otus-Python-HW04",
        "Content-Length": get_file_size(uri),
        "Content-Type": mimetypes.guess_type(uri)[0],
        "Connection": "close"
    })
    headers = "\r\n".join("{}: {}".format(k, v) for k, v in headers.items())
    return headers


def generate_body(code: int, method: str, uri: str,
                  retry: int = 0) -> Union[bytes, None]:
    try:
        if code == OK and method != "GET":
            return None

        with open(uri, "rb") as file:
            body = file.read()

        return body
    except OSError:
        if retry < 5:
            return generate_body(code, method, uri, retry+1)
        raise


def get_date() -> str:
    """
    :return: current datetime in RFC-1123 format
    """
    now = datetime.utcnow()
    weekday = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][now.weekday()]
    month = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep",
             "Oct", "Nov", "Dec"][now.month - 1]
    rfc_fmt_dt = "%s, %02d %s %04d %02d:%02d:%02d GMT" % (
        weekday, now.day, month, now.year, now.hour, now.minute, now.second
    )
    return rfc_fmt_dt


def get_file_size(uri: str, retry:int = 0) -> int:
    try:
        return os.path.getsize(uri)
    except OSError:
        if retry < 5:
            return get_file_size(uri, retry+1)
        raise

