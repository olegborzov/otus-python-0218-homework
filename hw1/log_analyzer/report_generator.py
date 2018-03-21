import os
import re
import json
from datetime import datetime


def save_report_html(report_list, report_date, report_dir):
    """
    Prepare and save report file in report_dir
    """
    report_name = report_date.strftime("report-%Y.%m.%d.html")
    report_path = os.path.join(report_dir, report_name)

    with open("report.html", encoding="UTF-8") as f:
        report_template = f.read()

    table_json = json.dumps(report_list)
    report_template = report_template.replace("$table_json", table_json)

    with open(report_path, "w", encoding="UTF-8") as f:
        f.write(report_template)

    return report_path


def report_by_date_exists(log_date, report_dir):
    """
    Check if report for log_date exist in report_dir
    """

    for filename in os.listdir(report_dir):
        if compare_report_date_with_log_date(filename, log_date):
            return True

    return False


def compare_report_date_with_log_date(filename, log_date):
    """
    Check if date from report filename and log_date are equal
    """
    report_date = None

    regex = re.compile(r"report-(\d{4}\.\d{2}\.\d{2})\.html")
    report_date_str = re.findall(regex, filename)
    if report_date_str:
        report_date = datetime.strptime(report_date_str[0], "%Y.%m.%d").date()

    return log_date == report_date
