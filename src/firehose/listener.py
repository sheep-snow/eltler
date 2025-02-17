from atproto import CAR, FirehoseSubscribeReposClient, models, parse_subscribe_repos_message

client = FirehoseSubscribeReposClient()

def on_message_handler(message):
    '''watermarkerタグを含む投稿をListenする

    Args:
        message (_type_): _description_
    Examples:
        https://github.com/MarshalX/atproto/tree/main/examples/firehose
    '''
    commit = parse_subscribe_repos_message(message)

    if not isinstance(commit, models.ComAtprotoSyncSubscribeRepos.Commit):
        return
    
    if not commit.blocks:
        return
    
    car = CAR.from_bytes(commit.blocks)
    for op in commit.ops:
        if op.action in ["create"] and op.cid:
            data = car.blocks.get(op.cid)

            if data['$type'] == 'app.bsky.feed.post':
                text = data['text']

                if 'watermarker' in text:
                    print(text)


def main(*args, **kwargs):
    client.start(on_message_handler)