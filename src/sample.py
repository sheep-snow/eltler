from atproto import IdResolver, models

from lib.bs.client import get_dm_client
from settings import settings

USERNAME = settings.BOT_USERID
PASSWORD = settings.BOT_APP_PASSWORD


def main() -> None:
    """Main function to demonstrate how to use the SDK.

    See:
        https://github.com/MarshalX/atproto/blob/main/examples/advanced_usage/direct_messages.py
    """
    # create client proxied to Bluesky Chat service
    dm_client = get_dm_client(USERNAME, PASSWORD)
    # create shortcut to convo methods
    dm = dm_client.chat.bsky.convo

    convo_list = dm.list_convos()  # use limit and cursor to paginate
    print(f"Your conversations ({len(convo_list.convos)}):")
    for convo in convo_list.convos:
        member = convo.members[0]
        print(f"convo-id=`{convo.id}`, did=`{member.did}`")

    # create resolver instance with in-memory cache
    id_resolver = IdResolver()
    # resolve DID
    chat_to = id_resolver.handle.resolve(member.handle)

    # create or get conversation with chat_to
    convo = dm.get_convo_for_members(
        models.ChatBskyConvoGetConvoForMembers.Params(members=[chat_to]),
    ).convo

    print(f"\nConvo ID: {convo.id}")
    print("Convo members:")
    for member in convo.members:
        print(f"- {member.display_name} ({member.did})")

    # send a message to the conversation
    dm.send_message(
        models.ChatBskyConvoSendMessage.Data(
            convo_id=convo.id,
            message=models.ChatBskyConvoDefs.MessageInput(
                text="Hello from Python SDK!",
            ),
        )
    )
    print("\nMessage sent!")


if __name__ == "__main__":
    main()
