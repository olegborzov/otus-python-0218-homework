# -*- coding: utf-8 -*-

import abc
import json
import datetime
from dateutil.relativedelta import relativedelta
import logging
import hashlib
import re
import uuid
from optparse import OptionParser
from http.server import HTTPServer, BaseHTTPRequestHandler

from scoring_api import scoring

SALT = "Otus"
ADMIN_LOGIN = "admin"
ADMIN_SALT = "42"

OK = 200
BAD_REQUEST = 400
FORBIDDEN = 403
NOT_FOUND = 404
INVALID_REQUEST = 422
INTERNAL_ERROR = 500
ERRORS = {
    BAD_REQUEST: "Bad Request",
    FORBIDDEN: "Forbidden",
    NOT_FOUND: "Not Found",
    INVALID_REQUEST: "Invalid Request",
    INTERNAL_ERROR: "Internal Server Error",
}
UNKNOWN = 0
MALE = 1
FEMALE = 2
GENDERS = {
    UNKNOWN: "unknown",
    MALE: "male",
    FEMALE: "female",
}


class Field(metaclass=abc.ABCMeta):
    """
    Base class for other fields
    """

    def __init__(self, required=False, nullable=False):
        self.error_msgs = {
            'required': 'This field is required.',
            'nullable': "This field can't be null"
        }
        self.required = required
        self.nullable = nullable

    @abc.abstractmethod
    def validate(self, value):
        raise NotImplementedError

    @abc.abstractmethod
    def is_empty(self, value):
        raise NotImplementedError

    def prepare(self, value):
        return value


class CharField(Field):
    """
    Character field:
        1. type - str
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.error_msgs.update({
            'invalid_type': 'Value type must be str'
        })

    def validate(self, value):
        if not isinstance(value, str):
            raise TypeError(self.error_msgs["invalid_type"])

    def is_empty(self, value):
        return not value


class ArgumentsField(Field):
    """
    Arguments field:
        1. type - dict

    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.error_msgs.update({
            'invalid_type': 'Value type must be dict'
        })

    def validate(self, value):
        if not isinstance(value, dict):
            raise TypeError(self.error_msgs["invalid_type"])

    def is_empty(self, value):
        return not value


class EmailField(CharField):
    """
    Email field:
        1. type - str
        2. must contain @
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.error_msgs.update({
            'invalid_value': 'Value must contain @ symbol'
        })

    def validate(self, value):
        super().validate(value)
        if self.is_empty(value):
            return

        if "@" not in value:
            raise ValueError(self.error_msgs['invalid_value'])

    def is_empty(self, value):
        return not value


class PhoneField(Field):
    """
    Phone number:
        1. type - int or str
        2. length = 11
        3. field[0] == 7
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.error_msgs.update({
            'invalid_type': "Value type must be str or int",
            'invalid_value': "Value must start with 7",
            'invalid_value_len': "Length of value must be 11 characters"
        })

    def validate(self, value):
        if not isinstance(value, (int, str)):
            raise TypeError(self.error_msgs['invalid_type'])

        if self.is_empty(value):
            return

        value_str = str(value)
        if len(value_str) != 11:
            raise ValueError(self.error_msgs['invalid_value_len'])

        if not value_str.startswith("7"):
            raise ValueError(self.error_msgs['invalid_value'])

    def is_empty(self, value):
        return not value


class DateField(CharField):
    """
    Date:
        1. type - str
        2. format - DD.MM.YYYY
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.error_msgs.update({
            'invalid_format': "Value format must be DD.MM.YYYY",
            'invalid_date': "Value must be valid date",
        })

    def _to_datetime(self, value):
        return datetime.datetime.strptime(value, "%d.%m.%Y")

    def validate(self, value):
        super().validate(value)

        if self.is_empty(value):
            return

        if not re.match(r"\d{2}\.\d{2}.\d{4}", value):
            raise ValueError(self.error_msgs['invalid_format'])

        try:
            self._to_datetime(value)
        except (TypeError, ValueError):
            raise ValueError(self.error_msgs['invalid_date'])

    def is_empty(self, value):
        return not value

    def prepare(self, value):
        return self._to_datetime(value)


class BirthDayField(DateField):
    """
    BirthDay:
        1. type - str
        2. format - DD.MM.YYYY
        3. Age < 70
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.error_msgs.update({
            'invalid_year': "Age must be less than 70 years",
            'future_date': "Date mustn't be in the future"
        })

    def validate(self, value):
        super().validate(value)

        if self.is_empty(value):
            return

        now = datetime.datetime.now()
        date_value = self._to_datetime(value)
        delta = relativedelta(now, date_value)
        years_delta = delta.years
        if not (0 <= years_delta < 70):
            raise ValueError(self.error_msgs['invalid_year'])

        if now < date_value:
            raise ValueError(self.error_msgs['future_date'])

    def is_empty(self, value):
        return not value


