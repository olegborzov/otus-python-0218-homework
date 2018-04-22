# uWSGI daemon
OTUS uWSGI daemon. Determines the user's city by IP using the site ipinfo.io.<br>
Return information in json-format about the weather in given city, using the site openweathermap.org.

### Requirements
- CentOS 7
- Python 3+
- python-requests library
- systemd
- nginx

### How to install:
- Clone repo from github:
```
>>> git clone https://github.com/olegborzov/otus-python-0218-homework/
```
- Go to to package folder:
```
>>> cd hw5
```
- Compile package:
```
>>> ./buildrpm.sh $PWD/ip2w.spec
```

### How to run daemon: 
```
>>> systemctl start ip2w
```

### Query example
```
>>> curl http://localhost/ip2w/176.14.221.123
{"city": "Moscow", "temp": "+20", "conditions": "небольшой дождь"}
```

### How to stop:
```
>>> systemctl stop ip2w
```

### How to run tests: 
```
>>> cd %path_to_module_dir%
>>> python3 ip2w_test.py

Send malformed IP ... ok
Send empty IP (server must take it from headers) ... ok
Send good IP ... ok
Send URL with large level of nesting ... ok
Send IP from reserved range ... ok

----------------------------------------------------------------------
Ran 5 tests in 1.389s

OK
```