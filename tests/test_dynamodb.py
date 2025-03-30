import unittest
from uuid import uuid4
from decimal import Decimal
from aws_tools.dynamoDB import list_tables, get_table, table_exists, create_table, delete_table
from aws_tools.dynamoDB import item_exists, get_item, put_item, batch_put_items, delete_item, batch_delete_items
from aws_tools.dynamoDB import query_items, Attr
from aws_tools.dynamoDB import (get_item_field, put_item_field, remove_item_field,
                                increment_item_field, extend_array_item_field,
                                extend_set_item_field, remove_from_set_item_field)


class check_fail:
    """
    Context that exit silently at the first error.
    If there was no error on leaving the context, raise one.
    """

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is not None:
            return True
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
            cls.another_id = {"id": str(uuid4()), "event_time": "21h00"}
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
            items, _ = query_items(self.table)
            batch_delete_items(self.table, items)

    def test_table_api(self):
        """
        Test basic table creation and listing
        """
        assert self.table_name in list_tables()
        table = get_table(self.table_name)
        with check_fail():
            get_table("unknown_table")
        assert table_exists(self.table_name)
        assert not table_exists("unknown_table")
        with check_fail():
            create_table(self.table_name, {"HASH": "id", "RANGE": "event_time"}, {"id": "S", "event_time": "S"})

    def test_item_api(self):
        """
        Test basic item API
        """
        # test missing item behaviour
        assert len(query_items(self.table)[0]) == 0
        assert not item_exists(self.table, self.item)
        assert not item_exists(self.table, self.item_id)
        assert get_item(self.table, self.item_id) is None
        assert delete_item(self.table, self.item_id, return_object=True) is None  # Fails silently and return None, as the object did not exist
        batch_delete_items(self.table, [self.item_id])  # Fails silently, as there is no verification of item existence
        # test item putting
        assert put_item(self.table, self.item, return_object=True) is None
        batch_put_items(self.table, [self.item, self.another_item])
        # check item exists behaviour
        assert item_exists(self.table, self.item_id)
        assert get_item(self.table, self.item_id) == self.item
        assert get_item(self.table, self.item) == self.item
        assert get_item(self.table, self.another_id) == self.another_item
        assert len(query_items(self.table)[0]) == 2
        assert len(query_items(self.table, hash_key=self.item_id["id"], sort_key_interval=(None, "21h00"), subset=["event_time"])[0]) == 0
        assert len(query_items(self.table, hash_key=self.item_id["id"], sort_key_interval=("23h00", "23h59"))[0]) == 1
        assert len(query_items(self.table, conditions=Attr("some_field").gte("not_ok") & Attr("field").lt(Decimal(100)) | Attr("id").eq("ID10"), subset=["id"])[0]) == 1
        assert len(query_items(self.table, conditions=Attr("some_field").not_exists(), subset=["id"])[0]) == 1
        # check overwrite behaviour
        with check_fail():
            put_item(self.table, self.item_id)
        assert put_item(self.table, self.new_item, overwrite=True, return_object=True) == self.item
        assert get_item(self.table, self.item_id) == self.new_item  # verify that the item has correctly be overwritten
        batch_put_items(self.table, [self.item, self.another_item])
        assert get_item(self.table, self.item_id) == self.item  # verify that the item has correctly be overwritten
        # check delete behaviour
        assert delete_item(self.table, self.item_id, return_object=True)
        batch_delete_items(self.table, [self.item_id, self.another_id])

    def test_field_api(self):
        # everything raise an error on missing item
        with check_fail():
            get_item_field(self.table, self.item_id, "field")
        with check_fail():
            put_item_field(self.table, self.item_id, "field")
        with check_fail():
            put_item_field(self.table, self.item_id, "field", overwrite=True)
        with check_fail():
            remove_item_field(self.table, self.item_id, "field")
        with check_fail():
            increment_item_field(self.table, self.item_id, "field", 0., default=None)
        with check_fail():
            extend_array_item_field(self.table, self.item_id, "array_field", [0.])
        with check_fail():
            extend_set_item_field(self.table, self.item_id, "set_field", {"d"})
        with check_fail():
            remove_from_set_item_field(self.table, self.item_id, "set_field", {"c"})
        # create the item
        put_item(self.table, self.new_item, overwrite=False)
        # creating several depths of field at once does not work
        with check_fail():
            put_item_field(self.table, self.item_id, "missing_field.subfield", 4, overwrite=True)
        # set item can overwrite an existing field or raise an error depending on the 'overwrite' flag
        assert put_item_field(self.table, self.item_id, "array_field[0].nested", 3.5, overwrite=True, return_object=True) == 10.0
        with check_fail():
            put_item_field(self.table, self.item_id, "array_field[0].nested", 3.5, overwrite=False)
        # existing items can be returned, you can use complex field paths
        assert get_item_field(self.table, self.item_id, "field") == -1
        assert get_item_field(self.table, self.item_id, "array_field[0].nested")  == 3.5
        # set field can be modified, the returned object is whether the value previously existed in the set
        assert extend_set_item_field(self.table, self.item_id, "set_field", {"d"}, return_object=True) == {"d"}
        assert extend_set_item_field(self.table, self.item_id, "set_field", {"d"}, return_object=True) == set()
        assert get_item_field(self.table, self.item_id, "set_field") == {"a", "b", "c", "d"}
        assert remove_from_set_item_field(self.table, self.item_id, "set_field", {"c"}, return_object=True) == {"c"}
        assert remove_from_set_item_field(self.table, self.item_id, "set_field", {"c"}, return_object=True) == set()
        assert get_item_field(self.table, self.item_id, "set_field") == {"a", "b", "d"}
        # some functions raise an error on a missing field, because if they returned None, we could not distinguishe between a None field or no field
        with check_fail():
            get_item_field(self.table, self.item_id, "missing_field")
        with check_fail():
            remove_item_field(self.table, self.item_id, "missing_field")
        with check_fail():
            increment_item_field(self.table, self.item_id, "missing_field", 0.)
        with check_fail():
            extend_array_item_field(self.table, self.item_id, "missing_field", [0.])
        with check_fail():
            extend_set_item_field(self.table, self.item_id, "missing_field", {"d"})
        with check_fail():
            remove_from_set_item_field(self.table, self.item_id, "missing_field", {"c"})
        # put_item_field returns None if the item was missing
        assert put_item_field(self.table, self.item_id, "missing_field", "abcd", return_object=True) is None
        # append and increment functions work
        assert increment_item_field(self.table, self.item_id, "another_missing_field", delta=1, default=0, return_object=True) == 1  # with default value, missing field works
        assert increment_item_field(self.table, self.item_id, "field", delta=1, return_object=True) == 0.0
        assert increment_item_field(self.table, self.item_id, "field", delta=2.0, return_object=True) == 2.0
        # increment with default can create a missing item together with the field
        assert not item_exists(self.table, self.another_id)
        assert increment_item_field(self.table, self.another_id, "field", delta=-1.0, default=0.0, return_object=True) == -1.0
        assert item_exists(self.table, self.another_id)
        # directly creating nested fields still does not work though
        with check_fail():
            increment_item_field(self.table, self.item_id, "yet_another_missing_field.subfield", delta=1, default=0, return_object=True)
        # testing array extend
        assert extend_array_item_field(self.table, self.item_id, "array_field", [None, "abcd"], return_object=True) == [{"nested": 3.5}, None, "abcd"]
        # you can delete a single nested path or a full field at once
        assert remove_item_field(self.table, self.item_id, "array_field[0].nested", return_object=True) == 3.5
        assert remove_item_field(self.table, self.item_id, "array_field", return_object=True) == [{}, None, 'abcd']
    
    def test_increment_item_field_api(self):
        # everything raise an error on missing item
        pass
    
    def test_extend_array_field_api(self):
        # everything raise an error on missing item
        pass

    def test_set_field_api(self):
        # everything raise an error on missing item
        pass

    def test_table_delete(self):
        new_table_name = "unit-test-unknown-table-"+str(uuid4())
        new_table = create_table(new_table_name, {"HASH": "id", "RANGE": "event_time"}, {"id": "S", "event_time": "S"})
        assert table_exists(new_table_name)
        delete_table(new_table)
        assert not table_exists(new_table_name)
        assert new_table_name not in list_tables()
        with check_fail():
            delete_table(new_table)

if __name__ == "__main__":
    unittest.main()