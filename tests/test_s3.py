import unittest
import pathlib
from uuid import uuid4
from aws_tools.s3 import S3Exception, create_bucket, delete_bucket, bucket_exists, object_exists, get_object_bytes_size, list_objects, upload_files, download_files, upload_data, download_data, delete_objects, copy_object, delete_object, move_object, initiate_multipart_upload, upload_part, complete_multipart_upload, abort_multipart_upload, generate_download_url
from aws_tools._check_fail_context import check_fail


data_path = pathlib.Path(__file__).parent / "data" / "s3"


class DynamoDBTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """
        create a table and define items
        """
        cls.bucket_name = "unit-test-"+str(uuid4())
        create_bucket(cls.bucket_name)
        with open(data_path / "sample_file.json", "r") as f:
            cls.data = f.read()

    @classmethod
    def tearDownClass(cls):
        """
        Delete the table if it was not done already
        """
        try:
            delete_objects(cls.bucket_name, prefix="")
            delete_bucket(cls.bucket_name)
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
        if bucket_exists(self.bucket_name):
            delete_objects(self.bucket_name, prefix="")

    def test_upload(self):
        """
        Test basic table creation and listing
        """
        key = "sample_file.json"
        # create the file
        assert not object_exists(self.bucket_name, key)
        upload_data(self.data, self.bucket_name, key, overwrite=False)
        with check_fail(S3Exception):
            upload_data(self.data, self.bucket_name, key, overwrite=False)
        upload_data(self.data, self.bucket_name, key, overwrite=True)
        assert object_exists(self.bucket_name, key)
        assert list(list_objects(self.bucket_name, "")) == [key]
        assert get_object_bytes_size(self.bucket_name, key) == len(self.data)
        assert download_data(self.bucket_name, key) == self.data.encode()
        # delete the file
        delete_object(self.bucket_name, key)
        assert not object_exists(self.bucket_name, key)
        # check missing file behaviour
        missing_key = "missing_file.json"
        assert not object_exists(self.bucket_name, missing_key)
        with check_fail(S3Exception):
            get_object_bytes_size(self.bucket_name, missing_key)
        # upload files from disk
        upload_files(data_path, self.bucket_name, prefix="")
        assert set(list_objects(self.bucket_name, "")) == {key, "empty_file.json"}
        assert get_object_bytes_size(self.bucket_name, "empty_file.json") == 0
        # move objects
        move_object(self.bucket_name, key, self.bucket_name, missing_key, blocking=True)
        assert not object_exists(self.bucket_name, key)
        assert object_exists(self.bucket_name, missing_key)
        # delete multiple files
        delete_objects(self.bucket_name, prefix="")
        assert list(list_objects(self.bucket_name, "")) == []


if __name__ == "__main__":
    unittest.main()
