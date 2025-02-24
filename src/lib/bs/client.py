import tempfile
from typing import Optional

from atproto import Client, Session, SessionEvent

temp_file_name = "saved_session.txt"


def get_session() -> Optional[str]:
    try:
        with open(temp_file_name, "r", encoding="UTF-8") as f:
            return f.read()
    except FileNotFoundError:
        return None
    except Exception:
        return None


def save_session(session_string: str) -> None:
    with tempfile.NamedTemporaryFile(mode="w", encoding="UTF-8", delete=False) as f:
        temp_file_name = f.name  # noqa
        f.write(session_string)


def on_session_change(event: SessionEvent, session: Session) -> None:
    print("Session changed:", event, repr(session))
    if event in (SessionEvent.CREATE, SessionEvent.REFRESH):
        print("Saving changed session")
        save_session(session.export())


def get_client(identifier: str, password: str) -> Client:
    """Login to the Bsky app

    Args:
        identifier (str): Bluesky User Handle
        password (str): Bluesky User App Password

    Returns:
        atproto.Client: Atproto client object
    SeeAlso:
        https://docs.bsky.app/docs/api/com-atproto-server-create-session
    """
    client = Client()
    # session reusing configuration
    client.on_session_change(on_session_change)

    session_string = get_session()
    if session_string:
        client.login(session_string=session_string)
    else:
        client.login(identifier, password)

    return client


def get_dm_client(identifier: str, password: str) -> Client:
    """Login to the Bsky app

    Args:
        identifier (str): Bluesky User Handle
        password (str): Bluesky User App Password

    Returns:
        atproto.Client: Atproto client object
    SeeAlso:
        https://docs.bsky.app/docs/api/com-atproto-server-create-session
    """
    return get_client(identifier, password).with_bsky_chat_proxy()
