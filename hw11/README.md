# YCrawler
Async crawler for news.ycombinator.com<br>
<ol>
    <li>Create queue for communication</li>
    <li>
        Run worker for periodic check main page:
        <ol>
            <li>Parse new posts from main page</li>
            <li>Put new posts to queue</li>
        </ol>
    </li>
    <li>
        Run N async workers for posts processing<br>
        Each worker:
        <ol>
        <li>Get task from queue</li>
        <li>Parse links from post comments</li>
        <li>Fetch and save post's article and pages by links from comments</li>
        </ol>
    </li>
</ol>

### Requirements
<ul>
    <li>Python 3+</li>
</ul>
<b>Python packages</b>:
<ul>
    <li>beautifulsoup4</li>
    <li>aiohttp</li>
    <li>typing</li>
</ul>

### How to run
```
>>> python ycrawler.py 
optional arguments:
  -h, --help            show this help message and exit
  --store_dir STORE_DIR dir for storing files
  --log_dir LOG_DIR     dir for log
  --period PERIOD       seconds between checks
  --workers WORKERS     number of workers to process urls
  --verbose             detailed output

```
