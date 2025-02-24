import json

from atproto import Client

from lib.aws.sqs import get_sqs_client
from lib.log import get_logger
from settings import settings

logger = get_logger(__name__)


def handler(event, context):
    """通知からフォローを取得しフォロワーのdidをSQSに投げる"""
    logger.info(f"Received event: {event}")
    client = Client()
    client.login(settings.BOT_USERID, settings.BOT_APP_PASSWORD)

    # save the time in UTC when we fetch notifications
    last_seen_at = client.get_current_time_iso()
    response = client.app.bsky.notification.list_notifications()
    if len(response.notifications) == 0:
        logger.info("notifications not found.")
        return {"message": "OK", "status": 200}

    sqs_client = get_sqs_client()
    for notification in response.notifications:
        if not notification.is_read and notification.reason == "follow":
            try:
                logger.info(
                    f"found followed notification from `{notification.author.display_name}`"
                )
                body = json.dumps({"did": notification.author.did})

                response = sqs_client.send_message(
                    QueueUrl=settings.FOLLOWED_QUEUE_URL, MessageBody=body
                )
                logger.info(
                    f"Message sent to SQS, message id: {response['MessageId']}, body: {body}"
                )
            except Exception as e:
                logger.warning(f"Failed to send message to SQS: `{e}`")
    # mark notifications as processed (isRead=True)
    client.app.bsky.notification.update_seen({"seen_at": last_seen_at})
    logger.info(f"Successfully process notification. Last seen at: {last_seen_at}")
    return {"message": "OK", "status": 200}


if __name__ == "__main__":
    handler({}, {})
