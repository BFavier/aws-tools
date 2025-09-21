"""
This module was automatically generated from aws_tools.asynchrone.sqs
"""
from aws_tools._async_tools import _run_async, _async_iter_to_sync, _sync_iter_to_async
from typing import Iterable, Iterator
from aws_tools.asynchrone.sqs import __name__, __doc__, __package__, __loader__, __spec__, __file__, __cached__, __builtins__, Literal, Iterable, BaseModel, Field, get_session, SQSMessageAttribute, SQSMessage, SQSMessageResponse, session, poll_sqs_message_async, delete_sqs_event_async, send_sqs_message_async, batch_send_sqs_messages_async


def batch_send_sqs_messages(queue_url: str, messages: Iterable[SQSMessage], delay_seconds: int=0, chunk_size: int=10):
    """
    Send the given messages to the SQS queue, by batches of chunk_size, with retry for failures
    """
    return _run_async(batch_send_sqs_messages_async(queue_url=queue_url, messages=messages, delay_seconds=delay_seconds, chunk_size=chunk_size))


def delete_sqs_event(queue_url: str, receipt_handle: str):
    """
    After processing a polled event, you have to delete it, otherwise after 30s, it will appear back in the queue.
    """
    return _run_async(delete_sqs_event_async(queue_url=queue_url, receipt_handle=receipt_handle))


def poll_sqs_message(queue_url: str, max_messages: int=10, wait_seconds: int=10) -> list[SQSMessageResponse]:
    """
    Poll messages in an sqs queue
    """
    return _run_async(poll_sqs_message_async(queue_url=queue_url, max_messages=max_messages, wait_seconds=wait_seconds))


def send_sqs_message(queue_url: str, message: SQSMessage, delay_seconds: int=0):
    return _run_async(send_sqs_message_async(queue_url=queue_url, message=message, delay_seconds=delay_seconds))
