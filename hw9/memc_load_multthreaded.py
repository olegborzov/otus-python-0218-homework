#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import gzip
import sys
import glob
import logging
import collections
from multiprocessing import Queue, Process
from queue import Empty
from typing import List, Dict
from argparse import ArgumentParser
# brew install protobuf
# protoc  --python_out=. ./appsinstalled.proto
# pip install protobuf
import appsinstalled_pb2
# pip install python-memcached
import memcache


AppsInstalled = collections.namedtuple(
    "AppsInstalled", ["dev_type", "dev_id", "lat", "lon", "apps"]
)

NORMAL_ERR_RATE = 0.01
CHUNK_SIZE = 500
TRIES = 3
DELAY = 1
BACKOFF = 2
BLOCK_TIMEOUT = 0.1
SOCKET_TIMEOUT = 2

FLAG_FILE_END = "file_end"
FLAG_SENTINEL = "sentinel"
FLAG_WORKER_READY = "worker_ready"


class MemcacheUpdateWorker(Process):
    def __init__(self,
                 queue: Queue, queue_errors: Queue,
                 memc_addr: str, dry: bool):
        super().__init__()
        self.queue = queue
        self.queue_errors = queue_errors
        self.memc_addr = memc_addr
        self.dry = dry
        self.client = memcache.Client(
            [memc_addr], socket_timeout=SOCKET_TIMEOUT
        )

    def apps_list_from_dict(self, chunk: List) -> Dict:
        chunk_dict = {}
        for app in chunk:
            key = "%s:%s" % (app.dev_type, app.dev_id)
            ua = appsinstalled_pb2.UserApps()
            ua.lat = app.lat
            ua.lon = app.lon
            ua.apps.extend(app.apps)
            value = ua.SerializeToString()
            chunk_dict[key] = value
        return chunk_dict

    def set_multi(self, chunk: List):
        if self.dry:
            logging.debug("{}: set {} keys".format(self.memc_addr, len(chunk)))
            return

        chunk_dict = self.apps_list_from_dict(chunk)
        bad_keys = self.client.set_multi(chunk_dict)
        tries, delay = TRIES, DELAY
        while bad_keys and tries:
            new_chunk_dict = {k: v for k, v in chunk_dict if k in bad_keys}
            bad_keys = self.client.set_multi(new_chunk_dict)
            tries -= 1
            delay *= BACKOFF

        if bad_keys:
            self.queue_errors.put(len(bad_keys))

    def run(self):
        end = False
        chunk = []
        while not end:
            try:
                task = self.queue.get(timeout=BLOCK_TIMEOUT)
            except Empty:
                continue

            file_end = task == FLAG_FILE_END
            end = task == FLAG_SENTINEL

            if not (file_end or end):
                chunk.append(task)

            if len(chunk) == CHUNK_SIZE or file_end:
                self.set_multi(chunk)
                chunk = []

            if file_end:
                logging.debug(
                    "{}: file tasks end".format(self.memc_addr)
                )
                self.queue_errors.put(FLAG_WORKER_READY)

        if chunk:
            self.set_multi(chunk)

        logging.debug(
            "{}: sentinel".format(self.memc_addr)
        )


def dot_rename(path):
    head, fn = os.path.split(path)
    # atomic in most cases
    os.rename(path, os.path.join(head, "." + fn))


def parse_appsinstalled(line):
    line_parts = line.strip().split("\t")
    if len(line_parts) < 5:
        return
    dev_type, dev_id, lat, lon, raw_apps = line_parts
    if not dev_type or not dev_id:
        return
    try:
        apps = [int(a.strip()) for a in raw_apps.split(",")]
    except ValueError:
        apps = [int(a.strip()) for a in raw_apps.split(",") if a.isidigit()]
        logging.info("Not all user apps are digits: `%s`" % line)
    try:
        lat, lon = float(lat), float(lon)
    except ValueError:
        logging.info("Invalid geo coords: `%s`" % line)
    return AppsInstalled(dev_type, dev_id, lat, lon, apps)


