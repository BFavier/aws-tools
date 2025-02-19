import boto3
from operator import __and__
from typing import Type, Literal, Iterable
from decimal import Decimal
from boto3.dynamodb.conditions import ConditionBase, Key, Attr
from botocore.exceptions import ClientError

dynamodb = boto3.resource("dynamodb")

KeyType = dict[Literal["HASH", "RANGE"], object]


def _recursive_convert(item: object, to: Type[Decimal] | Type[float]) -> object:
    """
    replace floats with Decimal objects recursively in a dict
    """
    if isinstance(item, list):
        return [_recursive_convert(i, to) for i in item]
    elif isinstance(item, set):
        return {_recursive_convert(i, to) for i in item}
    elif isinstance(item, dict):
        return {k: _recursive_convert(v, to) for k, v in item.items()}
    elif isinstance(item, float) and to == Decimal:
        return Decimal(item)
    elif isinstance(item, Decimal) and to == float:
        return float(item)
    elif item is None or type(item) in [str, int, bool]:
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


def get_table_keys(table: object) -> dict:
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


def item_exists(table: object, key: KeyType) -> bool:
    """
    Returns True if the item exists and False otherwise.
    Faster and cheaper than a 'get_item' as this only query the partition key.
    """
    response = table.get_item(Key=key, ProjectionExpression=",".join(key.keys()))
    return "Item" in response


def get_item(table: object, key: KeyType) -> dict | None:
    """
    Get a full item from it's key, returns None if the key does not exist.

    Example
    -------
    >>> get_item(table, {"id": "ID0"})
    {"uuid": "ID0", "field": 10.0}
    """
    response = table.get_item(Key=key)
    return _recursive_convert(response.get("Item"), float)


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
                Item=_recursive_convert(item, Decimal),
                ReturnValues="ALL_OLD" if return_object else "NONE",  # returns the overwritten item if any
                **(dict() if overwrite else dict(ConditionExpression=_key_not_exists_condition(table_keys)))
                )
    except ClientError as e:
        if e.response['Error']['Code'] == "ConditionalCheckFailedException":
            key = {k: item[k] for k in table_keys.values()}
            raise KeyError(f"Item '{key}' already exists for table '{table.name}'")
        else:
            raise e
    return _recursive_convert(response.get("Attributes"), float)


def batch_put_items(table: object, items: Iterable[dict]) -> int:
    """
    Create items in batch, overwriting if they already exist.
    Returns the number of writen items.
    """
    i = 0
    with table.batch_writer() as batch:
        for i, item in enumerate(items, start=1):
            batch.put_item(Item=_recursive_convert(item, Decimal))
    return i


def delete_item(table: object, key: dict, return_object: bool = False) -> dict | None:
    """
    Delete an item at given key, and optionally return the erased item.
    Raise an error if the item does not exists.

    Example
    -------
    >>> delete_item(table, {"id": "ID0"})
    >>> delete_item(table, {"id": "ID0"}, return_object=True)
    {"uuid": "ID1", "field": 10.0}
    """
    table_keys = get_table_keys(table)
    try:
        response = table.delete_item(
            Key={k: key[k] for k in table_keys.values()},
            ReturnValues="ALL_OLD" if return_object else "NONE",  # returns the removed item
            ConditionExpression=_key_exists_condition(table_keys)
            )
    except ClientError as e:
        if e.response['Error']['Code'] == "ConditionalCheckFailedException":
            raise KeyError(f"Item '{key}' is missing from table '{table.name}'")
        else:
            raise e
    return _recursive_convert(response.get("Attributes"), float)


def batch_delete_items(table: object, keys_or_items: list[KeyType | dict]) -> int:
    """
    Delete the items by batch, there is no verification that they did not exist.
    Returns the number of deleted items.
    """
    i = 0
    table_keys = get_table_keys(table)
    with table.batch_writer() as batch:
        for i, key in enumerate(keys_or_items, start=1):
            batch.delete_item(Key={v: key[v] for v in table_keys.values()})
    return i


