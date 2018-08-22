# MemcLoad
GO version of memc_load_multiprocessing.py

### How to run
```
>>> go run memc_load.go -help
  -adid string          ip and port of adid memcached server (default "127.0.0.1:33015")
  -dry                  debug mode (without sending to memcached)
  -dvid string          ip and port of dvid memcached server (default "127.0.0.1:33016")
  -gaid string          ip and port of gaid memcached server (default "127.0.0.1:33014")
  -idfa string          ip and port of idfa memcached server (default "127.0.0.1:33013")
  -log string           path to log file (default "./memc.log")
  -pattern string       files path pattern (default "/data/appsinstalled/*.tsv.gz")
  -test                 test protobuf
>>> go run memc_log.go -dry -pattern "/data/appsinstalled/*.tsv.gz"
```