class GenderField(Field):
    """
    Gender:
        1. type - int
        2. value in (0, 1, 2)
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.error_msgs.update({
            'invalid_type': "Value type must be int",
            'invalid_value': "Value must be 0, 1 or 2"
        })

    def validate(self, value):
        if not isinstance(value, int):
            raise TypeError(self.error_msgs['invalid_type'])

        if self.is_empty(value):
            return

        if value not in GENDERS:
            raise ValueError(self.error_msgs['invalid_value'])

    def is_empty(self, value):
        return False


class ClientIDsField(Field):
    """
    Client IDs:
        1. type - list
        2. len > 0
        3. type of elements of list - int
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.error_msgs.update({
            'invalid_type': "Value type must be list",
            'invalid_value': "Type of elements of list must be int",
        })

    def validate(self, value):
        if not isinstance(value, list):
            raise TypeError(self.error_msgs['invalid_type'])

        if self.is_empty(value):
            return

        for elem in value:
            if not isinstance(elem, int):
                raise ValueError(self.error_msgs['invalid_value'])

    def is_empty(self, value):
        return not value


class AbstractRequest(metaclass=abc.ABCMeta):
    """
    AbstractRequest with defined iint
    """
    def __init__(self, **kwargs):
        """
        Request init.
        Copies declarative classes to self.fields_classes
        and deletes them from attributes
        """
        if not hasattr(self, 'error_msgs'):
            self.error_msgs = {}
        self.error_msgs.update({
            "required": "Field {} is required",
            "nullable": "Field {} can't be empty",
            "unexpected": "Field {} is unexpected"
        })

        self.errors = {}
        self.field_classes = {}
        for field_name in dir(self):
            field_value = getattr(self, field_name, None)
            if isinstance(field_value, Field):
                self.field_classes[field_name] = field_value
                setattr(self, field_name, None)

        # Set object attributes by args
        for field_name, field_value in kwargs.items():
            setattr(self, field_name, field_value)

        self.validate()

        # Set prepared fields values if they are valid
        if not self.errors:
            for field_name in dir(self):
                if field_name in self.field_classes:
                    prepared_value = self.field_classes[field_name].prepare(
                        getattr(self, field_name)
                    )
                    setattr(self, field_name, prepared_value)

    def validate(self):
        """
        Fields validation method.
        Checks required and nullable fields and validate
        their values
        """
        for field_name, field_cls in self.field_classes.items():
            field_value = getattr(self, field_name, None)

            # Check for required
            if field_cls.required:
                if field_value is None:
                    msg = self.error_msgs["required"].format(field_name)
                    self.errors[field_name] = msg
                    continue

            # Check for not nullable
            if not field_cls.nullable:
                if not field_value:
                    msg = self.error_msgs["nullable"].format(field_name)
                    self.errors[field_name] = msg
                    continue

            # Validate field value
            try:
                field_cls.validate(field_value)
            except (TypeError, ValueError) as ex:
                self.errors[field_name] = str(ex)


class ClientsInterestsRequest(AbstractRequest):
    """
    Handler for method clients_interests
    """
    client_ids = ClientIDsField(required=True)
    date = DateField(required=False, nullable=True)

    def get_answer(self, store, context, is_admin):
        """
        Return user's interests for list of ids
        """
        context["nclients"] = len(self.client_ids)
        result = {}
        for cid in self.client_ids:
            result[str(cid)] = scoring.get_interests(store=store, cid=cid)

        return result


class OnlineScoreRequest(AbstractRequest):
    """
    Handler for method online_score.
    """
    first_name = CharField(required=False, nullable=True)
    last_name = CharField(required=False, nullable=True)
    email = EmailField(required=False, nullable=True)
    phone = PhoneField(required=False, nullable=True)
    birthday = BirthDayField(required=False, nullable=True)
    gender = GenderField(required=False, nullable=True)

    def __init__(self, **kwargs):
        self.field_pairs = [
            ("phone", "email"),
            ("first_name", "last_name"),
            ("gender", "birthday")
        ]
        pairs_str = ", ".join(["(%s, %s)" % pair for pair in self.field_pairs])
        if not hasattr(self, 'error_msgs'):
            self.error_msgs = {}
        self.error_msgs.update({
            "invalid_pairs": "Request must have at least one pair "
                             "with non-empty values of: {}".format(pairs_str)
        })

        super().__init__(**kwargs)

    def validate(self):
        """
        Redefined validation method from AbstractRequest
        Checks that at least one pair of fields is non-empty of:
        (phone, email), (first_name, last_name), (gender, birthday)'
        """
        super().validate()

        is_valid = False
        for pair in self.field_pairs:
            field_1_value = getattr(self, pair[0], None)
            field_1_empty = self.field_classes[pair[0]].is_empty(field_1_value)
            field_1_empty = field_1_value is None or field_1_empty

            field_2_value = getattr(self, pair[1], None)
            field_2_empty = self.field_classes[pair[1]].is_empty(field_2_value)
            field_2_empty = field_1_value is None or field_2_empty

            if not(field_1_empty or field_2_empty):
                is_valid = True
                break

        if not is_valid:
            self.errors["invalid_pairs"] = self.error_msgs["invalid_pairs"]

    def get_answer(self, store, context, is_admin):
        """
        Return user's score, calculated by given fields
        """
        filled_field_names = [
            field_name
            for field_name in self.field_classes.keys()
            if getattr(self, field_name, None)
        ]
        context["has"] = ", ".join(filled_field_names)

        if is_admin:
            result = 42
        else:
            result = scoring.get_score(
                store=store,
                phone=self.phone, email=self.email,
                birthday=self.birthday, gender=self.gender,
                first_name=self.first_name, last_name=self.last_name
            )

        return {"score": result}


