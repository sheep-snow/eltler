from lib.bs.client import get_dm_client
from lib.bs.convos import send_dm_to_did
from lib.log import get_logger
from settings import settings

logger = get_logger(__name__)

msg = """サインアップが完了しました!
次は、あなたのウォーターマーク画像を登録してください。
登録法は https://xxxxx.com/ で確認できます。"""


def handler(event, context):
    body = event.Records[0]["body"]
    did = body["did"]
    client = get_dm_client(settings.BOT_USERID, settings.BOT_APP_PASSWORD)
    send_dm_to_did(client.chat.bsky.convo, did, msg)
    return {"message": "OK", "status": 200}


if __name__ == "__main__":
    print(handler({}, {}))
