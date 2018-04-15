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
wrk -t4 -c100 -d10s http://localhost:8099/httptest/dir2/

Running 10s test @ http://localhost:8099/httptest/dir2/
  4 threads and 100 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     3.10ms    1.43ms  60.80ms   98.18%
    Req/Sec   662.05    381.55     1.60k    67.49%
  16082 requests in 10.06s, 2.76MB read
  Socket errors: connect 0, read 18, write 2, timeout 0
Requests/sec:   1598.28
Transfer/sec:    280.95KB
```