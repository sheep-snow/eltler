from atproto import models

from lib.bs.client import get_client
from lib.log import get_logger
from settings import settings

logger = get_logger(__name__)


def handler(event, context):
    """フォローバックする"""
    logger.info(f"Received event: {event}")

    client = get_client(settings.BOT_USERID, settings.BOT_APP_PASSWORD)
    follows = client.get_follows(settings.BOT_USERID)
    body = event.Records[0]["body"]
    did = body["did"]
    if did in [f.did for f in follows.follows]:
        return {"message": f"User-DID `{did}` has already followed", "status": 200}

    resp: models.AppBskyGraphFollow.CreateRecordResponse = client.follow(did)
    return {"message": "Followback Succeeded.", "cid": resp.cid, "uri": resp.uri, "status": 200}


if __name__ == "__main__":
    print(handler({}, {}))
