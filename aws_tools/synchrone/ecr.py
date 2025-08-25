"""
This module was automatically generated from aws_tools.asynchrone.ecr
"""
from aws_tools._async_tools import _run_async, _async_iter_to_sync, _sync_iter_to_async
from aws_tools.asynchrone.ecr import get_session, session, list_repositories_async, list_image_tags_async


def list_image_tags(repository_name: str) -> list[str]:
    """
    Return all the tagged ecr images from the ecr repository
    """
    return _run_async(list_image_tags_async(repository_name=repository_name))


def list_repositories() -> list[str]:
    """
    Return all existing repository names
    """
    return _run_async(list_repositories_async())
