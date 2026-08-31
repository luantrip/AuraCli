"""
Binary search and insertion utilities for efficient sorted collection management.

Provides O(log n) search and insertion operations for sorted arrays,
essential for performance in large data collections (messages, sessions, tasks).
"""

from typing import Callable, List, Tuple, TypeVar

T = TypeVar("T")


def binary_search(
    array: List[T],
    target_id: str,
    get_id: Callable[[T], str],
) -> Tuple[bool, int]:
    """
    Binary search in a sorted array.

    Args:
        array: Sorted array to search in
        target_id: ID to search for
        get_id: Function to extract ID from array element

    Returns:
        Tuple of (found: bool, index: int)
        - If found: (True, index of element)
        - If not found: (False, insertion point)
    """
    left = 0
    right = len(array) - 1

    while left <= right:
        mid = (left + right) // 2
        mid_id = get_id(array[mid])

        if mid_id == target_id:
            return True, mid
        elif mid_id < target_id:
            left = mid + 1
        else:
            right = mid - 1

    return False, left


def binary_insert(
    array: List[T],
    item: T,
    get_id: Callable[[T], str],
) -> List[T]:
    """
    Insert item into sorted array maintaining order.

    Args:
        array: Sorted array to insert into
        item: Item to insert
        get_id: Function to extract ID from array element

    Returns:
        The modified array with item inserted at correct position
    """
    target_id = get_id(item)
    _, index = binary_search(array, target_id, get_id)
    array.insert(index, item)
    return array


def binary_update(
    array: List[T],
    item: T,
    get_id: Callable[[T], str],
) -> Tuple[List[T], bool]:
    """
    Update item in sorted array or insert if not found.

    Args:
        array: Sorted array to update
        item: Item to update/insert
        get_id: Function to extract ID from array element

    Returns:
        Tuple of (modified array, was_update: bool)
    """
    target_id = get_id(item)
    found, index = binary_search(array, target_id, get_id)

    if found:
        array[index] = item
        return array, True
    else:
        array.insert(index, item)
        return array, False


def binary_remove(
    array: List[T],
    target_id: str,
    get_id: Callable[[T], str],
) -> Tuple[List[T], bool]:
    """
    Remove item from sorted array by ID.

    Args:
        array: Sorted array to remove from
        target_id: ID of item to remove
        get_id: Function to extract ID from array element

    Returns:
        Tuple of (modified array, was_removed: bool)
    """
    found, index = binary_search(array, target_id, get_id)

    if found:
        array.pop(index)
        return array, True

    return array, False
