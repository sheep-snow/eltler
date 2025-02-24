from lib.log import get_logger

logger = get_logger(__name__)


def get_message() -> str:
    return "Hello from testcode!"


def handler(event, context):
    """Lambda handler."""
    logger.info(f"Received event: {event}")
    msg = get_message()
    logger.info(msg)
    return {"message": "OK", "status": 200}


# for local debugging
if __name__ == "__main__":
    print(get_message())