def query_items(table: object,
                hash_key: object | None = None,
                sort_key: tuple[object, object] | object | None = None,
                ascending: bool=True,
                conditions: ConditionBase | None = None,
                subset: list[str] | None = None,
                limit: int | None = None) -> Iterable[dict]:
    """
    Query items that match the hash key and/or the sort key

    Params
    ------
    table : object
        The dynamodb Table object
    hash_key : object or None
        the value of the hash_key for returned items, or None
    sort_key : (object, object) or object or None
        the interval of valid values for the sort key, or the value, or None
    ascending : bool
        If one of 'hash_key' or 'sort_key' is provided, this argument defines the
        sort_key order in which results are returned (ascending or descending).
        Otherwise it has no effect.
    conditions : ConditionBase
        the conditions on which returned items are filtered
    subset : list of str
        the list of field subset to return to avoid returning the full object
    limit : int or None
        maximum number of items returned
    
    Returns
    -------
    Iterable of dict :
        the matching items are yielded

    Example
    -------
    >>> from boto3.dynamodb.conditions import Attr
    >>> put_item(table, {"uuid": "ID0", "field": 10.0})
    >>> for item in query_items(table, hash_key="ID0", conditions=Attr("field").eq(10.0)):
    >>>     print(item)
    {"uuid": "ID0", "field": 10.0}
    """
    # build key conditions if any
    table_keys = get_table_keys(table)
    hash_condition = Key(table_keys["HASH"]).eq(hash_key)
    if isinstance(sort_key, tuple) or isinstance(sort_key, list):
        sort_key_start, sort_key_end = sort_key
        sort_condition = Key(table_keys["RANGE"]).between(sort_key_start, sort_key_end)
    elif sort_key is not None:
        sort_condition = Key(table_keys["RANGE"]).eq(sort_key)
    # combine hash and sort key conditions
    if sort_key is None and hash_key is not None:
        key_conditions = hash_condition
    elif hash_key is None and sort_key is not None:
        key_conditions = sort_condition
    elif hash_key is None and sort_key is None:
        key_conditions = None
    else:
        key_conditions = hash_condition & sort_condition
    # loop on all pages of results
    response = None
    while True:
        if key_conditions is not None:
            response = table.query(
                KeyConditionExpression=key_conditions,
                ScanIndexForward=ascending,
                **(dict(FilterExpression=conditions) if conditions is not None else dict()),
                **(dict(ExclusiveStartKey=response['LastEvaluatedKey']) if response else dict()),
                **(dict(ProjectionExpression=",".join(subset)) if subset is not None else dict()),
                **(dict(Limit=limit) if limit is not None else dict())
            )
        else:
            response = table.scan(
                **(dict(FilterExpression=conditions) if conditions is not None else dict()),
                **(dict(ExclusiveStartKey=response['LastEvaluatedKey']) if response else dict()),
                **(dict(ProjectionExpression=",".join(subset)) if subset is not None else dict()),
                **(dict(Limit=limit) if limit is not None else dict())
            )
        yield from (_recursive_convert(item, float) for item in response.get("Items", []))
        if 'LastEvaluatedKey' not in response:
            break


def get_item_field(table: object, key: KeyType, field: str) -> dict | None:
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
    return _extract_item_field_value(_recursive_convert(item, float), field)


def put_item_field(table: object, key: KeyType, field: str, new_value: float, overwrite: bool=False, return_object: bool=False) -> dict | None:
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
            ExpressionAttributeValues={':new_value': _recursive_convert(new_value, Decimal)},
            ReturnValues="UPDATED_OLD" if return_object else "NONE",  # Return the updated values after setting
            ConditionExpression=condition # only update if the item did exist
            )
    except ClientError as e:
        if e.response['Error']['Code'] == "ConditionalCheckFailedException":
            raise KeyError(f"Item '{key}' is missing for table '{table.name}'"+("" if overwrite else f"  or it's field '{field}' already exists"))
        else:
            raise e
    return _extract_item_field_value(_recursive_convert(response.get("Attributes"), float), field)


def remove_item_field(table: object, key: KeyType, field: str, return_object: bool=False) -> dict | None:
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
    except ClientError as e:
        if e.response['Error']['Code'] == "ConditionalCheckFailedException":
            raise KeyError(f"Item '{key}' or it's field '{field}' is missing from table '{table.name}'")
        else:
            raise e
    return _extract_item_field_value(_recursive_convert(response.get("Attributes"), float), field)


