import json
import os

import aws_cdk as cdk
from aws_cdk import Environment

from cdk.api_stack import ApiStack
from cdk.common_resource_stack import CommonResourceStack
from cdk.signout_flow_stack import SignoutFlowStack
from cdk.signup_flow_stack import SignupFlowStack
from src.lib.log import logger

VALID_STAGES=("dev", "prod")
app = cdk.App()

# cdk deploy で指定した context によって stage を決定
if app.node.try_get_context("env") in VALID_STAGES:
    stage = app.node.try_get_context("env")
    context_json = app.node.try_get_context(stage)
else:
    raise ValueError("Please specify the context. i.e. `--context env=dev|prod`")
# cdk.context.json の dev|prod に対応する env_vars を取得
logger.debug(f"env_vars: {json.dumps(context_json)}")
env = Environment(account=os.getenv("CDK_DEFAULT_ACCOUNT"), region=os.getenv("CDK_DEFAULT_REGION"))

app_name = context_json["app_name"]
common_resource = CommonResourceStack(app, f"{app_name}-CommonResourceStack-{stage}", context_json=context_json, env=env)
api = ApiStack(app, f"{app_name}-ApiStack-{stage}", common_resource=common_resource, env=env)
signup = SignupFlowStack(app, f"{app_name}-SignupFlowStack-{stage}", common_resource=common_resource, env=env)
signout = SignoutFlowStack(app, f"{app_name}-SignoutFlowStack-{stage}", common_resource=common_resource, env=env)

app.synth()
