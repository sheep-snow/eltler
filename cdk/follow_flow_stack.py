from aws_cdk import Duration
from aws_cdk import aws_events as events
from aws_cdk import aws_events_targets as targets
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as _lambda
from aws_cdk import aws_pipes as pipes
from aws_cdk import aws_stepfunctions as sfn
from aws_cdk import aws_stepfunctions_tasks as tasks
from constructs import Construct

from cdk.common_resource_stack import CommonResourceStack
from cdk.defs import BaseStack


class FollowFlowStack(BaseStack):
    def __init__(
        self, scope: Construct, construct_id: str, common_resource: CommonResourceStack, **kwargs
    ) -> None:
        super().__init__(scope, construct_id, common_resource=common_resource, **kwargs)
        self.cronrule = self.create_eventbridge_cron_rule()
        self.executor_lambda = self.create_executor_lambda()
        self.common_resource.followed_queue.grant_send_messages(self.executor_lambda)
        self.touch_user_file_lambda = self.create_touch_user_file_lambda()
        self.followback_lambda = self.create_followback_lambda()

        # Lambda関数をEventBridgeのターゲットに追加
        self.cronrule.add_target(targets.LambdaFunction(self.executor_lambda))
        # Secrets Managerの利用権限付与
        common_resource.secret_manager.grant_read(self.executor_lambda)
        common_resource.secret_manager.grant_read(self.touch_user_file_lambda)
        common_resource.secret_manager.grant_read(self.followback_lambda)

        # step functionの作成
        self.flow = self.create_workflow(self.touch_user_file_lambda, self.followback_lambda)
        self.create_eventbridge_pipe()

    def create_eventbridge_pipe(self) -> pipes.CfnPipe:
        """EventBridge Pipes を介してSQSメッセージでステートマシンを起動されるようにする"""
        pipes_role = iam.Role(
            self, "FollowFlowPipesRole", assumed_by=iam.ServicePrincipal("pipes.amazonaws.com")
        )
        self.common_resource.followed_queue.grant_consume_messages(pipes_role)
        self.flow.grant_start_execution(pipes_role)
        pipe_name = f"{self.stack_name}-follow-flow-pipe"
        pipes.CfnPipe(
            self,
            id=pipe_name,
            name=pipe_name,
            role_arn=pipes_role.role_arn,
            source=self.common_resource.followed_queue.queue_arn,
            target=self.flow.state_machine_arn,
            # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-pipes-pipe-pipetargetstatemachineparameters.html
            target_parameters=pipes.CfnPipe.PipeTargetParametersProperty(
                step_function_state_machine_parameters=pipes.CfnPipe.PipeTargetStateMachineParametersProperty(
                    invocation_type="FIRE_AND_FORGET"
                )
            ),
        )

    def create_workflow(self, getter_lambda, notifier_lambda) -> sfn.StateMachine:
        # Lambdaタスク定義
        getter_task = tasks.LambdaInvoke(
            self,
            "TouchUserFile",
            lambda_function=self.touch_user_file_lambda,
            output_path="$.Payload",
        )
        followback_task = tasks.LambdaInvoke(
            self, "Followback", lambda_function=self.followback_lambda, output_path="$.Payload"
        )
        # ステートマシンの定義
        definition = getter_task.next(followback_task)
        return sfn.StateMachine(
            self,
            "FollowFlow",
            definition_body=sfn.DefinitionBody.from_chainable(definition),
            timeout=Duration.minutes(5),
        )

    def create_eventbridge_cron_rule(self) -> events.Rule:
        rule = events.Rule(
            self, "FollowFlowRule", schedule=events.Schedule.cron(minute="*/5", hour="*")
        )
        self._add_common_tags(rule)
        return rule

    def create_executor_lambda(self) -> _lambda.DockerImageFunction:
        name: str = f"{self.stack_name}-follow-executor"
        code = _lambda.DockerImageCode.from_image_asset(
            directory=".", cmd=["follow.executor.handler"]
        )
        func = _lambda.DockerImageFunction(
            scope=self,
            id=name.lower(),
            function_name=name,
            code=code,
            timeout=Duration.seconds(60),
            environment={
                "LOG_LEVEL": self.common_resource.loglevel,
                "FOLLOWED_QUEUE_URL": self.common_resource.followed_queue.queue_url,
                "SECRET_NAME": self.common_resource.secret_manager.secret_name,
            },
        )
        self._add_common_tags(func)
        return func

    def create_touch_user_file_lambda(self) -> _lambda.DockerImageFunction:
        name: str = f"{self.stack_name}-signup-touch_user_file"
        code = _lambda.DockerImageCode.from_image_asset(
            directory=".", cmd=["follow.touch_user_file.handler"]
        )
        func = _lambda.DockerImageFunction(
            scope=self,
            id=name.lower(),
            function_name=name,
            code=code,
            environment={
                "LOG_LEVEL": self.common_resource.loglevel,
                "USERINFO_BUCKET_NAME": self.common_resource.userinfo_bucket.bucket_name,
                "SECRET_NAME": self.common_resource.secret_manager.secret_name,
            },
        )
        self._add_common_tags(func)
        return func

    def create_followback_lambda(self) -> _lambda.DockerImageFunction:
        name: str = f"{self.stack_name}-signup-followback"
        code = _lambda.DockerImageCode.from_image_asset(
            directory=".", cmd=["follow.followback.handler"]
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
        )
        self._add_common_tags(func)
        return func
