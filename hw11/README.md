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
- Python 3+
- beautifulsoup4

### How to run
```
>>> python ycrawler.py 
optional arguments:
  --log_dir LOG_DIR     # Path to log dir
  --store_dir STORE_DIR # Path to dir, for storing files
  --period NUM          # Seconds between checks
  --verbose BOOL        # Detailed output
```