def increment_item_field(table: object, key: KeyType, field: str, delta: float, return_object: bool=False) -> dict | None:
    """
    increment the field of an item at given key.
    Raise an error if the item or field does not exist.

    Example
    -------
    >>> increment_item_field(table, {"id": "ID0"}, "value", -2.5)
    >>> increment_item_field(table, {"id": "ID0"}, "value", 8, return_object=True)
    3
    """
    try:
        response = table.update_item(
            Key=key,
            UpdateExpression=f"SET {field} = {field} + :increment_amount",
            ExpressionAttributeValues={':increment_amount': _recursive_convert(delta, Decimal)},
            ConditionExpression=f"attribute_exists({field})",  # only update if the field did exist
            ReturnValues="UPDATED_NEW" if return_object else "NONE"  # Return the updated values after the increment
            )
    except ClientError as e:
        if e.response['Error']['Code'] == "ConditionalCheckFailedException":
            raise KeyError(f"Item '{key}' or it's field '{field}' is missing from table '{table.name}'")
        else:
            raise e
    return _extract_item_field_value(_recursive_convert(response.get("Attributes"), float), field)


def extend_array_item_field(table: object, key: KeyType, field: str, values: list[object], return_object: bool=False) -> dict | None:
    """
    increment the field of an item at given key.
    Raise an error if the item or field does not exist.

    Example
    -------
    >>> increment_item_field(table, {"id": "ID0"}, "array_field", -2.5)
    """
    try:
        response = table.update_item(
            Key=key,
            UpdateExpression=f"SET {field} = list_append({field}, :new_items)",
            ExpressionAttributeValues={':new_items': _recursive_convert(values, Decimal)},
            ConditionExpression=f"attribute_exists({field})",  # only update if the field did exist
            ReturnValues="UPDATED_NEW" if return_object else "NONE"  # Return the updated value after the insertion
            )
    except ClientError as e:
        if e.response['Error']['Code'] == "ConditionalCheckFailedException":
            raise KeyError(f"Item '{key}' or it's field '{field}' is missing from table '{table.name}'")
        else:
            raise e
    return _extract_item_field_value(_recursive_convert(response.get("Attributes"), float), field)


def insert_in_set_item_field(table: object, key: KeyType, field: str, value: object, return_object: bool=False) -> bool | None:
    """
    Insert a value in a set field at given key.
    Raise an error if the item or field does not exist.
    Returns wether the value already exist in the set if return_object is True.

    Example
    -------
    >>> insert_in_set_item_field(table, {"id": "ID0"}, "alphabet", "d")
    """
    try:
        response = table.update_item(
            Key=key,
            UpdateExpression=f"ADD {field} :item_to_add",
            ExpressionAttributeValues={':item_to_add': {_recursive_convert(value, Decimal)}},
            ConditionExpression=f"attribute_exists({field})",  # only update if the field did exist
            ReturnValues="UPDATED_OLD" if return_object else "NONE"  # Return the updated value after the insertion
            )
    except ClientError as e:
        if e.response['Error']['Code'] == "ConditionalCheckFailedException":
            raise KeyError(f"Item '{key}' or it's field '{field}' is missing from table '{table.name}'")
        else:
            raise e
    if return_object:
        return value in _extract_item_field_value(_recursive_convert(response.get("Attributes"), float), field)
    else:
        return


def remove_from_set_item_field(table: object, key: KeyType, field: str, value: object, return_object: bool=False) -> bool | None:
    """
    Removes the given value from a set field at given key.
    Raise an error if the item or field does not exists.
    Returns wether the value already exist in the set if return_object is True.

    Example
    -------
    >>> delete_from_set_item_field(table, {"id": "ID0"}, "alphabet", "d")
    """
    try:
        response = table.update_item(
            Key=key,
            UpdateExpression=f"DELETE {field} :item_to_delete",
            ExpressionAttributeValues={':item_to_delete': {_recursive_convert(value, Decimal)}},
            ConditionExpression=f"attribute_exists({field})",  # only update if the field did exist
            ReturnValues="UPDATED_OLD" if return_object else "NONE"  # Return the updated value after the insertion
            )
    except ClientError as e:
        if e.response['Error']['Code'] == "ConditionalCheckFailedException":
            raise KeyError(f"Item '{key}' or it's field '{field}' is missing from table '{table.name}'")
        else:
            raise e
    if return_object:
        return value in _extract_item_field_value(_recursive_convert(response.get("Attributes"), float), field)
    else:
        return


if __name__ == "__main__":
    import IPython
    IPython.embed()
