import os
import gzip
import random
import tarfile
import asyncio
import unittest
from io import BytesIO
from uuid import uuid4
from copy import deepcopy
from typing import AsyncIterable, Iterable, Any, TypeVar
from compression_tools.gz import gz_stream_async
from compression_tools.tar import tar_stream_async, StreamedFile


T = TypeVar("T")


async def as_async_iterable(iterable: Iterable[T]) -> AsyncIterable[T]:
    for v in iterable:
        yield v


def as_iterable(data: bytes, CHUNK_SIZE: int=100) -> Iterable[bytes]:
    for i in range(0, len(data), CHUNK_SIZE):
        yield data[i:i+CHUNK_SIZE]


async def sum_async(iterable: AsyncIterable, start=0) -> Any:
    start = deepcopy(start)
    async for value in iterable:
        start += value
    return start


def tar_to_dict(tar_bytes: bytes) -> dict[str, bytes]:
    """
    Read a tar archive from bytes and return a dict {filename: file_content_bytes}.
    """
    result = {}
    with tarfile.open(fileobj=BytesIO(tar_bytes), mode="r:*") as tar:
        for member in tar.getmembers():
            if member.isfile():  # skip directories
                file_obj = tar.extractfile(member)
                if file_obj is not None:
                    result[member.name] = file_obj.read()
    return result


class TestCompression(unittest.TestCase):

    def test_gz(self):
        async def test_gz_async():
            data = os.urandom(4096)
            assert gzip.decompress(await sum_async(gz_stream_async(as_iterable(data)), b"")) == data
            assert gzip.decompress(await sum_async(gz_stream_async(as_async_iterable(as_iterable(data))), b"")) == data
        asyncio.run(test_gz_async())

    @staticmethod
    def _generate_files_content(n_files: int=10, min_size: int=1024, max_size: int=4096) -> dict[str, bytes]:
        return {str(uuid4()): os.urandom(random.randint(min_size, max_size)) for _ in range(n_files)}

    def test_tar(self):
        async def test_tar_async():
            files_by_name = self._generate_files_content()
            assert tar_to_dict(await sum_async(tar_stream_async((StreamedFile(name=k, bytes_size=len(v), data_stream=as_async_iterable(as_iterable(v))) for k, v in files_by_name.items())), b"")) == files_by_name
            assert tar_to_dict(await sum_async(tar_stream_async(as_async_iterable(StreamedFile(name=k, bytes_size=len(v), data_stream=as_async_iterable(as_iterable(v))) for k, v in files_by_name.items())), b"")) == files_by_name
        asyncio.run(test_tar_async())


if __name__ == "__main__":
    unittest.main()