def main(args):
    device_memc = {
        "idfa": args.idfa,
        "gaid": args.gaid,
        "adid": args.adid,
        "dvid": args.dvid,
    }

    # Create and start workers with separate queues
    # and a general queue for errors
    queue_errors = Queue()
    workers = {
        dev_type: MemcacheUpdateWorker(
            Queue(), queue_errors, memc_addr, args.dry
        )
        for dev_type, memc_addr in device_memc.items()
    }
    for worker in workers.values():
        worker.start()

    for fn in glob.iglob(args.pattern):
        processed = errors = 0
        logging.info('Processing %s' % fn)
        fd = gzip.open(fn)
        try:
            for line in fd:
                line = line.decode("UTF-8").strip()
                if not line:
                    continue

                appsinstalled = parse_appsinstalled(line)
                if not appsinstalled:
                    errors += 1
                    continue

                memc_addr = device_memc.get(appsinstalled.dev_type)
                if not memc_addr:
                    errors += 1
                    logging.error(
                        "Unknown device type: %s" % appsinstalled.dev_type
                    )
                    continue

                processed += 1
                workers[appsinstalled.dev_type].queue.put(appsinstalled)
                if processed % 100000 == 0:
                    logging.debug("{}: parsed {} lines".format(fn, processed))

            logging.debug("{}: parsed {} lines".format(fn, processed))

            for worker in workers.values():
                worker.queue.put(FLAG_FILE_END)

            workers_ready = 0
            while workers_ready != len(workers):
                try:
                    errors_chunk = queue_errors.get(timeout=BLOCK_TIMEOUT)
                except Empty:
                    continue
                if errors_chunk == FLAG_WORKER_READY:
                    workers_ready += 1
                    continue

                errors += int(errors_chunk)
                processed -= int(errors_chunk)

            logging.debug("All workers ready")

            if processed:
                err_rate = float(errors) / processed
                if err_rate < NORMAL_ERR_RATE:
                    logging.info(
                        "Acceptable error rate (%s). Successfull load" % err_rate
                    )
                else:
                    logging.error(
                        "High error rate (%s > %s). Failed load" % (
                            err_rate, NORMAL_ERR_RATE
                        )
                    )

            dot_rename(fn)
        finally:
            fd.close()

    for worker in workers.values():
        worker.queue.put(FLAG_SENTINEL)


def prototest():
    sample = "idfa\t1rfw452y52g2gq4g\t55.55\t42.42\t" \
             "1423,43,567,3,7,23\ngaid\t7rfw452y52g2gq4g\t" \
             "55.55\t42.42\t7423,424"
    for line in sample.splitlines():
        dev_type, dev_id, lat, lon, raw_apps = line.strip().split("\t")
        apps = [int(a) for a in raw_apps.split(",") if a.isdigit()]
        lat, lon = float(lat), float(lon)
        ua = appsinstalled_pb2.UserApps()
        ua.lat = lat
        ua.lon = lon
        ua.apps.extend(apps)
        packed = ua.SerializeToString()
        unpacked = appsinstalled_pb2.UserApps()
        unpacked.ParseFromString(packed)
        assert ua == unpacked


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument("-t", "--test", action="store_true", default=False)
    parser.add_argument("-l", "--log", action="store", default=None)
    parser.add_argument("--dry", action="store_true", default=False)
    parser.add_argument(
        "--pattern", action="store", default="/data/appsinstalled/*.tsv.gz"
    )
    parser.add_argument("--idfa", action="store", default="127.0.0.1:33013")
    parser.add_argument("--gaid", action="store", default="127.0.0.1:33014")
    parser.add_argument("--adid", action="store", default="127.0.0.1:33015")
    parser.add_argument("--dvid", action="store", default="127.0.0.1:33016")

    args = parser.parse_args()
    logging.basicConfig(
        filename=args.log,
        level=logging.INFO if not args.dry else logging.DEBUG,
        format='[%(asctime)s] %(levelname).1s %(message)s',
        datefmt='%Y.%m.%d %H:%M:%S'
    )

    if args.test:
        prototest()
        sys.exit(0)

    logging.info("Memc loader started with options: %s" % args)

    try:
        main(args)
    except Exception as ex:
        logging.exception("Unexpected error: %s" % ex)
        sys.exit(1)
