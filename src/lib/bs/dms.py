import re

from atproto import models

from lib.fernet import encrypt

app_pass_pattern = re.compile(
    r"^\s*([a-zA-Z0-9]{4}-[a-zA-Z0-9]{4}-[a-zA-Z0-9]{4}-[a-zA-Z0-9]{4})\s*$"
)
"""Bluesky アプリパスワードの正規表現"""

APP_PASS_RECEIVED_RESPONSE = """"🙌🏻アプリパスワードを受信しました。
サインアップ完了後に使い方をDMでお知らせしますのでお待ち下さい!
この会話からは退出して頂いてかまいません。"""


def get_unread_dms(client) -> None:
    """DMからアプリパスワードを受信し暗号化して保存する"""
    dm_client = client.with_bsky_chat_proxy()
    dm = dm_client.chat.bsky.convo

    convo_list = dm.list_convos()  # use limit and cursor to paginate
    print(f"Your conversations ({len(convo_list.convos)}):")
    for convo in convo_list.convos:
        print(f"getting convo-id: {convo.id}")
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
                # TOOD ユーザ情報バケットにファイルとして保存する処理を追加する
                dm.send_message(
                    models.ChatBskyConvoSendMessage.Data(
                        convo_id=convo.id,
                        message=models.ChatBskyConvoDefs.MessageInput(
                            text=APP_PASS_RECEIVED_RESPONSE
                        ),
                    )
                )
                break
        # 見終わったDMは二度と見ないよう会話から脱退する
        dm.leave_convo(models.ChatBskyConvoLeaveConvo.Data(convo_id=convo.id))


def send_dm(client, convo_id, message) -> None:
    """DMを送信する

    Args:
        client (_type_): _description_
        convo_id (_type_): _description_
        message (_type_): _description_
    See:
        https://atproto.blue/en/latest/dm.html
    """

    # create client proxied to Bluesky Chat service
    dm_client = client.with_bsky_chat_proxy()
    # create shortcut to convo methods
    dm = dm_client.chat.bsky.convo

    # send message
    dm.send_message(convo_id, message)


if __name__ == "__main__":
    from lib.bs.client import get_dm_client
    from settings import settings

    get_unread_dms(get_dm_client(settings.BOT_USERID, settings.BOT_APP_PASSWORD))
