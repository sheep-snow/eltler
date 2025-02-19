import os
from sre_parse import State
from uuid import uuid4

import boto3

from lib.bs.client import get_dm_client
from lib.log import get_logger
from settings import settings

logger = get_logger(__name__)


def handler(event, context):
    """Lambda handler."""
    # Get the list of conversations
    client = get_dm_client(settings.BOT_USERID, settings.BOT_APP_PASSWORD)
    convo_list = client.chat.bsky.convo.list_convos()  # use limit and cursor to paginate
    logger.info(f"Found ({len(convo_list.convos)}) new conversations.")

    # Start the state machine
    sfn_client = boto3.client("stepfunctions")
    for c in convo_list.convos:
        try:
            execution_id = f"{c.id}-{uuid4()}"
            resp = sfn_client.start_execution(
                **{
                    "input": {"convo_id": c.id},
                    "stateMachineArn": os.environ["stateMachineArn"],
                    "name": execution_id,
                }
            )
            logger.info(f"Started state machine for convo_id: {execution_id}")
        except Exception as e:
            logger.error(
                f"Could not start state machine: {e.response['Error']['Code']} {e.response['Error']['Message']}"
            )
    return {"message": "OK", "status": 200}


if __name__ == "__main__":
    print(handler({}, {}))
