import boto3
from operator import __and__
from typing import Type, Literal, Iterable
from decimal import Decimal
from boto3.dynamodb.conditions import ConditionBase, Key, Attr
from botocore.exceptions import ClientError

dynamodb = boto3.resource("dynamodb")

KeyType = dict[Literal["HASH", "RANGE"], object]


def _recursive_convert(item: object, to_decimal: bool) -> object:
    """
    replace floats with Decimal objects recursively in a dict
    """
    if isinstance(item, list):
        return [_recursive_convert(i, to_decimal) for i in item]
    elif isinstance(item, set):
        return {_recursive_convert(i, to_decimal) for i in item}
    elif isinstance(item, dict):
        return {k: _recursive_convert(v, to_decimal) for k, v in item.items()}
    elif isinstance(item, (int, float)) and to_decimal:
        return Decimal(item)
    elif isinstance(item, Decimal) and not to_decimal:
        return float(item) if item % 1 != 0 else int(item)
    elif item is None or type(item) in [str, bool]:
        return item
    else:
        raise ValueError(f"Unexpected type '{type(item).__name__}' encountered.")


def _extract_item_field_value(item: dict | None, path: str) -> object:
    """
    returnds the value at given path
    """
    if item is None:
        return None
    path = path.replace("[", ".").replace("]", "").split(".")
    for key in path:
        item = item[int(key) if key.isdigit() else key]
    return item


def _key_exists_condition(table_keys: KeyType):
    """
    Return the condition that the key exist
    """
    condition = f"attribute_exists({table_keys['HASH']})"
    if "RANGE" in table_keys.keys():
        condition += f" AND attribute_exists({table_keys['RANGE']})"
    return condition


def _key_not_exists_condition(table_keys: KeyType):
    """
    Return the condition that the key exist
    """
    condition = f"attribute_not_exists({table_keys['HASH']})"
    if "RANGE" in table_keys.keys():
        condition += f" AND attribute_not_exists({table_keys['RANGE']})"
    return condition


def list_tables() -> list[str]:
    """
    list existing tables
    """
    return [table.name for table in dynamodb.tables.all()]


def get_table(table_name: str) -> object:
    """
    Returns the table object.
    Raise an error if it does not exist.
    """
    table = dynamodb.Table(table_name)
    table.load()
    return table


def get_table_keys(table: object) -> KeyType:
    """
    Get the {type: name} of the table keys
    """
    return {ks["KeyType"]: ks["AttributeName"] for ks in table.key_schema}


def table_exists(table_name: str) -> bool:
    """
    Returns True if the table exists and False otherwise

    Example
    -------
    >>> table_exist("test-table")
    False
    """
    try:
        get_table(table_name)
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            return False
        else:
            raise e
    return True


def create_table(table_name: str,
                 partition_names: dict[Literal["HASH", "RANGE"], str],
                 data_types: dict[str, Literal["S", "N", "B"]],
                 blocking: bool=True) -> object:
    """
    Creates a table, raise an error if it already exists.

    Example
    -------
    >>> table = create_table("test-table")
    """
    table = dynamodb.create_table(
        TableName=table_name,
        KeySchema=[
            {
                'AttributeName': partition_name,
                'KeyType': partition_type
            }
        for partition_type, partition_name in partition_names.items()],
        AttributeDefinitions=[
            {
                'AttributeName': name,
                'AttributeType': data_type
            }
        for name, data_type in data_types.items()],
        BillingMode='PAY_PER_REQUEST'
    )
    # Wait until the table exists before continuing
    if blocking:
        table.meta.client.get_waiter('table_exists').wait(TableName=table_name)
    return table


def delete_table(table: object, blocking: bool=True):
    """
    Delete a table, raise an error if it does not exists

    Example
    -------
    >>> table = delete_table("test_table")
    """
    table.delete()
    # Wait until the table is correctly deleted before continuing
    if blocking:
        table.meta.client.get_waiter('table_not_exists').wait(TableName=table.name)


def item_exists(table: object, key_or_item: dict) -> bool:
    """
    Returns True if the item exists and False otherwise.
    Faster and cheaper than a 'get_item' as this only query the partition key.
    """
    table_keys = get_table_keys(table)
    key = {v: key_or_item[v] for v in table_keys.values()}
    response = table.get_item(Key=key, ProjectionExpression=",".join(key.keys()))
    return "Item" in response


def get_item(table: object, key_or_item: dict) -> dict | None:
    """
    Get a full item from it's keys, returns None if the key does not exist.
    If the table has an hash key and a range key, both must be provided in the 'keys' dict.

    Example
    -------
    >>> get_item(table, {"id": "ID0"})
    {"uuid": "ID0", "field": 10.0}
    """
    table_keys = get_table_keys(table)
    key = {v: key_or_item[v] for v in table_keys.values()}
    response = table.get_item(Key=key)
    return _recursive_convert(response.get("Item"), to_decimal=False)


