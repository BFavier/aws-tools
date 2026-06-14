import aioboto3
from operator import __and__
from datetime import datetime, UTC
from typing import Literal, ClassVar, Iterable, AsyncIterable, AsyncGenerator, Generator, Awaitable, Any
from pydantic import BaseModel, Field, ConfigDict
from pydantic.alias_generators import to_camel


CpuArchitecture = Literal["i386", "x86_64", "arm64", "x86_64_mac", "arm64_mac"]
InstanceState = Literal["pending", "running", "shutting-down", "terminated", "stopping", "stopped"]
InstanceLifecycle = Literal["spot", "scheduled", "capacity-block", "interruptible-capacity-reservation"]


class _SnakeBaseModel(BaseModel):
    """
    Handle converting camel case to snake case
    """
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


class Ec2InstanceDescription(_SnakeBaseModel):
    """
    Simplified response schema of boto3's 'describe_instances'
    https://docs.aws.amazon.com/boto3/latest/reference/services/ec2/client/describe_instances.html
    """

    class Tag(_SnakeBaseModel):
        """
        """
        key: str
        value: str

    class State(_SnakeBaseModel):
        """
        State of an EC2 instance
        """
        code: str
        name: InstanceState

    class SecurityGroup(_SnakeBaseModel):
        """
        """
        group_id: str
        group_name: str
    
    class IamInstanceProfile(_SnakeBaseModel):
        """
        """
        arn: str
        id: str
    
    class BlockDeviceMapping(_SnakeBaseModel):
        """
        """

        class Ebs(_SnakeBaseModel):
            """
            """

            class Operator(_SnakeBaseModel):
                """
                """
                managed: bool
                principal: str
                hidden_by_default: bool

            attach_time: datetime
            delete_on_termination: bool
            status: Literal["attaching", "attached", "detaching", "detached"]
            volume_id: str
            associated_resource: str
            volume_owner_id: str
            operator: Operator
            ebs_card_index: int

        device_name: str
        ebs: Ebs

    instance_id: str
    instance_type: str = Field(description="The EC2 naming of the instance type", examples=["m5.xlarge"])
    instance_lifecycle: InstanceLifecycle
    state: State
    launch_time: datetime
    image_id: str
    vpc_id: str
    subnet_id: str
    security_groups: list[SecurityGroup]
    private_ip_address: str
    public_ip_address: str
    tags: list[Tag]
    iam_instance_profile: IamInstanceProfile
    block_device_appings: list[BlockDeviceMapping]
    cpu_architecture: CpuArchitecture


class Ec2InstanceType(_SnakeBaseModel):
    """
    Simplified response schema of boto3's 'describe_instance_types'
    https://docs.aws.amazon.com/boto3/latest/reference/services/ec2/client/describe_instance_types.html
    """

    class ProcessorInfo(_SnakeBaseModel):
        supported_architectures: list[CpuArchitecture]
        sustained_clock_speed_in_ghz: float
        manufacturer: str

    class VCpuInfo(_SnakeBaseModel):
        default_v_cpus: int | float
        default_cores: int
        default_threads_per_core: int
        valid_cores: list[int]
        valid_thread_per_core: list[int]

    class MemoryInfo(_SnakeBaseModel):
        size_in_miB: int
    
    class InstanceStorageInfo(_SnakeBaseModel):
        total_size_in_gb: int
    
    class NetworkInfo(_SnakeBaseModel):

        class EfaInfo(_SnakeBaseModel):
            maximum_efa_interfaces: int

        ipv4_addresses_per_interface: int
        ipv6_addresses_per_interface: int
        ipv6_supported: bool
        ena_support: Literal["unsupported", "supported", "required"]
        efa_supported: bool
        efa_info: EfaInfo
        secondary_network_supported: bool
        maximum_secondary_network_interfaces: int
        ipv4_addresses_per_secondary_interface: int

    class GpuInfo(_SnakeBaseModel):

        class Gpu(_SnakeBaseModel):
            name: str
            manufacturer: str
            count: int
            logical_gpu_count: int
            gpu_partition_size: float
            workloads: list[str]
            memory_info: "Ec2InstanceType.MemoryInfo"

        gpus: list[Gpu]
        total_gpu_memory_in_mib: int

    instance_type: str = Field(description="The EC2 naming of the instance type", examples=["m5.xlarge"])
    current_generation: bool
    free_tier_eligible: bool
    supported_usage_classes: list[Literal["spot", "on-demand", "capacity-block"]]
    bare_metal: bool
    processor_info: ProcessorInfo
    v_cpu_info: VCpuInfo
    memory_info: MemoryInfo
    instance_storage_supported: bool
    network_info: NetworkInfo
    gpu_info: GpuInfo


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

    async def list_instance_types_paginated_async(
            self,
            page_start_token: str | None,
            instance_types_filter: list[str] | None = None,
            max_page_size: int = 100,
        ) -> tuple[list[Ec2InstanceType], str | None]:
        """
        Returns EC2 instance types in a paginated fashion as tuples of (page, next_page_token)
        """
        kwargs = dict()
        if instance_types_filter is not None:
            kwargs.setdefault("Filters", []).append(
                {
                    "Name": "instance-type-filter",
                    "Values": instance_types_filter
                }
            )
        response = await self.client.describe_instance_types(
            MaxResults=max_page_size,
            NextToken=page_start_token,
            **kwargs
        )
        return [Ec2InstanceType(**it) for it in response["InstanceTypes"]], response.get("NextToken")

    async def list_instance_types_async(
            self,
            instance_types_filter: list[str] | None = None
        ) -> AsyncIterable[Ec2InstanceType]:
        """
        Return an async iterable over the ec2 instance types
        """
        page_start_token = None
        while True:
            page, next_page_token = await self.list_instance_types_paginated_async(page_start_token, instance_types_filter)
            for it in page:
                yield it
            if next_page_token is None:
                break

    async def get_instance_type_properties_async(self, instance_type: str) -> Ec2InstanceType | None:
        """
        Get the properties of an instance type, or return None if not found
        """
        async for it in self.list_instance_types_async(instance_types_filter=[instance_type]):
            return it
        else:
            return None

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
        Initiate instance bootup, return it's id
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
        ) -> tuple[list[Ec2InstanceDescription], str | None]:
        """
        Returns (page, next_page_token) with page a list of running instances
        """
        kwargs = dict()
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
            Ec2InstanceDescription(**instance)
            for reservation in response["Reservations"]
            for instance in reservation["Instances"]
        ]
        return page, response.get("NextToken")

    async def list_instances_async(
            self,
            instance_state_filter: None | list[InstanceState] = None,
            instance_id_filter: list[str] | None = None,
    ) -> AsyncIterable[Ec2InstanceDescription]:
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

    async def get_instance_async(self, instance_id: str) -> Ec2InstanceDescription | None:
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
