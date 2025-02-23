import json

from atproto import models

from firehose.listener import ALT_OF_SET_WATERMARK_IMG
from lib.aws.s3 import post_object
from lib.bs.client import get_client
from lib.bs.get_bsky_post_by_url import get_did_from_url, get_rkey_from_url
from lib.log import get_logger
from settings import settings

logger = get_logger(__name__)


def handler(event, context):
    """SQSイベントが差すポストからウォーターマーク画像を特定し、フローを起動する"""
    logger.info(f"Received event: {event}")
    input = json.loads(event["Records"][0]["body"])
    author_did = input.get("author_did")
    client = get_client(settings.BOT_USERID, settings.BOT_APP_PASSWORD)
    rkey = get_rkey_from_url(input.get("uri"))
    did = get_did_from_url(input.get("uri"))
    post = client.get_post(post_rkey=rkey, profile_identify=did)
    for image in post.value.embed.images:
        re = client.com.atproto.repo.get_record(
            models.ComAtprotoRepoGetRecord.Params(
                repo=did, collection="app.bsky.feed.post", rkey=rkey, cid=post.cid
            )
        )

        if "alt" in image.model_fields_set and ALT_OF_SET_WATERMARK_IMG == image.alt:
            url = image.image.ref
            mime_type = image.image.mime_type
            size = image.image.size
            width = image.aspect_ratio.width
            height = image.aspect_ratio.height
            # S3に画像を保存
            post_object(settings.USERINFO_BUCKET_NAME, author_did, image.image.data)
            pass

    return {"message": "OK", "status": 200}


if __name__ == "__main__":
    sample_event = {
        "Records": [
            {
                "messageId": "a32d5df7-d7c6-4f2f-9f02-db7cb20bf67c",
                "receiptHandle": "AQEB7tdHEKllr3H+LxqEjVmk8UE1w2kNcoS4ZBBN2aMWRGTaaJXfNE9vrEz6UHvdj8644/xTd6JyZFOuJmsR9DLr57DxRvBXc6+mzYSf6+1zKKpfM7+hgWphqgWT33xGCh9kFfRtGR1/HAvPoI3HlWdbdnLeMpkxwRXE7pcOJ+XOe65nrDNsejMhn921DO5MuDxMCEM0ZhD2NLY2DEeY3EHqldl6I4nVM9uCSRxXwjr/xdg4q1Df5geaOn47rBRzQAwDugm/cfVP9jSjU6gezxF8c4fTz2UHQ5kntXzV2qJlwawW9HC4pGbRMg+4PmPQW8StlucQSbNyO3HadHu3GzCTleh+jydRfZy5W+kfQ7g/9WgKU/3TkRAYkmWHPS6sg6AORYGVo5lpsRMu3AkegOqNnSQwAPC3zRpsmmV6ATlkxrc=",
                "body": '{"cid": "bafyreiajtjhuqvurnhmxzrwwmbiyr4yobcr27p23fqoadwienqz4rjlyoy", "uri": "at://did:plc:fjxxrpznhne7yw3ranpfboee/app.bsky.feed.post/3lisx3eaggq2q", "author_did": "did:plc:fjxxrpznhne7yw3ranpfboee", "created_at": "2025-02-23T04:00:00.000Z"}',
                "attributes": {
                    "ApproximateReceiveCount": "2",
                    "SentTimestamp": "1740281997436",
                    "SenderId": "AIDA43SZXFH4MN6KJJRM4",
                    "ApproximateFirstReceiveTimestamp": "1740282418247",
                },
                "messageAttributes": {},
                "md5OfBody": "23c9b35fabe32a4f5b56a7333f6be4a0",
                "eventSource": "aws:sqs",
                "eventSourceARN": "arn:aws:sqs:ap-northeast-1:883877685752:wmput-set-watermark-img-queue-dev",
                "awsRegion": "ap-northeast-1",
            }
        ]
    }
    print(handler(sample_event, {}))
