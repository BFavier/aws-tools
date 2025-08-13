import os
import pathlib
import aioboto3
from urllib.parse import urlparse
from typing import Iterator, Callable, Optional, AsyncIterator
from botocore.exceptions import ClientError


session = aioboto3.Session()


class S3Exception(Exception):
    pass


async def create_bucket_async(bucket_name: str, region: str | None = None):
    """
    Create a bucket
    """
    if region is None:
        region = session._session.get_config_variable("region")
    async with session.client("s3", region_name=region) as s3_client:
        try:
            await s3_client.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={"LocationConstraint": region}
            )
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceInUseException":
                raise S3Exception(f"Bucket '{bucket_name}' already exists")
            else:
                raise


async def delete_bucket_async(bucket_name: str):
    """
    Delete an existing bucket
    """
    async with session.client("s3") as s3_client:
        try:
            await s3_client.delete_bucket(Bucket=bucket_name)
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceNotFoundException":
                raise S3Exception(f"Bucket '{bucket_name}' does not exist")
            else:
                raise


async def bucket_exists_async(bucket_name: str) -> bool:
    """
    Returns whether a bucket of the given name exists
    """
    async with session.client("s3") as s3_client:
        try:
            await s3_client.head_bucket(Bucket=bucket_name)
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code in ["404", "NoSuchBucket"]:
                return False
            else:
                raise
        return True


async def object_exists_async(bucket_name: str, key: str|pathlib.Path) -> bool:
    """
    returns whether an object exists on as3 or not
    """
    async with session.resource("s3") as s3_resource:
        try:
            obj = await s3_resource.Object(bucket_name, key)
            await obj.load()
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            else:
                raise e
    return True


async def get_object_bytes_size_async(bucket_name: str, key: str) -> int:
    """
    Returns the object size in bytes, or None if it does not exists
    """
    async with session.resource("s3") as s3_resource:
        try:
            obj = await s3_resource.Object(bucket_name, key)
            return await obj.content_length
        except ClientError as e:
            raise S3Exception("Object does not exist")


async def list_objects_async(bucket_name: str, prefix: str | pathlib.Path="") -> AsyncIterator[str]:
    """
    List the objects found in the given prefix of the bucket
    """
    if isinstance(prefix, pathlib.Path):
        prefix = prefix.as_posix()
    async with session.resource("s3") as s3_resource:
        bucket = await s3_resource.Bucket(bucket_name)
        async for obj in bucket.objects.filter(Prefix=prefix):
            yield obj.key


async def upload_files_async(
        files_path: str | pathlib.Path,
        bucket_name: str,
        prefix: str | pathlib.Path,
        overwrite: bool = False,
        callback: Callable | None = None
    ):
    """
    upload the files in the given file path (or a single file path) to the given s3 bucket at given prefix
    """
    async with session.resource("s3") as s3_resource:
        bucket = await s3_resource.Bucket(bucket_name)
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
                if not overwrite and await object_exists_async(bucket_name, object_key):
                    raise FileExistsError(f"An object with key '{object_key}' exist already, use overwrite=True to overwrite")
                await bucket.upload_file(file_path, object_key)
                if callback is not None:
                    callback(file_path=file_path, object_key=object_key)


async def download_files_async(
        bucket_name: str,
        prefix: str | pathlib.Path,
        directory: str | pathlib.Path,
        create_missing_path: bool=False,
        callback: Callable | None = None
    ):
    """
    download the files at the given prefix (or a single file) of a given bucket in the given directory
    """
    async with session.resource("s3") as s3_resource:
        bucket = await s3_resource.Bucket(bucket_name)
        directory = pathlib.Path(directory)
        if not directory.exists():
            if create_missing_path:
                directory.mkdir(parents=True)
            else:
                raise NotADirectoryError(f"The directory '{directory}' does not exist, set create_missing_path=True to allow creating it")
        if not directory.is_dir():
            raise NotADirectoryError(f"The provided directory path '{directory}' is a file")
        prefix = pathlib.Path(prefix)
        for obj in list_objects_async(bucket_name, prefix):
            file_path = directory / pathlib.Path(obj.key).relative_to(prefix)
            file_path.parent.mkdir(exist_ok=True, parents=True)
            file_path = file_path.as_posix()
            await bucket.download_file(obj.key, file_path)
            if callback is not None:
                callback(object_key=obj.key, file_path=file_path)


