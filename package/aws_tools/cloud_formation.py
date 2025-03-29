import boto3

cloud_formation = boto3.client('cloudformation')


def list_stacks() -> list[str]:
    """
    list existing stacks
    """
    stack_names = []
    results = cloud_formation.list_stacks()
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


def get_stack_outputs(stack: str|None = None) -> dict:
    """
    Returns the exported stack outputs
    """
    if stack is None:
        stacks = list_stacks()
    else:
        stacks = [stack]
    stack_outputs = {}
    for stack_name in stacks:
        stack = cloud_formation.describe_stacks(StackName=stack_name)['Stacks'][0]
        for output in stack.get('Outputs', []):
            stack_outputs[output["OutputKey"]] = output["OutputValue"]
    return stack_outputs


if __name__ == "__main__":
    import IPython
    IPython.embed()
