# -*- coding: utf-8 -*-

import hashlib
from datetime import datetime

import pytest

from scoring_api import api
from scoring_api.store import Store


# -----------
# Global Functions and Mocks
# -----------

def get_token(is_admin=False, account="account", login="login"):
    if is_admin:
        digest = datetime.now().strftime("%Y%m%d%H") + api.ADMIN_SALT
    else:
        digest = account + login + api.SALT

    return hashlib.sha512(digest.encode()).hexdigest()


class StorageMock:
    def __init__(self, min_attempts=0):
        self.min_attempts = min_attempts
        self.attempts = 0
        self.store = {}

    def reconnect(self):
        self.attempts += 1

    def get(self, key):
        if self.attempts >= self.min_attempts:
            return self.store.get(key, None)
        raise ConnectionError

    def set(self, key, value, expires=0):
        if self.attempts >= self.min_attempts:
            self.store[key] = value
            return True
        raise ConnectionError


# -----------
# Method Handlers Test Cases
# -----------

class TestMethodRequestValidation:
    @classmethod
    def get_valid_args(cls, is_admin=False, method="online_score"):
        account = "otus_course"
        login = "admin" if is_admin else "simple_user"
        token = get_token(is_admin, account=account, login=login)

        return {
            "account": account,
            "login": login,
            "token": token,
            "arguments": {},
            "method": method
        }

    def test_valid_args(self):
        request = api.MethodRequest(**self.get_valid_args())
        assert not request.errors.keys()

    @pytest.mark.parametrize(
        "bad_field", ["login", "token", "arguments", "method"]
    )
    def test_bad_required_fields(self, bad_field):
        params = self.get_valid_args()
        del params[bad_field]

        request = api.MethodRequest(**params)
        error_msg = "Field %s is required" % bad_field

        assert bad_field in request.errors
        assert request.errors[bad_field] == error_msg

    @pytest.mark.parametrize("bad_field, bad_field_value", [
        ("method", ""),
    ])
    def test_bad_not_nullable_fields(self, bad_field, bad_field_value):
        params = self.get_valid_args()
        params[bad_field] = bad_field_value

        request = api.MethodRequest(**params)
        error_msg = "Field %s can't be empty" % bad_field

        assert bad_field in request.errors
        assert request.errors[bad_field] == error_msg

    @pytest.mark.parametrize("bad_field, bad_field_value, error_msg", [
        ("method", 123, "Value type must be str"),
        ("arguments", "", "Value type must be dict"),
    ])
    def test_not_valid_fields(self, bad_field, bad_field_value, error_msg):
        params = self.get_valid_args()
        params[bad_field] = bad_field_value

        request = api.MethodRequest(**params)

        assert bad_field in request.errors
        assert request.errors[bad_field] == error_msg


class TestOnlineScoreRequestValidation:
    @classmethod
    def get_valid_args(cls):
        return {
            "phone": 70123456789, "email": "test@test.ru",
            "first_name": "test", "last_name": "test",
            "gender": 0, "birthday": "01.01.2017"
        }

    def test_valid_args(self):
        request = api.OnlineScoreRequest(**self.get_valid_args())
        assert not request.errors.keys()

    @pytest.mark.parametrize("params", [
        {"phone": 70123456789, "email": "test@test.ru"},
        {"first_name": "test", "last_name": "test"},
        {"gender": 0, "birthday": "01.01.2017"},
        {"gender": 1, "birthday": "01.01.2017"},
    ], ids=[
        "phone‑email", "first name‑last name",
        "gender‑birthday", "gender‑birthday-2"
    ])
    def test_valid_pairs(self, params):
        request = api.OnlineScoreRequest(**params)
        assert "invalid_pairs" not in request.errors.keys()

    @pytest.mark.parametrize("change_fields", [
        ({"first_name": "", "email": "", "birthday": ""}),
        ({"first_name": None, "email": None, "birthday": None}),
        ({"last_name": "", "phone": "", "birthday": ""}),
        ({"last_name": None, "phone": None, "gender": None}),
        ({
            "last_name": None, "phone": None, "gender": None,
            "first_name": None, "email": None, "birthday": None
        }),
        ({
            "last_name": "", "phone": "",
            "first_name": "", "email": "", "birthday": ""
        }),
    ])
    def test_bad_pairs(self, change_fields):
        params = self.get_valid_args()
        for field_key, field_value in change_fields.items():
            params[field_key] = field_value

        request = api.OnlineScoreRequest(**params)
        assert "invalid_pairs" in request.errors.keys()


