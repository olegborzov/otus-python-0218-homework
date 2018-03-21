#!/usr/bin/env python
# -*- coding: utf-8 -*-

from statistics import median


def analyze_log(log_urls, max_errors_percent, report_size):
    """
    Analyze parsed log_urls and prepare report_list
    """
    errors_percent = calc_errors_percent(log_urls)
    if errors_percent > max_errors_percent:
        msg = "Log errors limit exceeded. " \
              "Errors percent: {}, " \
              "max errors percent (from config): {}"
        raise Exception(
            msg.format(errors_percent, max_errors_percent)
        )

    report_list = prepare_report_list(log_urls, report_size)
    return report_list


def calc_log_rows_count(log_urls):
    good_rows_count = sum(len(u) for u in log_urls["urls_times"].values())
    return log_urls["errors"] + good_rows_count


def calc_sum_request_time(log_urls):
    return sum(
        sum(url_times) for url_times in log_urls["urls_times"].values()
    )


def calc_errors_percent(log_urls):
    errors_percent = log_urls["errors"] * 100 / calc_log_rows_count(log_urls)
    errors_percent = round(errors_percent, 3)
    return errors_percent


def prepare_report_list(log_urls, report_size):
    urls_report = []

    log_rows_count = calc_log_rows_count(log_urls)
    sum_request_time = calc_sum_request_time(log_urls)

    for url, url_times in log_urls["urls_times"].items():
        url_info = dict()

        url_info["url"] = url
        url_info["count"] = len(url_times)
        url_info["count_perc"] = round(
            url_info["count"] * 100 / log_rows_count, 3
        )

        url_info["time_sum"] = round(sum(url_times), 3)
        url_info["time_perc"] = round(
            url_info["time_sum"] * 100 / sum_request_time, 3
        )
        url_info["time_avg"] = round(
            url_info["time_sum"] / url_info["count"], 3
        )
        url_info["time_max"] = round(max(url_times), 3)
        url_info["time_med"] = round(median(url_times), 3)

        urls_report.append(url_info)

    urls_report = sorted(
        urls_report, key=lambda u: u["time_sum"], reverse=True
    )
    urls_report = urls_report[:report_size]

    return urls_report
