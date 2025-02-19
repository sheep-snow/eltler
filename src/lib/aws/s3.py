import os

import boto3


def get_all_objects(bucket):
    """Get all objects in the bucket"""
    s3 = boto3.client("s3", region_name=os.getenv("AWS_REGION"))
    continuation_token = None
    while True:
        if continuation_token is None:
            res = s3.list_objects_v2(Bucket=bucket, MaxKeys=2)
        else:
            res = s3.list_objects_v2(Bucket=bucket, ContinuationToken=continuation_token)

        if res["KeyCount"] == 0:
            break

        for content in res["Contents"]:
            yield content

        # ContinuationTokenが渡されなかったらそこで終わり
        continuation_token = res.get("NextContinuationToken")
        if continuation_token is None:
            break


def put_object(bucket, key, body):
    """Put object to the bucket"""
    s3 = boto3.client("s3", region_name=os.getenv("AWS_REGION"))
    s3.put_object(Bucket=bucket, Key=key, Body=body)


def delete_object(bucket, key):
    """Delete object from the bucket"""
    s3 = boto3.client("s3", region_name=os.getenv("AWS_REGION"))
    s3.delete_object(Bucket=bucket, Key=key)