class MethodRequest(AbstractRequest):
    """
    Handler for validation top-level request args
    """
    account = CharField(required=False, nullable=True)
    login = CharField(required=True, nullable=True)
    token = CharField(required=True, nullable=True)
    arguments = ArgumentsField(required=True, nullable=True)
    method = CharField(required=True, nullable=False)

    @property
    def is_admin(self):
        return self.login == ADMIN_LOGIN


def check_auth(methodrequest):
    """
    Check user authorization
    """

    if methodrequest.is_admin:
        digest = datetime.datetime.now().strftime("%Y%m%d%H") + ADMIN_SALT
    else:
        digest = methodrequest.account + methodrequest.login + SALT

    digest = hashlib.sha512(digest.encode()).hexdigest()
    return digest == methodrequest.token


def method_handler(request, context, store):
    """
    Handle request.
    Validate arguments and return result or error

    :param request: {"body": request (dict), "headers": headers (dict)}
    :param context: dict
    :param store: object
    :return: Answer (errors_dict if error), Code
    """
    handlers = {
        "online_score": OnlineScoreRequest,
        "clients_interests": ClientsInterestsRequest
    }

    # 1. Validate MethodRequest args
    methodrequest = MethodRequest(**request["body"])
    if methodrequest.errors:
        return methodrequest.errors, INVALID_REQUEST

    # 2. Validate auth
    if not check_auth(methodrequest):
        return ERRORS[FORBIDDEN], FORBIDDEN

    # 3. Check if method exists
    if methodrequest.method not in handlers:
        msg = "Method {} isn't specified".format(methodrequest.method)
        return msg, NOT_FOUND

    # 4. Validate handler args
    handler = handlers[methodrequest.method](**methodrequest.arguments)
    if handler.errors:
        return handler.errors, INVALID_REQUEST

    return handler.get_answer(store, context, methodrequest.is_admin), OK


class MainHTTPHandler(BaseHTTPRequestHandler):
    """
    HTTP Server for processing POST requests
    """
    router = {
        "method": method_handler
    }
    store = None

    def get_request_id(self, headers):
        """
        Return request id from headers
        """
        return headers.get('HTTP_X_REQUEST_ID', uuid.uuid4().hex)

    def do_POST(self):
        """
        POST requests processing
        """
        response, code = {}, OK
        context = {"request_id": self.get_request_id(self.headers)}
        request = None
        data_string = None

        try:
            data_string = self.rfile.read(int(self.headers['Content-Length']))
            request = json.loads(data_string)
        except:
            code = BAD_REQUEST

        if request:
            path = self.path.strip("/")
            msg = "%s: %s %s" % (self.path, data_string, context["request_id"])
            logging.info(msg)
            if path in self.router:
                try:
                    response, code = self.router[path](
                        {"body": request, "headers": self.headers},
                        context,
                        self.store
                    )
                except Exception as e:
                    logging.exception("Unexpected error: %s" % e)
                    code = INTERNAL_ERROR
            else:
                code = NOT_FOUND

        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        if code not in ERRORS:
            r = {"response": response, "code": code}
        else:
            r = {
                "error": response or ERRORS.get(code, "Unknown Error"),
                "code": code
            }
        context.update(r)
        logging.info(context)
        self.wfile.write(json.dumps(r).encode())


if __name__ == "__main__":
    op = OptionParser()
    op.add_option("-p", "--port", action="store", type=int, default=8080)
    op.add_option("-l", "--log", action="store", default=None)
    (opts, args) = op.parse_args()
    logging.basicConfig(
        filename=opts.log,
        level=logging.INFO,
        format='[%(asctime)s] %(levelname).1s %(message)s',
        datefmt='%Y.%m.%d %H:%M:%S'
    )
    server = HTTPServer(("localhost", opts.port), MainHTTPHandler)
    logging.info("Starting server at %s" % opts.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()
