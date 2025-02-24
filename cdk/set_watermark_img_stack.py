from aws_cdk import Duration, aws_lambda_event_sources
from aws_cdk import aws_lambda as _lambda
from aws_cdk import aws_stepfunctions as sfn
from aws_cdk import aws_stepfunctions_tasks as tasks
from constructs import Construct

from cdk.common_resource_stack import CommonResourceStack
from cdk.defs import BaseStack


class SetWatermarkImgStack(BaseStack):
    def __init__(
        self, scope: Construct, construct_id: str, common_resource: CommonResourceStack, **kwargs
    ) -> None:
        super().__init__(scope, construct_id, common_resource=common_resource, **kwargs)
        self.executor_lambda = self.create_executor_lambda()
        self.executor_lambda.add_event_source(
            aws_lambda_event_sources.SqsEventSource(self.common_resource.set_watermark_img_queue)
        )
        self.notifier_lambda = self.create_notifier_lambda()

        # Secrets Managerの利用権限付与
        self.common_resource.secret_manager.grant_read(self.executor_lambda)
        self.common_resource.secret_manager.grant_read(self.notifier_lambda)

        # S3バケットの利用権限付与
        self.common_resource.watermarks_bucket.grant_read_write(self.executor_lambda)
        self.common_resource.watermarks_bucket.grant_read_write(self.notifier_lambda)

        # step functionの作成
        self.flow = self.create_workflow(self.notifier_lambda)
        self.executor_lambda.add_environment("STATEMACHINE_ARN", self.flow.state_machine_arn)

    def create_workflow(self, notifier_lambda) -> sfn.StateMachine:
        # Lambdaタスク定義
        notifier_task = tasks.LambdaInvoke(self, "notifier", lambda_function=self.notifier_lambda)

        return sfn.StateMachine(
            self,
            "set_watermark_imgFlow",
            definition_body=sfn.DefinitionBody.from_chainable(notifier_task),
            timeout=Duration.minutes(5),
        )

    def create_executor_lambda(self) -> _lambda.DockerImageFunction:
        name: str = f"{self.stack_name}-set_watermark_img-executor"
        code = _lambda.DockerImageCode.from_image_asset(
            directory=".", cmd=["set_watermark_img.executor.handler"]
        )
        func = _lambda.DockerImageFunction(
            scope=self,
            id=name.lower(),
            function_name=name,
            code=code,
            environment={
                "LOG_LEVEL": self.common_resource.loglevel,
                "SECRET_NAME": self.common_resource.secret_manager.secret_name,
                "WATERMARKS_BUCKET": self.common_resource.watermarks_bucket.bucket_name,
            },
            timeout=Duration.seconds(30),
            memory_size=256,
            retry_attempts=0,
        )
        self._add_common_tags(func)
        return func

    def create_notifier_lambda(self) -> _lambda.DockerImageFunction:
        name: str = f"{self.stack_name}-set_watermark_img-notifier"
        code = _lambda.DockerImageCode.from_image_asset(
            directory=".", cmd=["set_watermark_img.notifier.handler"]
        )
        func = _lambda.DockerImageFunction(
            scope=self,
            id=name.lower(),
            function_name=name,
            code=code,
            environment={
                "LOG_LEVEL": self.common_resource.loglevel,
                "SECRET_NAME": self.common_resource.secret_manager.secret_name,
                "WATERMARKS_BUCKET": self.common_resource.watermarks_bucket.bucket_name,
            },
            timeout=Duration.seconds(30),
            memory_size=256,
            retry_attempts=0,
        )
        self._add_common_tags(func)
        return func
