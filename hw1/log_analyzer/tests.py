import unittest
from datetime import date

import log_parser


class TestGetLogFileDate(unittest.TestCase):
    def test_plain_good_format_date(self):
        filename = "nginx-access-ui.log-20180305"
        log_date = log_parser.get_log_file_date(filename)
        self.assertEqual(log_date, date(2018, 3, 5))

    def test_gz_good_format_date(self):
        filename = "nginx-access-ui.log-20180305.gz"
        log_date = log_parser.get_log_file_date(filename)
        self.assertEqual(log_date, date(2018, 3, 5))

    def test_empty_filename(self):
        filename = ""
        log_date = log_parser.get_log_file_date(filename)
        self.assertEqual(log_date, None)

    def test_bad_filename_format(self):
        filename = "bad-filename-format-20180305"
        log_date = log_parser.get_log_file_date(filename)
        self.assertEqual(log_date, None)

    def test_plain_bad_format_date(self):
        filename = "nginx-access-ui.log-2017.06.30"
        log_date = log_parser.get_log_file_date(filename)
        self.assertEqual(log_date, None)

    def test_plain_bad_day(self):
        filename = "nginx-access-ui.log-20180239"
        log_date = log_parser.get_log_file_date(filename)
        self.assertEqual(log_date, None)

    def test_plain_bad_month(self):
        filename = "nginx-access-ui.log-20181320"
        log_date = log_parser.get_log_file_date(filename)
        self.assertEqual(log_date, None)

    def test_plain_bad_year(self):
        filename = "nginx-access-ui.log-00001320"
        log_date = log_parser.get_log_file_date(filename)
        self.assertEqual(log_date, None)


class TestParseLogLine(unittest.TestCase):
    def test_empty_line(self):
        log_line = ""

        log_info_good = {"url": "", "is_error": True, "request_time": 0}
        log_info_res = log_parser.parse_log_line(log_line)
        self.assertEqual(log_info_res, log_info_good)

    def test_bad_time(self):
        log_line = '1.194.135.240 -  - [29/Jun/2017:10:15:45 +0300] ' \
                   '"HEAD /slots/3938/ HTTP/1.1" 302 0 "-" ' \
                   '"Microsoft Office Excel 2013" "-" ' \
                   '"1498720545-244168387-4707-10016820" "-" 0.ABC0'

        log_info_good = {"url": "", "is_error": True, "request_time": 0}
        log_info_res = log_parser.parse_log_line(log_line)
        self.assertEqual(log_info_res, log_info_good)


if __name__ == '__main__':
    unittest.main()
