"""
This module was automatically generated from aws_tools.asynchrone.ecs
"""
from aws_tools._async_tools import _run_async, _async_iter_to_sync, _sync_iter_to_async
from typing import Iterable, Iterator
from aws_tools.asynchrone.ecs import __name__, __doc__, __package__, __loader__, __spec__, __file__, __cached__, __builtins__, get_session, Literal, Iterable, AsyncIterable, Optional, ClientError, session, run_fargate_task_async, stop_fargate_task_async, get_tasks_descriptions_async, TASK_STATUSES, get_tasks_statuses_async, task_is_running_async, task_exists_async, get_task_tags_async


def get_tasks_descriptions(cluster_name: str, task_arns: Iterable[str], chunk_size: int=100) -> Iterable[dict | None]:
    """
    Returns the description of the given tasks, by querying aws by batch. Yield None for non-existant tasks.
    """
    return _async_iter_to_sync(get_tasks_descriptions_async(cluster_name=cluster_name, task_arns=task_arns, chunk_size=chunk_size))


def get_tasks_statuses(cluster_name: str, task_arns: Iterable[str], chunk_size: int=100) -> Iterable[TASK_STATUSES | None]:
    """
    Returns whether the given tasks are running, by querying aws by batch
    """
    return _async_iter_to_sync(get_tasks_statuses_async(cluster_name=cluster_name, task_arns=task_arns, chunk_size=chunk_size))


def get_task_tags(cluster_name: str, task_arn: str) -> dict[str, str] | None:
    """
    Returns the tags of a task. Returns None if the task does not exists.
    """
    return _run_async(get_task_tags_async(cluster_name=cluster_name, task_arn=task_arn))


def run_fargate_task(
        cluster_name: str,
        task_definition: str,
        subnet_ids : list[str],
        security_group_arn: str,
        fargate_platform_version: str = "LATEST",
        tags: dict = {},
        vCPU_override: Literal["0.25", "0.5", 1, 2, 4, 8, 16] | None = None,
        memory_MiB_override: int | None = None,
        disk_GiB_override: int | None = None,
        env_overrides: dict | None = None,
    ) -> dict:
    """
    Run a standalone task on an ECS cluster.
    Returns the running task arn.
    """
    return _run_async(run_fargate_task_async(cluster_name=cluster_name, task_definition=task_definition, subnet_ids=subnet_ids, security_group_arn=security_group_arn, fargate_platform_version=fargate_platform_version, tags=tags, vCPU_override=vCPU_override, memory_MiB_override=memory_MiB_override, disk_GiB_override=disk_GiB_override, env_overrides=env_overrides))


def stop_fargate_task(cluster_name: str, task_arn: str, reason: str="Stopped by user") -> bool:
    """
    Stops a running ECS Fargate task.
    If the task did not exist, returns False.
    """
    return _run_async(stop_fargate_task_async(cluster_name=cluster_name, task_arn=task_arn, reason=reason))


def task_exists(cluster_name: str, task_arn: str) -> bool:
    """
    Returns whether the given task exists
    """
    return _run_async(task_exists_async(cluster_name=cluster_name, task_arn=task_arn))


def task_is_running(cluster_name: str, task_arn: str) -> bool:
    """
    Returns whether the given taks is running
    """
    return _run_async(task_is_running_async(cluster_name=cluster_name, task_arn=task_arn))
