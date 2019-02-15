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
SEC_BETWEEN_RETRIES = 3
SENTINEL = "EXIT"


############################
# FETCHER
############################


class Fetcher:
    """
    Provides fetching url, saving url content to file, counting of ready links
    """

    def __init__(self, store_dir: str, lock: asyncio.Lock):
        self.__posts_saved = 0
        self.__comments_links_saved = 0
        self.store_dir = store_dir
        self.lock = lock

    @property
    async def posts_saved(self):
        async with self.lock:
            return self.__posts_saved

    async def inc_posts_saved(self):
        async with self.lock:
            self.__posts_saved += 1

    @property
    async def comments_links_saved(self):
        async with self.lock:
            return self.__comments_links_saved

    async def inc_comments_links_saved(self):
        async with self.lock:
            self.__comments_links_saved += 1

    async def load_and_save(self, url: str, post_id: int, link_id: int):
        """
        Fetch url and save content to file
        """
        try:
            content = await self.fetch(url, need_bytes=True)
            filepath = self.get_path(link_id, post_id)
            self.write_to_file(filepath, content)

            if link_id > 0:
                await self.inc_comments_links_saved()
            else:
                await self.inc_posts_saved()

            log.debug("Fetched and saved link {} for post {}: {}".format(
                link_id, post_id, url
            ))
        except aiohttp.ClientError:
            pass

    async def fetch(self,
                    url: str,
                    need_bytes: bool = True,
                    retry: int = 0) -> (bytes, str):
        """
        Fetch an URL using aiohttp returning parsed JSON response.
        As suggested by the aiohttp docs we reuse the session.
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if need_bytes:
                        return await response.read()
                    else:
                        return await response.text()
        except aiohttp.ClientError as ex:
            if retry < MAX_RETRIES:
                log.debug("{}, {}: {}. Sleep {} sec and retry".format(
                    url, type(ex).__name__, ex.args, SEC_BETWEEN_RETRIES
                ))
                asyncio.sleep(SEC_BETWEEN_RETRIES)
                return await self.fetch(url, need_bytes, retry+1)
            else:
                log.error("Can't parse url {}. {}: {}".format(
                    url, type(ex).__name__, ex.args
                ))
                raise

    def get_path(self, link_id: int, post_id: int) -> str:
        if link_id > 0:
            filename = "{}_{}.html".format(post_id, link_id)
        else:
            filename = "{}.html".format(post_id)
        filepath = os.path.join(self.store_dir, str(post_id), filename)
        return filepath

    def create_dirs(self, path: str):
        dirpath = os.path.dirname(path)
        os.makedirs(dirpath, exist_ok=True)

    def get_dir_names(self) -> Set[int]:
        """
        Return child dirs from given dir (ready post ids)
        """
        self.create_dirs(self.store_dir)

        post_ids = set()
        for subdir_name in os.listdir(self.store_dir):
            if os.path.isdir(os.path.join(self.store_dir, subdir_name)):
                try:
                    post_id = int(subdir_name)
                    post_ids.add(post_id)
                except ValueError:
                    msg = "Wrong subdir name (should be number): {}"
                    log.warning(msg.format(subdir_name))

        return post_ids

    def write_to_file(self, path: str, content: bytes):
        """
        Save binary content to file
        """
        try:
            self.create_dirs(path)
            with open(path, "wb") as f:
                f.write(content)
        except OSError as ex:
            log.error("Can't save file {}. {}: {}".format(
                path, type(ex).__name__, ex.args
            ))
            return


############################
# CRAWL POSTS WORKER
############################


async def crawl_posts_worker(w_id: int,
                             fetcher: Fetcher,
                             queue: asyncio.Queue):
    """
    Fetch links from comments to article and save to local file
    """
    while True:
        task = await queue.get()
        if task == SENTINEL:
            log.warning("Worker {} got SENTINEL - exit".format(w_id))
            return
        else:
            post_id, url = task

        ready_post_ids = fetcher.get_dir_names()
        if post_id in ready_post_ids:
            log.debug("Post {} already saved".format(post_id))
            continue

        comments_links = await get_links_from_comments(post_id, fetcher)
        links = [url] + comments_links
        log.debug("Worker {} - found {} links in post {}".format(
            w_id, len(links), post_id
        ))

        tasks = [
            fetcher.load_and_save(link, post_id, ind)
            for ind, link in enumerate(links)
        ]

        await asyncio.gather(*tasks)


async def get_links_from_comments(post_id: int, fetcher: Fetcher) -> List[str]:
    """
    Fetch comments page and parse links from comments
    """
    url = YNEWS_POST_URL_TEMPLATE.format(id=post_id)
    links = set()
    try:
        html = await fetcher.fetch(url, need_bytes=False)

        soup = BeautifulSoup(html, "html5lib")
        for link in soup.select(".comment a[rel=nofollow]"):
            _url = link.attrs["href"]
            parsed_url = urlparse(_url)
            if parsed_url.scheme and parsed_url.netloc:
                links.add(_url)

        return list(links)
    except aiohttp.ClientError:
        return list(links)


############################
# CHECK MAIN PAGE WORKER
############################


async def monitor_ycombinator(fetcher: Fetcher,
                              queue: asyncio.Queue,
                              to_sleep: int,
                              num_workers: int):
    """
    Periodically check news.ycombinator.com for new articles.
    Parse articles and links from comments and save to local files
    """

    iteration = 1
    while True:
        log.info("Start crawl: {} iteration".format(iteration))

        try:
            await check_main_page(fetcher, queue)
        except Exception:
            log.exception("Unrecognized error -> close all workers and exit")
            for _ in range(num_workers):
                await queue.put(SENTINEL)
            return

        posts_saved = await fetcher.posts_saved
        comments_links_saved = await fetcher.comments_links_saved
        log.info("Saved {} posts, {} links from comments".format(
            posts_saved, comments_links_saved
        ))
        log.info("Waiting for {} sec...".format(to_sleep))
        await asyncio.sleep(to_sleep)
        iteration += 1


async def check_main_page(fetcher: Fetcher, queue: asyncio.Queue):
    html = await fetcher.fetch(YNEWS_MAIN_URL, need_bytes=False)

    posts = parse_main_page(html)
    ready_post_ids = fetcher.get_dir_names()

    not_ready_posts = {}
    for p_id, p_url in posts.items():
        if p_id not in ready_post_ids:
            not_ready_posts[p_id] = p_url
        else:
            log.debug("Post {} already parsed".format(p_id))

    for p_id, p_url in not_ready_posts.items():
        await queue.put((p_id, p_url))


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
            log.error("Error on {} post (id: {}, url: {})".format(
                ind, _id, _url
            ))
            continue

    return posts


############################
# MAIN
############################


def main():
    args = parse_args()
    set_logging(args.log_dir, args.verbose)

    loop = asyncio.get_event_loop()

    lock = asyncio.Lock(loop=loop)
    fetcher = Fetcher(store_dir=args.store_dir, lock=lock)
    queue = asyncio.Queue(loop=loop)

    workers = [
        crawl_posts_worker(i, fetcher, queue)
        for i in range(args.workers)
    ]
    workers.append(
        monitor_ycombinator(fetcher, queue, args.period, args.workers)
    )

    loop.run_until_complete(asyncio.gather(*workers))


def set_logging(dir_path: str = "./", verbose: bool = False):
    log_level = log.DEBUG if verbose else log.INFO

    log_path = os.path.join(dir_path, "ycrawler.log")
    file_handler = RotatingFileHandler(
        filename=log_path, maxBytes=1000000, backupCount=3, encoding="UTF-8"
    )

    log.basicConfig(
        handlers=[file_handler, log.StreamHandler()],
        level=log_level,
        format='%(asctime)s %(levelname)s '
               '{%(pathname)s:%(lineno)d}: %(message)s',
        datefmt='[%H:%M:%S]'
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Async crawler for news.ycombinator.com"
    )
    parser.add_argument(
        '--store_dir',
        type=str,
        default="./ynews/",
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
        '--workers',
        type=int,
        default=3,
        help='number of workers to process urls'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='detailed output'
    )
    args = parser.parse_args()

    return args


if __name__ == '__main__':
    main()
