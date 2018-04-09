# -*- coding: utf-8 -*-

import redis


class RedisStorage:
    def __init__(self, host="localhost", port=6379, timeout=3):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.db = None
        self.reconnect()

    def reconnect(self):
        self.db = redis.Redis(
            host=self.host,
            port=self.port,
            db=0,
            socket_connect_timeout=self.timeout,
            socket_timeout=self.timeout
        )

    def get(self, key):
        try:
            result = self.db.get(key)
            return result.decode("UTF-8")
        except (AttributeError, ValueError):
            return
        except redis.RedisError:
            raise ConnectionError

    def set(self, key, value, expires=0):
        try:
            return self.db.set(key, value, ex=expires)
        except redis.RedisError:
            raise ConnectionError


class Store:
    def __init__(self, storage, max_retries=6):
        self.storage = storage
        self.max_retries = max_retries

    def get(self, key):
        retries = 0
        while retries < self.max_retries:
            try:
                return self.storage.get(key)
            except ConnectionError:
                self.storage.reconnect()
                retries += 1

        raise ConnectionError

    def cache_get(self, key):
        retries = 0
        while retries < self.max_retries:
            try:
                return self.storage.get(key)
            except ConnectionError:
                self.storage.reconnect()
                retries += 1

    def cache_set(self, key, value, expires=0):
        retries = 0
        while retries < self.max_retries:
            try:
                return self.storage.set(key, value, expires)
            except ConnectionError:
                self.storage.reconnect()
                retries += 1

