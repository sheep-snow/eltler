from atproto import Client


def get_client(identifier:str, password:str)->Client:
    '''Login to the Bsky app

    Args:
        identifier (str): Bluesky User Handle
        password (str): Bluesky User App Password

    Returns:
        atproto.Client: Atproto client object
    SeeAlso:
        https://docs.bsky.app/docs/api/com-atproto-server-create-session
    '''
    client = Client()
    client.login(identifier, password)
    return client

def get_dm_client(identifier:str, password:str)->Client:
    '''Login to the Bsky app

    Args:
        identifier (str): Bluesky User Handle
        password (str): Bluesky User App Password

    Returns:
        atproto.Client: Atproto client object
    SeeAlso:
        https://docs.bsky.app/docs/api/com-atproto-server-create-session
    '''
    return get_client(identifier, password).with_bsky_chat_proxy()
