"""
This module was automatically generated from aws_tools.asynchrone.cloud_formation
"""
from aws_tools._async_tools import _run_async, _async_iter_to_sync
from aws_tools.asynchrone.cloud_formation import get_session, session, list_stacks_async, get_stack_outputs_async


def get_stack_outputs(stack: str | None = None) -> dict:
    """
    Returns the exported stack outputs. Or all the outputs of all stacks
    """
    return _run_async(get_stack_outputs_async(stack=stack))



def list_stacks() -> list:
    """
    list existing stacks
    """
    return _run_async(list_stacks_async())

