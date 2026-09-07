from __future__ import annotations

import dataclasses
import types
import typing
from typing import Any, get_args, get_origin

import coqpit.coqpit as coqpit_module


def is_union_type(field_type):
    origin = get_origin(field_type)

    return (
        origin is typing.Union
        or origin is types.UnionType
    )


def is_list_type(field_type):
    origin = get_origin(field_type)

    return (
        field_type is list
        or origin is list
        or origin is typing.List
    )


def is_dict_type(field_type):
    origin = get_origin(field_type)

    return (
        field_type is dict
        or origin is dict
        or origin is typing.Dict
    )


def safe_issubclass(field_type, class_or_tuple):
    if not isinstance(field_type, type):
        return False

    try:
        return issubclass(field_type, class_or_tuple)
    except TypeError:
        return False


def deserialize(value, field_type):

    # None
    if value is None:
        return None

    # No type
    if field_type is None:
        return value

    # Any
    if field_type is Any:
        return value

    # ---------------------------------------------------------
    # Optional[T] / T | None
    # ---------------------------------------------------------

    if is_union_type(field_type):

        args = get_args(field_type)

        for arg in args:

            if arg is type(None):
                continue

            try:
                return deserialize(value, arg)
            except Exception:
                continue

        return value

    # ---------------------------------------------------------
    # list / List[T]
    # ---------------------------------------------------------

    if is_list_type(field_type):

        if not isinstance(value, list):
            return value

        args = get_args(field_type)

        if not args:
            return value

        item_type = args[0]

        return [
            deserialize(item, item_type)
            for item in value
        ]

    # ---------------------------------------------------------
    # dict / Dict[K,V]
    # ---------------------------------------------------------

    if is_dict_type(field_type):

        if not isinstance(value, dict):
            return value

        args = get_args(field_type)

        if len(args) == 2:

            key_type = args[0]
            value_type = args[1]

            return {
                deserialize(key, key_type):
                deserialize(item, value_type)
                for key, item in value.items()
            }

        return value

    # ---------------------------------------------------------
    # Forward references
    # ---------------------------------------------------------

    if isinstance(field_type, str):
        return value

    # ---------------------------------------------------------
    # Python typing objects
    # ---------------------------------------------------------

    if not isinstance(field_type, type):
        return value

    # ---------------------------------------------------------
    # Serializable objects
    # ---------------------------------------------------------

    Serializable = getattr(
        coqpit_module,
        "Serializable",
        None,
    )

    if Serializable is not None:

        if safe_issubclass(
            field_type,
            Serializable,
        ):

            try:
                return field_type.deserialize_immutable(value)
            except Exception:
                pass

    # ---------------------------------------------------------
    # Dataclass
    # ---------------------------------------------------------

    if dataclasses.is_dataclass(field_type):

        if isinstance(value, dict):

            try:
                return field_type(**value)
            except Exception:
                pass

    # ---------------------------------------------------------
    # Primitive types
    # ---------------------------------------------------------

    if field_type in (
        str,
        int,
        float,
        bool,
        bytes,
        list,
        dict,
        tuple,
        set,
    ):
        return value

    # ---------------------------------------------------------
    # Already correct type
    # ---------------------------------------------------------

    try:

        if isinstance(value, field_type):
            return value

    except TypeError:
        pass

    return value


def install():

    # Replace the module-level _deserialize function.
    coqpit_module._deserialize = deserialize

    # IMPORTANT:
    # Coqpit.deserialize() has its own global namespace.
    # Explicitly replace the _deserialize reference there.
    coqpit_module.Coqpit.deserialize.__globals__[
        "_deserialize"
    ] = deserialize

    return True


install()