# -*- coding: utf-8 -*-
"""
Async crawler for news.ycombinator.com
"""

import os
import argparse
import logging as log
from logging.handlers import RotatingFileHandler
from urllib.parse import urlparse

from typing import Dict, List, Set

import aiohttp
import asyncio

from bs4 import BeautifulSoup


YNEWS_MAIN_URL = "https://news.ycombinator.com/"
YNEWS_POST_URL_TEMPLATE = "https://news.ycombinator.com/item?id={id}"
FETCH_TIMEOUT = 10
MAX_RETRIES = 3


class Fetcher:
    """
    Provides counting of saved posts and links from posts comments
    """

    def __init__(self, session: aiohttp.ClientSession, store_dir: str):
        self.posts_saved = 0
        self.comments_links_saved = 0
        self.session = session
        self.store_dir = store_dir

    async def load_and_save(self, url: str, post_id: int, link_id: int):
        try:
            content = await self.fetch(url, need_bytes=True)
            filepath = self.get_path(link_id, post_id)
            self.write_to_file(filepath, content)

            if link_id > 0:
                self.comments_links_saved += 1
            else:
                self.posts_saved += 1
        except aiohttp.ClientError:
            log.error("Can't fetch post page: {}".format(url))

    def get_path(self, link_id: int, post_id: int) -> str:
        if link_id > 0:
            filename = "{}_{}.html".format(post_id, link_id)
        else:
            filename = "{}.html".format(post_id)
        filepath = os.path.join(self.store_dir, str(post_id), filename)
        return filepath

    async def fetch(self,
                    url: str,
                    need_bytes: bool = True,
                    retry: int = 0) -> (bytes, str):
        """
        Fetch a URL using aiohttp returning parsed JSON response.
        As suggested by the aiohttp docs we reuse the session.
        """
        try:
            async with self.session.get(url) as response:
                if need_bytes:
                    return await response.read()
                else:
                    return await response.text()
        except aiohttp.ClientError:
            if retry < MAX_RETRIES:
                log.warning("Error on url {}, try again".format(url))
                return await self.fetch(url, need_bytes, retry + 1)
            else:
                log.exception("Can't parse url {}".format(url))
                raise

    def write_to_file(self, path: str, content: bytes):
        """
        Save binary content to file
        """
        try:
            with open(path, "wb") as f:
                f.write(content)
        except OSError:
            log.exception("Can't save file {}".format(path))
            return


async def get_links_from_comments(post_id: int, fetcher: Fetcher) -> List[str]:
    """
    Fetch comments page and parse links from comments
    """
    url = YNEWS_POST_URL_TEMPLATE.format(id=post_id)
    links = []
    try:
        html = await fetcher.fetch(url, need_bytes=False)

        soup = BeautifulSoup(html, "html5lib")
        links = []
        for link in soup.select(".comment a[rel=nofollow]"):
            parsed_url = urlparse(link)
            if parsed_url.scheme and parsed_url.netloc:
                links.append(link)

        return links
    except aiohttp.ClientError:
        log.error("Can't fetch comments page: {}".format(url))
        return links


async def crawl_post(url: str, post_id: int, fetcher: Fetcher,
                     loop: asyncio.AbstractEventLoop):
    """
    Fetch links from comments to article and save to local file
    """
    comments_links = await get_links_from_comments(post_id, fetcher)
    links = [url] + comments_links

    tasks = [
        fetcher.load_and_save(link, post_id, ind)
        for ind, link in enumerate(links)
    ]

    await asyncio.gather(*tasks)


def parse_main_page(html: str) -> Dict[int, str]:
    """
    Parse articles urls and their ids
    """
    posts = {}

    soup = BeautifulSoup(html, "html5lib")
    trs = soup.select("table.itemlist tr.athing")
    for ind, tr in enumerate(trs):
        _id, _url = "", ""
        try:
            _id = int(tr.attrs["id"])
            _url = tr.select_one("td.title a.storylink").attrs["href"]
            posts[_id] = _url
        except KeyError:
            log.exception("Error on {} post (id: {}, url: {})".format(
                ind, _id, _url
            ))
            continue

    return posts


