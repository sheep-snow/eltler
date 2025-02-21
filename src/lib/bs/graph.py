from venv import logger

import atproto
from atproto import models

from lib.bs.client import get_client
from settings import settings

logger = logger.get_logger(__name__)


def is_follower(client: atproto.Client, did: str) -> bool:
    """Check if the event is a follow event"""
    resp: models.AppBskyGraphGetFollowers.Response = client.get_followers(settings.BOT_USERID)
    if len([i for i in resp.followers if i.did == did]) > 0:
        return True
    else:
        return False
