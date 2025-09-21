import json
import pathlib
import unittest
from aws_tools.synchrone.ecs import ECSTaskStateChangeEvent



data_path = pathlib.Path(__file__).parent / "data" / "ecs-events"


ECSTaskStateChangeEvent.model_config = {"extra": "forbid"}


class TestSES(unittest.TestCase):

    def test_list_files_in_data_path(self):
        files = list(data_path.glob("*"))
        files = [f for f in data_path.iterdir() if f.is_file() and f.suffix.lower() == ".json"]
        for file in files:
            with open(data_path / file, "r") as h:
                kwargs = json.load(h)
            print(file.stem)
            ECSTaskStateChangeEvent(**kwargs)
        assert len(files) > 0, "No files found in the data path"


if __name__ == "__main__":
    unittest.main()