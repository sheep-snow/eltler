from pathlib import PurePath
from typing import Optional

from atproto import Client, models


def get_did_from_url(url: str) -> Optional[str]:
    url = PurePath(url)
    return url.parts[1]


def get_rkey_from_url(url: str) -> Optional[str]:
    url = PurePath(url)
    return url.parts[3]


def get_post(client: Client, post_rkey, did) -> Optional[models.AppBskyFeedPost.GetRecordResponse]:
    try:
        return client.get_post(post_rkey=post_rkey, profile_identify=did)
    except (ValueError, KeyError) as e:
        print(f"Error fetching post: {e}")
        return None