def put_item(table: object, item: dict, overwrite: bool=False, return_object: bool=False) -> dict | None:
    """
    Write an item, raise an error if it already exists and overwrite=False.
    Returns the old value if return_object=True.

    Example
    -------
    >>> put_item(table, {"uuid": "ID0", "field": 10.0})
    >>> put_item(table, {"uuid": "ID0", "field": 9.0}, overwrite=True, return_object=True)
    {"uuid": "ID0", "field": 10.0}
    """
    table_keys = get_table_keys(table)
    assert all(k in item.keys() for k in table_keys.values())
    try:
        response = table.put_item(
                Item=_recursive_convert(item, to_decimal=True),
                ReturnValues="ALL_OLD" if return_object else "NONE",  # returns the overwritten item if any
                **(dict() if overwrite else dict(ConditionExpression=_key_not_exists_condition(table_keys)))
                )
    except dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
        key = {k: item[k] for k in table_keys.values()}
        raise KeyError(f"Item '{key}' already exists for table '{table.name}'")
    return _recursive_convert(response.get("Attributes"), to_decimal=False)


def batch_put_items(table: object, items: Iterable[dict]):
    """
    Create items in batch, overwriting if they already exist.
    """
    with table.batch_writer() as batch:
        for item in items:
            batch.put_item(Item=_recursive_convert(item, to_decimal=True))


def delete_item(table: object, key_or_item: dict, return_object: bool = False) -> dict | None:
    """
    Delete an item at given key, and optionally return the erased item.
    Does not fail if the item does not exists.
    Returns None instead if the item did not exists.

    Example
    -------
    >>> delete_item(table, {"id": "ID0"})
    >>> delete_item(table, {"id": "ID0"}, return_object=True)
    {"uuid": "ID1", "field": 10.0}
    """
    table_keys = get_table_keys(table)
    try:
        response = table.delete_item(
            Key={k: key_or_item[k] for k in table_keys.values()},
            ReturnValues="ALL_OLD" if return_object else "NONE",  # returns the removed item
            ConditionExpression=_key_exists_condition(table_keys)
            )
    except dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
        return None
    return _recursive_convert(response.get("Attributes"), to_decimal=False)


def batch_delete_items(table: object, keys_or_items: Iterable[dict]):
    """
    Delete the items by batch, there is no verification that they did not exist.
    """
    table_keys = get_table_keys(table)
    with table.batch_writer() as batch:
        for key in keys_or_items:
            batch.delete_item(Key={v: key[v] for v in table_keys.values()})


def query_items(table: object,
                hash_key: object | None = None,
                sort_key_interval: tuple[object | None, object | None] = (None, None),
                ascending: bool=True,
                conditions: ConditionBase | None = None,
                subset: list[str] | None = None,
                page_size: int | None = 1_000,
                page_start_token: str | None = None) -> tuple[list[dict], str | None]:
    """
    Query items that match the hash key and/or the sort key.
    Return items in a paginated way.

    Params
    ------
    table : object
        The dynamodb Table object
    hash_key : object or None
        the value of the hash_key for returned items, or None
    sort_key_interval : tuple of two objects
        the (from, to) interval (including boundary on both sides) for the sort key, a None means an unbounded side for the interval
    ascending : bool
        If one of 'hash_key' or 'sort_key' is provided, the results are returned by ascending (or descending) order of 'sort_key'.
        Otherwise it has no effect, as the full scan is not ordered.
    conditions : ConditionBase
        the conditions on which returned items are filtered
    subset : list of str or None
        the subset of fields to return, when fields are not all usefull, to avoid returning the full object
        (dynamoDB is billed by the byte)
    page_size : int or None
        Maximum number of items returned in a single page.
        The number of items per page might be less than that if some filters ('conditions' argument) are applied.
    next_page_token : str or None
        If None, start the query from the beginning.
        If provided, resume the query from the last page.
        Must be a token returned by a call of this function on the same table,
        with the same parameters.

    Returns
    -------
    tuple :
        the (results, next_page_token) tuple, where results is a list of dict items,
        and 'next_page_token' must be passed as 'page_start_token' argument in the next call to resume the query (if it is not None).

    Example
    -------
    >>> from boto3.dynamodb.conditions import Attr
    >>> put_item(table, {"uuid": "ID0", "field": 10.0})
    >>> next_page_token = None
    >>> while True:
    >>>     items, next_page_token = query_items(table, hash_key="ID0", conditions=Attr("field").eq(10.0), page_start_token=next_page_token):
    >>>     print(item)
    {"uuid": "ID0", "field": 10.0}
    """
    # build key conditions if any
    table_keys = get_table_keys(table)
    sort_key_start, sort_key_end = sort_key_interval
    key_conditions = Key(table_keys["HASH"]).eq(hash_key) if hash_key is not None else None
    if any(k is not None for k in sort_key_interval): # Only a single condition by key is supported by boto3
        sort_key = Key(table_keys["RANGE"])
        if (sort_key_start is not None) and (sort_key_end is not None):
            sort_condition = sort_key.between(sort_key_start, sort_key_end)
        elif sort_key_start is not None:
            sort_condition = sort_key.gte(sort_key_start)
        elif sort_key_end is not None:
            sort_condition = sort_key.lte(sort_key_end)
        key_conditions = (key_conditions & sort_condition) if key_conditions is not None else sort_condition
    # get a single page of results
    kwargs = {
        **(dict(FilterExpression=conditions) if conditions is not None else dict()),
        **(dict(ExclusiveStartKey=page_start_token) if page_start_token is not None else dict()),
        **(dict(ProjectionExpression=",".join(subset)) if subset is not None else dict()),
        **(dict(Limit=page_size) if page_size is not None else dict())
    }
    if key_conditions is not None:
        response = table.query(
            KeyConditionExpression=key_conditions,
            ScanIndexForward=ascending,
            **kwargs
        )
    else:
        response = table.scan(**kwargs)
    return ([_recursive_convert(item, to_decimal=False) for item in response.get("Items", [])], response.get("LastEvaluatedKey"))


