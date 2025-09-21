"""
This module was automatically generated from aws_tools.asynchrone.dynamodb
"""
from aws_tools._async_tools import _run_async, _async_iter_to_sync, _sync_iter_to_async
from typing import Iterable, Iterator
from aws_tools.asynchrone.dynamodb import __name__, __doc__, __package__, __loader__, __spec__, __file__, __cached__, __builtins__, typing, boto3, aioboto3, __and__, Type, Union, Literal, Iterable, AsyncIterable, AsyncGenerator, IterableABC, AsyncIterableABC, Decimal, TypeSerializer, TypeDeserializer, ConditionBase, Key, Attr, ClientError, _run_async, session, KeyType, DynamoDBException, _recursive_convert, _extract_item_field_value, _field_exists, _field_path_to_expression, _key_exists_condition, _key_not_exists_condition, _get_table_async, _get_table_keys_async, list_tables_async, table_exists_async, get_table_keys_async, create_table_async, delete_table_async, item_exists_async, get_item_async, put_item_async, batch_get_items_async, batch_put_items_async, delete_item_async, batch_delete_items_async, scan_items_async, scan_all_items_async, query_items_async, query_all_items_async, update_item_async, get_item_fields_async


def batch_get_items(table_name: str, keys_or_items: Iterable[dict], chunk_size: int=100, consistent_read: bool=False) -> Iterable[dict]:
    """
    Get several items at once.
    Yield None for items that do not exist.
    """
    return _async_iter_to_sync(batch_get_items_async(table_name=table_name, keys_or_items=keys_or_items, chunk_size=chunk_size, consistent_read=consistent_read))


def query_all_items(
        table_name: str,
        hash_key: object,
        sort_key_filter: str | tuple[object|None, object|None] = (None, None),
        ascending: bool=True,
        conditions: ConditionBase | None = None,
        subset: list[str] | None = None,
        page_size: int | None = 1_000,
        consistent_read: bool = False,
    ) -> Iterable[dict]:
    """
    Iterate over all the results of a query, handling pagination
    """
    return _async_iter_to_sync(query_all_items_async(table_name=table_name, hash_key=hash_key, sort_key_filter=sort_key_filter, ascending=ascending, conditions=conditions, subset=subset, page_size=page_size, consistent_read=consistent_read))


def scan_all_items(
            table_name: str,
            conditions: ConditionBase | None = None,
            subset: list[str] | None = None,
            page_size: int | None = 1_000,
            consistent_read: bool=False,
        ) -> Iterable[dict]:
    """
    Return all the items returned by a scan operation, handling pagination
    """
    return _async_iter_to_sync(scan_all_items_async(table_name=table_name, conditions=conditions, subset=subset, page_size=page_size, consistent_read=consistent_read))


def batch_delete_items(table_name: str, keys_or_items: Iterable[dict] | Iterable[dict]):
    """
    Delete the items by batch, there is no verification that they did not exist.
    """
    return _run_async(batch_delete_items_async(table_name=table_name, keys_or_items=keys_or_items))


def batch_put_items(table_name: str, items: Iterable[dict] | Iterable[dict]):
    """
    Create items in batch, overwriting if they already exist.
    """
    return _run_async(batch_put_items_async(table_name=table_name, items=items))


def create_table(
        table_name: str,
        partition_names: dict[Literal["HASH", "RANGE"], str],
        data_types: dict[str, Literal["S", "N", "B"]],
        ttl_attribute: str | None = None,
    ):
    """
    Creates a table, raise an error if it already exists.
    
    Example
    -------
    >>> table = create_table("test-table")
    """
    return _run_async(create_table_async(table_name=table_name, partition_names=partition_names, data_types=data_types, ttl_attribute=ttl_attribute))


def delete_item(table_name: str, key_or_item: dict, return_object: bool = False) -> dict | None:
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
    return _run_async(delete_item_async(table_name=table_name, key_or_item=key_or_item, return_object=return_object))


def delete_table(table_name: str, blocking: bool=True):
    """
    Delete a table, raise an error if it does not exists
    
    Example
    -------
    >>> table = delete_table("test_table")
    """
    return _run_async(delete_table_async(table_name=table_name, blocking=blocking))


def get_item(table_name: str, key_or_item: dict, consistent_read: bool=False) -> dict | None:
    """
    Get a full item from it's keys, returns None if the key does not exist.
    If the table has an hash key and a range key, both must be provided in the 'keys' dict.
    
    Example
    -------
    >>> get_item(table, {"id": "ID0"})
    {"uuid": "ID0", "field": 10.0}
    """
    return _run_async(get_item_async(table_name=table_name, key_or_item=key_or_item, consistent_read=consistent_read))


