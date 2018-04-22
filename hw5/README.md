# HTTP Server
OTUS uWSGI daemon. Determines the user's city by IP using the site ipinfo.io.<br>
Return information in json-format about the weather in given city, using the site openweathermap.org.

### Requirements
- Python 3+ version required
- python-requests library
- systemd
- nginx

### How to install:
- Clone repo from github:
```
git clone https://github.com/olegborzov/otus-python-0218-homework/
```
- Go to to package folder:
```
cd hw5
```
- Compile package:
```
./buildrpm.sh $PWD/ip2w.spec
```

### How to run daemon: 
```
systemctl start ip2w
```

### Query example
```
>>> curl http://localhost/ip2w/176.14.221.123
{"city": "Moscow", "temp": "+20", "conditions": "небольшой дождь"}
```

### How to stop:
```
systemctl stop ip2w
```

### How to run tests: 
```
cd %path_to_module_dir%
python3 ip2w_test.py
```