from atproto import models

from lib.bs.client import get_client
from lib.log import get_logger
from settings import settings

logger = get_logger(__name__)


def handler(event, context):
    """フォローバックする"""
    logger.info(f"Received event: {event}")
    did = event["did"]
    client = get_client(settings.BOT_USERID, settings.BOT_APP_PASSWORD)
    follows = client.get_follows(settings.BOT_USERID)
    if did in [f.did for f in follows.follows]:
        return {"message": f"User-DID `{did}` has already followed", "status": 200}

    resp: models.AppBskyGraphFollow.CreateRecordResponse = client.follow(did)
    return {"did": did}


if __name__ == "__main__":
    print(handler({}, {}))
