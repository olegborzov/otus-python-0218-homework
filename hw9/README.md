# MemcLoad
Multiprocessing version of memc_load.py.<br>
Main process parse from given log files info about user's installed apps
and load to queue.<br>
For each memcache address create process for loading logs.

### Requirements
- Python 3+
- python-memcached
- protobuf

### How to run
```
>>> python memc_load_multthreaded.py 
optional arguments:
  -t, --test            # To run protobuf test  
  -l LOG, --log LOG     # Path to log file
  --dry                 # Debug mode
  --pattern PATTERN     # Pattern of files paths, where logs stored
  --idfa IDFA           # Address of IDFA memcache server
  --gaid GAID           # Address of GAID memcache server
  --adid ADID           # Address of ADID memcache server
  --dvid DVID           # Address of DVID memcache server
```
