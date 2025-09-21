from pydantic import BaseModel, Field
from aiobotocore.session import get_session
from typing import Literal, Iterable, AsyncIterable, Optional
from botocore.exceptions import ClientError

session = get_session()


async def run_fargate_task_async(
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
    assert (disk_GiB_override is None) or (20 <= disk_GiB_override <= 200)
    container_overrides = {
        "name": task_definition,
        "cpu": int(float(vCPU_override) * 1024) if vCPU_override is not None else None,
        "memory": memory_MiB_override,
        "environment": [{"name": k, "value": v} for k, v in env_overrides.items()] if env_overrides is not None else None
    }
    container_overrides = {k : v for k, v in container_overrides.items() if v is not None}
    overrides = {}
    if disk_GiB_override > 20:
        overrides["ephemeralStorage"] = {"sizeInGiB": disk_GiB_override}
    if len(container_overrides.keys()) > 1:
        overrides["containerOverrides"] = [container_overrides]
    kwargs = dict(
        cluster=cluster_name,
        taskDefinition=task_definition,
        launchType="FARGATE",
        platformVersion=fargate_platform_version,
        networkConfiguration={
            "awsvpcConfiguration":
            {
                "subnets": subnet_ids,
                "securityGroups": [security_group_arn],
                "assignPublicIp": "ENABLED"
            }
        },
        tags=[{"key": k, "value": v} for k, v in tags.items()]
    )
    if len(overrides.keys()) > 0:
        kwargs["overrides"] = overrides=overrides
    async with session.create_client("ecs") as ecs:
        response = await ecs.run_task(**kwargs)
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


async def get_tasks_descriptions_async(cluster_name: str, task_arns: Iterable[str], chunk_size: int=100) -> AsyncIterable[dict | None]:
    """
    Returns the description of the given tasks, by querying aws by batch. Yield None for non-existant tasks.
    """
    iterable = (arn for arn in task_arns)
    async with session.create_client("ecs") as ecs:
        subset_arns = [arn for _, arn in zip(range(chunk_size), iterable)]
        response = await ecs.describe_tasks(cluster=cluster_name, tasks=subset_arns, include=["TAGS"])
        status = {task["taskArn"]: task for task in response["tasks"]}
        for arn in subset_arns:
            yield status.get(arn)


TASK_STATUSES = Literal["PROVISIONING", "PENDING", "RUNNING", "DEPROVISIONING", "STOPPED", "ACTIVATING"]


async def get_tasks_statuses_async(cluster_name: str, task_arns: Iterable[str], chunk_size: int=100) -> AsyncIterable[TASK_STATUSES | None]:
    """
    Returns whether the given tasks are running, by querying aws by batch
    """
    async for description in get_tasks_descriptions_async(cluster_name=cluster_name, task_arns=task_arns, chunk_size=chunk_size):
        if description is None:
            yield None
        else:
            yield description["lastStatus"]


async def task_is_running_async(cluster_name: str, task_arn: str) -> bool:
    """
    Returns whether the given taks is running
    """
    async for status in get_tasks_statuses_async(cluster_name, [task_arn]):
        return status in {"PROVISIONING", "PENDING", "ACTIVATING", "RUNNING"}


async def task_exists_async(cluster_name: str, task_arn: str) -> bool:
    """
    Returns whether the given task exists
    """
    async for status in get_tasks_statuses_async(cluster_name, [task_arn]):
        return status is not None


async def get_task_tags_async(cluster_name: str, task_arn: str) -> dict[str, str] | None:
    """
    Returns the tags of a task. Returns None if the task does not exists.
    """
    async for description in get_tasks_descriptions_async(cluster_name=cluster_name, task_arns=[task_arn]):
        if description is None:
            return None
        else:
            return {tag["key"]: tag["value"] for tag in description["tags"]}


class Attribute(BaseModel):
    name: str
    value: str


class NetworkInterface(BaseModel):
    attachmentId: str
    privateIpv4Address: str


class ECSContainer(BaseModel):
    containerArn: str
    lastStatus: str
    name: str
    image: str | None = None
    imageDigest: str
    runtimeId: str
    taskArn: str
    networkInterfaces: list[NetworkInterface]
    cpu: str


ECSTaskStatus = Literal["PROVISIONING", "PENDING", "ACTIVATING", "RUNNING", "DEACTIVATING", "STOPPING", "DEPROVISIONING", "STOPPED", "DELETED"]


class ECSTaskDetails(BaseModel):
    attachments: list[dict]
    attributes: list[Attribute]
    availabilityZone: str
    capacityProviderName: str
    clusterArn: str
    connectivity: str
    connectivityAt: str
    containerInstanceArn: str | None = None
    containers: list[ECSContainer]
    cpu: str
    createdAt: str
    desiredStatus: ECSTaskStatus
    enableExecuteCommand: bool
    group: str
    launchType: Literal["EC2", "FARGATE"]
    lastStatus: ECSTaskStatus
    memory: str
    overrides: dict
    pullStartedAt: str
    pullStoppedAt: str
    startedAt: str
    taskArn: str
    taskDefinitionArn: str
    updatedAt: str
    version: int


class ECSTaskStateChangeEvent(BaseModel):
    """
    Event on ECS task state change, as captured by event bridge
    """
    version: str
    id: str
    detail_type: str = Field(..., alias="detail-type")
    source: str
    account: str
    time: str
    region: str
    resources: list[str]
    detail: ECSTaskDetails
