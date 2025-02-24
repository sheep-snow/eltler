import json
import os
from io import BytesIO, StringIO
from uuid import uuid4

import boto3
from atproto import Client, IdResolver, models

from firehose.listener import ALT_OF_SET_WATERMARK_IMG
from lib.aws.s3 import post_bytes_object, post_string_object
from lib.bs.client import get_client
from lib.bs.get_bsky_post_by_url import get_did_from_url, get_rkey_from_url
from lib.log import get_logger
from settings import settings

logger = get_logger(__name__)


def _get_authors_pds_client(author_did: str) -> Client:
    resolver = IdResolver()
    did_doc = resolver.did.resolve(author_did)
    # Since the image to be acquired is stored in the PDS in which the author participates, the Client of the PDS to which the author belongs is obtained from the author's DID.
    authors_pds_endpoint = did_doc.service[0].service_endpoint
    return Client(base_url=authors_pds_endpoint)


def handler(event, context):
    """SQSイベントが差すポストからウォーターマーク画像を特定し、フローを起動する"""
    logger.info(f"Received event: {event}")
    input = json.loads(event["Records"][0]["body"])
    sm_arn = os.environ["STATEMACHINE_ARN"]
    sfn_client = boto3.client("stepfunctions")
    rkey = get_rkey_from_url(input.get("uri"))
    did = get_did_from_url(input.get("uri"))
    client = get_client(settings.BOT_USERID, settings.BOT_APP_PASSWORD)
    post = client.get_post(post_rkey=rkey, profile_identify=did)

    author_did = input.get("author_did")
    authors_pds_client = _get_authors_pds_client(author_did)
    for image in post.value.embed.images:
        if "alt" in image.model_fields_set and ALT_OF_SET_WATERMARK_IMG == image.alt:
            blob_cid = image.image.cid.encode()
            blob = authors_pds_client.com.atproto.sync.get_blob(
                models.ComAtprotoSyncGetBlob.Params(cid=blob_cid, did=author_did)
            )
            metadata = json.dumps(
                {
                    "mime_type": image.image.mime_type,
                    "size": image.image.size,
                    "width": image.aspect_ratio.width,
                    "height": image.aspect_ratio.height,
                }
            )
            # S3に画像とそのmetadataのセットを保存
            with BytesIO(blob) as f:
                img_object_name = f"images/{author_did}"
                post_bytes_object(settings.WATERMARKS_BUCKET, img_object_name, f)
                logger.info(f"Saved watermark image to S3 {img_object_name}")
            with StringIO(metadata) as f:
                metadata_obj_name = f"metadatas/{author_did}"
                post_string_object(settings.WATERMARKS_BUCKET, metadata_obj_name, f)
                logger.info(f"Saved metadata to S3 {metadata_obj_name}")
            # 1ポストあたり複数のウォーターマーク画像がある場合、最初に受理したものだけを使ってウォーターマークを設定する
            break

    execution_id = uuid4()
    sfn_client.start_execution(
        stateMachineArn=sm_arn, name=execution_id, input=json.dumps({"convo_id": c.id})
    )
    logger.info(f"Started state machine execution_id=`{execution_id}`")

    return {"message": "OK", "status": 200}


if __name__ == "__main__":
    sample_event = {
        "Records": [
            {
                "body": '{"cid": "xxxxxx", "uri": "at://did:plc:xxxxxxx/app.bsky.feed.post/xxxxxxx", "author_did": "did:plc:xxxxxxxxxx", "created_at": "2025-02-23T14:13:00.709Z"}'
            }
        ]
    }
    handler(sample_event, {})
