"""
This module was automatically generated from aws_tools.asynchrone.firehose
"""
from aws_tools._async_tools import _run_async, _async_iter_to_sync, _sync_iter_to_async
from aws_tools.asynchrone.firehose import json, Any, get_session, session, save_to_firehose_async


def save_to_firehose(serialisable: Any, firehose_stream: str):
    """
        
    """
    return _run_async(save_to_firehose_async(serialisable=serialisable, firehose_stream=firehose_stream))
