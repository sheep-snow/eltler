import json

from lib.aws.s3 import post_object
from lib.log import get_logger
from settings import settings

logger = get_logger(__name__)

bucket_name = settings.USERINFO_BUCKET_NAME


def handler(event, context):
    logger.info(event)
    body = event.Records[0]["body"]
    did = body["did"]
    if not did.startswith("did:plc:"):
        raise ValueError(f"Invalid did: {did}")
    post_object(bucket_name, f"{did}", json.dumps({}))
    return {"message": "OK", "status": 200}


if __name__ == "__main__":
    print(handler({}, {}))