async def upload_data_async(
        data: bytes,
        bucket_name: str,
        key: str|pathlib.Path,
        overwrite: bool = False
    ):
    """
    save the given bytes as an object
    """
    if isinstance(key, pathlib.Path):
        key = key.as_posix()
    if not overwrite and await object_exists_async(bucket_name, key):
        raise S3Exception(f"An object with key '{key}' exist already, use overwrite=True to overwrite")
    async with session.resource("s3") as s3_resource:
        obj = await s3_resource.Object(bucket_name, key)
        await obj.put(Key=key, Body=data)


async def download_data_async(bucket_name: str, key: str | pathlib.Path) -> bytes | None:
    """
    load the data stored in the given bucket file
    """
    if isinstance(key, pathlib.Path):
        key = key.as_posix()
    async with session.resource("s3") as s3_resource:
        obj = await s3_resource.Object(bucket_name, key)
        try:
            response = await obj.get()
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                return None
            else:
                raise
        return await response["Body"].read()


async def delete_objects_async(bucket_name: str, prefix: str | pathlib.Path, callback: Callable | None = None):
    """
    Delete all objects that match the prefix
    """
    async with session.resource("s3") as s3_resource:
        bucket = await s3_resource.Bucket(bucket_name)
        objects = [obj async for obj in list_objects_async(bucket_name, prefix)]
        delete = [{"Key": key} for i, key in zip(range(1_000), objects)]
        if len(delete) == 0:
            return
        await bucket.delete_objects(Delete={"Objects": delete})
        if callback is not None:
            for obj in delete:
                callback(object_key=obj["Key"])


async def copy_object_async(
    source_bucket: str,
    source_key: str,
    dest_bucket: str,
    dest_key: str
):
    """
    Copy an object within S3.
    """
    async with session.client("s3") as s3:
        copy_source = {"Bucket": source_bucket, "Key": source_key}
        await s3.copy_object(
            Bucket=dest_bucket,
            Key=dest_key,
            CopySource=copy_source
        )


async def delete_object_async(
    bucket_name: str,
    key: str
):
    """
    Delete an object from S3.
    If the object did not exist, do nothing silently.
    """
    async with session.client("s3") as s3:
        await s3.delete_object(Bucket=bucket_name, Key=key)


async def move_object_async(
    source_bucket: str,
    source_key: str,
    dest_bucket: str,
    dest_key: str
):
    """
    Move an object in S3 by copying and then deleting.
    """
    await copy_object_async(source_bucket, source_key, dest_bucket, dest_key)
    await delete_object_async(source_bucket, source_key)


async def initiate_multipart_upload_async(bucket_name: str, key: str, content_type: str = 'application/octet-stream') -> str:
    async with session.client("s3") as s3_client:
        response = await s3_client.create_multipart_upload(
            Bucket=bucket_name,
            Key=key,
            ContentType=content_type
        )
        return response['UploadId']


async def upload_part_async(bucket_name: str, key: str, multipart_upload_id: str, part_number: int, chunk: bytes) -> str:
    async with session.client("s3") as s3_client:
        response = await s3_client.upload_part(
            Bucket=bucket_name,
            Key=key,
            PartNumber=part_number,
            UploadId=multipart_upload_id,
            Body=chunk
        )
        return response["ETag"]


async def complete_multipart_upload_async(bucket_name: str, key: str, multipart_upload_id: str, part_tags: list[str]):
    async with session.client("s3") as s3_client:
        await s3_client.complete_multipart_upload(
            Bucket=bucket_name,
            Key=key,
            UploadId=multipart_upload_id,
            MultipartUpload={
                'Parts': [{'ETag': e_tag, 'PartNumber': i} for i, e_tag in enumerate(part_tags, start=1)]
            }
        )


async def abort_multipart_upload_async(bucket_name: str, key: str, multipart_upload_id: str):
    async with session.client("s3") as s3_client:
        await s3_client.abort_multipart_upload(
            Bucket=bucket_name,
            Key=key,
            UploadId=multipart_upload_id
        )


async def generate_download_url_async(bucket_name: str, key: str, expiration: int = 3600) -> str:
    """
    Generate a download url, for the given s3 object, with the given validity
    """
    async with session.client("s3") as s3_client:
        return await s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket_name, 'Key': key},
            ExpiresIn=expiration
        )


def s3_uri_to_bucket_and_key(s3_uri: str) -> tuple[str, str]:
    """
    Splits an 's3://bucket-name/object/key' uri into a (bucket_name, object_key) tuple of str
    """
    parsed = urlparse(s3_uri)
    scheme, s3_bucket, s3_object_key = parsed.scheme, parsed.netloc, parsed.path
    assert scheme == "s3"
    return s3_bucket, s3_object_key