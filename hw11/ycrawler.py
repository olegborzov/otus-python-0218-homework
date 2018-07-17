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
        Fetch a URL using aiohttp returning parsed JSON response.
        As suggested by the aiohttp docs we reuse the session.
        """
        try:
            async with self.session.get(url) as response:
                if need_bytes:
                    return await response.read()
                else:
                    return await response.text()
        except aiohttp.ClientError as ex:
            if retry < MAX_RETRIES:
                log.debug("Error on {}, {}: {}. Sleep {} and retry".format(
                    url, type(ex).__name__, ex.args, SEC_BETWEEN_RETRIES
                ))
                asyncio.sleep(SEC_BETWEEN_RETRIES)
                return await self.fetch(url, need_bytes, retry + 1)
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
        if not os.path.exists(dirpath):
            os.makedirs(dirpath)

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
            _url = link.attrs["href"]
            parsed_url = urlparse(_url)
            if parsed_url.scheme and parsed_url.netloc:
                links.append(_url)

        return links
    except aiohttp.ClientError:
        return links


async def crawl_post(url: str, post_id: int, fetcher: Fetcher):
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
            log.error("Error on {} post (id: {}, url: {})".format(
                ind, _id, _url
            ))
            continue

    return posts


async def check_main_page(fetcher: Fetcher):
    try:
        html = await fetcher.fetch(YNEWS_MAIN_URL, need_bytes=False)
    except Exception:
        raise

    posts = parse_main_page(html)
    ready_post_ids = fetcher.get_dir_names()

    not_ready_posts = {}
    for p_id, p_url in posts.items():
        if p_id not in ready_post_ids:
            not_ready_posts[p_id] = p_url
        else:
            log.debug("Post {} already parsed".format(p_id))

    tasks = [
        crawl_post(p_url, p_id, fetcher)
        for p_id, p_url in not_ready_posts.items()
    ]

    try:
        await asyncio.gather(*tasks)
    except Exception as e:
        log.error("Error retrieving comments for top stories: {}".format(e))
        raise


async def monitor_ycombinator(loop: asyncio.AbstractEventLoop,
                              to_sleep: int,
                              store_dir: str):
    """
    Periodically check news.ycombinator.com for new articles.
    Parse articles and links from comments and save to local files
    """

    iteration = 1
    async with aiohttp.ClientSession(
            loop=loop, raise_for_status=True,
            read_timeout=FETCH_TIMEOUT, conn_timeout=FETCH_TIMEOUT
    ) as session:
        while True:
            log.info("Start crawl: {} iteration".format(iteration))

            try:
                fetcher = Fetcher(session, store_dir)
                await check_main_page(fetcher)
            except Exception:
                log.exception("Unrecognized error")
                continue

            log.info("Saved {} posts, {} links from comments".format(
                fetcher.posts_saved, fetcher.comments_links_saved
            ))
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
        handlers=[file_handler, log.StreamHandler()],
        level=log_level,
        format='%(asctime)s %(levelname)s {%(pathname)s:%(lineno)d}: %(message)s',
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
    loop.run_until_complete(
        monitor_ycombinator(loop, args.period, args.store_dir)
    )

    loop.close()


if __name__ == '__main__':
    main()
