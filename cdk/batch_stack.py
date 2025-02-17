import aws_cdk.aws_lambda_event_sources as eventsources
from aws_cdk import Duration, aws_lambda
from aws_cdk import aws_sns as sns
from aws_cdk import aws_sns_subscriptions as subs
from aws_cdk import aws_sqs as sqs
from constructs import Construct

from cdk.common_resource_stack import CommonResourceStack
from cdk.defs import BaseStack


class BatchStack(BaseStack):
    def __init__(self, scope: Construct, construct_id: str, common_resource: CommonResourceStack, **kwargs) -> None:
        super().__init__(scope, construct_id, common_resource=common_resource, **kwargs)

        queue = sqs.Queue(
            self,
            "SampleQueue",
            visibility_timeout=Duration.seconds(300),
        )

        topic = sns.Topic(self, "SampleTopic")

        topic.add_subscription(subs.SqsSubscription(queue))

        # Lambda 関数
        function = aws_lambda.DockerImageFunction(
            scope=self,
            id=f"{self.stack_name}-lambda",
            function_name=f"{self.stack_name}-lambda",
            code=aws_lambda.DockerImageCode.from_image_asset(
                directory=".", cmd=["hello.handler"]
            ),
            timeout=Duration.seconds(9),
            environment={
                "QUEUE_URL": queue.queue_url,
            },
        )
        function.add_event_source(eventsources.SqsEventSource(queue))
