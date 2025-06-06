from aiobotocore.session import get_session
from typing import Literal

session = get_session()


async def run_fargate_task_async(
        cluster_name: str,
        docker_image_arn: str,
        task_name: str,
        subnets_arn : list[str],
        security_group_arn: str,
        vCPU: Literal["0.25", "0.5", 1, 2, 4, 8, 16],
        memoryGB_per_vCPU: int,
        disk_space: int=20,
        environment_variables: dict = {},
        fargate_platform_version: str = "1.4.0"):
    """
    run a standalone task on an ECS cluster
    """
    assert 2 <= memoryGB_per_vCPU <= 8
    assert 20 <= disk_space <= 200
    async with session.create_client("ecs") as ecs:
        return await ecs.run_task(
            cluster=cluster_name,
            taskDefinition="FlexibleTaskDefinition",
            launchType="FARGATE",
            platformVersion=fargate_platform_version,
            networkConfiguration={
                'awsvpcConfiguration':
                {
                    'subnets': subnets_arn,
                    'securityGroups': [security_group_arn],
                    'assignPublicIp': 'ENABLED'
                }
            },
            overrides={
                'containerOverrides':
                [
                    {
                        'name': task_name,
                        'image': docker_image_arn,
                        'cpu': int(float(vCPU) * 1024),
                        'memory': int(float(vCPU) * memoryGB_per_vCPU * 1024),
                        'ephemeralStorage': {'sizeInGiB': disk_space},
                        'environment': [{"name": k, "value": v} for k, v in environment_variables]
                    }
                ]
            }
        )
