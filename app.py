import json
import os

import aws_cdk as cdk
from aws_cdk import Environment

from cdk.common_resource_stack import CommonResourceStack
from cdk.firehose_stack import FirehoseStack
from cdk.follow_flow_stack import FollowFlowStack
from cdk.set_watermark_img_stack import SetWatermarkImgStack
from cdk.signout_flow_stack import SignoutFlowStack
from cdk.signup_flow_stack import SignupFlowStack
from cdk.watermarking_flow_stack import WatermarkingFlowStack
from src.lib.log import logger

VALID_STAGES = ("dev", "prod")
app = cdk.App()

# cdk deploy で指定した context によって stage を決定
if app.node.try_get_context("env") in VALID_STAGES:
    stage = app.node.try_get_context("env")
    ctx = app.node.try_get_context(stage)
else:
    raise ValueError("Please specify the context. i.e. `--context env=dev|prod`")
# cdk.context.json の dev|prod に対応する env_vars を取得
logger.debug(f"env_vars: {json.dumps(ctx)}")
env = Environment(account=os.getenv("CDK_DEFAULT_ACCOUNT"), region=os.getenv("CDK_DEFAULT_REGION"))

app_name = ctx["app_name"]
common = CommonResourceStack(
    app, f"{app_name}-CommonResourceStack-{stage}", context_json=ctx, env=env
)
follow = FollowFlowStack(
    app, f"{app_name}-FollowFlowStack-{stage}", common_resource=common, env=env
)
signup = SignupFlowStack(
    app, f"{app_name}-SignupFlowStack-{stage}", common_resource=common, env=env
)
set_watermark_img = SetWatermarkImgStack(
    app, f"{app_name}-SetWatermarkImgStack-{stage}", common_resource=common, env=env
)
firehose = FirehoseStack(app, f"{app_name}-FirehoseStack-{stage}", common_resource=common, env=env)
watermarking = WatermarkingFlowStack(
    app, f"{app_name}-WatermarkingFlowStack-{stage}", common_resource=common, env=env
)
signout = SignoutFlowStack(
    app, f"{app_name}-SignoutFlowStack-{stage}", common_resource=common, env=env
)

app.synth()
