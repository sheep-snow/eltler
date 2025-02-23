from atproto import Client, models


def post(client: Client):
    with open("cat.jpg", "rb") as f:
        img_data = f.read()

        upload = client.upload_blob(img_data)
        images = [models.AppBskyEmbedImages.Image(alt="Img alt", image=upload.blob)]
        embed = models.AppBskyEmbedImages.Main(images=images)

        client.com.atproto.repo.create_record(
            models.ComAtprotoRepoCreateRecord.Data(
                repo=client.me.did,
                collection=models.ids.AppBskyFeedPost,
                record=models.AppBskyFeedPost.Record(
                    created_at=client.get_current_time_iso(), text="Text of the post", embed=embed
                ),
            )
        )

        post = models.AppBskyFeedPost.Record(
            text="Text of the post", embed=embed, created_at=client.get_current_time_iso()
        )
        client.app.bsky.feed.post.create(client.me.did, post)
        client.send_image(text="Text of the post", image=img_data, image_alt="Img alt")
