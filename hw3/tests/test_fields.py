# -*- coding: utf-8 -*-

from datetime import date
from dateutil.relativedelta import relativedelta

import pytest

from .. import api


class TestCharField(object):
    @pytest.mark.parametrize("value", [
        "test",
        ""
    ])
    def test_valid_value(self, value):
        api.CharField().validate(value)

    @pytest.mark.parametrize("value,exc_type,exc_msg", [
        (None, TypeError, 'Value type must be str'),
        (1, TypeError, 'Value type must be str'),
        ([1, 2, 3], TypeError, 'Value type must be str'),
    ])
    def test_not_valid_type(self, value, exc_type, exc_msg):
        with pytest.raises(exc_type, message=exc_msg):
            api.CharField().validate(value)


class TestArgumentsField(object):
    @pytest.mark.parametrize("value", [
        {"a": 1, "b": 2},
        {}
    ])
    def test_valid_value(self, value):
        api.ArgumentsField().validate(value)

    @pytest.mark.parametrize("value,exc_type,exc_msg", [
        (None, TypeError, 'Value type must be dict'),
        (1, TypeError, 'Value type must be dict'),
        ([1, 2, 3], TypeError, 'Value type must be dict'),
    ])
    def test_not_valid_type(self, value, exc_type, exc_msg):
        with pytest.raises(exc_type, message=exc_msg):
            api.ArgumentsField().validate(value)


class TestEmailField(object):
    @pytest.mark.parametrize("value", [
        "a@a.ru",
        "@a",
        "a@",
        "@"
    ])
    def test_valid_value(self, value):
        api.EmailField().validate(value)

    @pytest.mark.parametrize("value,exc_type,exc_msg", [
        (None, TypeError, 'Value type must be str'),
        (1, TypeError, 'Value type must be str'),
        ([1, 2, 3], TypeError, 'Value type must be str'),
    ])
    def test_not_valid_type(self, value, exc_type, exc_msg):
        with pytest.raises(exc_type, message=exc_msg):
            api.EmailField().validate(value)

    def test_not_valid_str_without_at_symbol(self):
        with pytest.raises(ValueError, message='Value must contain @ symbol'):
            api.EmailField().validate("bad_email")

    def test_not_valid_empty_str(self):
        with pytest.raises(ValueError, message='Value must contain @ symbol'):
            api.EmailField().validate("")


class TestPhoneField(object):
    @pytest.mark.parametrize("value", [
        70123456789,
        "70123456789",
        "7----------",
        "7-1-3-5-7-9"
    ])
    def test_valid_value(self, value):
        api.PhoneField().validate(value)

    @pytest.mark.parametrize("value,exc_type,exc_msg", [
        (None, TypeError, 'Value type must be str or int'),
        ({"a": 1}, TypeError, 'Value type must be str or int'),
        ([1, 2, 3], TypeError, 'Value type must be str or int'),
    ])
    def test_not_valid_type(self, value, exc_type, exc_msg):
        with pytest.raises(exc_type, message=exc_msg):
            api.PhoneField().validate(value)

    @pytest.mark.parametrize("value,exc_type,exc_msg", [
        (7, ValueError, 'Length of value must be 11 characters'),
        (70123456789000, ValueError, 'Length of value must be 11 characters'),
        ("7", ValueError, 'Length of value must be 11 characters'),
        ("7012345678900", ValueError, 'Length of value must be 11 characters'),
    ])
    def test_not_valid_wrong_length(self, value, exc_type, exc_msg):
        with pytest.raises(exc_type, message=exc_msg):
            api.PhoneField().validate(value)

    @pytest.mark.parametrize("value,exc_type,exc_msg", [
        (10123456789, ValueError, 'Value must start with 7'),
        ("10123456789", ValueError, 'Value must start with 7'),
    ])
    def test_not_valid_first_symbol_not_7(self, value, exc_type, exc_msg):
        with pytest.raises(exc_type, message=exc_msg):
            api.PhoneField().validate(value)


class TestDateField(object):
    @pytest.mark.parametrize("value", [
        "03.04.2018",
        "01.01.1000",
        "31.12.9999",
    ])
    def test_valid_value(self, value):
        api.DateField().validate(value)

    @pytest.mark.parametrize("value,exc_type,exc_msg", [
        (None, TypeError, 'Value type must be str'),
        (1, TypeError, 'Value type must be str'),
        ({"a": 1}, TypeError, 'Value type must be str'),
        ([1, 2, 3], TypeError, 'Value type must be str'),
    ])
    def test_not_valid_type(self, value, exc_type, exc_msg):
        with pytest.raises(exc_type, message=exc_msg):
            api.DateField().validate(value)

    @pytest.mark.parametrize("value,exc_type,exc_msg", [
        ("bad format", ValueError, 'Value format must be DD.MM.YYYY'),
        ("1.1.1", ValueError, 'Value format must be DD.MM.YYYY'),
        ("3.4.2018", ValueError, 'Value format must be DD.MM.YYYY'),
        ("3.04.2018", ValueError, 'Value format must be DD.MM.YYYY'),
        ("03.04.18", ValueError, 'Value format must be DD.MM.YYYY'),
        ("03.04.20181", ValueError, 'Value format must be DD.MM.YYYY'),
    ])
    def test_not_valid_format(self, value, exc_type, exc_msg):
        with pytest.raises(exc_type, message=exc_msg):
            api.DateField().validate(value)

    @pytest.mark.parametrize("value,exc_type,exc_msg", [
        ("10.99.2018", ValueError, 'Value must be valid date'),
        ("99.12.2018", ValueError, 'Value must be valid date'),
        ("00.12.2018", ValueError, 'Value must be valid date'),
        ("01.00.2018", ValueError, 'Value must be valid date'),
        ("01.01.0000", ValueError, 'Value must be valid date'),
    ])
    def test_not_valid_date(self, value, exc_type, exc_msg):
        with pytest.raises(exc_type, message=exc_msg):
            api.DateField().validate(value)


