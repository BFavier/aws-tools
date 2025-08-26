"""
This module was automatically generated from aws_tools.asynchrone.firehose
"""
from aws_tools._async_tools import _run_async, _async_iter_to_sync, _sync_iter_to_async
from typing import Iterable, Iterator
from aws_tools.asynchrone.firehose import __name__, __doc__, __package__, __loader__, __spec__, __file__, __cached__, __builtins__, json, get_session, session, save_to_firehose_async


def save_to_firehose(serialisable: dict, firehose_stream: str):
    return _run_async(save_to_firehose_async(serialisable=serialisable, firehose_stream=firehose_stream))
