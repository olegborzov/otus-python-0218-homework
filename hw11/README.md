# YCrawler
Async crawler for news.ycombinator.com<br>
Steps (repeat periodically):
<ol>
    <li>Crawl top 30 posts from main page</li>
    <li>Check every post is new</li>
    <li>Crawl links from comments to every post</li>
    <li>Save the contents of the article and 
    the pages of the links from the comments to the files</li>
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
