from atproto import models


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
            body = event["Records"][0]["body"]
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
    resp = dm.send_message(
        models.ChatBskyConvoSendMessage.Data(
            convo_id=convo.id, message=models.ChatBskyConvoDefs.MessageInput(text=message)
        )
    )
    leave_convo(dm, convo.id)
    return resp


def leave_convo(dm, convo_id) -> models.ChatBskyConvoLeaveConvo.Response:
    # 見終わったDMは二度と見ないよう会話から脱退する
    return dm.leave_convo(models.ChatBskyConvoLeaveConvo.Data(convo_id=convo_id))
