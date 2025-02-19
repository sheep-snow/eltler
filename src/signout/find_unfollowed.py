from lib.log import get_logger

logger = get_logger(__name__)


def handler(event, context):
    """Lambda handler."""
    return {"message": "OK", "status": 200}


if __name__ == "__main__":
    print(handler({}, {}))
