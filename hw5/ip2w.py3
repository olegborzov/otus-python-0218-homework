# -*- coding: utf-8 -*-
"""
Test uWSGI
"""

import time
import json
import ipaddress
import logging
import logging.handlers
from configparser import ConfigParser
from typing import Dict, Union, Tuple

import requests

OK = 200
BAD_REQUEST = 400
INTERNAL_ERROR = 500

CONFIG_PATH = "/usr/local/etc/ip2w.ini"


def get_weather_info(ip: str, config: Dict) -> Tuple[int, Union[Dict, str]]:
    if not validate_ip(ip):
        code = BAD_REQUEST
        msg = "Wrong ip. Please provide a valid IP address"
        return code, msg

    code, city_answer = get_city_from_ip(ip, config)
    if code != OK:
        return code, city_answer

    code, weather_info = get_weather_by_city(city_answer, config)
    return code, weather_info


def validate_ip(ip: str) -> bool:
    try:
        ipaddress.IPv4Address(ip)
        return True
    except ipaddress.AddressValueError:
        return False


def get_city_from_ip(ip: str,
                     config: Dict,
                     retry: int = 0) -> Tuple[int, str]:
    try:
        url = "https://ipinfo.io/" + ip
        res = requests.get(url, timeout=config["timeout"])
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
        if retry < config["max_retries"]:
            time.sleep(1)
            return get_city_from_ip(ip, config, retry+1)
        return INTERNAL_ERROR, "Requests retries to ipinfo.io exceeded"


def get_weather_by_city(city: str,
                        config: Dict,
                        retry: int = 0) -> Tuple[int, Union[Dict, str]]:
    try:
        url = "http://api.openweathermap.org/data/2.5/" \
              "weather?q={city}&units=metric&lang=ru&appid={api_key}"
        url = url.format(
            city=city,
            api_key=config["owm_api_key"]
        )

        res = requests.get(url, timeout=config["timeout"])
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
        if retry < config["max_retries"]:
            time.sleep(1)
            return get_weather_by_city(city, config, retry+1)

        err_msg = "Requests retries to api.openweathermap.org exceeded"
        return INTERNAL_ERROR, err_msg


def set_logging(log_path: str, log_level: int = logging.INFO):
    # File handler
    file_handler = logging.FileHandler(filename=log_path, encoding="UTF-8")

    logging.basicConfig(
        handlers=[file_handler],
        level=log_level,
        format='%(asctime)s %(levelname)s '
               '{%(pathname)s:%(lineno)d}: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )


def read_config() -> Dict:
    config = ConfigParser()
    config.read(CONFIG_PATH)
    config = dict(config["ip2w"])
    config["max_retries"] = int(config["max_retries"])
    config["timeout"] = float(config["timeout"])

    return config


def application(environ, start_response):
    config = read_config()
    set_logging(config["log_path"])

    request = environ['PATH_INFO'].strip('/').split('/')
    try:
        ip = request[1]
    except IndexError:
        ip = environ['REMOTE_ADDR']

    logging.info("Request: {}".format(ip))

    code, response = get_weather_info(ip, config)
    logging.info("Response: {}, {}".format(code, response))
    if not isinstance(response, str):
        response = json.dumps(response, ensure_ascii=False, indent="\t")
    response = response.encode(encoding="UTF-8")

    start_response(str(code), [
        ('Content-Type', 'application/json; charset=UTF-8'),
        ('Content-Length', str(len(response))),
    ])
    return [response]
