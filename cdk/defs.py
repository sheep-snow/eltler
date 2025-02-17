from aws_cdk import Aws, Stack, Tags
from aws_cdk import aws_secretsmanager as _sm
from constructs import Construct

from cdk.common_resource_stack import CommonResourceStack


class BaseStack(Stack):

    common_resource: CommonResourceStack

    def __init__(self, scope: Construct, id: str, common_resource: CommonResourceStack, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
        self.common_resource = common_resource

    def _add_common_tags(self, resource: Construct) -> None:
        Tags.of(resource).add("Application", self.common_resource.app_name)


    def _get_secrets_manager_resource(self, secret_name: str) -> _sm.Secret:
        ssm_arn = (
            f"arn:aws:secretsmanager:{self.region}:{self.account}:secret:{secret_name}"
        )
        self.sm_resource = _sm.Secret.from_secret_partial_arn(
            scope=self, id="secret", secret_partial_arn=ssm_arn
        )
