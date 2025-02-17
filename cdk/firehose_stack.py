import cmd

from aws_cdk import App, CfnOutput, Duration, RemovalPolicy, Stack
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_ecr as ecr
from aws_cdk import aws_ecs as ecs
from aws_cdk import aws_ecs_patterns as ecs_patterns
from aws_cdk.aws_ecr_assets import DockerImageAsset, DockerImageAssetInvalidationOptions
from constructs import Construct

from cdk.common_resource_stack import CommonResourceStack
from cdk.defs import BaseStack


class FirehoseStack(BaseStack):
    def __init__(self, scope: Construct, construct_id: str, common_resource: CommonResourceStack, **kwargs) -> None:
        super().__init__(scope, construct_id, common_resource=common_resource, **kwargs)
        self.image_asset = self.build_and_push_image()
        self.create_ecs_service()

    def create_ecs_service(self):
        # Create a cluster
        vpc_name = f'{self.stack_name}-{self.common_resource.stage}-vpc'
        vpc = ec2.Vpc(
            self, 
            id=vpc_name,
            vpc_name=vpc_name,
            ip_addresses=ec2.VpcIpv4CidrBlock(ipv4_cidr_block=self.common_resource.cidr),
            max_azs=2,
            nat_gateways=0,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name='public', subnet_type=ec2.SubnetType.PUBLIC, 
                    cidr_mask=self.common_resource.vpc_mask
                )
            ],
        )
        # Create Fargate Cluster
        cluster_name = f'{self.stack_name}-{self.common_resource.stage}-cluster'
        cluster = ecs.Cluster(self, cluster_name, cluster_name=cluster_name, vpc=vpc)

        # Create Fargate Service
        service_name = f'{self.stack_name}-{self.common_resource.stage}-service'
        fargate_service = ecs_patterns.NetworkLoadBalancedFargateService(
            self, service_name,
            cluster=cluster,
            task_image_options=ecs_patterns.NetworkLoadBalancedTaskImageOptions(
                image=ecs.ContainerImage.fromEcrRepository(self.image_asset.image_uri, self.image_asset.image_tag),
                # TODO add secrets 
                # container_name="firehose",
                # execution_role=self.common_resource.ecs_task_execution_role,
                # task_role=self.common_resource.ecs_task_role,
                # secrets=None,
                # environment=None,
            ),
            platform_version=ecs.FargatePlatformVersion.LATEST,
            public_load_balancer=True,
            enable_execute_command=True,
            enable_ecs_managed_tags=True,
        )

        # Setup AutoScaling policy
        scaling = fargate_service.service.auto_scale_task_count(
            max_capacity=1, 
            min_capacity=self.common_resource.max_capacity
        )
        scaling.scale_on_cpu_utilization("CpuScaling", target_utilization_percent=50)

        CfnOutput(
            self, "LoadBalancerDNS",
            value=fargate_service.load_balancer.load_balancer_dns_name
        )


    # def create_firehose_service_repo(self) -> ecr.Repository:
    #     repo_name = f'{self.common_resource.app_name}-firehose'
    #     return ecr.Repository(
    #         self, 
    #         id=repo_name, 
    #         repository_name=repo_name,
    #         removal_policy=RemovalPolicy.DESTROY,
    #         auto_delete_images=True
    #     )

    def build_and_push_image(self) -> DockerImageAsset:
        # Build the image
        img_name = 'firehose'
        return DockerImageAsset(self, img_name,
            directory=".",
            file="ecs.Dockerfile",
            invalidation=DockerImageAssetInvalidationOptions(build_args=False),
        )