class TestClientsInterestsRequestValidate:
    @classmethod
    def get_valid_args(cls):
        return {
            "client_ids": [1, 2],
            "date": "01.01.2017"
        }

    def test_valid_args(self):
        request = api.ClientsInterestsRequest(**self.get_valid_args())
        assert not request.errors.keys()


# -----------
# Function Method Handler Test Case
# -----------

class TestMethodHandler:
    @classmethod
    def get_response(cls, request, store=None):
        return api.method_handler(
            request={"body": request, "headers": {}},
            context={},
            store=store
        )

    @classmethod
    def get_valid_args(cls, is_admin=True, method="online_score"):
        if method == "online_score":
            arguments = TestOnlineScoreRequestValidation.get_valid_args()
        elif method == "clients_interests":
            arguments = TestClientsInterestsRequestValidate.get_valid_args()
        else:
            arguments = {}

        result_args = TestMethodRequestValidation.get_valid_args(
            is_admin, method
        )
        result_args["arguments"] = arguments
        return result_args

    @pytest.mark.parametrize("is_admin", [True, False])
    @pytest.mark.parametrize("method", ["online_score", "clients_interests"])
    @pytest.mark.parametrize("attempts", [0, 3, 5])
    def test_valid_requests(self, is_admin, method, attempts):
        request = self.get_valid_args(is_admin, method)
        storage_mock = StorageMock(min_attempts=attempts)
        store = Store(storage_mock)

        _, code = self.get_response(request, store)
        assert code == api.OK

    @pytest.mark.parametrize("attempts", [6, 8])
    def test_online_score_with_not_available_store(self, attempts):
        request = self.get_valid_args(True, "online_score")
        storage_mock = StorageMock(min_attempts=attempts)
        store = Store(storage_mock)

        _, code = self.get_response(request, store)
        assert code == api.OK

    @pytest.mark.parametrize("attempts", [6, 8])
    def test_clients_interests_with_not_available_store(self, attempts):
        request = self.get_valid_args(True, "clients_interests")
        storage_mock = StorageMock(min_attempts=attempts)
        store = Store(storage_mock)

        with pytest.raises(ConnectionError):
            self.get_response(request, store)

    def test_empty_request(self):
        _, code = self.get_response({})
        assert code == api.INVALID_REQUEST

    def test_bad_fields(self):
        _, code = self.get_response({
            "account": 123
        })
        assert code == api.INVALID_REQUEST

    @pytest.mark.parametrize("change_fields", [
        {"login": "simple", "token": ""},
        {"login": "simple", "token": "bad_token"},
        {"login": "admin", "token": ""},
        {"login": "admin", "token": "bad_token"},
        {"login": "simple", "token": get_token(True, "otus_course", "admin")},
        {"login": "admin", "token": get_token(False, "otus_course", "simple")}
    ], ids=[
        "empty_token", "bad_token", "empty_admin_token", "bad_admin_token",
        "admin_token_for_simple_user", "simple_user_token_for_admin"
    ])
    def test_bad_auth(self, change_fields):
        request = self.get_valid_args()
        for field_key, field_value in change_fields.items():
            request[field_key] = field_value

        _, code = self.get_response(request)
        assert code == api.FORBIDDEN

    def test_bad_method(self):
        request = self.get_valid_args(method="bad_method")
        _, code = self.get_response(request)
        assert code == api.NOT_FOUND

    @pytest.mark.parametrize("change_fields", [
        {"method": "online_score", "arguments": {}},
        {"method": "clients_interests", "arguments": {}},
        {"method": "online_score", "arguments": {"bad": 1}},
        {"method": "clients_interests", "arguments": {"bad": 1}},
    ],  ids=[
        "online_score_empty_args", "clients_interests_empty_args",
        "online_score_bad_args", "clients_interests_bad_args",
    ])
    def test_bad_handler_args(self, change_fields):
        request = self.get_valid_args()
        for field_key, field_value in change_fields.items():
            request[field_key] = field_value

        _, code = self.get_response(request)
        assert code == api.INVALID_REQUEST

