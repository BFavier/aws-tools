import asyncio
import unittest
from aws_tools.ec2 import EC2
from aws_tools.ssm import SSM

SUBNET_ID = "subnet-058fc142e8166e3ab"
SECURITY_GROUP_ID = "sg-0d0232be7aa36f482"
INSTANCE_TYPE = "t3.nano"


class TestEc2AndSsm(unittest.TestCase):

    def test_create_instance(self):

        async def test():
            async with EC2() as ec2, SSM() as ssm:
                instance_types = [it.instance_type async for it in ec2.list_instance_types_async(["m5"])]
                properties = await ec2.get_instance_type_properties_async(INSTANCE_TYPE)
                image_id = await ssm.get_latest_ECS_AMI_async(properties.processor_info.supported_architectures[0])
                instance_ids = await ec2.run_instances_async(instance_type=INSTANCE_TYPE, image_id=image_id, subnet_id=SUBNET_ID, security_group_ids=[SECURITY_GROUP_ID], iam_instance_profile_arn=None)
                print(instance_ids)
                instances = [instance async for instance in ec2.list_instances_async()]
                assert instance_ids[0] in [i.instance_id for i in instances]
                assert (await ec2.get_instance_async(instance_ids[0])) is not None
                await ec2.stop_instance_async(instance_ids[0])
                instance = await ec2.get_instance_async(instance_ids[0])
                assert instance is None or instance.state.name in ("stopping", "terminated")

        asyncio.run(test())


if __name__ == "__main__":
    unittest.main()
