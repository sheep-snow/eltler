from aws_cdk import CfnOutput
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_ecs as ecs
from aws_cdk.aws_ecr_assets import DockerImageAsset, DockerImageAssetInvalidationOptions
from constructs import Construct

# from aws_cdk.aws_ecs_patterns import FargateServiceBaseProps
from cdk.common_resource_stack import CommonResourceStack
from cdk.defs import BaseStack


class FirehoseStack(BaseStack):
    def __init__(
        self, scope: Construct, construct_id: str, common_resource: CommonResourceStack, **kwargs
    ) -> None:
        super().__init__(scope, construct_id, common_resource=common_resource, **kwargs)
        self.image_asset = self.build_and_push_image()
        self.create_ecs_service()

    def create_ecs_service(self):
        # Create a cluster
        vpc_name = f"{self.common_resource.app_name}-{self.common_resource.stage}-vpc"
        vpc = ec2.Vpc(
            self,
            id=vpc_name,
            vpc_name=vpc_name,
            ip_addresses=ec2.IpAddresses.cidr(self.common_resource.vpc_cidr),
            max_azs=2,
            nat_gateways=0,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=self.common_resource.vpc_mask,
                )
            ],
        )
        # Create Security Group
        sg_name = f"{self.common_resource.app_name}-{self.common_resource.stage}-ecs-sg"
        sg = ec2.SecurityGroup(
            self, sg_name, vpc=vpc, security_group_name=sg_name, allow_all_outbound=True
        )

        # Create Fargate Cluster
        cluster_name = f"{self.common_resource.app_name}-{self.common_resource.stage}-cluster"
        cluster = ecs.Cluster(
            self,
            cluster_name,
            cluster_name=cluster_name,
            vpc=vpc,
            enable_fargate_capacity_providers=True,
        )
        # ECS Task Definition
        task_name = f"{self.common_resource.app_name}-{self.common_resource.stage}-task"
        task_definition = ecs.FargateTaskDefinition(self, task_name)
        task_definition.add_container(
            "firehose",
            image=ecs.ContainerImage.from_ecr_repository(
                repository=self.image_asset.repository, tag=self.image_asset.image_tag
            ),
            environment={
                "FOLLOWED_QUEUE_URL": self.common_resource.followed_queue.queue_url,
                "SET_WATERMARK_IMG_QUEUE_URL": self.common_resource.followed_queue.queue_url,
                "WATERMARKING_QUEUE_URL": self.common_resource.followed_queue.queue_url,
                "SECRET_NAME": self.common_resource.secret_manager.secret_name,
            },
            # secrets={**self.common_resource.secret_manager.secret_value}, # TODO SecretsManagerの値を与える
        )

        # Create Fargate Service
        service_name = f"{self.common_resource.app_name}-{self.common_resource.stage}-service"
        ecs.FargateService(
            self,
            service_name,
            cluster=cluster,
            task_definition=task_definition,
            min_healthy_percent=100,
            capacity_provider_strategies=[
                ecs.CapacityProviderStrategy(capacity_provider="FARGATE_SPOT", weight=1)
            ],
            security_groups=[sg],
            desired_count=1,
            assign_public_ip=True,
            # execution_role=self.common_resource.ecs_execution_role,
            # task_role=self.common_resource.ecs_task_role,
            enable_ecs_managed_tags=True,
            enable_execute_command=True,
        )

    def build_and_push_image(self) -> DockerImageAsset:
        # Build the image
        img_name = "firehose"
        return DockerImageAsset(
            self,
            img_name,
            directory=".",
            file="ecs.Dockerfile",
            invalidation=DockerImageAssetInvalidationOptions(build_args=False),
        )
