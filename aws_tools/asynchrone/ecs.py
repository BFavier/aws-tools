from aiobotocore.session import get_session
from typing import Literal

session = get_session()


async def run_fargate_task_async(
        cluster_name: str,
        docker_image_uri: str,
        task_name: str,
        subnet_ids : list[str],
        security_group_arn: str,
        vCPU: Literal["0.25", "0.5", 1, 2, 4, 8, 16],
        memory_MiB: int,
        disk_space_GiB: int=20,
        environment_variables: dict = {},
        fargate_platform_version: str = "1.4.0"
    ) -> str:
    """
    Run a standalone task on an ECS cluster.
    Returns the running task arn.
    """
    assert 2 <= int((memory_MiB / 1024.0) / float(vCPU)) <= 8
    assert 20 <= disk_space_GiB <= 200
    async with session.create_client("ecs") as ecs:
        response = await ecs.run_task(
            cluster=cluster_name,
            taskDefinition="FlexibleTaskDefinition",
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
            overrides={
                'containerOverrides':
                [
                    {
                        'name': task_name,
                        'image': docker_image_uri,
                        'cpu': int(float(vCPU) * 1024),
                        'memory': memory_MiB,
                        'ephemeralStorage': {'sizeInGiB': disk_space_GiB},
                        'environment': [{"name": k, "value": v} for k, v in environment_variables]
                    }
                ]
            }
        )
    return response["tasks"][0]["taskArn"]


async def stop_fargate_task_async(cluster_name: str, task_arn: str, reason: str="Stopped by user"):
    """
    Stops a running ECS Fargate task.
    """
    async with session.create_client("ecs") as ecs:
        await ecs.stop_task(
            cluster=cluster_name,
            task=task_arn,
            reason=reason
        )
