from datetime import datetime
from pydantic import BaseModel, Field
from aiobotocore.session import get_session
from typing import Literal, Iterable, AsyncIterable, Optional
from botocore.exceptions import ClientError

session = get_session()


TASK_STATUSES = Literal["PROVISIONING", "PENDING", "RUNNING", "DEPROVISIONING", "STOPPED", "ACTIVATING"]


class Attribute(BaseModel):
    name: str
    value: str


class Attachment(BaseModel):
    id: str
    type: Literal["ElasticNetworkInterface", "Service Connect", "AmazonElasticBlockStorage"] | str
    status: Literal["PRECREATED", "CREATED", "ATTACHING", "ATTACHED", "DETACHING", "DETACHED", "DELETED", "FAILED"]
    details: list[Attribute]


class NetworkInterface(BaseModel):
    attachmentId: str
    privateIpv4Address: str
    ipv6Address: str | None = None


class NetworkBinding(BaseModel):
    bindIP: str
    containerPort: int
    hostPort: int
    protocol: Literal["tcp", "udp"]
    containerPortRange: str
    hostPortRange: str


class ManagedAgent(BaseModel):
    lastStartedAt: str
    name: str
    reason: str
    lastStatus: str


class ECSContainer(BaseModel):
    containerArn: str
    cpu: str
    image: str | None = None
    imageDigest: str
    lastStatus: str
    name: str
    networkInterfaces: list[NetworkInterface]
    runtimeId: str
    taskArn: str


class ECSContainerDescription(ECSContainer):
    exitCode: int
    reason: str | None = None
    networkBindings: list[NetworkBinding]
    healthStatus: Literal["HEALTHY", "UNHEALTHY", "UNKNOWN"]
    managedAgents: list[ManagedAgent] | None = None
    memory: str
    memoryReservation: str | None = None
    gpuIds: list[str] | None = None


class EnvironmentFile(BaseModel):
    value: str
    type: Literal["s3"]


class ResourceRequirement(BaseModel):
    value: str
    type: Literal["GPU", "InferenceAccelerator"]


class ECSContainerOverride(BaseModel):
    name: str | None = None
    cpu: int | None = None
    memory: int | None = None
    command: list[str] | None = None
    environment: list[Attribute] | None = None
    environmentFiles: list[EnvironmentFile] | None = None
    memoryReservation: int | None = None
    resourceRequirements: list[ResourceRequirement] | None = None


class Overrides(BaseModel):
    containerOverrides: list[ECSContainerOverride]


ECSTaskStatus = Literal["PROVISIONING", "PENDING", "ACTIVATING", "RUNNING", "DEACTIVATING", "STOPPING", "DEPROVISIONING", "STOPPED", "DELETED"]


class _ECSTask(BaseModel):
    attachments: list[Attachment]
    attributes: list[Attribute]
    availabilityZone: str
    clusterArn: str
    connectivity: Literal["CONNECTED", "DISCONECTED"]
    connectivityAt: datetime
    containerInstanceArn: str | None = None
    containers: list[ECSContainer]
    cpu: str
    createdAt: datetime
    desiredStatus: ECSTaskStatus
    enableExecuteCommand: bool
    group: str
    launchType: Literal["EC2", "FARGATE"]
    lastStatus: ECSTaskStatus
    memory: str
    overrides: dict
    pullStartedAt: datetime
    pullStoppedAt: datetime
    startedAt: datetime
    taskArn: str
    taskDefinitionArn: str
    version: int


class ECSTaskDetails(_ECSTask):
    updatedAt: str


class ECSTaskStateChangeEvent(BaseModel):
    """
    Event on ECS task state change, as captured by event bridge
    https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ecs_task_events.html
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


class StorageSize(BaseModel):
    sizeInGiB: int


class Tag(BaseModel):
    key: str
    value: str


class ECSTaskDescription(_ECSTask):
    """
    The return type from boto3 ecs 'describe_tasks'
    https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ecs/client/describe_tasks.html
    """
    containers: list[ECSContainerDescription]
    capacityProviderName: Literal["EC2", "FARGATE"] | None = None
    overrides: Overrides
    platformVersion: str
    platformFamily: str
    startedBy: str | None = None
    stopCode: Literal["TaskFailedToStart", "EssentialContainerExited", "UserInitiated", "ServiceSchedulerInitiated", "SpotInterruption", "TerminationNotice"]
    stoppedAt: datetime
    stoppedReason: str
    stoppingAt: datetime
    tags: list[Tag]
    ephemeralStorage: StorageSize | None = None
    fargateEphemeralStorage: StorageSize | None = None

    def is_running(self):
        return self.lastStatus in {"PROVISIONING", "PENDING", "ACTIVATING", "RUNNING"}


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
    ) -> ECSTaskDescription:
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
    return ECSTaskDescription(**response["tasks"][0])


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


async def get_tasks_descriptions_async(cluster_name: str, task_arns: Iterable[str], chunk_size: int=100) -> AsyncIterable[ECSTaskDescription | None]:
    """
    Returns the description of the given tasks, by querying aws by batch. Yield None for non-existant tasks.
    """
    iterable = (arn for arn in task_arns)
    async with session.create_client("ecs") as ecs:
        subset_arns = [arn for _, arn in zip(range(chunk_size), iterable)]
        response = await ecs.describe_tasks(cluster=cluster_name, tasks=subset_arns, include=["TAGS"])
        descriptions = {task["taskArn"]: task for task in response["tasks"]}
        for arn in subset_arns:
            desc = descriptions.get(arn)
            if desc is not None:
                desc = ECSTaskDescription(**desc)
            yield desc


async def get_task_description_async(cluster_name: str, task_arn: str) -> ECSTaskDescription | None:
    """
    """
    async for desc in get_tasks_descriptions_async(cluster_name, [task_arn]):
        return desc
