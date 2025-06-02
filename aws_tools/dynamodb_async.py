import typing
import boto3
import aioboto3
from operator import __and__
from typing import Type, Literal, Iterable, AsyncIterable
from decimal import Decimal
from boto3.dynamodb.conditions import ConditionBase, Key, Attr
from botocore.exceptions import ClientError
from aws_tools._async_tools import _run_async

session = aioboto3.Session()

KeyType = dict[Literal["HASH", "RANGE"], object]


class DynamoDBException(Exception):
    pass


def _recursive_convert(item: object, to_decimal: bool, n_decimals: int=6) -> object:
    """
    replace floats with Decimal objects recursively in a dict
    """
    if isinstance(item, list):
        return [_recursive_convert(i, to_decimal) for i in item]
    elif isinstance(item, set):
        return {_recursive_convert(i, to_decimal) for i in item}
    elif isinstance(item, dict):
        return {k: _recursive_convert(v, to_decimal) for k, v in item.items() if v != set()}  # remove keys corresponding to empty sets
    elif isinstance(item, (int, float)) and to_decimal:
        number = str(round(item, 6))
        if "." in number:
            int_part, decimal_part = number.split(".")
            number = f"{int_part}.{decimal_part[:n_decimals]}"
        return Decimal(number)
    elif isinstance(item, Decimal) and not to_decimal:
        return float(item) if item % 1 != 0 else int(item)
    elif item is None or type(item) in [str, bool]:
        return item
    else:
        raise ValueError(f"Unexpected type '{type(item).__name__}' encountered.")


def _extract_item_field_value(item: dict | None, field_path: str | tuple[str | int]) -> object:
    """
    returns the value at given path

    Example
    -------
    >>> _extract_item_field_value({"array": ["A", "B", {"sub_field": 1}]}, ["array", 2, "sub_field"])
    1
    """
    if isinstance(field_path, str):
        field_path = (field_path,)
    for key in field_path:
        item = item[key]
    return item


def _field_exists(item: dict | None, field_path: str | tuple[str | int]) -> bool:
    """
    returns whether a field path exists within an item

    Example
    -------
    >>> _field_exists({"array": ["A", "B", {"sub_field": 1}]}, ["array", 2, "sub_field"])
    True
    >>> _fields_exists({"array": ["A", "B", {"sub_field": 1}]}, ["array", 2, "other_sub_field"])
    False
    >>> _field_exists({"array": ["A", "B", {"sub_field": 1}]}, "array")
    True
    >>> _field_exists({"array": ["A", "B", {"sub_field": 1}]}, "other_field")
    False
    """
    if isinstance(field_path, str):
        field_path = (field_path,)
    for key in field_path:
        if isinstance(key, str) and key not in item:
            return False
        elif isinstance(key, int) and (not isinstance(item, list) or key >= len(item)):
            return False
        item = item[key]
    return True


def _field_path_to_expression(*args: tuple[str | tuple[str | int], ...]) -> tuple[str, dict]:
    """
    converts a set of field path to a tuple of (expressions, path_representation, attribute_names)

    Example
    -------
    >>> _field_path_to_expression(("array_field", 0, "sub_field"), ("array_field", 1, "other_subfield"))
    (('#f2[0].#f0', '#f2[1].#f1'),
     {'#f0': 'sub_field', '#f1': 'other_subfield', '#f2': 'array_field'})
    """
    args = tuple((f,) if isinstance(f, str) else f for f in args)
    unique_attributes = {f for arg in args for f in arg if isinstance(f, str)}
    attributes_mapping = {k: f"#f{i}" for i, k in enumerate(unique_attributes)}
    expressions = tuple("".join("."+attributes_mapping[f] if isinstance(f, str) else f"[{f}]" for f in arg).strip(".") for arg in args)
    attribute_names = {v: k for k, v in attributes_mapping.items()}
    return expressions, attribute_names