def get_dir_names(store_dir: str) -> Set(int):
    """
    Return child dirs from given dir (ready post ids)
    """
    post_ids = set()
    for subdir_name in os.listdir(store_dir):
        if os.path.isdir(os.path.join(store_dir, subdir_name)):
            try:
                post_id = int(subdir_name)
                post_ids.add(post_id)
            except ValueError:
                log.error("Wrong subdir name (should be number): {}".format(
                    subdir_name
                ))

    return post_ids


async def check_main_page(fetcher: Fetcher, loop: asyncio.AbstractEventLoop):
    try:
        html = await fetcher.fetch(YNEWS_MAIN_URL, need_bytes=False)
    except Exception as ex:
        log.error("Error retrieving {}: {}".format(YNEWS_MAIN_URL, ex))
        raise

    posts = parse_main_page(html)
    ready_post_ids = get_dir_names(fetcher.store_dir)
    not_ready_posts = {
        p_id: p_url
        for p_id, p_url in posts.items()
        if p_id not in ready_post_ids
    }

    tasks = [
        crawl_post(p_url, p_id, fetcher, loop)
        for p_id, p_url in not_ready_posts.items()
    ]

    try:
        await asyncio.gather(*tasks)
    except Exception as e:
        log.error("Error retrieving comments for top stories: {}".format(e))
        raise


async def monitor_ycombinator(session: aiohttp.ClientSession,
                              loop: asyncio.AbstractEventLoop,
                              to_sleep: int,
                              store_dir: str):
    """
    Periodically check news.ycombinator.com for new articles.
    Parse articles and links from comments and save to local files
    """
    def callback(fut):
        try:
            fut.result()
        except Exception as e:
            log.exception('Unexpected error')
        else:
            log.info("Saved {} posts, {} links from comments".format(
                fetcher.posts_saved, fetcher.comments_links_saved
            ))

    iteration = 1

    while True:
        log.info("Start crawl: {} iteration".format(iteration))

        fetcher = Fetcher(session, store_dir)
        future = asyncio.ensure_future(
            check_main_page(fetcher, loop)
        )
        future.add_done_callback(callback)

        log.info("Waiting for {} sec...".format(to_sleep))
        await asyncio.sleep(to_sleep)
        iteration += 1


def set_logging(dir_path: str = "./", verbose: bool = False):
    log_level = log.DEBUG if verbose else log.INFO

    log_path = os.path.join(dir_path, "ycrawler.log")
    file_handler = RotatingFileHandler(
        filename=log_path, maxBytes=1000000, backupCount=3, encoding="UTF-8"
    )

    log.basicConfig(
        loggers=[file_handler, log.StreamHandler()],
        level=log_level,
        format='%(asctime)s %(levelname)s %(lineno)d}: %(message)s',
        datefmt='[%H:%M:%S]'
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Async crawler for news.ycombinator.com"
    )
    parser.add_argument(
        '--store_dir',
        type=str,
        required=True,
        help='dir for storing files'
    )
    parser.add_argument(
        '--log_dir',
        type=str,
        default="./",
        help='dir for log'
    )
    parser.add_argument(
        '--period',
        type=int,
        default=30,
        help='seconds between checks'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='detailed output'
    )
    args = parser.parse_args()

    return args


def main():
    args = parse_args()
    set_logging(args.log_dir, args.verbose)

    loop = asyncio.get_event_loop()
    with aiohttp.ClientSession(
            loop=loop, raise_for_status=True,
            read_timeout=FETCH_TIMEOUT, conn_timeout=FETCH_TIMEOUT
    ) as session:
        loop.run_until_complete(
            monitor_ycombinator(session, loop, args.period, args.store_dir)
        )

    loop.close()


if __name__ == '__main__':
    pass
