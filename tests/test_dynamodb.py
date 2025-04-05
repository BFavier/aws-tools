import unittest
from uuid import uuid4
from decimal import Decimal
from aws_tools.dynamoDB import list_tables, get_table, get_table_keys, table_exists, create_table, delete_table
from aws_tools.dynamoDB import item_exists, get_item, put_item, batch_put_items, delete_item, batch_delete_items, update_item, get_item_fields
from aws_tools.dynamoDB import scan_items, query_items, Scan, Query, Attr, Decimal
from aws_tools.dynamoDB import DynamoDBException


class check_fail:
    """
    Context that exit silently at the first error.
    If there was no error on leaving the context, raise one.
    """

    def __init__(self, exception_type: type[Exception] = Exception):
        self.exception_type = exception_type

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if isinstance(exc_value, self.exception_type):
            return True
        elif exc_value is not None:
            raise exc_value
        raise RuntimeError("This should have raised an error.")


class DynamoDBTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """
        create a table and define items
        """
        cls.table_name = "unit-test-"+str(uuid4())
        cls.table = create_table(cls.table_name, {"HASH": "id", "RANGE": "event_time"}, {"id": "S", "event_time": "S"})
        cls.item_id = {"id": str(uuid4()), "event_time": "23h30"}
        cls.item = {**cls.item_id, "field": 10.0, "some_field": "ok", "other_field": True}
        cls.new_item = {**cls.item_id, "field": -1.0, "array_field": [{"nested": 10.0}], "set_field": {"a", "b", "c"}}
        while True:
            cls.another_id = {"id": cls.item_id["id"], "event_time": "21h00"}
            if cls.another_id != cls.item_id:
                break
        cls.another_item = {**cls.another_id, "another_field": 10.0}

    @classmethod
    def tearDownClass(cls):
        """
        Delete the table if it was not done already
        """
        try:
            delete_table(cls.table)
        except:
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
        if table_exists(self.table_name):
            items, _ = scan_items(self.table)
            batch_delete_items(self.table, items)

    def test_table_api(self):
        """
        Test basic table creation and listing
        """
        assert self.table_name in list_tables()
        table = get_table(self.table_name)
        with check_fail(DynamoDBException):
            get_table("unknown_table")
        assert table_exists(self.table_name)
        assert not table_exists("unknown_table")
        with check_fail(DynamoDBException):
            create_table(self.table_name, {"HASH": "id", "RANGE": "event_time"}, {"id": "S", "event_time": "S"})

    def test_table_deletion(self):
        new_table_name = "unit-test-unknown-table-"+str(uuid4())
        new_table = create_table(new_table_name, {"HASH": "id", "RANGE": "event_time"}, {"id": "S", "event_time": "S"})
        assert table_exists(new_table_name)
        delete_table(new_table)
        assert not table_exists(new_table_name)
        assert new_table_name not in list_tables()
        with check_fail(DynamoDBException):
            delete_table(new_table)

    def test_item_api(self):
        """
        Test basic item API
        """
        # test missing item behaviour
        assert not item_exists(self.table, self.item)
        assert not item_exists(self.table, self.item_id)
        assert get_item(self.table, self.item_id) is None
        assert delete_item(self.table, self.item_id, return_object=True) is None  # Fails silently and return None, as the object did not exist
        batch_delete_items(self.table, [self.item_id])  # Fails silently, as there is no verification of item existence
        # test item putting
        assert put_item(self.table, self.item, return_object=True) is None
        assert item_exists(self.table, self.item_id)
        batch_put_items(self.table, [self.another_item])
        assert item_exists(self.table, self.another_id)
        # check getting item by id or full item
        assert get_item(self.table, self.item_id) == self.item
        assert get_item(self.table, self.item) == self.item
        assert get_item(self.table, self.another_id) == self.another_item
        # check overwrite behaviour
        with check_fail(DynamoDBException):
            put_item(self.table, self.item_id)
        assert put_item(self.table, self.new_item, overwrite=True, return_object=True) == self.item
        assert get_item(self.table, self.item_id) == self.new_item  # verify that the item has correctly be overwritten
        batch_put_items(self.table, [self.item, self.another_item])
        assert get_item(self.table, self.item_id) == self.item  # verify that the item has correctly be overwritten
        # check delete behaviour
        assert delete_item(self.table, self.item_id, return_object=True)
        batch_delete_items(self.table, [self.item_id, self.another_id])

    def test_query_scan_api(self):
        # test missing items behaviour
        assert scan_items(self.table)[0] == []
        assert query_items(self.table, hash_key=self.item_id["id"])[0] == []
        # create the item
        put_item(self.table, self.item, overwrite=False)
        assert get_item(self.table, self.item_id)["event_time"] == "23h30"
        put_item(self.table, self.another_item, overwrite=False)
        assert get_item(self.table, self.another_id)["event_time"] == "21h00"
        assert get_table_keys(self.table)["RANGE"] == "event_time"  # event time is the sort key
        # scan all items
        assert all(v in (self.another_item, self.item) for v in scan_items(self.table)[0])
        assert all(v in (self.another_item, self.item) for v in Scan(self.table, conditions=Attr("field").eq(Decimal(10.0))))
        # query with hash key only
        assert all(v in (self.another_item, self.item) for v in query_items(self.table, hash_key=self.item_id["id"])[0])
        assert all(v in (self.another_item, self.item) for v in Query(self.table, hash_key=self.item_id["id"]))
        # query with hash and sort key
        assert query_items(self.table, hash_key=self.item_id["id"], sort_key_interval=(None, "21h00"))[0] == [self.another_item]
        assert query_items(self.table, hash_key=self.item_id["id"], sort_key_interval=("23h30", None))[0] == [self.item]
        assert query_items(self.table, hash_key=self.item_id["id"], sort_key_interval=("21h00", "23h30"))[0] == [self.another_item, self.item]
        assert query_items(self.table, hash_key=self.item_id["id"], sort_key_interval=("21h00", "23h30"), ascending=False)[0] == [self.item, self.another_item]
        # scan with conditions
        assert scan_items(self.table, conditions=Attr("field").eq(Decimal(10.0)) & Attr("some_field").eq("ok"))[0] == [self.item]
        # query with conditions
        assert query_items(self.table, hash_key=self.item_id["id"], sort_key_interval=("21h00", "23h30"), conditions=Attr("field").eq(Decimal(10.0)))[0] == [self.item]

    def test_update_item(self):
        # raise an error on missing item
        with check_fail(DynamoDBException):
            update_item(self.table, self.item_id, put_fields={"field": 1})
        assert get_item_fields(self.table, self.item_id, {"field"}) is None
        update_item(self.table, self.another_id, put_fields={"field": None}, create_item_if_missing=True)
        assert get_item_fields(self.table, self.another_id, {"field"}) == {"field": None}
        # create the item
        put_item(self.table, self.new_item)
        # modify it
        assert update_item(self.table, self.item_id,
            put_fields={"new_field": 1},
            increment_fields={("array_field", 0, "nested"): 2},
            remove_from_sets={"set_field": {"b", "d"}},
            delete_fields=["field"],
            return_object=True
        ) == {"new_field": 1, "array_field": [{"nested": 12.0}], "set_field": {"a", "c"}}
        update_item(self.table, self.item_id, extend_arrays={"array_field": [None]}, extend_sets={"set_field": {"a", "d"}})
        assert get_item_fields(self.table, self.item_id, {"array_field", "set_field"}) == {"array_field": [{"nested": 12.0}, None], "set_field": {"a", "c", "d"}}

    def test_get_item_fields(self):
        # return None on a missing item
        assert get_item_fields(self.table, self.item_id, {"field"}) is None
        # create the item
        put_item(self.table, self.new_item)
        # check that we can get the existing fields
        assert get_item_fields(self.table, self.item_id, {"field", ("array_field", 0), "missing_field"}) == {"field": -1, ("array_field", 0): {"nested": 10.0}}


if __name__ == "__main__":
    unittest.main()