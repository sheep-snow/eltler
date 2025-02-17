from atproto import Client


def login(identifier:str, password:str)->Client:
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
