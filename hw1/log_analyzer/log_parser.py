#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import gzip
from datetime import datetime


def parse_log_file(log_path):
    """
    Parse log file and prepare dict for analyze
    """
    is_gzipped = log_path.endswith(".gz")

    if is_gzipped:
        opener = gzip.open(log_path, "r")
    else:
        opener = open(log_path, "r", encoding="UTF-8")

    log_urls = {"errors": 0, "urls_times": {}}

    with opener:
        for line in opener:

            if is_gzipped:
                line = line.decode("UTF-8")

            line_parsed = parse_log_line(line)

            if line_parsed["is_error"]:
                log_urls["errors"] += 1
            else:
                if line_parsed["url"] not in log_urls["urls_times"]:
                    log_urls["urls_times"][line_parsed["url"]] = []

                log_urls["urls_times"][line_parsed["url"]].append(
                    line_parsed["request_time"]
                )

    return log_urls


def parse_log_line(line):
    """
    Parse url and request time from log line
    """
    log_info = {"url": "", "is_error": True, "request_time": 0}

    regex = re.compile(r"\"[A-Z]+ ([^\s]+) .* (\d+\.\d+)\n")
    parsed_line = re.findall(regex, line)

    if not parsed_line:
        return log_info

    log_info["url"] = parsed_line[0][0]
    log_info["request_time"] = float(parsed_line[0][1])

    if log_info["url"] and log_info["request_time"]:
        log_info["is_error"] = False

    return log_info


def get_newest_log_file(log_dir):
    """
    Get newest ui_log file in log_dir
    """
    fileslist = os.listdir(log_dir)
    last_log = get_newest_file_from_list(fileslist, log_dir)

    return last_log


def get_newest_file_from_list(fileslist, log_dir):
    last_log = {"date": None, "filepath": None}
    for filename in fileslist:
        log_date = get_log_file_date(filename)
        if log_date:
            if not last_log["date"] or log_date > last_log["date"]:
                last_log["date"] = log_date
                last_log["filepath"] = os.path.join(log_dir, filename)

    return last_log


def get_log_file_date(filename):
    """
    Get date from log filename
    """
    log_date = None

    try:
        regex = re.compile(r"nginx-access-ui\.log-(\d{8})(\.gz)?")
        log_date_str = re.findall(regex, filename)

        if log_date_str:
            log_date = datetime.strptime(
                log_date_str[0][0], "%Y%m%d"
            ).date()

        return log_date
    except ValueError:
        return log_date
