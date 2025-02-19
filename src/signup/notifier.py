from lib.bs.client import get_dm_client
from lib.bs.convos import leave_convo, send_dm
from lib.log import get_logger
from settings import settings

logger = get_logger(__name__)


def handler(event, context):
    """Lambda handler."""
    convo_id = event["convo_id"]
    dm_client = get_dm_client(settings.BOT_USERID, settings.BOT_APP_PASSWORD)
    send_dm(dm_client.chat.bsky.convo, convo_id)
    leave_convo(dm_client.chat.bsky.convo, convo_id)
    return {"message": "OK", "status": 200}


if __name__ == "__main__":
    print(handler({}, {}))
