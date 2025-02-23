from lib.bs.client import get_dm_client
from lib.bs.convos import send_dm_to_did
from lib.log import get_logger
from settings import settings

logger = get_logger(__name__)

msg = """ユーザー登録を開始します。アプリパスワードをこのチャット（DM）に送ってください。
方法は https://xxxxx.com/help#reg-apppasswd で確認できます。"""


def handler(event, context):
    """ユーザにアプリパスワードの提供をDMで依頼する"""
    logger.info(f"Received event: {event}")

    body = event["Records"][0]["body"]
    did = body["did"]
    client = get_dm_client(settings.BOT_USERID, settings.BOT_APP_PASSWORD)
    send_dm_to_did(client.chat.bsky.convo, did, msg)
    return {"message": "OK", "status": 200}


# if __name__ == "__main__":
#     print(handler({}, {}))
