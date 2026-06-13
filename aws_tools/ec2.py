import aioboto3
from operator import __and__
from datetime import datetime, UTC
from typing import Literal, ClassVar, Iterable, AsyncIterable, AsyncGenerator, Generator, Awaitable, Any
from pydantic import BaseModel, Field


CpuArchitecture = Literal["i386", "x86_64", "arm64", "x86_64_mac", "arm64_mac"]
InstanceState = Literal["pending", "running", "shutting-down", "terminated", "stopping", "stopped"]


class EC2:
    """
    An EC2 client that initalizes ec2 resources
    >>> ec2 = EC2()
    >>> await ec2.open()
    >>> ...
    >>> await ec2.close()

    It can also be used as an async context
    >>> async with EC2() as ec2:
    >>>     ...
    """


    class InstanceTypeProperties(BaseModel):
        """
        Properties of an EC2 instance type
        """

        class CPU(BaseModel):
            """
            Describes a CPU
            """
            cores_count: int
            vcpu_count: Literal["0.25", "0.5"] | int = Field(description="Virtual CPUs, aka threads in SMT/Hyper-Threading")
            supported_cpu_architectures: list[CpuArchitecture]

        class GPU(BaseModel):
            """
            Describes a GPU
            """
            name: str
            vram_MiB: int

        instance_type: str = Field(description="The EC2 naming of the instance type", examples=["m5.xlarge"])
        cpu: CPU
        ram_MiB: int
        gpus: list[GPU]


    class InstanceDescription(BaseModel):
        """
        Description of an existing EC2 instance
        """
        instance_id: str
        instance_type: str = Field(description="The EC2 naming of the instance type", examples=["m5.xlarge"])
        state: InstanceState
        launch_time: datetime
        image_id: str
        vpc_id: str
        subnet_id: str
        security_group_ids: list[str]
        private_ip_address: str
        public_ip_address: str
        tags: dict[str, str]
        iam_instance_profile_arn: str
        ebs_volume_ids: list[str]
        cpu_architecture: CpuArchitecture


    def __init__(self):
        self.session = aioboto3.Session()
        self._client = None

    async def open(self):
        self._client = await self.session.client("ec2").__aenter__()

    async def close(self):
        await self.client.__aexit__(None, None, None)
        self._client = None

    async def __aenter__(self) -> "EC2":
        await self.open()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()

    @property
    def client(self) -> object:
        if self._client is None:
            self._raise_not_initialized()
        else:
            return self._client

    def _raise_not_initialized(self):
        raise RuntimeError(f"{type(self).__name__} object was not awaited on creation, and as such, is not initialized")

    async def list_instance_types_paginated_async(self, page_start_token: str | None) -> tuple[list[InstanceTypeProperties], str]:
        """
        return a list of valid ec2 instance types
        """
        ...
    
    async def list_instance_types_async(self) -> AsyncIterable[InstanceTypeProperties]:
        """
        """
        ...

    async def get_instance_type_properties_async(self, type: str) -> InstanceTypeProperties | None:
        """
        Get the properties of an instance type, or return None if not found
        """
        ...

    async def start_instance_async(
            self,
            instance_type: str,
            image_id: str,
            subnet_id: str,
            security_group_ids: list[str],
            disk_size_GiB: int,
            user_data_script: str | None = None,
        ) -> str:
        """
        Initiate instance bootup
        """
        # TODO : how to specify cpu architecture ? enable disable Hyper-Threading ? AWS AMI ? IAM role ?
        response = await self.client.run_instances(
            ImageId=instance_type,
            InstanceType=type,
            MinCount=1,
            MaxCount=1,
            UserData=user_data_script,
            NetworkInterfaces=[
                {
                    "AssociatePublicIpAddress": True,
                    "DeviceIndex": 0,
                    "SubnetId": subnet_id,
                    "Groups": security_group_ids,
                }
            ],
            BlockDeviceMappings=[
                {
                    "DeviceName": "/dev/xvda",
                    "Ebs": {
                        "VolumeSize": disk_size_GiB,
                        "DeleteOnTermination": True,
                        "VolumeType": "gp3",
                    },
                }
            ],
        )
        return response["Instances"][0]["InstanceId"]

    async def list_instances_paginated_async(
            self,
            page_start_token: str | None,
            instance_state_filter: None | list[InstanceState] = None,
            instance_id_filter: list[str] | None = None,
            max_page_size: int = 100
        ) -> tuple[list[InstanceDescription], str]:
        """
        Returns (page, next_page_token) with page a list of running instances
        """
        kwargs = {}
        if page_start_token:
            kwargs["NextToken"] = page_start_token
        if instance_state_filter is not None:
            kwargs.setdefault("Filters", list()).append(
                {
                    "Name": "instance-state-name",
                    "Values": instance_state_filter,
                }
            )
        if instance_id_filter is not None:
            kwargs.setdefault("Filters", list()).append(
                {
                    "Name": "instance-ids",
                    "Values": instance_id_filter,
                }
            )
        response = await self.client.describe_instances(
            MaxResults=max_page_size,
            **kwargs,
        )
        page = [
            self.InstanceDescription(
                instance_id=instance["InstanceId"],
                instance_type=instance["InstanceType"],
                state=instance["State"]["Name"],
                launch_time=datetime.fromisoformat(instance["LaunchTime"]).astimezone(UTC),
                image_id=instance["ImageId"],
                vpc_id=instance["VpcId"],
                subnet_id=instance["SubnetId"],
                security_group_ids=[sg["GroupId"] for sg in instance["SecurityGroups"]],
                private_ip_address=instance["PrivateIpAdress"],
                public_ip_address=instance["PublicIpAddress"],
                tags={tag["Key"]: tag["Value"] for tag in instance["Tags"]},
                iam_instance_profile_arn=instance["IamInstanceProfile"]["arn"],
                ebs_volume_ids=[block["Ebs"]["VolumeId"] for block in instance["BlockDeviceMappings"]],
                cpu_architecture=instance["Architecture"],
            )
            for reservation in response["Reservations"] for instance in reservation["Instances"]
        ]
        return page, response.get("NextToken")

    async def list_instances_async(
            self,
            instance_state_filter: None | list[InstanceState] = None,
            instance_id_filter: list[str] | None = None,
    ) -> AsyncIterable[InstanceDescription]:
        """
        Yield instances in an async fashion
        """
        next_page_token = None
        while True:
            page, next_page_token = await self.list_instances_paginated_async(next_page_token, instance_state_filter, instance_id_filter)
            for description in page:
                yield description
            if next_page_token is None:
                break

    async def get_instance_async(self, instance_id: str) -> InstanceDescription | None:
        """
        Describe an existing instance, or return None if it does not exists
        """
        async for instance in self.list_instances_async(instance_id_filter=[instance_id]):
            return instance
        else:
            return None

    async def stop_instances_async(self, instance_ids: list[str]):
        """
        Initiate the instance shutdown
        """
        await self.client.stop_instances(
            InstanceIds=[instance_ids]
        )

    async def stop_instance_async(self, instance_id: str):
        """
        Initiate the instance shutdown
        """
        await self.stop_instances_async([instance_id])
