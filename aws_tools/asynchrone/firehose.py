import json
from typing import Any
from aiobotocore.session import get_session

session = get_session()


async def save_to_firehose_async(serialisable: Any, firehose_stream: str):
    """
    """
    async with session.create_client("firehose") as firehose:
        await firehose.put_record(
            DeliveryStreamName=firehose_stream,
            Record={
                "Data": json.dumps(serialisable)+"\n"
            }
        )
