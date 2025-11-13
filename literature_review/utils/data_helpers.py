"""
Data Helper Functions

This module provides utility functions for data manipulation and validation,
such as detecting circular references in complex objects.
"""

def detect_circular_refs(obj, seen=None, path="root"):
    """
    Detects circular references in a dictionary or list.
    Raises a ValueError if a circular reference is found.
    """
    if seen is None:
        seen = {id(obj): path}

    if isinstance(obj, dict):
        for key, value in obj.items():
            new_path = f"{path}.{key}"
            if id(value) in seen:
                raise ValueError(f"Circular reference detected at '{new_path}' pointing back to '{seen[id(value)]}'")
            if isinstance(value, (dict, list)):
                seen[id(value)] = new_path
                detect_circular_refs(value, seen, new_path)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            new_path = f"{path}[{i}]"
            if id(item) in seen:
                raise ValueError(f"Circular reference detected at '{new_path}' pointing back to '{seen[id(item)]}'")
            if isinstance(item, (dict, list)):
                seen[id(item)] = new_path
                detect_circular_refs(item, seen, new_path)
