"""Bluesky Firehose Listener

See:
    https://github.com/MarshalX/atproto/blob/main/examples/firehose/process_commits.py
"""

import json
import multiprocessing
import os
import signal
import time
from collections import defaultdict
from types import FrameType
from typing import Any

import boto3
from atproto import (
    CAR,
    AtUri,
    FirehoseSubscribeReposClient,
    firehose_models,
    models,
    parse_subscribe_repos_message,
)

from lib.aws.sqs import get_sqs_client
from lib.bs.client import get_client
from lib.log import logger
from settings import settings

_INTERESTED_RECORDS = {
    models.ids.AppBskyFeedPost: models.AppBskyFeedPost,  # Posts
    models.ids.AppBskyGraphFollow: models.AppBskyGraphFollow,  # Follows
}

sqs_client: boto3.client = None

TAG_OF_SET_WATERMARK_IMG = "wmset"

FOLLOWED_QUEUE_URL = os.getenv("FOLLOWED_QUEUE_URL")
SET_WATERMARK_IMG_QUEUE_URL = os.getenv("SET_WATERMARK_IMG_QUEUE_URL")
WATERMARKING_QUEUE_URL = os.getenv("WATERMARKING_QUEUE_URL")

FOLLOWED_LIST_UPDATE_INTERVAL_SECS = 300
"""フォロワーテーブルを更新する間隔"""

MEASURE_EVENT_INTERVAL_SECS = 10
"""イベントの計測間隔"""

current_followers = set()
"""listener稼働中を通じて更新され続けるフォロワー"""


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


def _is_post_has_image(record) -> bool:
    """Check if the post has an image"""
    is_followers_post = True  # TODO implement it

    if (
        is_followers_post
        and "embed" in record.model_fields_set
        and "images" in record.embed.model_fields_set
        and "mime_type" in record.embed.image.model_fields_set
        and record.embed.image.mime_type.startswith("image/")
    ):
        return True
    else:
        return False


def _is_watermarking_post(record) -> bool:
    """Check if the record has an image"""
    if _is_post_has_image(record) and "tags" in record.model_fields_set:
        return True
    else:
        return False


def _is_set_watermark_img_post(record) -> bool:
    """Check if the record has new watermark image"""
    if _is_watermarking_post(record) and TAG_OF_SET_WATERMARK_IMG in record.tags:
        return True
    else:
        return False


def _followed_to_bot(record) -> bool:
    """Check if the followed DID is a bot user"""
    return record.startswith("did:at:bot:")


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

        # for created_post in ops[models.ids.AppBskyFeedPost]["created"]:
        #     # TODO implement it
        #     # https://atproto.blue/en/latest/atproto/atproto_client.models.app.bsky.feed.post.html
        #     record = created_post["record"]
        #     if _is_watermarking_post(record) is False:
        #         continue
        #     sqs_client.send_message(
        #         QueueUrl="https://sqs.ap-south-1.amazonaws.com/123456789012/MyQueue",
        #         MessageBody=json.dumps(
        #             {
        #                 "cid": created_post["cid"],
        #                 "uri": created_post["uri"],
        #                 "author_did": created_post["author"],
        #                 "created_at": record.created_at,
        #                 "image_url": record.embed.image.url,
        #             }
        #         ),
        #     )

        # for follow in ops[models.ids.AppBskyGraphFollow]["created"]:
        #     # TODO implement it
        #     # https://pub.dev/documentation/lexicon/latest/docs/appBskyGraphFollow-constant.html
        #     payload = json.dumps(
        #         {
        #             "cid": follow["cid"],
        #             "uri": follow["uri"],
        #             "follower_did": follow["author"],
        #             "followed_did": follow["record"].subject,
        #             "created_at": follow["record"].created_at,
        #         }
        #     )
        #     logger.info(f"NEW FOLLOW: {payload}")


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


def update_follower_table_per_interval(func: callable) -> callable:
    """Update follower table per interval"""

    def wrapper(*args) -> Any:
        cur_time = time.time()

        if cur_time - wrapper.start_time >= FOLLOWED_LIST_UPDATE_INTERVAL_SECS:
            # Update the follower table
            # TODO implement getting current follwer of bot user
            # current_follower_in_memory = get_current_follower_of_bot()
            logger.info(f"Update in memory Follower table, {cur_time}")
            wrapper.start_time = cur_time
            wrapper.calls = 0

        return func(*args)

    wrapper.start_time = time.time()

    return wrapper


def measure_events_per_interval(func: callable) -> callable:
    """Measure events per second"""

    def wrapper(*args) -> Any:
        wrapper.calls += 1
        cur_time = time.time()

        if cur_time - wrapper.start_time >= MEASURE_EVENT_INTERVAL_SECS:
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
    sqs_client.stop()

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


def get_followers() -> set:
    cursor = None
    followers = []
    client = get_client(settings.BOT_USERID, settings.BOT_APP_PASSWORD)

    while True:
        fetched = client.get_followers(settings.BOT_USERID, cursor)
        followers = followers + fetched.followers
        if not fetched.cursor:
            break
        cursor = fetched.cursor
    return {f.did for f in followers}


if __name__ == "__main__":
    logger.info("Starting listener...")
    logger.info("Press Ctrl+C to stop the listener.")
    current_followers = get_followers()
    logger.info("Got current followers successfully.")
    sqs_client = get_sqs_client()
    signal.signal(signal.SIGINT, signal_handler)

    start_cursor = None

    params = None
    cursor = multiprocessing.Value("i", 0)
    if start_cursor is not None:
        cursor = multiprocessing.Value("i", start_cursor)
        params = get_firehose_params(cursor)

    sqs_client = FirehoseSubscribeReposClient(params)

    workers_count = multiprocessing.cpu_count() * 2 - 1
    # workers_count = 1 # DEBUG
    max_queue_size = 10000

    queue = multiprocessing.Queue(maxsize=max_queue_size)
    pool = multiprocessing.Pool(workers_count, worker_main, (cursor, queue))

    @update_follower_table_per_interval
    @measure_events_per_interval
    def on_message_handler(message: firehose_models.MessageFrame) -> None:
        if cursor.value:
            # we are using updating the cursor state here because of multiprocessing
            # typically you can call client.update_params() directly on commit processing
            sqs_client.update_params(get_firehose_params(cursor))

        queue.put(message)

    sqs_client.start(on_message_handler, on_callback_error_handler)