def _key_exists_condition(table_keys: KeyType, attribute_names: dict[str, str]):
    """
    Return the condition that the key exist
    """
    attributes_mapping = {v: k for k, v in attribute_names.items()}
    condition = f"attribute_exists({attributes_mapping[table_keys['HASH']]})"
    if "RANGE" in table_keys.keys():
        condition += f" AND attribute_exists({attributes_mapping[table_keys['RANGE']]})"
    return condition


def _key_not_exists_condition(table_keys: KeyType, attribute_names: dict[str, str]):
    """
    Return the condition that the key exist
    """
    attributes_mapping = {v: k for k, v in attribute_names.items()}
    condition = f"attribute_not_exists({attributes_mapping[table_keys['HASH']]})"
    if "RANGE" in table_keys.keys():
        condition += f" AND attribute_not_exists({attributes_mapping[table_keys['RANGE']]})"
    return condition


async def _get_table_async(dynamodb: object, table_name: str) -> object:
    """
    Returns the table object.
    Raise an error if it does not exist.
    """
    table = await dynamodb.Table(table_name)
    try:
        await table.load()
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceNotFoundException":
            raise DynamoDBException(f"The table '{table.name}' does not exist")
        else:
            raise
    return table


async def _get_table_keys_async(table: object) -> KeyType:
    """
    Get the {type: name} of the table keys
    """
    return {ks["KeyType"]: ks["AttributeName"] for ks in await table.key_schema}


async def list_tables_async() -> list[str]:
    """
    list existing tables
    """
    async with session.resource("dynamodb") as dynamodb:
        return [table.name async for table in dynamodb.tables.all()]


async def table_exists_async(table_name: str) -> bool:
    """
    Returns True if the table exists and False otherwise

    Example
    -------
    >>> table_exist("test-table")
    False
    """
    async with session.resource("dynamodb") as dynamodb:
        try:
            await _get_table_async(dynamodb, table_name)
        except DynamoDBException:
            return False
        else:
            return True


async def get_table_keys_async(table_name: str) -> KeyType:
    """
    Get the {type: name} of the table keys
    """
    async with session.resource("dynamodb") as dynamodb:
        table = await _get_table_async(dynamodb, table_name)
        return await _get_table_keys_async(table)


