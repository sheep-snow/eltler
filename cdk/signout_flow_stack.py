from aws_cdk import Duration
from aws_cdk import aws_events as events
from aws_cdk import aws_events_targets as targets
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as _lambda
from aws_cdk import aws_pipes as pipes
from aws_cdk import aws_sqs as sqs
from aws_cdk import aws_stepfunctions as sfn
from aws_cdk import aws_stepfunctions_tasks as tasks
from constructs import Construct

from cdk.common_resource_stack import CommonResourceStack
from cdk.defs import BaseStack


class SignoutFlowStack(BaseStack):
    def __init__(
        self, scope: Construct, construct_id: str, common_resource: CommonResourceStack, **kwargs
    ) -> None:
        super().__init__(scope, construct_id, common_resource=common_resource, **kwargs)
        self.cronrule = self.create_eventbridge_cron_rule()
        self.signout_queue = self.create_signout_queue()
        self.find_unfollowed_lambda = self.create_find_unfollowed_lambda()
        # Lambda関数をEventBridgeのターゲットに追加
        self.cronrule.add_target(targets.LambdaFunction(self.find_unfollowed_lambda))
        self.signout_queue.grant_send_messages(self.find_unfollowed_lambda)
        self.find_unfollowed_lambda.add_environment(
            "SIGNOUT_QUEUE_URL", self.signout_queue.queue_url
        )

        # state machineのLambda関数  delete_user_files_lambda, delete_watermarks_lambda, send_dm_lambda
        self.del_userfiles_lambda = self.create_del_userfiles_lambda()
        self.del_watermarks_lambda = self.create_delete_watermarks_lambda()
        self.send_dm_lambda = self.create_send_dm_lambda()

        # Secrets Managerの利用権限付与
        self.common_resource.secret_manager.grant_read(self.find_unfollowed_lambda)
        self.common_resource.secret_manager.grant_read(self.del_userfiles_lambda)
        self.common_resource.secret_manager.grant_read(self.del_watermarks_lambda)
        self.common_resource.secret_manager.grant_read(self.send_dm_lambda)
        self.del_userfiles_lambda.add_environment(
            "USERINFO_BUCKET_NAME", self.common_resource.userinfo_bucket.bucket_name
        )
        self.del_watermarks_lambda.add_environment(
            "WATERMARKS_BUCKET_NAME", self.common_resource.watermarks_bucket.bucket_name
        )

        # step functionの作成
        self.flow = self.create_workflow(
            self.del_userfiles_lambda, self.del_watermarks_lambda, self.send_dm_lambda
        )
        self.find_unfollowed_lambda.add_environment(
            "STATE_MACHINE_ARN", self.flow.state_machine_arn
        )

        self.create_eventbridge_pipe(self.signout_queue)

    def create_eventbridge_pipe(self, src_sqs: sqs.IQueue) -> pipes.CfnPipe:
        """EventBridge Pipes を介してSQSメッセージでステートマシンを起動されるようにする"""
        pipes_role = iam.Role(
            self, "SignOutFlowPipesRole", assumed_by=iam.ServicePrincipal("pipes.amazonaws.com")
        )
        self.common_resource.followed_queue.grant_consume_messages(pipes_role)
        self.flow.grant_start_execution(pipes_role)
        pipe_name = f"{self.stack_name}-signout-flow-pipe"
        pipes.CfnPipe(
            self,
            id=pipe_name,
            name=pipe_name,
            role_arn=pipes_role.role_arn,
            source=src_sqs.queue_arn,
            source_parameters=pipes.CfnPipe.PipeSourceParametersProperty(
                sqs_queue_parameters=pipes.CfnPipe.PipeSourceSqsQueueParametersProperty(
                    batch_size=1
                )
            ),
            target=self.flow.state_machine_arn,
            # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-pipes-pipe-pipetargetstatemachineparameters.html
            target_parameters=pipes.CfnPipe.PipeTargetParametersProperty(
                step_function_state_machine_parameters=pipes.CfnPipe.PipeTargetStateMachineParametersProperty(
                    invocation_type="FIRE_AND_FORGET"
                )
            ),
        )

    def create_signout_queue(self) -> sqs.Queue:
        name = f"{self.common_resource.app_name}-signout-queue-{self.common_resource.stage}"
        return sqs.Queue(
            self, name, visibility_timeout=Duration.seconds(60), retention_period=Duration.days(14)
        )

    def create_workflow(self, delete_user_files_lambda, delete_watermarks_lambda, send_dm_lambda):
        # Lambdaタスク定義
        delete_user_files_task = tasks.LambdaInvoke(
            self,
            "DelUserfile",
            lambda_function=delete_user_files_lambda,
            input_path="$.[0].body",
            output_path="$",
        )
        delete_watermarks_task = tasks.LambdaInvoke(
            self,
            "DelWatermarks",
            lambda_function=delete_watermarks_lambda,
            input_path="$.Payload",
            output_path="$",
        )
        send_dm_task = tasks.LambdaInvoke(
            self, "SendDM", lambda_function=send_dm_lambda, input_path="$.Payload", output_path="$"
        )

        # ステートマシンの定義
        definition = delete_user_files_task.next(delete_watermarks_task).next(send_dm_task)
        return sfn.StateMachine(
            self,
            "SignoutFlow",
            definition_body=sfn.DefinitionBody.from_chainable(definition),
            timeout=Duration.minutes(5),
        )

    def create_eventbridge_cron_rule(self) -> events.Rule:
        rule = events.Rule(
            self, "EveryMinuteRule", schedule=events.Schedule.rate(Duration.minutes(5))
        )
        self._add_common_tags(rule)
        return rule

    def create_find_unfollowed_lambda(self) -> _lambda.DockerImageFunction:
        name: str = f"{self.common_resource.app_name}-signout-executor-{self.common_resource.stage}"
        code = _lambda.DockerImageCode.from_image_asset(
            directory=".", cmd=["signout.find_unfollowed.handler"]
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

    def create_del_userfiles_lambda(self) -> _lambda.DockerImageFunction:
        name: str = (
            f"{self.common_resource.app_name}-signout-del_userfiles-{self.common_resource.stage}"
        )
        code = _lambda.DockerImageCode.from_image_asset(
            directory=".", cmd=["signout.delete_user_files.handler"]
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

    def create_delete_watermarks_lambda(self) -> _lambda.DockerImageFunction:
        name: str = (
            f"{self.common_resource.app_name}-signout-del_watermarks-{self.common_resource.stage}"
        )
        code = _lambda.DockerImageCode.from_image_asset(
            directory=".", cmd=["signout.delete_watermarks.handler"]
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

    def create_send_dm_lambda(self) -> _lambda.DockerImageFunction:
        name: str = f"{self.common_resource.app_name}-send_dm-{self.common_resource.stage}"
        code = _lambda.DockerImageCode.from_image_asset(
            directory=".", cmd=["signout.send_dm.handler"]
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
