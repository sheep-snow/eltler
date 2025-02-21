from lib.bs.client import get_dm_client
from lib.bs.convos import get_app_password_from_convo
from lib.log import get_logger
from settings import settings

logger = get_logger(__name__)


def handler(event, context):
    """Lambda handler."""
    dm_client = get_dm_client(settings.BOT_USERID, settings.BOT_APP_PASSWORD)
    dm = dm_client.chat.bsky.convo
    get_app_password_from_convo(dm, event["convo_id"])
    return {"message": "OK", "status": 200}


if __name__ == "__main__":
    print(handler({}, {}))
