# YCrawler
Async crawler for news.ycombinator.com<br>
Steps (repeat periodically):
<ol>
    <li>Crawl top 30 posts from main page</li>
    <li>Get new posts (not parsed before)</li>
    <li>Crawl links from comments to posts</li>
    <li>Save to files the content by links from post and comments</li>
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
  -h, --help                show this help message and exit
  --store_dir STORE_DIR     dir for storing files
  --log_dir LOG_DIR         dir for log
  --period PERIOD           seconds between checks
  --verbose                 detailed output
```
