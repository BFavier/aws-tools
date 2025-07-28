"""
This module was automatically generated from aws_tools.asynchrone.ecs
"""
from aws_tools._async_tools import _run_async, _async_iter_to_sync, _sync_iter_to_async
from aws_tools.asynchrone.ecs import get_session, Literal, Iterable, AsyncIterable, ClientError, session, run_fargate_task_async, stop_fargate_task_async, tasks_are_running_async, task_is_running


def tasks_are_running(cluster_name: str, task_arns: Iterable[str], chunk_size: int = 100) -> Iterable:
    """
    Returns whether the given tasks are running, by querying aws by batch
    """
    return _async_iter_to_sync(tasks_are_running_async(cluster_name=cluster_name, task_arns=task_arns, chunk_size=chunk_size))


def run_fargate_task(cluster_name: str, task_definition: str, subnet_ids: list[str], security_group_arn: str, vCPU: Literal['0.25', '0.5', 1, 2, 4, 8, 16], memory_MiB: int, disk_space_GiB: int = 20, environment_variables: dict = {}, fargate_platform_version: str = '1.4.0') -> str:
    """
    Run a standalone task on an ECS cluster.
    Returns the running task arn.
    """
    return _run_async(run_fargate_task_async(cluster_name=cluster_name, task_definition=task_definition, subnet_ids=subnet_ids, security_group_arn=security_group_arn, vCPU=vCPU, memory_MiB=memory_MiB, disk_space_GiB=disk_space_GiB, environment_variables=environment_variables, fargate_platform_version=fargate_platform_version))


def stop_fargate_task(cluster_name: str, task_arn: str, reason: str = 'Stopped by user') -> bool:
    """
    Stops a running ECS Fargate task.
    If the task did not exist, returns False.
    """
    return _run_async(stop_fargate_task_async(cluster_name=cluster_name, task_arn=task_arn, reason=reason))


def task_is_running(cluster_name, task_arn: str) -> bool:
    """
    Returns whether the given taks is running
    """
    return _run_async(task_is_running(cluster_name=cluster_name, task_arn=task_arn))
