import json
from logging import DEBUG

import boto3
from aws_cdk import CfnOutput, Duration, RemovalPolicy, Stack
from aws_cdk import aws_iam as iam
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_secretsmanager as secretsmanager
from aws_cdk import aws_sqs as sqs
from constructs import Construct
from cryptography.fernet import Fernet


class CommonResourceStack(Stack):
    """共通リソース"""

    stage: str
    env_vars: str
    cidr: str
    vpc_mask: int
    vpc_cidr: str
    max_capacity: int
    image_expiration_days: int
    userinfo_expiration_days: int
    aws_account: str
    app_name: str
    loglevel: str
    max_retries: int

    secret_manager: secretsmanager.ISecret
    original_image_bucket: s3.IBucket
    transformed_image_bucket: s3.IBucket
    userinfo_bucket: s3.IBucket
    followed_queue: sqs.IQueue
    set_watermark_img_queue: sqs.IQueue
    watermarking_queue: sqs.IQueue

    create_ecs_execution_role: iam.IRole
    create_ecs_task_role: iam.IRole

    def __init__(self, scope: Construct, construct_id: str, context_json: dict, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        self.aws_account = Stack.of(self).account
        # context から環境変数を取得
        self.stage = self.node.try_get_context("env")
        env_vars = self.node.try_get_context(self.stage)
        self.loglevel = env_vars.get("loglevel", DEBUG)
        self.cidr = env_vars.get("vpc-cidr")
        self.vpc_cidr = env_vars.get("vpc-cidr")
        self.vpc_mask = int(env_vars.get("vpc-mask"))
        self.max_capacity = int(env_vars.get("max_capacity"))
        self.app_name = env_vars.get("app_name")
        self.max_retries = int(env_vars.get("max_retries"))
        self.image_expiration_days = int(env_vars.get("image_expiration_days"))
        self.userinfo_expiration_days = int(env_vars.get("userinfo_expiration_days"))
        # リソースの作成
        self.secret_manager = self.create_secret_manager()
        self.original_image_bucket = self.create_original_image_bucket()
        self.transformed_image_bucket = self.create_transformed_image_bucket()
        self.userinfo_bucket = self.create_userinfo_bucket()
        self.followed_queue = self.create_followed_queue()
        self.set_watermark_img_queue = self.create_set_watermark_img_queue()
        self.watermarking_queue = self.create_watermarking_quque()
        self.create_ecs_execution_role = self.create_ecs_execution_role()
        self.create_ecs_task_role = self.create_ecs_task_role()

    def _get_exists_secret_manager(self, secret_id):
        """シークレットマネージャーが既存の場合はリソースを取得する"""
        try:
            return secretsmanager.Secret.from_secret_name_v2(
                scope=self, id=secret_id, secret_name=secret_id
            )
        except Exception:
            return None

    def check_secret_exists(self, secret_id: str) -> bool:
        """Secrets Manager にシークレットが存在するかチェック"""
        client = boto3.client("secretsmanager")
        try:
            client.describe_secret(SecretId=secret_id)
            return True
        except client.exceptions.ResourceNotFoundException:
            return False

    def create_secret_manager(self):
        """既存のシークレットがあれば取得し、なければ作成する"""
        secret_id = f"{self.app_name}-secretsmanager-{self.stage}".lower()
        if self.check_secret_exists(secret_id):
            # 既存のシークレットを取得
            CfnOutput(self, "SecretExists", value=f"Using existing secret: {secret_id}")
            return secretsmanager.Secret.from_secret_name_v2(
                self, id=secret_id, secret_name=secret_id
            )
        else:
            # 既存のシークレットがない場合のみ新規作成
            default_secret = json.dumps(
                {
                    "fernet_key": Fernet.generate_key().decode(),
                    "bot_userid": "?????.bsky.social",
                    "bot_app_password": "somepassword",
                }
            )
            CfnOutput(self, "SecretCreated", value=f"Created new secret: {secret_id}")
            return secretsmanager.Secret(
                self,
                secret_id,
                secret_name=secret_id,
                description="A secret for storing credentials",
                removal_policy=RemovalPolicy.RETAIN,
                generate_secret_string=secretsmanager.SecretStringGenerator(
                    secret_string_template=default_secret, generate_string_key="password"
                ),
            )

    def create_original_image_bucket(self):
        """オリジナル画像用バケットの作成"""
        original_bucket_id = (
            f"{self.app_name}-original-imgs-{self.stage}-{self.aws_account}".lower()
        )
        return s3.Bucket(
            scope=self,
            id=original_bucket_id,
            bucket_name=original_bucket_id,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            lifecycle_rules=[
                s3.LifecycleRule(expiration=Duration.days(self.image_expiration_days))
            ],
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
        )

    def create_transformed_image_bucket(self):
        """加工済画像用バケットの作成"""
        transformed_bucket_id = (
            f"{self.app_name}-watermarked-imgs-{self.stage}-{self.aws_account}".lower()
        )
        return s3.Bucket(
            scope=self,
            id=transformed_bucket_id,
            bucket_name=transformed_bucket_id,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            lifecycle_rules=[
                s3.LifecycleRule(expiration=Duration.days(self.image_expiration_days))
            ],
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
        )

    def create_userinfo_bucket(self):
        """ユーザバケットの作成"""
        userinfo_bucket_id = (
            f"{self.app_name}-userinfo-files-{self.stage}-{self.aws_account}".lower()
        )
        return s3.Bucket(
            scope=self,
            id=userinfo_bucket_id,
            bucket_name=userinfo_bucket_id,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            lifecycle_rules=[
                s3.LifecycleRule(expiration=Duration.days(self.userinfo_expiration_days))
            ],
            encryption=s3.BucketEncryption.S3_MANAGED,
        )

    def create_followed_queue(self):
        """フォロー通知用の SQS キューを作成"""
        return sqs.Queue(
            self,
            f"{self.app_name}-followed-queue-{self.stage}",
            queue_name=f"{self.app_name}-followed-queue-{self.stage}",
            visibility_timeout=Duration.seconds(2),
            retention_period=Duration.days(14),
            encryption=sqs.QueueEncryption.KMS_MANAGED,
        )

    def create_set_watermark_img_queue(self):
        """画像加工用の SQS キューを作成"""
        return sqs.Queue(
            self,
            f"{self.app_name}-set-watermark-img-queue-{self.stage}",
            queue_name=f"{self.app_name}-set-watermark-img-queue-{self.stage}",
            visibility_timeout=Duration.seconds(2),
            retention_period=Duration.days(14),
            encryption=sqs.QueueEncryption.KMS_MANAGED,
        )

    def create_watermarking_quque(self):
        """画像加工用の SQS キューを作成"""
        return sqs.Queue(
            self,
            f"{self.app_name}-watermarking-queue-{self.stage}",
            queue_name=f"{self.app_name}-watermarking-queue-{self.stage}",
            visibility_timeout=Duration.seconds(2),
            retention_period=Duration.days(14),
            encryption=sqs.QueueEncryption.KMS_MANAGED,
        )

    def create_ecs_execution_role(self):
        # create execution role
        self.ecs_execution_role = iam.Role(
            self,
            f"{self.app_name}-ecs_execution_role-{self.stage}",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AmazonECSTaskExecutionRolePolicy"
                )
            ],
        )

    def create_ecs_task_role(self):
        self.ecs_task_role = iam.Role(
            self,
            f"{self.app_name}-ecs_task_role-{self.stage}",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSQSFullAccess"),
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonS3FullAccess"),
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSNSFullAccess"),
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonDynamoDBFullAccess"),
            ],
        )
