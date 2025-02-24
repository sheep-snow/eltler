import json
from io import StringIO

from lib.aws.s3 import post_string_object
from lib.log import get_logger
from settings import settings

logger = get_logger(__name__)

bucket_name = settings.USERINFO_BUCKET_NAME


def handler(event, context):
    """S3バケットに空のユーザファイルを新規作成する"""
    logger.info(f"Received event: {event}")
    did = event["did"]
    if not did.startswith("did:plc:"):
        raise ValueError(f"Invalid did: {did}")
    with StringIO(json.dumps({})) as f:
        post_string_object(bucket_name, f"{did}", f)
        logger.info(f"Created user file: {did} to {bucket_name}")
    return {"did": did}


if __name__ == "__main__":
    sample_event = [{"body": '{"did": "did:plc:e4pwxsrsghzjud5x7pbe6t65"}'}]
    handler(sample_event, {})
