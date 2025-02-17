import json
import os
from typing import Any, Optional

from boto3.session import Session
from botocore.exceptions import ClientError

from lib.log import get_logger


class GettingSecretsFailedError(BaseException):
    """"""


class SecretNameIsEmptyError(BaseException):
    """"""


def get_secret(secret_name: Optional[str] = None) -> Any:
    """Get Secrets from AWS KMS

    Returns:
        Optional[Any]: Pairs of Key and Value of Secrets
    """
    logger = get_logger(__name__)
    logger.debug("get_secret begin.")
    if not secret_name or len(secret_name) == 0 or secret_name == str(None):
        raise SecretNameIsEmptyError("secret_name `secret_name` is invalid.")
    sn = secret_name
    logger.debug(f"Getting secret_name: `{sn}`")
    region_name = os.getenv("AWS_REGION_NAME", default="ap-northeast-1")

    # Create a Secrets Manager client
    session = Session()
    client = session.client(service_name="secretsmanager", region_name=region_name)

    # In this sample we only handle the specific exceptions for the 'GetSecretValue' API.
    # See https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
    # We rethrow the exception by default.

    try:
        get_secret_value_response = client.get_secret_value(SecretId=sn)
    except ClientError as e:
        if e.response["Error"]["Code"] == "DecryptionFailureException":
            # Secrets Manager can't decrypt the protected secret text using the provided KMS key.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response["Error"]["Code"] == "InternalServiceErrorException":
            # An error occurred on the server side.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response["Error"]["Code"] == "InvalidParameterException":
            # You provided an invalid value for a parameter.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response["Error"]["Code"] == "InvalidRequestException":
            # You provided a parameter value that is not valid for the current state of the resource.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response["Error"]["Code"] == "ResourceNotFoundException":
            # We can't find the resource that you asked for.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
    else:
        # Decrypts secret using the associated KMS CMK.
        # Depending on whether the secret is a string or binary, one of these fields will be populated.
        if get_secret_value_response.get("SecretString"):
            secret = dict(json.loads(get_secret_value_response["SecretString"]))
            logger.debug(f"Got Secret keys: {secret.keys()}")
            return secret
        else:
            raise GettingSecretsFailedError("SecretString is not got but empty.")
