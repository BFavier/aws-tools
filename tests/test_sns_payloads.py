import json
import pathlib
import unittest
from aws_tools.synchrone.sns import SNSEventsTypes, verify_sns_signature
from pydantic import TypeAdapter



data_path = pathlib.Path(__file__).parent / "data" / "SNS-events"



class TestSNS(unittest.TestCase):

    def test_list_files_in_data_path(self):
        files = list(data_path.glob("*"))
        files = [f for f in data_path.iterdir() if f.is_file() and f.suffix.lower() == ".json"]
        for file in files:
            with open(data_path / file, "r") as h:
                payload = json.load(h)
            body = TypeAdapter(SNSEventsTypes).validate_python(payload)
            assert verify_sns_signature(body)
        assert len(files) > 0, "No files found in the data path"


if __name__ == "__main__":
    unittest.main()