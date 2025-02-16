from logging import INFO, getLogger

logger = getLogger()
logger.setLevel(INFO)


def get_message() -> str:
    return "Hello from testcode!"


def handler(event, context):
    """Lambda handler."""
    msg = get_message()
    logger.info(msg)
    return {"message": "OK", "status": 200}


# for local debugging
if __name__ == "__main__":
    print(get_message())
