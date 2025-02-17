from aws_cdk import aws_apigateway as _apigw
from aws_cdk import aws_lambda as _lambda
from constructs import Construct

from cdk.common_resource_stack import CommonResourceStack
from cdk.defs import BaseStack


class ApiStack(BaseStack):

    def __init__(self, scope: Construct, id: str, common_resource: CommonResourceStack, **kwargs) -> None:
        super().__init__(scope, id, common_resource, **kwargs)

        self.sm_resource = self._get_secrets_manager_resource(common_resource.secret.secret_name)
        self.apigw = self.create_api_gateway()
        self.entry_lambda = self.create_entry_lambda()
        self.apigw.root.add_method("POST", _apigw.LambdaIntegration(self.entry_lambda))


    def create_api_gateway(self) -> _apigw.RestApi:
        """API Gatewayを作成する"""
        api_name = f"{self.stack_name}"
        apigw = _apigw.RestApi(self, id=api_name.lower(), rest_api_name=api_name)
        # APIキーを作成する
        key_name = f"{self.stack_name}-api-key"
        api_key = apigw.add_api_key(id=key_name, api_key_name=key_name)
        usage_plan = apigw.add_usage_plan(id=f"{self.stack_name}-usage-plan")
        usage_plan.add_api_key(api_key)
        usage_plan.add_api_stage(stage=apigw.deployment_stage)
        self._add_common_tags(apigw)
        return apigw



    def create_entry_lambda(self) -> _lambda.DockerImageFunction:
        name: str = f"{self.stack_name}-entry"
        code = _lambda.DockerImageCode.from_image_asset(
            directory=".", cmd=["hello.handler"]
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
        # Secrets Managerの利用権限付与
        self.common_resource.secret.grant_read(func)
        return func