class TestBirthDayField(object):
    def test_valid_value(self):
        yesterday = (date.today() - relativedelta(days=1))
        api.BirthDayField().validate(yesterday.strftime("%d.%m.%Y"))

        near_69_years_ago = (date.today() - relativedelta(years=69, days=364))
        api.BirthDayField().validate(near_69_years_ago.strftime("%d.%m.%Y"))

    @pytest.mark.parametrize("value,exc_type,exc_msg", [
        (None, TypeError, 'Value type must be str'),
        (1, TypeError, 'Value type must be str'),
        ({"a": 1}, TypeError, 'Value type must be str'),
        ([1, 2, 3], TypeError, 'Value type must be str'),
    ])
    def test_not_valid_type(self, value, exc_type, exc_msg):
        with pytest.raises(exc_type, message=exc_msg):
            api.BirthDayField().validate(value)

    @pytest.mark.parametrize("value,exc_type,exc_msg", [
        ("bad format", ValueError, 'Value format must be DD.MM.YYYY'),
        ("1.1.1", ValueError, 'Value format must be DD.MM.YYYY'),
        ("3.4.2018", ValueError, 'Value format must be DD.MM.YYYY'),
        ("3.04.2018", ValueError, 'Value format must be DD.MM.YYYY'),
        ("03.04.18", ValueError, 'Value format must be DD.MM.YYYY'),
        ("03.04.20181", ValueError, 'Value format must be DD.MM.YYYY'),
    ])
    def test_not_valid_format(self, value, exc_type, exc_msg):
        with pytest.raises(exc_type, message=exc_msg):
            api.BirthDayField().validate(value)

    @pytest.mark.parametrize("value,exc_type,exc_msg", [
        ("10.99.2018", ValueError, 'Value must be valid date'),
        ("99.12.2018", ValueError, 'Value must be valid date'),
        ("00.12.2018", ValueError, 'Value must be valid date'),
        ("01.00.2018", ValueError, 'Value must be valid date'),
        ("01.01.0000", ValueError, 'Value must be valid date'),
    ])
    def test_not_valid_date(self, value, exc_type, exc_msg):
        with pytest.raises(exc_type, message=exc_msg):
            api.BirthDayField().validate(value)

    def test_not_valid_age(self):
        tomorrow = (date.today() + relativedelta(days=1))
        exc_msg = "Date mustn't be in the future"
        with pytest.raises(ValueError, message=exc_msg):
            api.BirthDayField().validate(tomorrow.strftime("%d.%m.%Y"))

        ago_70_years = (date.today() - relativedelta(years=70))
        exc_msg = "Age must be less than 70 years"
        with pytest.raises(ValueError, message=exc_msg):
            api.BirthDayField().validate(ago_70_years.strftime("%d.%m.%Y"))


class TestGenderField(object):
    @pytest.mark.parametrize("value", [
        0,
        1,
        2
    ])
    def test_valid_value(self, value):
        api.GenderField().validate(value)

    @pytest.mark.parametrize("value,exc_type,exc_msg", [
        (None, TypeError, 'Value type must be int'),
        ("1", TypeError, 'Value type must be int'),
        (0.1, TypeError, 'Value type must be int'),
        ({"a": 1}, TypeError, 'Value type must be int'),
        ([1, 2, 3], TypeError, 'Value type must be int'),
    ])
    def test_not_valid_type(self, value, exc_type, exc_msg):
        with pytest.raises(exc_type, message=exc_msg):
            api.GenderField().validate(value)

    @pytest.mark.parametrize("value,exc_type,exc_msg", [
        (-1, ValueError, 'Value must be 0, 1 or 2'),
        (3, ValueError, 'Value must be 0, 1 or 2'),
    ])
    def test_not_valid_value(self, value, exc_type, exc_msg):
        with pytest.raises(exc_type, message=exc_msg):
            api.GenderField().validate(value)


class TestClientIDsField(object):
    @pytest.mark.parametrize("value", [
        [1],
        [1, 2, 3],
    ])
    def test_valid_value(self, value):
        api.ClientIDsField().validate(value)

    @pytest.mark.parametrize("value,exc_type,exc_msg", [
        (None, TypeError, 'Value type must be list'),
        ("1", TypeError, 'Value type must be list'),
        (0.1, TypeError, 'Value type must be list'),
        ({"a": 1}, TypeError, 'Value type must be list'),
        ((1, 2, 3), TypeError, 'Value type must be list'),
    ])
    def test_not_valid_type(self, value, exc_type, exc_msg):
        with pytest.raises(exc_type, message=exc_msg):
            api.ClientIDsField().validate(value)

    @pytest.mark.parametrize("value,exc_type,exc_msg", [
        ([], ValueError, "Value mustn't be empty"),
    ])
    def test_empty_list(self, value, exc_type, exc_msg):
        with pytest.raises(exc_type, message=exc_msg):
            api.ClientIDsField().validate(value)

    @pytest.mark.parametrize("value,exc_type,exc_msg", [
        (["a"], ValueError, "Type of elements of list must be int"),
        ([0.1], ValueError, "Type of elements of list must be int"),
        ([None], ValueError, "Type of elements of list must be int"),
        ([[1]], ValueError, "Type of elements of list must be int"),
    ])
    def test_not_valid_elements(self, value, exc_type, exc_msg):
        with pytest.raises(exc_type, message=exc_msg):
            api.ClientIDsField().validate(value)
