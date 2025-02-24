from aws_cdk import Duration
from aws_cdk import aws_events as events
from aws_cdk import aws_events_targets as targets
from aws_cdk import aws_lambda as _lambda
from aws_cdk import aws_stepfunctions as sfn
from aws_cdk import aws_stepfunctions_tasks as tasks
from constructs import Construct

from cdk.common_resource_stack import CommonResourceStack
from cdk.defs import BaseStack


class SignoutFlowStack(BaseStack):
    def __init__(self, scope: Construct, construct_id: str, common_resource: CommonResourceStack, **kwargs) -> None:
        super().__init__(scope, construct_id, common_resource=common_resource, **kwargs)
        self.cronrule = self.create_eventbridge_cron_rule()
        self.executor_lambda = self.create_executor_lambda()
        self.getter_lambda = self.create_getter_lambda()
        self.notifier_lambda = self.create_notifier_lambda()
        self.sm_resource = self._get_secrets_manager_resource(common_resource.secret.secret_name)

        # Lambda関数をEventBridgeのターゲットに追加
        self.cronrule.add_target(targets.LambdaFunction(self.executor_lambda))
        # Secrets Managerの利用権限付与
        self.common_resource.secret.grant_read(self.executor_lambda)
        self.common_resource.secret.grant_read(self.getter_lambda)
        self.common_resource.secret.grant_read(self.notifier_lambda)

        # step functionの作成
        self.flow = self.create_workflow(self.getter_lambda, self.notifier_lambda)

    def create_workflow(self, getter_lambda, notifier_lambda):
        # Lambdaタスク定義
        getter_task = tasks.LambdaInvoke(self, "getter", lambda_function=self.getter_lambda, output_path="$.Payload")
        notifier_task = tasks.LambdaInvoke(self, "notifier", lambda_function=self.notifier_lambda, output_path="$.Payload")

        # Mapステート定義
        map_state = sfn.Map(
            self, "MapState",
            items_path="$.items"  # JSON配列を受け取る
        )
        map_state.iterator(getter_task.next(notifier_task))

        # Waitステート
        wait_state = sfn.Wait(
            self, "WaitState",
            time=sfn.WaitTime.seconds_path("$.waitSeconds")
        )

        # ステートマシンの定義
        definition = wait_state.next(map_state)
        return sfn.StateMachine(
            self, "SignoutFlow",
            definition=definition,
            timeout=Duration.minutes(5)
        )


    def create_eventbridge_cron_rule(self) -> events.Rule:
        rule = events.Rule(
            self, "EveryMinuteRule",
            schedule=events.Schedule.cron(
                minute="*/1",
                hour="*"
            )
        )
        self._add_common_tags(rule)
        return rule

    def create_executor_lambda(self) -> _lambda.DockerImageFunction:
        name: str = f"{self.stack_name}-signout-executor"
        code = _lambda.DockerImageCode.from_image_asset(
            directory=".", cmd=["signout.executor.handler"]
        )
        func = _lambda.DockerImageFunction(
            scope=self,
            id=name.lower(),
            function_name=name,
            code=code,
            environment={
                "LOG_LEVEL": self.common_resource.loglevel,
                "MAX_RETRIES": str(self.common_resource.max_retries),
            },
        )
        self._add_common_tags(func)
        return func

    def create_getter_lambda(self) -> _lambda.DockerImageFunction:
        name: str = f"{self.stack_name}-signout-getter"
        code = _lambda.DockerImageCode.from_image_asset(
            directory=".", cmd=["signout.getter.handler"]
        )
        func = _lambda.DockerImageFunction(
            scope=self,
            id=name.lower(),
            function_name=name,
            code=code,
            environment={
                "LOG_LEVEL": self.common_resource.loglevel,
                "MAX_RETRIES": str(self.common_resource.max_retries),
            },
        )
        self._add_common_tags(func)
        return func

    def create_notifier_lambda(self) -> _lambda.DockerImageFunction:
        name: str = f"{self.stack_name}-signout-notifier"
        code = _lambda.DockerImageCode.from_image_asset(
            directory=".", cmd=["signout.notifier.handler"]
        )
        func = _lambda.DockerImageFunction(
            scope=self,
            id=name.lower(),
            function_name=name,
            code=code,
            environment={
                "LOG_LEVEL": self.common_resource.loglevel,
                "MAX_RETRIES": str(self.common_resource.max_retries),
            },
        )
        self._add_common_tags(func)
        return func