def get_item_fields(
        table_name: str,
        key_or_item: dict,
        fields: set[str | tuple[str | int]],
        consistent_read: bool=False,
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
    return _run_async(get_item_fields_async(table_name=table_name, key_or_item=key_or_item, fields=fields, consistent_read=consistent_read))


def get_table_keys(table_name: str) -> KeyType:
    """
    Get the {type: name} of the table keys
    """
    return _run_async(get_table_keys_async(table_name=table_name))


def item_exists(table_name: str, key_or_item: dict, consistent_read: bool=False) -> bool:
    """
    Returns True if the item exists and False otherwise.
    Faster and cheaper than a 'get_item' as this only query the partition key.
    """
    return _run_async(item_exists_async(table_name=table_name, key_or_item=key_or_item, consistent_read=consistent_read))


def list_tables() -> list[str]:
    """
    list existing tables
    """
    return _run_async(list_tables_async())


def put_item(table_name: str, item: dict, overwrite: bool=False, return_object: bool=False) -> dict | None:
    """
    Write an item, raise an error if it already exists and overwrite=False.
    Returns the old value if return_object=True.
    
    Example
    -------
    >>> put_item(table, {"uuid": "ID0", "field": 10.0})
    >>> put_item(table, {"uuid": "ID0", "field": 9.0}, overwrite=True, return_object=True)
    {"uuid": "ID0", "field": 10.0}
    """
    return _run_async(put_item_async(table_name=table_name, item=item, overwrite=overwrite, return_object=return_object))


def query_items(
        table_name: str,
        hash_key: object,
        page_start_token: str | None,
        sort_key_filter: str | tuple[object|None, object|None] = (None, None),
        ascending: bool=True,
        conditions: ConditionBase | None = None,
        subset: list[str] | None = None,
        page_size: int | None = 1_000,
        consistent_read: bool=False,
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
    return _run_async(query_items_async(table_name=table_name, hash_key=hash_key, page_start_token=page_start_token, sort_key_filter=sort_key_filter, ascending=ascending, conditions=conditions, subset=subset, page_size=page_size, consistent_read=consistent_read))


def scan_items(
        table_name: str,
        conditions: ConditionBase | None = None,
        subset: list[str] | None = None,
        page_size: int | None = 1_000,
        page_start_token: str | None = None,
        consistent_read: bool=False,
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
    return _run_async(scan_items_async(table_name=table_name, conditions=conditions, subset=subset, page_size=page_size, page_start_token=page_start_token, consistent_read=consistent_read))


def table_exists(table_name: str) -> bool:
    """
    Returns True if the table exists and False otherwise
    
    Example
    -------
    >>> table_exist("test-table")
    False
    """
    return _run_async(table_exists_async(table_name=table_name))


def update_item(
        table_name: str,
        key_or_item: dict,
        *,
        put_fields: dict[str | tuple[str | int], object] = {},
        increment_fields: dict[str | tuple[str | int], object] = {},
        extend_sets: dict[str | tuple[str | int], object | set] = {},
        remove_from_sets: dict[str | tuple[str | int], object | set] = {},
        extend_arrays: dict[str | tuple[str | int], list] = {},
        delete_fields: set[str | tuple[str | int]] = set(),
        create_item_if_missing: bool=False,
        conditions: ConditionBase | None = None,
        return_object: Literal["OLD", "NEW", None]=None
    ) -> dict | None:
    """
    Update an item fields.
    Only one operation can be done on a single field at a time.
    A set of conditions can optionaly be specified, in which case the update only happen if they are met, and do nothing silently otherwise, and return None if 'return_object' is specified.
    The 'create_if_missing' is implemented as an additional condition, so if it is False, updating will silently do nothing.
    
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
    conditions : boto3.dynamodb.conditions.ConditionBase or None
        The conditions to be met
    return_object : "OLD", "NEW" or None
        If not None, the function return the subset of the item containing the updated fields. (values before update if "OLD", values after update if "NEW")
    
    Returns
    -------
    dict | None
        The updated item if return_object is True, otherwise None.
    """
    return _run_async(update_item_async(table_name=table_name, key_or_item=key_or_item, put_fields=put_fields, increment_fields=increment_fields, extend_sets=extend_sets, remove_from_sets=remove_from_sets, extend_arrays=extend_arrays, delete_fields=delete_fields, create_item_if_missing=create_item_if_missing, conditions=conditions, return_object=return_object))
