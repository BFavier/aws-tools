from uuid import uuid4
from decimal import Decimal
from aws_tools.dynamoDB import list_tables, get_table, table_exists, create_table, delete_table
from aws_tools.dynamoDB import item_exists, get_item, put_item, batch_put_items, delete_item, batch_delete_items
from aws_tools.dynamoDB import query_items, Attr
from aws_tools.dynamoDB import (get_item_field, put_item_field, remove_item_field,
                                   increment_item_field, extend_array_item_field,
                                   insert_in_set_item_field, remove_from_set_item_field)


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


def test_dynamodb():
    """
    test the table API
    """
    table_name = "unit-test-"+str(uuid4())
    assert not table_exists(table_name)
    with check_fail():
        get_table(table_name)
    table = create_table(table_name, {"HASH": "id", "RANGE": "event_time"}, {"id": "S", "event_time": "S"})
    try:
        assert table_name in list_tables()
        table = get_table(table_name)
        assert table_exists(table_name)
        with check_fail():
            create_table(table_name, {"HASH": "id", "RANGE": "event_time"}, {"id": "S", "event_time": "S"})
        check_item(table)
    except Exception as e:
        delete_table(table)
        raise e
    delete_table(table)
    assert not table_exists(table_name)
    with check_fail():
        delete_table(table)


def check_item(table: object):
    """
    test the table item API
    """
    item_id = {"id": str(uuid4()), "event_time": "23h30"}
    item = {**item_id, "field": 10.0, "some_field": "ok", "other_field": True}
    assert not item_exists(table, item_id)
    assert get_item(table, item_id) is None
    with check_fail():
        delete_item(table, item_id)
    assert put_item(table, item, return_object=True) is None
    assert item_exists(table, item_id)
    assert len(query_items(table, hash_key=item_id["id"], sort_key_interval=(None, "21h00"), subset=["event_time"])[0]) == 0
    assert len(query_items(table, hash_key=item_id["id"], sort_key_interval=("23h00", "23h59"))[0]) == 1
    assert len(query_items(table, conditions=Attr("some_field").gte("not_ok") & Attr("field").lt(Decimal(100)) | Attr("id").eq("ID10"), subset=["id"])[0]) == 1
    with check_fail():
        put_item(table, item_id)
    new_item = {**item_id, "field": -1.0, "array_field": [{"nested": 10.0}], "set_field": {"a", "b", "c"}}
    assert put_item(table, new_item, overwrite=True, return_object=True) == item
    batch_put_items(table, [new_item])
    assert get_item(table, item_id) == new_item
    check_item_field(table, item_id)
    assert isinstance(delete_item(table, item_id, return_object=True), dict)
    with check_fail():
        delete_item(table, item)
    assert put_item(table, item, return_object=True) is None
    batch_delete_items(table, [new_item])
    assert get_item(table, item_id) is None
    with check_fail():
        delete_item(table, item)


def check_item_field(table: object, item_id: str):
    """
    test the table item field API
    """
    while True:
        missing_id = {"id": str(uuid4()), "timestamp": "23h30"}
        if missing_id != item_id:
            break
    # everything raise an error on missing item
    with check_fail():
        get_item_field(table, missing_id, "field")
    with check_fail():
        put_item_field(table, missing_id, "field")
    with check_fail():
        put_item_field(table, missing_id, "field", overwrite=True)
    with check_fail():
        remove_item_field(table, missing_id, "field")
    with check_fail():
        increment_item_field(table, missing_id, "field", 0.)
    with check_fail():
        extend_array_item_field(table, missing_id, "array_field", [0.])
    with check_fail():
        insert_in_set_item_field(table, missing_id, "set_field", "d")
    with check_fail():
        remove_from_set_item_field(table, missing_id, "set_field", "c")
    # set item can overwrite an existing field or raise an error depending on the 'overwrite' flag
    assert put_item_field(table, item_id, "array_field[0].nested", 3.5, overwrite=True, return_object=True) == 10.0
    with check_fail():
        put_item_field(table, item_id, "array_field[0].nested", 3.5)
    # existing items can be returned, you can use complex field paths
    assert get_item_field(table, item_id, "field") == -1.0
    assert get_item_field(table, item_id, "array_field[0].nested")  == 3.5
    # set field can be modified, the returned object is whether the value previously existed in the set
    assert insert_in_set_item_field(table, item_id, "set_field", "d", return_object=True) == False
    assert insert_in_set_item_field(table, item_id, "set_field", "d", return_object=True) == True
    assert get_item_field(table, item_id, "set_field") == {"a", "b", "c", "d"}
    assert remove_from_set_item_field(table, item_id, "set_field", "c", return_object=True) == True
    assert remove_from_set_item_field(table, item_id, "set_field", "c", return_object=True) == False
    assert get_item_field(table, item_id, "set_field") == {"a", "b", "d"}
    # some functions raise an error on a missing field
    with check_fail():
        get_item_field(table, item_id, "missing_field")
    with check_fail():
        remove_item_field(table, item_id, "missing_field")
    with check_fail():
        extend_array_item_field(table, item_id, "missing_field", [0.])
    with check_fail():
        insert_in_set_item_field(table, missing_id, "missing_field", "d")
    with check_fail():
        remove_from_set_item_field(table, missing_id, "missing_field", "c")
    # put_item_field returns None if the item was missing
    assert put_item_field(table, item_id, "missing_field", "abcd", return_object=True) is None
    # you can't set a full missing path without error
    with check_fail():
        put_item_field(table, item_id, "other_missing_field.missing_nested", 4)
    # append and increment functions work
    assert increment_item_field(table, item_id, "another_missing_field", 1, return_object=True) == 1
    assert increment_item_field(table, item_id, "field", 2.0, return_object=True) == 1.0
    assert extend_array_item_field(table, item_id, "array_field", [None, "abcd"], return_object=True) == [{"nested": 3.5}, None, "abcd"]
    # you can delete a single nested path or a full field at once
    assert remove_item_field(table, item_id, "array_field[0].nested", return_object=True) == 3.5
    remove_item_field(table, item_id, "array_field")


if __name__ == "__main__":
    test_dynamodb()