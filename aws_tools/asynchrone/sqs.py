from typing import Literal, Iterable
from pydantic import BaseModel
from aiobotocore.session import get_session


class SQSMessageAttribute(BaseModel):
    DataType: Literal["String", "Number", "Binary"]
    StringValue: str = ""
    BinaryValue: bytes = b""
    StringListValues: list[str] = []
    BinaryListValues: list[bytes] = []


class SQSMessage(BaseModel):
    Body: str
    MessageAttributes: dict[str, SQSMessageAttribute] = {}


class SQSMessageResponse(SQSMessage):
    MessageId: str
    ReceiptHandle: str
    MD5OfBody: str
    Attributes: dict[str, str]
    MD5OfMessageAttributes: str


session = get_session()


async def poll_sqs_message_async(queue_url: str, max_messages: int=10, wait_seconds: int=10) -> list[SQSMessageResponse]:
    """
    Poll messages in an sqs queue
    """
    async with session.client("sqs") as sqs:
        response = await sqs.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=max_messages,
            WaitTimeSeconds=wait_seconds,
        )
    return [SQSMessageResponse(**msg) for msg in response.get("Messages", [])]


async def delete_sqs_event_async(queue_url: str, receipt_handle: str):
    """
    After processing a polled event, you have to delete it, otherwise after 30s, it will appear back in the queue.
    """
    async with session.client("sqs") as sqs:
        await sqs.delete_message(
            QueueUrl=queue_url,
            ReceiptHandle=receipt_handle,
        )


async def send_sqs_message_async(queue_url: str, message: SQSMessage, delay_seconds: int=0):
    """
    """
    async with session.clien("sqs") as sqs:
        response = await sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=message.Body,
            MessageAttributes={k: v.model_dump() for k, v in message.MessageAttributes.items()},
            DelaySeconds=delay_seconds,
        )
        return SQSMessageResponse(**response)


async def batch_send_sqs_messages_async(queue_url: str, messages: Iterable[SQSMessage], delay_seconds: int=0, chunk_size: int=10):
    """
    Send the given messages to the SQS queue, by batches of chunk_size, with retry for failures
    """
    iterable = iter(messages)
    message_to_process = True
    batch: dict[str, SQSMessage] = {}
    async with session.client("sqs") as sqs:
        while message_to_process or len(batch) > 0:
            while len(batch) < chunk_size:
                try:
                    batch[f"msg{len(batch)}"] = next(iterable)
                except StopIteration:
                    message_to_process = False
                    break
            response = await sqs.send_message_batch(
                QueueUrl=queue_url,
                Entries=[
                    {
                        "Id": k,
                        "MessageBody": m.Body,
                        "MessageAttributes": {k: v.model_dump() for k, v in m.MessageAttributes.items()},
                        "DelaySeconds": delay_seconds,
                    }
                    for k, m in batch.items()
                ]
            )
            for failed in response["Failed"]:
                if failed["SenderFault"]:
                    raise RuntimeError(f"Failed to send a message to SQS queue: '{failed['Message']}'")
            retry = (failed for failed in response["Failed"] if not failed["SenderFault"])
            batch = {f"msg{i}": batch[failed["Id"]] for i, failed in enumerate(retry)}
