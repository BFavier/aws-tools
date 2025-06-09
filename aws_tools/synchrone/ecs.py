"""
This module was automatically generated from aws_tools.asynchrone.ecs
"""
from aws_tools._async_tools import _run_async, _async_iter_to_sync, _sync_iter_to_async
from aws_tools.asynchrone.ecs import get_session, Literal, session, run_fargate_task_async


def run_fargate_task(cluster_name: str, docker_image_arn: str, task_name: str, subnets_arn: list[str], security_group_arn: str, vCPU: Literal['0.25', '0.5', 1, 2, 4, 8, 16], memoryGB_per_vCPU: int, disk_space: int = 20, environment_variables: dict = {}, fargate_platform_version: str = '1.4.0'):
    """
    run a standalone task on an ECS cluster
    """
    return _run_async(run_fargate_task_async(cluster_name=cluster_name, docker_image_arn=docker_image_arn, task_name=task_name, subnets_arn=subnets_arn, security_group_arn=security_group_arn, vCPU=vCPU, memoryGB_per_vCPU=memoryGB_per_vCPU, disk_space=disk_space, environment_variables=environment_variables, fargate_platform_version=fargate_platform_version))
