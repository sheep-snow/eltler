from atproto import models

from lib.bs.client import get_dm_client
from lib.bs.convos import leave_convo
from lib.log import get_logger
from settings import settings

logger = get_logger(__name__)


msg = """🙌🏻ユーザー登録が終わりました。この会話からは退出して構いません。
次はウォーターマークの登録をお願いします。
なお、フォローを外すことでユーザー登録情報が抹消され利用停止ができます。
使い方は https://xxxxx.com/ で確認できます。
"""


def send_dm(dm, convo_id=None) -> models.ChatBskyConvoDefs.MessageView:
    resp = dm.send_message(
        models.ChatBskyConvoSendMessage.Data(
            convo_id=convo_id, message=models.ChatBskyConvoDefs.MessageInput(text=msg)
        )
    )
    leave_convo(dm, convo_id)
    return resp


def handler(event, context):
    logger.info(f"Received event: {event}")
    convo_id = event["convo_id"]
    dm_client = get_dm_client(settings.BOT_USERID, settings.BOT_APP_PASSWORD)
    send_dm(dm_client.chat.bsky.convo, convo_id)
    leave_convo(dm_client.chat.bsky.convo, convo_id)
    return {"message": "OK", "status": 200}


if __name__ == "__main__":
    print(handler({}, {}))
