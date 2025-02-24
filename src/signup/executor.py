import json
import os
from typing import Optional
from uuid import uuid4

import atproto
import boto3
from atproto import models

from lib.bs.client import get_client, get_dm_client
from lib.bs.convos import leave_convo
from lib.log import get_logger
from settings import settings

logger = get_logger(__name__)


LOOP_LIMITATION = 5
"""単一実行内で処理する最大会話数"""


def get_followers_did(client: atproto.Client, did: str) -> set[Optional[str]]:
    resp: models.AppBskyGraphGetFollowers.Response = client.get_followers(client.me.did)
    return {i.did for i in resp.followers}


def handler(event, context):
    """新規に開始された会話を処理するStatemachineを実行する"""
    logger.info(f"Received event: {event}")
    sm_arn = os.environ["STATEMACHINE_ARN"]
    if sm_arn is None:
        raise ValueError("STATEMACHINE_ARN is not set.")

    # Get the list of conversations
    convo_client = get_dm_client(settings.BOT_USERID, settings.BOT_APP_PASSWORD)
    convo_list = convo_client.chat.bsky.convo.list_convos()  # use limit and cursor to paginate
    logger.info(f"Found ({len(convo_list.convos)}) new conversations.")
    client = get_client(settings.BOT_USERID, settings.BOT_APP_PASSWORD)
    followers = get_followers_did(client, client.me.did)

    # Start the state machine
    sfn_client = boto3.client("stepfunctions")
    for c in convo_list.convos[:LOOP_LIMITATION]:
        if c.members[0].did not in followers:
            leave_convo(convo_client, c.id)
            logger.info(f"Skip and leave the conversation because the user is not follower {c.id}.")
            continue
        try:
            execution_id = f"{c.id}-{uuid4()}"
            sfn_client.start_execution(
                stateMachineArn=sm_arn, name=execution_id, input=json.dumps({"convo_id": c.id})
            )
            logger.info(f"Started state machine for convo_id: {execution_id}")
        except Exception as e:
            logger.error(
                f"Could not start state machine: {e.response['Error']['Code']} {e.response['Error']['Message']}"
            )
    return {"statusCode": 200, "body": "OK"}


if __name__ == "__main__":
    handler({}, {})
