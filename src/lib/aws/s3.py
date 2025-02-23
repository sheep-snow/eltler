import os
import re
from io import BytesIO, StringIO

import boto3

s3 = boto3.client("s3", region_name=os.getenv("AWS_REGION"))


def is_exiests_object(bucket_name, key):
    """Check if the object exists in the bucket"""
    try:
        s3.head_object(Bucket=bucket_name, Key=key)
        return True
    except Exception:
        return False


def get_object_keys(bucket_name, regex):
    regex += "$"  # 末尾文字を付与
    obj_list = get_all_objects(bucket_name)
    obj_list = list(filter(lambda x: re.compile(regex).search(x["Key"]), obj_list))
    return obj_list


def get_all_objects(bucket_name):
    """Get all objects in the bucket"""
    continuation_token = None
    while True:
        if continuation_token is None:
            res = s3.list_objects_v2(Bucket=bucket_name, MaxKeys=2)
        else:
            res = s3.list_objects_v2(Bucket=bucket_name, ContinuationToken=continuation_token)

        if res["KeyCount"] == 0:
            break

        for content in res["Contents"]:
            yield content

        # ContinuationTokenが渡されなかったらそこで終わり
        continuation_token = res.get("NextContinuationToken")
        if continuation_token is None:
            break


def put_object(bucket_name, key, body):
    """Overwrite object in the bucket

    See:
        Objectを上書き(PUT)する
    """
    obj = s3.Object(bucket_name, key)
    return obj.put(Body=body)


def delete_object(bucket_name, key):
    """Delete object from the bucket"""
    s3.delete_object(Bucket=bucket_name, Key=key)


def post_bytes_object(bucket_name: str, key: str, body: BytesIO):
    """Creates object to the bucket

    See:
        Objectを新規作成(POST)する
    """
    s3.upload_fileobj(body, bucket_name, key)


def post_string_object(bucket_name: str, key: str, body: StringIO):
    bytes_body = BytesIO(body.getvalue().encode("utf-8"))
    s3.upload_fileobj(bytes_body, bucket_name, key)
