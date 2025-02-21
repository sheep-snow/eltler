import re
from venv import logger

from atproto import models

from lib.bs.client import get_dm_client
from lib.bs.convos import leave_convo
from lib.fernet import encrypt
from lib.log import get_logger
from settings import settings

logger = get_logger(__name__)


class AppPasswordNotFoundError(Exception):
    pass


app_pass_pattern = re.compile(
    r"^\s*([a-zA-Z0-9]{4}-[a-zA-Z0-9]{4}-[a-zA-Z0-9]{4}-[a-zA-Z0-9]{4})\s*$"
)
"""Bluesky アプリパスワードの正規表現"""


def get_encrypted_app_password_from_convo(dm, convo_id) -> str | None:
    """DMで送られたアプリパスワードを暗号化して取得する"""
    convo = dm.get_convo(models.ChatBskyConvoGetConvo.ParamsDict(convo_id=convo_id)).convo
    convo_sender_did = [
        member.did for member in convo.members if member.handle != settings.BOT_USERID
    ].pop()
    messages = dm.get_messages(
        models.ChatBskyConvoGetMessages.ParamsDict(convo_id=convo.id)
    ).messages

    latest_app_passwd_in_convo = None

    for m in messages:
        if m.sender.did == convo_sender_did and app_pass_pattern.match(m.text):
            latest_app_passwd_in_convo = encrypt(app_pass_pattern.match(m.text).group(1))
            logger.info(
                f"found App Password in Convo, message_id=`{m.id}`, from=`{m.sender.did}`, at=`{m.sent_at}`"
            )
    # 見終わったDMは二度と見ないよう会話から脱退する
    leave_convo(dm, convo_id)
    return latest_app_passwd_in_convo


def handler(event, context):
    logger.info(f"Received event: {event}")
    dm_client = get_dm_client(settings.BOT_USERID, settings.BOT_APP_PASSWORD)
    dm = dm_client.chat.bsky.convo
    enc_passwd = get_encrypted_app_password_from_convo(dm, event["convo_id"])
    if enc_passwd is None:
        # アプリパスワードが見つからなかった場合は例外とし後続処理に流さない
        raise AppPasswordNotFoundError("No encrypted app password")
    return {"message": "OK", "status": 200}


if __name__ == "__main__":
    print(handler({}, {}))
