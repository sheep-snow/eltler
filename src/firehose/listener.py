"""Bluesky Firehose Listener

See:
    https://github.com/MarshalX/atproto/blob/main/examples/firehose/process_commits.py
"""

import json
import multiprocessing
import signal
import time
from collections import defaultdict
from types import FrameType
from typing import Any

from atproto import (
    CAR,
    AtUri,
    FirehoseSubscribeReposClient,
    firehose_models,
    models,
    parse_subscribe_repos_message,
)

from lib.log import logger

_INTERESTED_RECORDS = {
    models.ids.AppBskyFeedPost: models.AppBskyFeedPost,  # Posts
    models.ids.AppBskyGraphFollow: models.AppBskyGraphFollow,  # Follows
}


def on_callback_error_handler(error: BaseException) -> None:
    """Error handler for the callback

    Args:
        error (BaseException): Error object
    """
    logger.error("Got error!", error)


def _get_ops_by_type(commit: models.ComAtprotoSyncSubscribeRepos.Commit) -> defaultdict:
    """Get operations by type

    Args:
        commit (models.ComAtprotoSyncSubscribeRepos.Commit): Commit object

    Returns:
        defaultdict: Operations by type
    """
    operation_by_type = defaultdict(lambda: {"created": [], "deleted": []})

    car = CAR.from_bytes(commit.blocks)
    for op in commit.ops:
        if op.action == "update":
            # not supported yet
            continue

        uri = AtUri.from_str(f"at://{commit.repo}/{op.path}")

        if op.action == "create":
            if not op.cid:
                continue

            create_info = {"uri": str(uri), "cid": str(op.cid), "author": commit.repo}

            record_raw_data = car.blocks.get(op.cid)
            if not record_raw_data:
                continue

            record = models.get_or_create(record_raw_data, strict=False)
            record_type = _INTERESTED_RECORDS.get(uri.collection)
            if record_type and models.is_record_type(record, record_type):
                operation_by_type[uri.collection]["created"].append(
                    {"record": record, **create_info}
                )

        if op.action == "delete":
            operation_by_type[uri.collection]["deleted"].append({"uri": str(uri)})

    return operation_by_type


def worker_main(cursor_value: multiprocessing.Value, pool_queue: multiprocessing.Queue) -> None:
    """Worker main function

    Args:
        cursor_value (multiprocessing.Value): value of the cursor
        pool_queue (multiprocessing.Queue): Queue object
    """
    signal.signal(signal.SIGINT, signal.SIG_IGN)  # we handle it in the main process

    while True:
        message = pool_queue.get()

        commit = parse_subscribe_repos_message(message)
        if not isinstance(commit, models.ComAtprotoSyncSubscribeRepos.Commit):
            continue

        if commit.seq % 20 == 0:
            cursor_value.value = commit.seq

        if not commit.blocks:
            continue

        ops = _get_ops_by_type(commit)

        for created_post in ops[models.ids.AppBskyFeedPost]["created"]:
            # TODO implement it
            # https://atproto.blue/en/latest/atproto/atproto_client.models.app.bsky.feed.post.html
            author = created_post["author"]
            record = created_post["record"]
            inlined_text = record.text.replace("\n", " ")
            # when a new post is captured
            logger.info(
                f"NEW POST [CREATED_AT={record.created_at}][AUTHOR={author}]: {inlined_text}"
            )

        for follow in ops[models.ids.AppBskyGraphFollow]["created"]:
            # TODO implement it
            # https://pub.dev/documentation/lexicon/latest/docs/appBskyGraphFollow-constant.html
            payload = json.dumps(
                {
                    "cid": follow["cid"],
                    "uri": follow["uri"],
                    "follower_did": follow["author"],
                    "followed_did": follow["record"].subject,
                    "created_at": follow["record"].created_at,
                }
            )
            logger.info(f"NEW FOLLOW: {payload}")


def get_firehose_params(
    cursor_value: multiprocessing.Value,
) -> models.ComAtprotoSyncSubscribeRepos.Params:
    """Get firehose params

    Args:
        cursor_value (multiprocessing.Value): Cursor value

    Returns:
        models.ComAtprotoSyncSubscribeRepos.Params: Firehose params
    """
    return models.ComAtprotoSyncSubscribeRepos.Params(cursor=cursor_value.value)


def measure_events_per_second(func: callable) -> callable:
    """Measure events per second

    Args:
        func (callable): Function

    Returns:
        callable: Wrapper function
    """

    def wrapper(*args) -> Any:
        wrapper.calls += 1
        cur_time = time.time()

        if cur_time - wrapper.start_time >= 1:
            logger.info(f"NETWORK LOAD: {wrapper.calls} events/second")
            wrapper.start_time = cur_time
            wrapper.calls = 0

        return func(*args)

    wrapper.calls = 0
    wrapper.start_time = time.time()

    return wrapper


def signal_handler(_: int, __: FrameType) -> None:
    """Signal handler"""
    logger.info(
        "Keyboard interrupt received. Waiting for the queue to empty before terminating processes..."
    )

    # Stop receiving new messages
    client.stop()

    # Drain the messages queue
    while not queue.empty():
        logger.info("Waiting for the queue to empty...")
        time.sleep(0.2)

    logger.info("Queue is empty. Gracefully terminating processes...")

    pool.terminate()
    pool.join()
    # exit the main process gracefully.
    logger.info("Listener stopped gracefully, Bye!")
    exit(0)


if __name__ == "__main__":
    logger.info("Starting listener...")
    signal.signal(signal.SIGINT, signal_handler)

    start_cursor = None

    params = None
    cursor = multiprocessing.Value("i", 0)
    if start_cursor is not None:
        cursor = multiprocessing.Value("i", start_cursor)
        params = get_firehose_params(cursor)

    client = FirehoseSubscribeReposClient(params)

    # workers_count = multiprocessing.cpu_count() * 2 - 1
    workers_count = 1
    max_queue_size = 10000

    queue = multiprocessing.Queue(maxsize=max_queue_size)
    pool = multiprocessing.Pool(workers_count, worker_main, (cursor, queue))

    @measure_events_per_second
    def on_message_handler(message: firehose_models.MessageFrame) -> None:
        if cursor.value:
            # we are using updating the cursor state here because of multiprocessing
            # typically you can call client.update_params() directly on commit processing
            client.update_params(get_firehose_params(cursor))

        queue.put(message)

    client.start(on_message_handler, on_callback_error_handler)
