# -*- coding: utf-8 -*-
"""
Test uWSGI
"""

import os
import time
import json
import ipaddress
import logging
import logging.handlers
from typing import Dict, Union, Tuple

import requests

# TODO: Конфиг файл (в папке /usr/local/etc/)

OK = 200
BAD_REQUEST = 400
INTERNAL_ERROR = 500

MAX_RETRIES = os.environ.get("MAX_RETRIES", 3)
TIMEOUT = os.environ.get("TIMEOUT", 3)
OWM_API_KEY = os.environ.get("OWM_API_KEY", "92ad6b11cd73fb8367b03e1e8ac10701")


def get_weather_info(ip: str) -> Tuple[int, Union[Dict, str]]:
    if not validate_ip(ip):
        code = BAD_REQUEST
        msg = "Wrong ip. Please provide a valid IP address"
        logging.info(code, msg)
        return code, msg

    code, city_answer = get_city_from_ip(ip)
    if code != OK:
        logging.info(code, city_answer)
        return code, city_answer

    code, weather_info = get_weather_by_city(city_answer)
    logging.info(code, city_answer)
    return code, weather_info


def validate_ip(ip: str) -> bool:
    try:
        ipaddress.IPv4Address(ip)
        return True
    except ipaddress.AddressValueError:
        return False


def get_city_from_ip(ip: str, retry=0) -> Tuple[int, str]:
    try:
        res = requests.get("https://ipinfo.io/" + ip, timeout=TIMEOUT)
        res.raise_for_status()
        res = res.json()

        if "error" in res:
            err_msg = "{}. {}".format(
                res["error"]["title"], res["error"]["message"]
            )
            return BAD_REQUEST, err_msg
        if not("city" in res and "country" in res):
            return INTERNAL_ERROR, "Unrecognized error"
        else:
            return OK, "{},{}".format(res["city"], res["country"])
    except requests.RequestException:
        if retry < MAX_RETRIES:
            time.sleep(1)
            return get_city_from_ip(ip, retry+1)
        return INTERNAL_ERROR, "Requests retries to ipinfo.io exceeded"


def get_weather_by_city(city: str, retry=0) -> Tuple[int, Union[Dict, str]]:
    try:
        url = "http://api.openweathermap.org/data/2.5/" \
              "weather?q={city}&units=metric&lang=ru&appid={api_key}"
        url = url.format(
            city=city,
            api_key=OWM_API_KEY
        )

        res = requests.get(url, timeout=TIMEOUT)
        res.raise_for_status()
        res = res.json()

        if "cod" not in res:
            return INTERNAL_ERROR, "Unrecognized error"
        result_code = int(res["cod"])
        if result_code == OK:
            temp = str(res["main"]["temp"])
            if not temp.startswith("-"):
                temp = "+" + temp
            conditions = ", ".join(
                [cond["description"] for cond in res["weather"]]
            )
            res = {
                "city": res["name"],
                "temp": temp,
                "conditions": conditions
            }
            return OK, res
        else:
            return result_code, res["message"]
    except requests.RequestException:
        if retry < MAX_RETRIES:
            time.sleep(1)
            return get_weather_by_city(city, retry+1)

        err_msg = "Requests retries to api.openweathermap.org exceeded"
        return INTERNAL_ERROR, err_msg


def set_logging(log_path: str, log_level: int = logging.INFO):
    # File handler
    file_handler = logging.handlers.RotatingFileHandler(
        filename=log_path, maxBytes=1000000, backupCount=3, encoding="UTF-8"
    )
    stream_handler = logging.StreamHandler()

    logging.basicConfig(
        handlers=[stream_handler, file_handler],
        level=log_level,
        format='%(asctime)s %(levelname)s '
               '{%(pathname)s:%(lineno)d}: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )


def application(environ, start_response):
    set_logging("/")

    request = environ['PATH_INFO'].strip('/').split('/')
    try:
        ip = request[1]
    except IndexError:
        ip = environ['REMOTE_ADDR']

    code, response = get_weather_info(ip)
    if not isinstance(response, str):
        response = json.dumps(response, ensure_ascii=False, indent="\t")
    response = response.encode(encoding="UTF-8")

    start_response(str(code), [
        ('Content-Type', 'application/json; charset=UTF-8'),
        ('Content-Length', str(len(response))),
    ])
    return [response]
