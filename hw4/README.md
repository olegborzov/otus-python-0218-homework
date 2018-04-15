# HTTP Server
HTTP server with implemented GET and HEAD methods.<br>
Run with several listening processes on given port.<br>
Multiprocessing scheme:
```
httpd.py--|----------|
          |          |--thread<--->client
          |          |--thread<--->client
          |          |--thread<--->client
          |
          |--fork()--|
          |          |--thread<--->client
          |          |--thread<--->client
          |          |--thread<--->client
          |
          |--fork()--|
          |          |--thread<--->client
          |          |--thread<--->client
          |          |--thread<--->client
```

### Requirements
Python 3+ version required

### How to see possible options:
 - <b>%path_to_module_dir%</b> - path to dir with module
```
cd %path_to_module_dir%
python3 httpd.py --help
```

### How to run: 
 - <b>%path_to_module_dir%</b> - path to dir with module
 - <b>%port%</b> - server listened port, default - 8099
 - <b>%workers_count%</b> - server workers count, default - 5
 - <b>%DOCUMENT_ROOT%</b> - DIRECTORY_ROOT with site files, default - doc_root

```
cd %path_to_module_dir%
python3 httpd.py -p %port% -w %workers_count% -r %DOCUMENT_ROOT%
```

### How to run tests: 
Print in terminal:
```
cd %path_to_module_dir%
python2.7 httptest.py
```

### Load Testing
Results of load testing

```
ab -n 20000 -c 100 -r "http://localhost:8099/httptest/dir2"
This is ApacheBench, Version 2.3 <$Revision: 1807734 $>
Copyright 1996 Adam Twiss, Zeus Technology Ltd, http://www.zeustech.net/
Licensed to The Apache Software Foundation, http://www.apache.org/

Benchmarking localhost (be patient)
Completed 2000 requests
Completed 4000 requests
Completed 6000 requests
Completed 8000 requests
Completed 10000 requests
Completed 12000 requests
Completed 14000 requests
Completed 16000 requests
Completed 18000 requests
Completed 20000 requests
Finished 20000 requests


Server Software:        Otus-Python-HW04
Server Hostname:        localhost
Server Port:            8099

Document Path:          /httptest/dir2
Document Length:        34 bytes

Concurrency Level:      100
Time taken for tests:   49.403 seconds
Complete requests:      20000
Failed requests:        14
   (Connect: 0, Receive: 0, Length: 14, Exceptions: 0)
Non-2xx responses:      14
Total transferred:      3602136 bytes
HTML transferred:       682024 bytes
Requests per second:    404.83 [#/sec] (mean)
Time per request:       123.507 [ms] (mean)
Time per request:       2.470 [ms] (mean, across all concurrent requests)
Transfer rate:          71.20 [Kbytes/sec] received

Connection Times (ms)
              min  mean[+/-sd] median   max
Connect:        0   28 577.3      0   14228
Processing:     5   95 196.2     60    3225
Waiting:        5   93 196.2     58    3225
Total:          5  122 608.0     60   14345

Percentage of the requests served within a certain time (ms)
  50%     60
  66%     69
  75%     75
  80%     79
  90%     95
  95%    137
  98%   1107
  99%   1148
 100%  14345 (longest request)
```