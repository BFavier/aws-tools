from aiobotocore.session import get_session
from typing import Literal, Iterable, AsyncIterable
from botocore.exceptions import ClientError

session = get_session()


async def run_fargate_task_async(
        cluster_name: str,
        task_definition: str,
        subnet_ids : list[str],
        security_group_arn: str,
        vCPU: Literal["0.25", "0.5", 1, 2, 4, 8, 16],
        memory_MiB: int,
        disk_space_GiB: int=20,
        environment_variables: dict = {},
        fargate_platform_version: str = "1.4.0"
    ) -> dict:
    """
    Run a standalone task on an ECS cluster.
    Returns the running task arn.
    """
    assert 2 <= int((memory_MiB / 1024.0) / float(vCPU)) <= 8
    assert 20 <= disk_space_GiB <= 200
    overrides = {
        'containerOverrides':
        [
            {
                'name': task_definition,
                'cpu': int(float(vCPU) * 1024),
                'memory': memory_MiB,
                'environment': [{"name": k, "value": v} for k, v in environment_variables.items()]
            }
        ],
    }
    if disk_space_GiB > 20:
        overrides["ephemeralStorage"] = {'sizeInGiB': disk_space_GiB}
    async with session.create_client("ecs") as ecs:
        response = await ecs.run_task(
            cluster=cluster_name,
            taskDefinition=task_definition,
            launchType="FARGATE",
            platformVersion=fargate_platform_version,
            networkConfiguration={
                'awsvpcConfiguration':
                {
                    'subnets': subnet_ids,
                    'securityGroups': [security_group_arn],
                    'assignPublicIp': 'ENABLED'
                }
            },
            overrides=overrides
        )
    return response["tasks"][0]


async def stop_fargate_task_async(cluster_name: str, task_arn: str, reason: str="Stopped by user") -> bool:
    """
    Stops a running ECS Fargate task.
    If the task did not exist, returns False.
    """
    async with session.create_client("ecs") as ecs:
        try:
            await ecs.stop_task(
                cluster=cluster_name,
                task=task_arn,
                reason=reason
            )
        except ClientError as e:
            error = e.response["Error"]
            if (error["Code"] == "InvalidParameterException") and ("The referenced task was not found" in error["Message"]):
                return False
            else:
                raise
    return True


async def tasks_are_running_async(cluster_name: str, task_arns: Iterable[str], chunk_size: int=100) -> AsyncIterable[bool]:
    """
    Returns whether the given tasks are running, by querying aws by batch
    """
    iterable = (arn for arn in task_arns)
    async with session.create_client("ecs") as ecs:
        subset_arns = [arn for _, arn in zip(range(chunk_size), iterable)]
        response = await ecs.describe_tasks(cluster=cluster_name, tasks=subset_arns)
        status = {task["taskArn"]: task["lastStatus"] for task in response["tasks"]}
        for arn in subset_arns:
            yield status.get(arn, "MISSING") in ("PROVISIONING", "PENDING", "ACTIVATING", "RUNNING")


async def task_is_running(cluster_name, task_arn: str) -> bool:
    """
    Returns whether the given taks is running
    """
    async for running in tasks_are_running_async(cluster_name, [task_arn]):
        return running
