import re

from atproto import models

from lib.fernet import encrypt
from settings import settings

app_pass_pattern = re.compile(
    r"^\s*([a-zA-Z0-9]{4}-[a-zA-Z0-9]{4}-[a-zA-Z0-9]{4}-[a-zA-Z0-9]{4})\s*$"
)
"""Bluesky アプリパスワードの正規表現"""


def get_app_password_from_convo(dm, convo_id) -> str:
    convo = dm.get_convo(models.ChatBskyConvoGetConvo.ParamsDict(convo_id=convo_id)).convo
    convo_sender_did = [
        member.did for member in convo.members if member.handle != settings.BOT_USERID
    ].pop()
    messages = dm.get_messages(
        models.ChatBskyConvoGetMessages.ParamsDict(convo_id=convo.id)
    ).messages

    # TODO convo.id 単位の処理になるようSQSに convo_id を送信する処理を実装する。以下の処理はSQSのサブスクライバのLambdaに移譲する
    for m in messages:
        if m.sender.did == convo_sender_did and app_pass_pattern.match(m.text):
            encrypted_app_password = encrypt(app_pass_pattern.match(m.text).group(1))
            message_text = m.text
            sender_did = m.sender.did
            sent_at = m.sent_at
            message_id = m.id
            print(
                f"id {message_id}, text: {message_text}, from: {sender_did}, at: {sent_at}, passwd: {encrypted_app_password}"
            )


def send_dm_to_did(dm, did, message) -> models.ChatBskyConvoDefs.MessageView:
    """_summary_

    Args:
        dm (_type_): _description_
        did (_type_): _description_
        message (_type_): _description_

    Returns:
        models.ChatBskyConvoDefs.MessageView: _description_
    Usage:
        ```
        from lib.bs.client import get_dm_client
        from lib.bs.convos import send_dm_to_did
        from lib.log import get_logger
        from settings import settings

        logger = get_logger(__name__)

        msg = "xxxx"


        def handler(event, context):
            body = event.Records[0]["body"]
            did = body["did"]
            client = get_dm_client(settings.BOT_USERID, settings.BOT_APP_PASSWORD)
            send_dm_to_did(client.chat.bsky.convo, did, msg)
            return {"message": "OK", "status": 200}


        if __name__ == "__main__":
            print(handler({}, {}))
        ```
    """
    convo = dm.get_convo_for_members(
        models.ChatBskyConvoGetConvoForMembers.Params(members=[did])
    ).convo
    return dm.send_message(
        models.ChatBskyConvoSendMessage.Data(
            convo_id=convo.id, message=models.ChatBskyConvoDefs.MessageInput(text=message)
        )
    )


def send_dm(dm, convo_id=None) -> models.ChatBskyConvoDefs.MessageView:
    msg = """"🙌🏻アプリパスワードを受信しました。
    サインアップ完了後に使い方をDMでお知らせしますのでお待ち下さい!
    この会話からは退出して頂いてかまいません。"""
    return dm.send_message(
        models.ChatBskyConvoSendMessage.Data(
            convo_id=convo_id, message=models.ChatBskyConvoDefs.MessageInput(text=msg)
        )
    )


def leave_convo(dm, convo_id) -> models.ChatBskyConvoLeaveConvo.Response:
    # 見終わったDMは二度と見ないよう会話から脱退する
    return dm.leave_convo(models.ChatBskyConvoLeaveConvo.Data(convo_id=convo_id))
