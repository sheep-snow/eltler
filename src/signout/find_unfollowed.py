from atproto import Client, models

from lib.aws.sqs import get_sqs_client
from lib.bs.client import get_client
from lib.log import get_logger
from settings import settings

logger = get_logger(__name__)


def get_followers(client: Client):
    # This is an example for get_follows method.
    cursor = None
    followers = []

    while True:
        fetched: models.AppBskyGraphGetFollowers.Response = client.get_followers(
            actor=client.me.did, cursor=cursor
        )
        followers = followers + fetched.followers
        if not fetched.cursor:
            break
        cursor = fetched.cursor
    return set([i.did for i in followers])


def get_follows(client: Client):
    # This is an example for get_follows method.
    cursor = None
    follows = []

    while True:
        fetched: models.AppBskyGraphGetFollows.Response = client.get_follows(
            actor=client.me.did, cursor=cursor
        )
        follows = follows + fetched.follows
        if not fetched.cursor:
            break
        cursor = fetched.cursor
    return set([i.did for i in follows])


def handler(event, context):
    logger.info(f"Received event: {event}")
    client = get_client(settings.BOT_USERID, settings.BOT_APP_PASSWORD)
    # フォローしているがフォローされていないユーザーを取得
    unfollowers = get_follows(client).difference(get_followers(client))
    sqs = get_sqs_client()
    for unfollower in unfollowers:
        sqs.send_message(QueueUrl=settings.SIGNOUT_QUEUE_URL, MessageBody={"did": unfollower})
        logger.info(f"Send did {unfollower} to the SQS")

    return {"message": "OK", "status": 200}


if __name__ == "__main__":
    print(handler({}, {}))