def get_item_field(table: object, key: dict, field: str) -> dict | None:
    """
    Get the given field from an item.
    Raise an error if the item does not exists, but returns None if the field does not exist.

    Example
    -------
    >>> get_item_field(table, {"id": "ID0"}, "field.list_field[0].sub_field")
    {"number": 10.0, "string": "abc"}
    """
    response = table.get_item(
        Key=key,
        ProjectionExpression=field
    )
    if "Item" not in response:
        raise KeyError(f"Item '{key}' is missing from table '{table.name}'")
    item = response.get("Item")
    if item == {}:
        raise KeyError(f"Field '{field}' is missing from item '{key}' in table '{table.name}'")
    return _recursive_convert(_extract_item_field_value(item, field), to_decimal=False)


def put_item_field(table: object, key: dict, field: str, new_value: float, overwrite: bool=False, return_object: bool=False) -> dict | None:
    """
    set the field of an item at given key.

    Example
    -------
    >>> put_item_field(table, {"id": "ID0"}, "value", "abcd")
    >>> put_item_field(table, {"id": "ID0"}, "value", -2.5, overwrite=True, return_object=True)
    "abcd"
    """
    table_keys = get_table_keys(table)
    condition = _key_exists_condition(table_keys)
    if not overwrite:
        condition += f" AND attribute_not_exists({field})"
    try:
        response = table.update_item(
            Key=key,
            UpdateExpression=f"SET {field} = :new_value",
            ExpressionAttributeValues={':new_value': _recursive_convert(new_value, to_decimal=True)},
            ReturnValues="UPDATED_OLD" if return_object else "NONE",  # Return the updated values after setting
            ConditionExpression=condition # only update if the item did exist
            )
    except dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
        raise KeyError(f"Item '{key}' is missing for table '{table.name}'"+("" if overwrite else f"  or it's field '{field}' already exists"))
    return _recursive_convert(_extract_item_field_value(response.get("Attributes"), field), to_decimal=False)


def remove_item_field(table: object, key: dict, field: str, return_object: bool=False) -> dict | None:
    """
    Remove a field from an existing item.
    Raise an error if the item or field does not exist.

    Example
    -------
    >>> remove_item_field(table, {"id": "ID0"}, "value")
    >>> remove_item_field(table, {"id": "ID0"}, "field.list_field[0].nested", return_object=True)
    {"other-nested": -5}
    """
    try:
        response = table.update_item(
            Key=key,
            UpdateExpression=f"REMOVE {field}",
            ConditionExpression=f"attribute_exists({field})",  # only update if the item did exist
            ReturnValues="UPDATED_OLD" if return_object else "NONE"  # Returns the removed values
            )
    except dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
        raise KeyError(f"Item '{key}' or it's field '{field}' is missing from table '{table.name}'")
    return _recursive_convert(_extract_item_field_value(response.get("Attributes"), field), to_decimal=False)


