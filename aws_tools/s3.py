import os
import pathlib
import boto3
from typing import Iterator, Callable
from botocore.exceptions import ClientError
from boto3.s3.transfer import TransferManager, TransferConfig
from s3transfer.futures import TransferFuture

s3_resource = boto3.resource('s3')
s3_client = boto3.client("s3")


def object_exists(bucket_name: str, key: str|pathlib.Path) -> bool:
    """
    returns whether an object exists on as3 or not
    """
    try:
        s3_resource.Object(bucket_name, key).load()
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            return False
        else:
            raise e
    return True


def get_object_bytes_size(bucket_name: str, key: str) -> int | None:
    """
    Returns the object size in bytes, or None if it does not exists
    """
    try:
        s3_object = s3_resource.Object(bucket_name, key)
        return s3_object.content_length
    except ClientError as e:
        return None


def list_objects(bucket_name: str, prefix: str|pathlib.Path="") -> Iterator[object]:
    """
    List the objects found in the given prefix of the bucket
    """
    bucket = s3_resource.Bucket(bucket_name)
    if isinstance(prefix, pathlib.Path):
        prefix = prefix.as_posix()
    yield from bucket.objects.filter(Prefix=prefix)


def upload_files(files_path: str|pathlib.Path, bucket_name: str, prefix: str|pathlib.Path, overwrite: bool = False, callback: Callable|None = None):
    """
    upload the files in the given file path (or a single file path) to the given s3 bucket at given prefix
    """
    bucket = s3_resource.Bucket(bucket_name)
    files_path = pathlib.Path(files_path)
    prefix = pathlib.Path(prefix)
    if not files_path.exists():
        raise FileNotFoundError(f"The file_path '{files_path}' does not exist")
    iterable = os.walk(files_path) if files_path.is_dir() else [(files_path.parent, [], [file_path.name])]
    for root, dirs, files in iterable:
        root = pathlib.Path(root)
        for file in files:
            file_path = (root / file).as_posix()
            object_key = (prefix / root.relative_to(files_path) / file).as_posix()
            if not overwrite and object_exists(bucket_name, object_key):
                raise FileExistsError(f"An object with key '{object_key}' exist already, use overwrite=True to overwrite")
            bucket.upload_file(file_path, object_key)
            if callback is not None:
                callback(file_path=file_path, object_key=object_key)


def download_files(bucket_name: str, prefix: str|pathlib.Path, directory: str|pathlib.Path, create_missing_path: bool=False, callback: Callable|None = None):
    """
    download the files at the given prefix (or a single file) of a given bucket in the given directory
    """
    bucket = s3_resource.Bucket(bucket_name)
    directory = pathlib.Path(directory)
    if not directory.exists():
        if create_missing_path:
            directory.mkdir(parents=True)
        else:
            raise NotADirectoryError(f"The directory '{directory}' does not exist, set create_missing_path=True to allow creating it")
    if not directory.is_dir():
        raise NotADirectoryError(f"The provided directory path '{directory}' is a file")
    prefix = pathlib.Path(prefix)
    for obj in list_objects(bucket_name, prefix):
        file_path = directory / pathlib.Path(obj.key).relative_to(prefix)
        file_path.parent.mkdir(exist_ok=True, parents=True)
        file_path = file_path.as_posix()
        bucket.download_file(obj.key, file_path)
        if callback is not None:
            callback(object_key=obj.key, file_path=file_path)


def upload_data(data: bytes, bucket_name: str, key: str|pathlib.Path, overwrite: bool = False):
    """
    save the given bytes as an object
    """
    if isinstance(key, pathlib.Path):
        key = key.as_posix()
    if not overwrite and object_exists(bucket_name, key):
        raise FileExistsError(f"An object with key '{key}' exist already, use overwrite=True to overwrite")
    s3_resource.Object(bucket_name, key).put(Key=key, Body=data)


def download_data(bucket_name: str, key: str|pathlib.Path) -> bytes:
    """
    load the data stored in the given bucket file
    """
    if isinstance(key, pathlib.Path):
        key = key.as_posix()
    return s3_resource.Object(bucket_name, key).get()["Body"].read()


def delete_objects(bucket_name: str, prefix: str|pathlib.Path, callback: Callable|None = None):
    """
    Delete all objects that match the prefix
    """
    bucket = s3_resource.Bucket(bucket_name)
    objects = list_objects(bucket_name, prefix)
    while True:
        delete = [{"Key": obj.key} for i, obj in zip(range(1_000), objects)]
        if len(delete) == 0:
            break
        bucket.delete_objects(Delete={"Objects": delete})
        if callback is not None:
            for obj in delete:
                callback(object_key=obj["Key"])


def copy_object(bucket_name: str, key: str|pathlib.Path, new_bucket_name: str, new_key: str|pathlib.Path, blocking: bool=False, callback: Callable[[TransferFuture], None] | None = None) -> TransferFuture:
    """
    Copy an object without downloading it. Can handle very big files, and is non blocking.
    """
    transfer_config = TransferConfig(multipart_threshold=100 * 1024**2)  # 100 MB chunks
    tm = TransferManager(s3_client, config=transfer_config)
    future = tm.copy(
        copy_source={'Bucket': bucket_name, 'Key': key.as_posix() if isinstance(key, pathlib.Path) else key},
        bucket=new_bucket_name,
        key=new_key.as_posix() if isinstance(new_key, pathlib.Path) else new_key
    )
    if callback is not None:
        future.add_done_callback(callback)
    if blocking:
        future.result()
        tm.shutdown()
    return future


def delete_object(bucket_name: str, key: str|pathlib.Path):
    """
    Delete an object, which is always non blocking
    """
    obj = s3_resource.Object(bucket_name, key.as_posix() if isinstance(key, pathlib.Path) else key)
    obj.delete()


def move_object(bucket_name: str, key: str|pathlib.Path, new_bucket_name: str, new_key: str|pathlib.Path, blocking: bool=False):
    """
    Move an s3 object
    """
    copy_object(
        bucket_name,
        key,
        new_bucket_name,
        new_key,
        blocking=blocking,
        callback=lambda future: delete_object(bucket_name, key) if not blocking else None
    )
    if blocking:
        delete_object(bucket_name, key)


if __name__ == "__main__":
    import IPython
    IPython.embed()
