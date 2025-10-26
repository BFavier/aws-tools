import asyncio
import unittest
import pathlib
from uuid import uuid4
from aws_tools.s3 import S3Exception, S3
from aws_tools._check_fail_context import check_fail


data_path = pathlib.Path(__file__).parent / "data" / "s3"


class DynamoDBTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """
        create a table and define items
        """
        cls.bucket_name = "unit-test-"+str(uuid4())
        async def setup():
            async with S3() as s3:
                await s3.create_bucket_async(cls.bucket_name)
                with open(data_path / "sample_file.json", "r") as f:
                    cls.data = f.read().encode()
        asyncio.run(setup())

    @classmethod
    def tearDownClass(cls):
        """
        Delete the table if it was not done already
        """
        try:
            async def tear_down():
                async with S3() as s3:
                    await s3.delete_objects_async(cls.bucket_name, prefix="")
                    await s3.delete_bucket_async(cls.bucket_name)
            asyncio.run(tear_down())
        except S3Exception:
            pass

    def setUp(self):
        """
        Before each test case, do nothing
        """
        pass

    def tearDown(self):
        """
        After each test case, delete all items
        """
        async def tear_down():
            async with S3() as s3:
                if await s3.bucket_exists_async(self.bucket_name):
                    await s3.delete_objects_async(self.bucket_name, prefix="")
        asyncio.run(tear_down())

    def test_upload(self):
        """
        Test basic table creation and listing
        """
        key = "sample_file.json"
        # create the file
        async def test():
            async with S3() as s3:
                assert not await s3.object_exists_async(self.bucket_name, key)
                await s3.upload_data_async(self.data, self.bucket_name, key, overwrite=False)
                with check_fail(S3Exception):
                    await s3.upload_data_async(self.data, self.bucket_name, key, overwrite=False)
                await s3.upload_data_async(self.data, self.bucket_name, key, overwrite=True)
                assert await s3.object_exists_async(self.bucket_name, key)
                assert [key async for key, _ in s3.list_objects_key_and_size_async(self.bucket_name)] == [key]
                assert (await s3.get_object_bytes_size_async(self.bucket_name, key)) == len(self.data)
                assert (await s3.download_data_async(self.bucket_name, key)) == self.data
                # delete the file
                await s3.delete_object_async(self.bucket_name, key)
                assert not await s3.object_exists_async(self.bucket_name, key)
                # check missing file behaviour
                missing_key = "missing_file.json"
                assert not await s3.object_exists_async(self.bucket_name, missing_key)
                assert (await s3.get_object_bytes_size_async(self.bucket_name, missing_key)) is None
                # upload files from disk
                await s3.upload_files_async(data_path, self.bucket_name, prefix="")
                assert {key async for key, _ in s3.list_objects_key_and_size_async(self.bucket_name)} == {key, "empty_file.json"}
                assert await s3.get_object_bytes_size_async(self.bucket_name, "empty_file.json") == 0
                # move objects
                await s3.move_object_async(self.bucket_name, key, self.bucket_name, missing_key)
                assert not await s3.object_exists_async(self.bucket_name, key)
                assert await s3.object_exists_async(self.bucket_name, missing_key)
                # copy object
                await s3.copy_object_async(self.bucket_name, missing_key, self.bucket_name, key)
                assert await s3.object_exists_async(self.bucket_name, key)
                assert await s3.object_exists_async(self.bucket_name, missing_key)
                assert await s3.download_data_async(self.bucket_name, key)
                # delete multiple files
                await s3.delete_objects_async(self.bucket_name, prefix="")
                assert [key async for key, _ in s3.list_objects_key_and_size_async(self.bucket_name, "")] == []
        asyncio.run(test())


if __name__ == "__main__":
    unittest.main()