def increment_item_field(
        table: object,
        key: dict,
        field: str,
        delta: int | float,
        default: int | float | None = None,
        return_object: bool=False
    ) -> int | float | None:
    """
    Increment the field of an item at given key.
    If default is provided, missing item or field are created with 'default' as initial value for the field, before increment.
    Otherwise raise a KeyError if the item or field does not exist.

    Example
    -------
    >>> increment_item_field(table, {"id": "ID0"}, "value", -2.5)
    >>> increment_item_field(table, {"id": "ID0"}, "value", 8, return_object=True)
    3.0
    """
    kwargs = dict(ConditionExpression=f"attribute_exists({field})") if default is None else dict()
    try:
        response = table.update_item(
            Key=key,
            UpdateExpression=f"SET {field} = if_not_exists({field}, :default) + :increment_amount",
            ExpressionAttributeValues={":increment_amount": _recursive_convert(delta, to_decimal=True), ":default": _recursive_convert(default, to_decimal=True)},
            ReturnValues="UPDATED_NEW" if return_object else "NONE",  # Return the updated values after the increment
            **kwargs
        )
    except dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
        raise KeyError(f"Item '{key}' or it's field '{field}' is missing from table '{table.name}'")
    return _recursive_convert(_extract_item_field_value(response.get("Attributes"), field), to_decimal=False)


def extend_array_item_field(
        table: object,
        key: dict,
        field: str,
        values: list,
        default: list|None = None,
        return_object: bool=False
    ) -> list | None:
    """
    increment the field of an item at given key.
    Raise an error if the item or field does not exist,
    unless default is provided in which case it is initialized to default before.

    Example
    -------
    >>> increment_item_field(table, {"id": "ID0"}, "array_field", -2.5)
    """
    kwargs = dict(ConditionExpression=f"attribute_exists({field})") if default is None else dict()
    try:
        response = table.update_item(
            Key=key,
            UpdateExpression=f"SET {field} = list_append(if_not_exists({field}, :default), :new_items)",
            ExpressionAttributeValues={':new_items': _recursive_convert(values, to_decimal=True), ":default": _recursive_convert(default, to_decimal=True)},
            ReturnValues="UPDATED_NEW" if return_object else "NONE",  # Return the updated value after the insertion
            **kwargs
            )
    except dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
        raise KeyError(f"Item '{key}' or it's field '{field}' is missing from table '{table.name}'")
    return _recursive_convert(_extract_item_field_value(response.get("Attributes"), field), to_decimal=False)


def extend_set_item_field(
        table: object,
        key: dict,
        field: str,
        value: set,
        create_if_missing: bool = False,
        return_object: bool=False
    ) -> set | None:
    """
    Insert the given values in a set field at given key.
    Raise an error if the item or field does not exist.
    If 'return_object' is True, returns the subset of add objects that were not already present.

    Example
    -------
    >>> insert_in_set_item_field(table, {"id": "ID0"}, "alphabet", "d")
    """
    kwargs = dict(ConditionExpression=f"attribute_exists({field})") if not create_if_missing else dict()
    try:
        response = table.update_item(
            Key=key,
            UpdateExpression=f"ADD {field} :set_to_add",
            ExpressionAttributeValues={':set_to_add': _recursive_convert(value, to_decimal=True)},
            ReturnValues="UPDATED_OLD" if return_object else "NONE",  # Return the updated value after the insertion
            **kwargs
            )
    except dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
        raise KeyError(f"Item '{key}' or it's field '{field}' is missing from table '{table.name}'")
    return {v for v in value if v not in _recursive_convert(_extract_item_field_value(response.get("Attributes"), field), to_decimal=False)}


def remove_from_set_item_field(
        table: object,
        key: dict,
        field: str,
        value: set,
        return_object: bool=False
    ) -> set | None:
    """
    Removes the given values from a set field at given key.
    Raise an error if the item or field does not exists.
    If 'return_object' is True, returns the subset of removed objects that were present.

    Example
    -------
    >>> delete_from_set_item_field(table, {"id": "ID0"}, "alphabet", "d")
    """
    try:
        response = table.update_item(
            Key=key,
            UpdateExpression=f"DELETE {field} :set_to_delete",
            ExpressionAttributeValues={':set_to_delete': _recursive_convert(value, to_decimal=True)},
            ConditionExpression=f"attribute_exists({field})",  # only update if the field did exist
            ReturnValues="UPDATED_OLD" if return_object else "NONE"
            )
    except dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
        raise KeyError(f"Item '{key}' or it's field '{field}' is missing from table '{table.name}'")
    return {v for v in value if v in _recursive_convert(_extract_item_field_value(response.get("Attributes"), field), to_decimal=False)}


if __name__ == "__main__":
    import IPython
    IPython.embed()
