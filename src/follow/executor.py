from atproto import Client

from lib.aws.sqs import get_sqs_client
from lib.log import get_logger
from settings import settings

logger = get_logger(__name__)


def handler(event, context):
    """Lambda handler."""
    client = Client()
    client.login(settings.BOT_USERID, settings.BOT_APP_PASSWORD)

    # save the time in UTC when we fetch notifications
    last_seen_at = client.get_current_time_iso()
    sqs_client = get_sqs_client()

    response = client.app.bsky.notification.list_notifications()
    for notification in response.notifications:
        if not notification.is_read and notification.reason == "follow":
            try:
                sqs_client.send_message(
                    QueueUrl=settings.FOLLOW_QUEUE_URL,
                    MessageBody={"follower": notification.author.did},
                )
            except Exception:
                logger.warning("Failed to send message to SQS")
                continue
    # mark notifications as processed (isRead=True)
    client.app.bsky.notification.update_seen({"seen_at": last_seen_at})
    logger.info("Successfully process notification. Last seen at:", last_seen_at)
    return {"message": "OK", "status": 200}


if __name__ == "__main__":
    print(handler({}, {}))
