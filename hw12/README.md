# MemcLoad
GO version of memc_load_multiprocessing.py.<br>

# Algorythm
When initializing, a Memcache client map is created for the specified addresses in the arguments.<br>
The script reads the files line by line: <br>
For each successfully read line, an AppsInstalled structure is created and passed to the goroutine for uploading to the corresponding Memcache client.<br>
<b>MaxActiveGoroutines</b> - maximum number of concurrently running goroutines<br>.
<b>MaxMemcConns</b> - maximum number of simultaneous connections for each Memcache client.

### How to run
```
>>> go run memc_load.go 
optional arguments:
  -test                # To run protobuf test  
  -log LOG             # Path to log file
  -dry                 # Debug mode
  -pattern PATTERN     # Pattern of files paths, where logs stored
  -idfa IDFA           # Address of IDFA memcache server
  -gaid GAID           # Address of GAID memcache server
  -adid ADID           # Address of ADID memcache server
  -dvid DVID           # Address of DVID memcache server
```
