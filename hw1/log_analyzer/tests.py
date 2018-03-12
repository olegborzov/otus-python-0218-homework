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


class TestGetNewestLogFile(unittest.TestCase):
    def test_empty_fileslist(self):
        fileslist = []
        log_dir = "/"

        result = log_parser.get_newest_file_from_list(fileslist, log_dir)
        expected_result = {"date": None, "filepath": None}
        self.assertEqual(expected_result, result)

    def test_list_without_ui_log(self):
        fileslist = ["main.py", "readme.txt", "apache-access-ui.log-20170630"]
        log_dir = "/"

        result = log_parser.get_newest_file_from_list(fileslist, log_dir)
        expected_result = {"date": None, "filepath": None}
        self.assertEqual(expected_result, result)

    def test_two_files_with_equal_dates(self):
        fileslist = ["main.py", "nginx-access-ui.log-20170630.gz", "nginx-access-ui.log-20170630"]
        log_dir = "/"

        result = log_parser.get_newest_file_from_list(fileslist, log_dir)
        expected_result = [
            {'date': date(2017, 6, 30), 'filepath': '/nginx-access-ui.log-20170630.gz'},
            {'date': date(2017, 6, 30), 'filepath': '/nginx-access-ui.log-20170630'}
        ]
        self.assertIn(result, expected_result)

    def test_good_case(self):
        fileslist = ["main.py", "readme.txt", "nginx-access-ui.log-20170630"]
        log_dir = "/"

        result = log_parser.get_newest_file_from_list(fileslist, log_dir)
        expected_result = {'date': date(2017, 6, 30), 'filepath': '/nginx-access-ui.log-20170630'}
        self.assertEqual(expected_result, result)


class TestParseLogLine(unittest.TestCase):
    def test_empty_line(self):
        log_line = ""

        result_expected = {"url": "", "is_error": True, "request_time": 0}
        result = log_parser.parse_log_line(log_line)
        self.assertEqual(result, result_expected)

    def test_bad_time(self):
        log_line = '1.194.135.240 -  - [29/Jun/2017:10:15:45 +0300] ' \
                   '"HEAD /slots/3938/ HTTP/1.1" 302 0 "-" ' \
                   '"Microsoft Office Excel 2013" "-" "1498720545-244168387-4707-10016820" "-" 0.ABC0'

        result_expected = {"url": "", "is_error": True, "request_time": 0}
        result = log_parser.parse_log_line(log_line)
        self.assertEqual(result, result_expected)

    def test_good_case(self):
        log_line = '1.196.116.32 -  - [29/Jun/2017:03:50:22 +0300] ' \
                   '"GET /test HTTP/1.1" 200 927 "-" "-" "-" "-" "-" 0.390'

        result_expected = {"url": "/test", "is_error": False, "request_time": 0.39}
        result = log_parser.parse_log_line(log_line)
        self.assertEqual(result, result_expected)


if __name__ == '__main__':
    unittest.main()
