from aiobotocore.session import get_session


session = get_session()


async def list_stacks_async() -> list[str]:
    """
    list existing stacks
    """
    async with session.create_client("cloudformation") as cloud_formation:
        stack_names = []
        results = await cloud_formation.list_stacks()
        while True:
            stack_names.extend([stack["StackName"] for stack in results["StackSummaries"]
                                if stack["StackStatus"] in ["CREATE_COMPLETE", "UPDATE_COMPLETE", "UPDATE_ROLLBACK_COMPLETE"]
                                and stack["StackName"] not in stack_names])
            next_token = results.get("NextToken")
            if next_token is None:
                break
            else:
                results = cloud_formation.list_stacks(NextToken=next_token)
        return stack_names


async def get_stack_outputs_async(stack: str | None = None) -> dict:
    """
    Returns the exported stack outputs. Or all the outputs of all stacks
    """
    async with session.create_client("cloudformation") as cloud_formation:
        if stack is None:
            stacks = await list_stacks_async()
        else:
            stacks = [stack]
        stack_outputs = {}
        for stack_name in stacks:
            descriptions = await cloud_formation.describe_stacks(StackName=stack_name)
            stack = descriptions['Stacks'][0]
            for output in stack.get('Outputs', []):
                stack_outputs[output["OutputKey"]] = output["OutputValue"]
        return stack_outputs