async def create_table_async(
        table_name: str,
        partition_names: dict[Literal["HASH", "RANGE"], str],
        data_types: dict[str, Literal["S", "N", "B"]],
        blocking: bool=True
    ):
    """
    Creates a table, raise an error if it already exists.

    Example
    -------
    >>> table = create_table("test-table")
    """
    async with session.resource("dynamodb") as dynamodb:
        try:
            table = await dynamodb.create_table(
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
                await table.meta.client.get_waiter('table_exists').wait(TableName=table_name)
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceInUseException":
                raise DynamoDBException(f"The table '{table_name}' already exists")
            else:
                raise


async def delete_table_async(table_name: str, blocking: bool=True):
    """
    Delete a table, raise an error if it does not exists

    Example
    -------
    >>> table = delete_table("test_table")
    """
    async with session.resource("dynamodb") as dynamodb:
        table = await _get_table_async(dynamodb, table_name)
        try:
            await table.delete()
            # Wait until the table is correctly deleted before continuing
            if blocking:
                await table.meta.client.get_waiter('table_not_exists').wait(TableName=table.name)
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceNotFoundException":
                raise DynamoDBException(f"The table '{table.name}' does not exist")
            else:
                raise


async def item_exists_async(table_name: str, key_or_item: dict) -> bool:
    """
    Returns True if the item exists and False otherwise.
    Faster and cheaper than a 'get_item' as this only query the partition key.
    """
    async with session.resource("dynamodb") as dynamodb:
        table = await _get_table_async(dynamodb, table_name)
        table_keys = await _get_table_keys_async(table)
        key = {v: key_or_item[v] for v in table_keys.values()}
        response = await table.get_item(Key=key, ProjectionExpression=",".join(key.keys()))
        return "Item" in response


async def get_item_async(table_name: str, key_or_item: dict) -> dict | None:
    """
    Get a full item from it's keys, returns None if the key does not exist.
    If the table has an hash key and a range key, both must be provided in the 'keys' dict.

    Example
    -------
    >>> get_item(table, {"id": "ID0"})
    {"uuid": "ID0", "field": 10.0}
    """
    async with session.resource("dynamodb") as dynamodb:
        table = await _get_table_async(dynamodb, table_name)
        table_keys = await _get_table_keys_async(table)
        key = {v: key_or_item[v] for v in table_keys.values()}
        response = await table.get_item(Key=key)
        return _recursive_convert(response.get("Item"), to_decimal=False)


async def put_item_async(table_name: str, item: dict, overwrite: bool=False, return_object: bool=False) -> dict | None:
    """
    Write an item, raise an error if it already exists and overwrite=False.
    Returns the old value if return_object=True.

    Example
    -------
    >>> put_item(table, {"uuid": "ID0", "field": 10.0})
    >>> put_item(table, {"uuid": "ID0", "field": 9.0}, overwrite=True, return_object=True)
    {"uuid": "ID0", "field": 10.0}
    """
    async with session.resource("dynamodb") as dynamodb:
        table = await _get_table_async(dynamodb, table_name)
        table_keys = await _get_table_keys_async(table)
        _, attribute_names = _field_path_to_expression(*(v for v in table_keys.values()))
        assert all(k in item.keys() for k in table_keys.values())
        try:
            response = await table.put_item(
                Item=_recursive_convert(item, to_decimal=True),
                ReturnValues="ALL_OLD" if return_object else "NONE",  # returns the overwritten item if any
                **(dict() if overwrite else dict(ConditionExpression=_key_not_exists_condition(table_keys, attribute_names), ExpressionAttributeNames=attribute_names))
            )
        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                key = {k: item[k] for k in table_keys.values()}
                raise DynamoDBException(f"Item '{key}' already exists for table '{table.name}'")
            else:
                raise
        return _recursive_convert(response.get("Attributes"), to_decimal=False)


async def batch_put_items_async(table_name: str, items: Iterable[dict]):
    """
    Create items in batch, overwriting if they already exist.
    """
    async with session.resource("dynamodb") as dynamodb:
        table = await _get_table_async(dynamodb, table_name)
        async with table.batch_writer() as batch:
            for item in items:
                await batch.put_item(Item=_recursive_convert(item, to_decimal=True))


async def delete_item_async(table_name: str, key_or_item: dict, return_object: bool = False) -> dict | None:
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
    async with session.resource("dynamodb") as dynamodb:
        table = await _get_table_async(dynamodb, table_name)
        table_keys = await _get_table_keys_async(table)
        _, attribute_names = _field_path_to_expression(*(v for v in table_keys.values()))
        try:
            response = await table.delete_item(
                Key={k: key_or_item[k] for k in table_keys.values()},
                ReturnValues="ALL_OLD" if return_object else "NONE",  # returns the removed item
                ConditionExpression=_key_exists_condition(table_keys, attribute_names),
                ExpressionAttributeNames=attribute_names,
            )
        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                return None
            else:
                raise
        return _recursive_convert(response.get("Attributes"), to_decimal=False)


async def batch_delete_items_async(table_name: str, keys_or_items: Iterable[dict]):
    """
    Delete the items by batch, there is no verification that they did not exist.
    """
    async with session.resource("dynamodb") as dynamodb:
        table = await _get_table_async(dynamodb, table_name)
        table_keys = await _get_table_keys_async(table)
        async with table.batch_writer() as batch:
            for key in keys_or_items:
                await batch.delete_item(Key={v: key[v] for v in table_keys.values()})


async def scan_items_async(
        table_name: str,
        conditions: ConditionBase | None = None,
        subset: list[str] | None = None,
        page_size: int | None = 1_000,
        page_start_token: str | None = None
    ) -> tuple[list[dict], str | None]:
    """
    Scan all items in the table.
    Return items in a paginated way.

    Params
    ------
    table : object
        The dynamodb Table object
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
    >>>     items, next_page_token = scan_items(table, conditions=Attr("field").eq(10.0), page_start_token=next_page_token):
    >>>     print(item)
    {"uuid": "ID0", "field": 10.0}
    """
    async with session.resource("dynamodb") as dynamodb:
        table = await _get_table_async(dynamodb, table_name)
        kwargs = {
            **(dict(FilterExpression=conditions) if conditions is not None else dict()),
            **(dict(ExclusiveStartKey=page_start_token) if page_start_token is not None else dict()),
            **(dict(ProjectionExpression=",".join(subset)) if subset is not None else dict()),
            **(dict(Limit=page_size) if page_size is not None else dict())
        }
        response = await table.scan(**kwargs)
        return ([_recursive_convert(item, to_decimal=False) for item in response.get("Items", [])], response.get("LastEvaluatedKey"))


async def scan_all_items_async(
            table_name: str,
            conditions: ConditionBase | None = None,
            subset: list[str] | None = None,
            page_size: int | None = 1_000,
        ):
    """
    Return all the items returned by a scan operation, handling pagination
    """
    kwargs = dict(
        table_name=table_name,
        conditions=conditions,
        subset=subset,
        page_size=page_size
    )
    next_page_token = None
    while True:
        items, next_page_token = await scan_items_async(page_start_token=next_page_token, **kwargs)
        for item in items:
            yield item
        if next_page_token is None:
            break


async def query_items_async(
        table_name: str,
        hash_key: object,
        sort_key_filter: str | tuple[object|None, object|None] = (None, None),
        ascending: bool=True,
        conditions: ConditionBase | None = None,
        subset: list[str] | None = None,
        page_size: int | None = 1_000,
        page_start_token: str | None = None
    ) -> tuple[list[dict], str | None]:
    """
    Query items that match the hash key and/or the sort key.
    Return items in a paginated way.

    Params
    ------
    table : object
        The dynamodb Table object
    hash_key : object
        the value of the hash_key for returned items
    sort_key_filter : str, or tuple of two objects, or None
        Ignored if the table does not have a sort key.
        If a single str is provided, query items for which sort key begin with the provided string.
        If a (from, to) tuple is provided, it is the interval (including boundary on both sides) used to filter the sort key, a None means an unbounded side for the interval
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
    async with session.resource("dynamodb") as dynamodb:
        table = await _get_table_async(dynamodb, table_name)
        # build key conditions if any
        table_keys = await _get_table_keys_async(table)
        key_conditions = Key(table_keys["HASH"]).eq(hash_key)
        if "RANGE" in table_keys.keys():
            sort_key = Key(table_keys["RANGE"])
            if isinstance(sort_key_filter, str):
                key_conditions = key_conditions & sort_key.begins_with(sort_key_filter)
            else:
                sort_key_start, sort_key_end = sort_key_filter
                if any(k is not None for k in sort_key_filter): # Only a single condition by key is supported by boto3
                    if (sort_key_start is not None) and (sort_key_end is not None):
                        key_conditions = key_conditions & sort_key.between(sort_key_start, sort_key_end)
                    elif sort_key_start is not None:
                        key_conditions = key_conditions & sort_key.gte(sort_key_start)
                    elif sort_key_end is not None:
                        key_conditions = key_conditions & sort_key.lte(sort_key_end)
        # get a single page of results
        kwargs = {
            **(dict(FilterExpression=conditions) if conditions is not None else dict()),
            **(dict(ExclusiveStartKey=page_start_token) if page_start_token is not None else dict()),
            **(dict(ProjectionExpression=",".join(subset)) if subset is not None else dict()),
            **(dict(Limit=page_size) if page_size is not None else dict())
        }
        response = await table.query(
            KeyConditionExpression=key_conditions,
            ScanIndexForward=ascending,
            **kwargs
        )
        return ([_recursive_convert(item, to_decimal=False) for item in response.get("Items", [])], response.get("LastEvaluatedKey"))


async def query_all_items_async(
        table_name: str,
        hash_key: object,
        sort_key_filter: str | tuple[object|None, object|None] = (None, None),
        ascending: bool=True,
        conditions: ConditionBase | None = None,
        subset: list[str] | None = None,
        page_size: int | None = 1_000
    ) -> AsyncIterable[dict]:
    """
    Iterate over all the results of a query, handling pagination
    """
    kwargs = dict(
        table_name=table_name,
        hash_key=hash_key,
        sort_key_filter=sort_key_filter,
        ascending=ascending,
        conditions=conditions,
        subset=subset,
        page_size=page_size
    )
    next_page_token = None
    while True:
        items, next_page_token = await query_items_async(page_start_token=next_page_token, **kwargs)
        for item in items:
            yield item
        if next_page_token is None:
            break


async def update_item_async(
        table_name: str,
        key_or_item: dict,
        *,
        put_fields: dict[str | tuple[str | int], object] = {},
        increment_fields: dict[str | tuple[str | int], object] = {},
        extend_sets: dict[str | tuple[str | int], object | set] = {},
        remove_from_sets: dict[str | tuple[str | int], object | set] = {},
        extend_arrays: dict[str | tuple[str | int], list] = {},
        delete_fields: Iterable[str | tuple[str | int]] = [],
        create_item_if_missing: bool=False,
        return_object: bool=False
    ) -> dict | None:
    """
    Update an item fields.
    Only one operation can be done on a single field at a time.
    
    Params
    ------
    table : object
        The dynamodb Table object
    key_or_item : dict
        The item or the key of the item to update.
    put_fields : dict
        the field names or paths, and their associated values to set
    increment_fields : dict
        the field names or paths, and their associated values to increment (if the field is missing, set it to the increment value instead)
    extend_sets : dict
        the field names or paths, and the associated values to add to a set (if the field is missing, create it with the value)
    remove_from_sets : dict
        the field names or paths, and the associated values to remove from a set
    extend_arrays : dict
        the field names or paths, and the associated list of values to append to an array (if the field is missing, create it with the value)
    delete_fields : dict
        the field names or paths to delete from the item
    create_item_if_missing : bool
        If True, create the item if it does not exist.
        Several nested paths can't be created at once.
        If False, raise an error if the item does not exist.
    return_object : bool
        If True, the function return the subset of the item containing the updated fields.

    Returns
    -------
    dict | None
        The updated item if return_object is True, otherwise None.
    """
    async with session.resource("dynamodb") as dynamodb:
        table = await _get_table_async(dynamodb, table_name)
        delete_fields = set(delete_fields)
        if sum(len(v) for v in (put_fields, increment_fields, extend_sets, remove_from_sets, extend_arrays, delete_fields)) == 0:
            raise DynamoDBException("At least one update must be made to the item")
        table_keys = await _get_table_keys_async(table)
        key = {k: key_or_item[k] for k in table_keys.values()}
        expressions, attribute_names = _field_path_to_expression(
            *put_fields.keys(), *extend_arrays.keys(), *increment_fields.keys(),
            *extend_sets.keys(), *remove_from_sets.keys(), *delete_fields,
            *((v for v in table_keys.values()) if not create_item_if_missing else [])
        )
        attribute_values = {}
        expression_iterable = iter(expressions)
        set_expressions = []
        for i, (value, expr) in enumerate(zip(put_fields.values(), expression_iterable)):
            attribute_values[f":set_value{i}"] = _recursive_convert(value, to_decimal=True)
            set_expressions.append(f"{expr} = :set_value{i}")
        for i, (value, expr) in enumerate(zip(extend_arrays.values(), expression_iterable)):
            attribute_values[f":extend_value{i}"] = _recursive_convert(list(value), to_decimal=True)
            attribute_values[f":empty_list"] = []
            set_expressions.append(f"{expr} = list_append(if_not_exists({expr}, :empty_list), :extend_value{i})")
        add_expressions = []
        for i, (value, expr) in enumerate(zip(increment_fields.values(), expression_iterable)):
            attribute_values[f":add_value{i}"] = _recursive_convert(value, to_decimal=True)
            add_expressions.append(f"{expr} :add_value{i}")
        for i, (value, expr) in enumerate(zip(extend_sets.values(), expression_iterable)):
            attribute_values[f":insert_value{i}"] = _recursive_convert(value, to_decimal=True)
            add_expressions.append(f"{expr} :insert_value{i}")
        delete_expressions = []
        for i, (value, expr) in enumerate(zip(remove_from_sets.values(), expression_iterable)):
            value = value if isinstance(value, set) else {value}
            attribute_values[f":pop_value{i}"] = _recursive_convert(value, to_decimal=True)
            delete_expressions.append(f"{expr} :pop_value{i}")
        remove_expressions = []
        for i, (value, expr) in enumerate(zip(delete_fields, expression_iterable)):
            remove_expressions.append(f"{expr}")
        expression = " ".join(f"{kw} {', '.join(expr)}" for kw, expr in (("SET", set_expressions), ("ADD", add_expressions), ("DELETE", delete_expressions), ("REMOVE", remove_expressions)) if len(expr) > 0)
        kwargs = (dict() if create_item_if_missing else dict(ConditionExpression=_key_exists_condition(table_keys, attribute_names)))
        try:
            response = await table.update_item(
                Key=key,
                UpdateExpression=expression,
                ExpressionAttributeValues=attribute_values,
                ExpressionAttributeNames=attribute_names,
                ReturnValues="UPDATED_NEW" if return_object else "NONE",  # Return the updated values after setting
                **kwargs
                )
        except ClientError as e:
            if e.response["Error"]["Code"] == "ValidationException":
                raise DynamoDBException(str(e))
            elif e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                raise DynamoDBException(f"The item '{key}' from table '{table.name}' does not exist ({str(e)})")
            else:
                raise
        if not return_object:
            return
        else:
            return _recursive_convert(response.get("Attributes"), to_decimal=False)


async def get_item_fields_async(
        table_name: str,
        key_or_item: dict,
        fields: set[str | tuple[str | int]]
    ) -> dict | None:
    """
    Returns the given fields (or field paths) from the item at given key.
    If the items does not exist, returns None.

    Params
    ------
    table : object
        The dynamodb Table object
    key_or_item : dict
        The item or the key of the item to update.
    fields : set
        the field names or paths to return
        To specify a field path, use a tuple of strings or integers.
    
    Returns
    -------
    dict | None
        The mapping between fields and their values, for the existing fields.
        If the item does not exists, return None.
    """
    async with session.resource("dynamodb") as dynamodb:
        table = await _get_table_async(dynamodb, table_name)
        table_keys = await _get_table_keys_async(table)
        key = {k: key_or_item[k] for k in table_keys.values()}
        expressions, attribute_names = _field_path_to_expression(*fields)
        response = await table.get_item(
            Key=key,
            ProjectionExpression=", ".join(expressions),
            ExpressionAttributeNames=attribute_names
        )
    if "Item" not in response:
        return None
    item = response.get("Item")
    if item is None:
        return None
    fields = {f: _extract_item_field_value(item, f) for f in fields if _field_exists(item, f)}
    return _recursive_convert(fields, to_decimal=False)


if __name__ == "__main__":
    from aws_tools._async_tools import _generate_sync_module
    _generate_sync_module(__name__)
