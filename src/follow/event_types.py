from typing import TypedDict


class AppBskyGraphFollow(TypedDict):
    """Firehose"""

    author: str
    record: str
    inlined_text: str


class AppBskyFeedPost(TypedDict):
    cid: str
    uri: str
    author_did: str
    content: str
    created_at: str
