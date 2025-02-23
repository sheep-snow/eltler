from aws_cdk import Duration
from aws_cdk import aws_events as events
from aws_cdk import aws_events_targets as targets
from aws_cdk import aws_lambda as _lambda
from aws_cdk import aws_sqs as sqs
from aws_cdk import aws_stepfunctions as sfn
from aws_cdk import aws_stepfunctions_tasks as tasks
from constructs import Construct

from cdk.common_resource_stack import CommonResourceStack
from cdk.defs import BaseStack


class SignupFlowStack(BaseStack):
    def __init__(
        self, scope: Construct, construct_id: str, common_resource: CommonResourceStack, **kwargs
    ) -> None:
        super().__init__(scope, construct_id, common_resource=common_resource, **kwargs)

        # # S3バケットにファイルがPOSTされた際に、対象ユーザーにAppPasswordのDM経由の提供を促すDMを送る
        # self.userfile_posted_queue = self.create_userfile_object_posted_queue()
        # self.add_event_notification_to_bucket(
        #     self.common_resource.userfile_bucket, self.userfile_posted_queue
        # )

        self.executor_lambda = self.create_executor_lambda()
        self.getter_lambda = self.create_getter_lambda()
        self.notifier_lambda = self.create_notifier_lambda()

        # Secrets Managerの利用権限付与
        self.common_resource.secret_manager.grant_read(self.executor_lambda)
        self.common_resource.secret_manager.grant_read(self.getter_lambda)
        self.common_resource.secret_manager.grant_read(self.notifier_lambda)

        # step functionの作成
        self.flow = self.create_workflow(self.getter_lambda, self.notifier_lambda)

        # executor lambdaをEventBridgeのターゲットに追加
        self.cronrule = self.create_eventbridge_cron_rule()
        self.cronrule.add_target(targets.LambdaFunction(self.executor_lambda))

    def create_eventbridge_cron_rule(self) -> events.Rule:
        rule = events.Rule(
            self,
            "SignupExecutionRule",
            schedule=events.Schedule.cron(minute="*/2", hour="*"),
            enabled=True,
        )
        self._add_common_tags(rule)
        return rule

    def create_userfile_posted_queue(self) -> sqs.Queue:
        name = f"{self.common_resource.app_name}-userfile-posted-{self.common_resource.stage}"
        queue = sqs.Queue(
            self,
            id=name,
            queue_name=name,
            visibility_timeout=Duration.seconds(2),
            retention_period=Duration.days(14),
        )
        self._add_common_tags(queue)
        return queue

    # def add_event_notification_to_bucket(bucket: s3.IBucket, sqs: sqs.IQueue):
    #     # S3 POST イベント時の通知をSQSに追加
    #     bucket.add_event_notification(s3.EventType.OBJECT_CREATED_POST, s3n.SqsDestination(sqs))

    def create_workflow(self, getter_lambda, notifier_lambda) -> sfn.StateMachine:
        # Lambdaタスク定義
        getter_task = tasks.LambdaInvoke(
            self, "getter", lambda_function=getter_lambda, output_path="$.Payload"
        )
        notifier_task = tasks.LambdaInvoke(
            self, "notifier", lambda_function=notifier_lambda, output_path="$.Payload"
        )
        # ステートマシンの定義
        definition = getter_task.next(notifier_task)
        return sfn.StateMachine(
            self,
            "SignupFlow",
            definition_body=sfn.DefinitionBody.from_chainable(definition),
            timeout=Duration.minutes(5),
        )

    def create_executor_lambda(self) -> _lambda.DockerImageFunction:
        name: str = f"{self.common_resource.app_name}-signup-executor-{self.common_resource.stage}"
        code = _lambda.DockerImageCode.from_image_asset(
            directory=".", cmd=["signup.executor.handler"]
        )
        func = _lambda.DockerImageFunction(
            scope=self,
            id=name.lower(),
            function_name=name,
            code=code,
            environment={
                "LOG_LEVEL": self.common_resource.loglevel,
                "SECRET_NAME": self.common_resource.secret_manager.secret_name,
            },
            timeout=Duration.seconds(60),
            memory_size=256,
            retry_attempts=0,
        )
        self._add_common_tags(func)
        return func

    def create_getter_lambda(self) -> _lambda.DockerImageFunction:
        """conv_id を元にConversation内のメッセージからApp Passwordを取得する"""
        name: str = f"{self.common_resource.app_name}-signup-getter-{self.common_resource.stage}"
        code = _lambda.DockerImageCode.from_image_asset(
            directory=".", cmd=["signup.getter.handler"]
        )
        func = _lambda.DockerImageFunction(
            scope=self,
            id=name.lower(),
            function_name=name,
            code=code,
            environment={
                "LOG_LEVEL": self.common_resource.loglevel,
                "SECRET_NAME": self.common_resource.secret_manager.secret_name,
            },
            timeout=Duration.seconds(30),
            memory_size=256,
            retry_attempts=0,
        )
        self._add_common_tags(func)
        return func

    def create_notifier_lambda(self) -> _lambda.DockerImageFunction:
        name: str = f"{self.common_resource.app_name}-signup-notifier-{self.common_resource.stage}"
        code = _lambda.DockerImageCode.from_image_asset(
            directory=".", cmd=["signup.notifier.handler"]
        )
        func = _lambda.DockerImageFunction(
            scope=self,
            id=name.lower(),
            function_name=name,
            code=code,
            environment={
                "LOG_LEVEL": self.common_resource.loglevel,
                "SECRET_NAME": self.common_resource.secret_manager.secret_name,
            },
            timeout=Duration.seconds(30),
            memory_size=256,
            retry_attempts=0,
        )
        self._add_common_tags(func)
        return func
