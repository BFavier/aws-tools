"""
This module was automatically generated from aws_tools.asynchrone.s3
"""
from aws_tools._async_tools import _run_async, _async_iter_to_sync, _sync_iter_to_async
from aws_tools.asynchrone.s3 import os, pathlib, aioboto3, Iterator, Callable, Optional, AsyncIterator, ClientError, session, S3Exception, create_bucket_async, delete_bucket_async, bucket_exists_async, object_exists_async, get_object_bytes_size_async, list_objects_async, upload_files_async, download_files_async, upload_data_async, download_data_async, delete_objects_async, copy_object_async, delete_object_async, move_object_async, initiate_multipart_upload_async, upload_part_async, complete_multipart_upload_async, abort_multipart_upload_async, generate_download_url_async


def list_objects(bucket_name: str, prefix: str | pathlib.Path = '') -> AsyncIterator:
    """
    List the objects found in the given prefix of the bucket
    """
    return _async_iter_to_sync(list_objects_async(bucket_name=bucket_name, prefix=prefix))


def abort_multipart_upload(bucket_name: str, key: str, upload_id: str):
    return _run_async(abort_multipart_upload_async(bucket_name=bucket_name, key=key, upload_id=upload_id))


def bucket_exists(bucket_name: str) -> bool:
    """
    Returns whether a bucket of the given name exists
    """
    return _run_async(bucket_exists_async(bucket_name=bucket_name))


def complete_multipart_upload(bucket_name: str, key: str, upload_id: str, part_tags: list[str]):
    return _run_async(complete_multipart_upload_async(bucket_name=bucket_name, key=key, upload_id=upload_id, part_tags=part_tags))


def copy_object(source_bucket: str, source_key: str, dest_bucket: str, dest_key: str):
    """
    Copy an object within S3.
    """
    return _run_async(copy_object_async(source_bucket=source_bucket, source_key=source_key, dest_bucket=dest_bucket, dest_key=dest_key))


def create_bucket(bucket_name: str, region: str | None = None):
    """
    Create a bucket
    """
    return _run_async(create_bucket_async(bucket_name=bucket_name, region=region))


def delete_bucket(bucket_name: str):
    """
    Delete an existing bucket
    """
    return _run_async(delete_bucket_async(bucket_name=bucket_name))


def delete_object(bucket_name: str, key: str):
    """
    Delete an object from S3.
    """
    return _run_async(delete_object_async(bucket_name=bucket_name, key=key))


def delete_objects(bucket_name: str, prefix: str | pathlib.Path, callback: Optional[Callable] = None):
    """
    Delete all objects that match the prefix
    """
    return _run_async(delete_objects_async(bucket_name=bucket_name, prefix=prefix, callback=callback))


def download_data(bucket_name: str, key: str | pathlib.Path) -> bytes:
    """
    load the data stored in the given bucket file
    """
    return _run_async(download_data_async(bucket_name=bucket_name, key=key))


def download_files(bucket_name: str, prefix: str | pathlib.Path, directory: str | pathlib.Path, create_missing_path: bool = False, callback: Optional[Callable] = None):
    """
    download the files at the given prefix (or a single file) of a given bucket in the given directory
    """
    return _run_async(download_files_async(bucket_name=bucket_name, prefix=prefix, directory=directory, create_missing_path=create_missing_path, callback=callback))


def generate_download_url(bucket_name: str, key: str, expiration: int = 3600) -> str:
    """
    Generate a download url, for the given s3 object, with the given validity
    """
    return _run_async(generate_download_url_async(bucket_name=bucket_name, key=key, expiration=expiration))


def get_object_bytes_size(bucket_name: str, key: str) -> int:
    """
    Returns the object size in bytes, or None if it does not exists
    """
    return _run_async(get_object_bytes_size_async(bucket_name=bucket_name, key=key))


def initiate_multipart_upload(bucket_name: str, key: str, content_type: str = 'application/octet-stream') -> str:
    return _run_async(initiate_multipart_upload_async(bucket_name=bucket_name, key=key, content_type=content_type))


def move_object(source_bucket: str, source_key: str, dest_bucket: str, dest_key: str):
    """
    Move an object in S3 by copying and then deleting.
    """
    return _run_async(move_object_async(source_bucket=source_bucket, source_key=source_key, dest_bucket=dest_bucket, dest_key=dest_key))


def object_exists(bucket_name: str, key: str | pathlib.Path) -> bool:
    """
    returns whether an object exists on as3 or not
    """
    return _run_async(object_exists_async(bucket_name=bucket_name, key=key))


def upload_data(data: bytes, bucket_name: str, key: str | pathlib.Path, overwrite: bool = False):
    """
    save the given bytes as an object
    """
    return _run_async(upload_data_async(data=data, bucket_name=bucket_name, key=key, overwrite=overwrite))


def upload_files(files_path: str | pathlib.Path, bucket_name: str, prefix: str | pathlib.Path, overwrite: bool = False, callback: Optional[Callable] = None):
    """
    upload the files in the given file path (or a single file path) to the given s3 bucket at given prefix
    """
    return _run_async(upload_files_async(files_path=files_path, bucket_name=bucket_name, prefix=prefix, overwrite=overwrite, callback=callback))


def upload_part(bucket_name: str, key: str, upload_id: str, part_number: int, chunk: bytes) -> str:
    return _run_async(upload_part_async(bucket_name=bucket_name, key=key, upload_id=upload_id, part_number=part_number, chunk=chunk))
