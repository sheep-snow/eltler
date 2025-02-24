from lib.bs.client import get_dm_client
from lib.bs.convos import send_dm_to_did
from lib.log import get_logger
from settings import settings

logger = get_logger(__name__)

msg = """"""


def handler(event, context):
    """ユーザにアプリパスワードの提供をDMで依頼する"""
    logger.info(f"Received event: {event}")

    did = event["did"]
    client = get_dm_client(settings.BOT_USERID, settings.BOT_APP_PASSWORD)
    send_dm_to_did(client.chat.bsky.convo, did, msg)
    return {"did": did}


# if __name__ == "__main__":
#     print(handler({}, {}))
