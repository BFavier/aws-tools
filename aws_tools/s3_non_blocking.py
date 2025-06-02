import pathlib
import threading
import boto3
from typing import Callable
from boto3.s3.transfer import TransferManager, TransferConfig
from s3transfer.futures import TransferFuture

s3_resource = boto3.resource('s3')
s3_client = boto3.client("s3")


def copy_object(
        bucket_name: str,
        key: str | pathlib.Path,
        new_bucket_name: str,
        new_key: str | pathlib.Path,
        blocking: bool=False,
        callback: Callable[[TransferFuture], None] | None = None
    ) -> TransferFuture:
    """
    Copy an object without downloading it. Can handle very big files, and can be non-blocking.
    """
    transfer_config = TransferConfig(multipart_threshold=100 * 1024**2)  # 100 MB chunks
    tm = TransferManager(s3_client, config=transfer_config)
    future = tm.copy(
        copy_source={'Bucket': bucket_name, 'Key': key.as_posix() if isinstance(key, pathlib.Path) else key},
        bucket=new_bucket_name,
        key=new_key.as_posix() if isinstance(new_key, pathlib.Path) else new_key
    )

    def handle_completion():
        future.result()
        if callback:
            callback(future)
        tm.shutdown()

    if blocking:
        handle_completion()
    else:
        threading.Thread(target=handle_completion, daemon=True).start()
    return future


def delete_object(bucket_name: str, key: str | pathlib.Path):
    """
    Delete an object, with immediate effect whatever the size of the object
    """
    obj = s3_resource.Object(bucket_name, key.as_posix() if isinstance(key, pathlib.Path) else key)
    obj.delete()


def move_object(
        bucket_name: str,
        key: str | pathlib.Path,
        new_bucket_name: str,
        new_key: str | pathlib.Path,
        blocking: bool=False
    ):
    """
    Move an s3 object
    """
    copy_object(
        bucket_name,
        key,
        new_bucket_name,
        new_key,
        blocking=blocking,
        callback=(lambda future: delete_object(bucket_name, key)) if not blocking else None
    )
    if blocking:
        delete_object(bucket_name, key)
