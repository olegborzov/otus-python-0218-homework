#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import argparse
import json
import logging
from datetime import datetime

import log_parser
import log_analyzer
import report_generator

# log_format ui_short '$remote_addr $remote_user '
#                     '$http_x_real_ip [$time_local] "$request" '
#                     '$status $body_bytes_sent "$http_referer" '
#                     '"$http_user_agent" "$http_x_forwarded_for"'
#                     '"$http_X_REQUEST_ID" "$http_X_RB_USER" '
#                     '$request_time';

DEFAULT_CONFIG = {
    "REPORT_SIZE": 1000,
    "REPORT_DIR": "./reports",
    "LOG_DIR": "./log",
    "LOG_RESULT_DIR": "./log_result",
    "TS_DIR": "./",
    "MAX_LOG_ERRORS_PERCENT": 25
}
DEFAULT_CONFIG_PATH = "./config.json"


def get_config_path_from_args(default_config_path):
    """
    Setup args for command line, read args
    :param default_config_path: path to default config file
    :return: path to config file
    """
    parser = argparse.ArgumentParser()
    help_msg = "path to config file, example: /home/me/config.json"
    parser.add_argument("-c", "--config", type=str, help=help_msg)
    args = parser.parse_args()

    config_path = args.config if args.config else default_config_path
    return config_path


def parse_config(path, default_config):
    """
    Parse config from json file by path
    and concatenate with default config
    :return: result config
    """
    with open(path) as f:
        config = json.load(f)

    if not isinstance(config, dict):
        raise json.JSONDecodeError("It's not a dict")

    if not config:
        return default_config

    for k in default_config.keys():
        if k in config:
            default_config[k] = config[k]

    return default_config


def set_logging(log_dir):
    """
    Set logging config - to file if is set log_dir, else - to stdout
    """
    log_file = None

    if log_dir and os.access(log_dir, os.W_OK):
        log_file_name = datetime.now().strftime(
            "log_analyzer_%Y%m%d_%H%M%S.log"
        )
        log_file = os.path.join(log_dir, log_file_name)

    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format='[%(asctime)s] %(levelname).1s %(message)s',
        datefmt='%Y.%m.%d %H:%M:%S',
    )


def update_ts(ts_dir):
    """
    Update timestamp file
    :param ts_dir: path to dir, where ts file will be stored
    """
    ts_path = os.path.join(ts_dir, "log_analyzer.ts")

    now = datetime.now()
    timestamp = int(now.timestamp())
    with open(ts_path, "w", encoding="UTF-8") as f:
        f.write(str(timestamp))

    os.utime(ts_path, times=(timestamp, timestamp))


def main():
    try:
        # 1. Prepare
        set_logging(None)

        config_path = get_config_path_from_args(DEFAULT_CONFIG_PATH)
        config = parse_config(config_path, DEFAULT_CONFIG)

        set_logging(config["LOG_RESULT_DIR"])

        # 2. Parse log
        last_log_file_info = log_parser.get_newest_log_file(config["LOG_DIR"])
        if not last_log_file_info["filepath"]:
            log_msg = "No log file found in dir {}"
            logging.info(log_msg.format(
                config["LOG_DIR"])
            )
            return

        if report_generator.report_by_date_exists(
                last_log_file_info["date"], config["REPORT_DIR"]
        ):
            log_msg = "Report for {} already exists"
            logging.info(log_msg.format(
                last_log_file_info["date"])
            )
            return

        log_urls = log_parser.parse_log_file(last_log_file_info["filepath"])
        if not log_urls:
            log_msg = "Log file ({}) is empty"
            logging.info(log_msg.format(
                last_log_file_info["filepath"])
            )
            return

        log_msg = "Parsed {lines} lines, {urls} urls from log file"
        logging.info(log_msg.format(
            lines=log_analyzer.calc_log_rows_count(log_urls),
            urls=len(log_urls["urls_times"])
        ))

        # 3. Analyze log
        report_list = log_analyzer.analyze_log(
            log_urls, config["MAX_LOG_ERRORS_PERCENT"], config["REPORT_SIZE"]
        )
        log_msg = "Log has been analyzed"
        logging.info(log_msg)

        # 4. Generate report
        report_path = report_generator.save_report_html(
            report_list, last_log_file_info["date"], config["REPORT_DIR"]
        )

        update_ts(config["TS_DIR"])

        log_msg = "Log file ({log_path}) parsed succesfully. " \
                  "Created report file - {report_path}"
        logging.info(log_msg.format(
            log_path=last_log_file_info["filepath"],
            report_path=report_path
        ))
    except Exception as ex:
        msg = "{0}: {1}".format(type(ex).__name__, ex)
        logging.exception(msg, exc_info=True)
        raise


if __name__ == "__main__":
    main()
