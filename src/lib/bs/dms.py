from atproto import Client, IdResolver, models


def get_unread_dms(client) -> None:
    '''未読のDMを取得する

    Args:
        client (_type_): _description_
    See:
        https://atproto.blue/en/latest/dm.html
    '''

    # create client proxied to Bluesky Chat service
    dm_client = client.with_bsky_chat_proxy()
    # create shortcut to convo methods
    dm = dm_client.chat.bsky.convo

    convo_list = dm.list_convos()  # use limit and cursor to paginate
    print(f'Your conversations ({len(convo_list.convos)}):')
    for convo in convo_list.convos:
        members = ', '.join(member.display_name for member in convo.members)
        print(f'- ID: {convo.id} ({members})')

    # create resolver instance with in-memory cache
    id_resolver = IdResolver()
    # resolve DID
    chat_to = id_resolver.handle.resolve('test.marshal.dev')
