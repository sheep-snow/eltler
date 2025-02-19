import os

import boto3


def send_followed_to_queue(client: boto3.client, queue_url: str, message: str) -> None:
    try:
        client.send_message(QueueUrl=queue_url, MessageBody=message)
    except Exception as e:
        print(f"Failed to send message to queue: {e}")


def get_sqs_client() -> boto3.client:
    """Get SQS client

    Returns:
        boto3.client: SQS client
    """
    return boto3.client("sqs", region_name=os.getenv("AWS_REGION"))
