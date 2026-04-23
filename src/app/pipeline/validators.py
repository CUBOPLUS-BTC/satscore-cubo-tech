"""
Data validation module for the Magma pipeline framework.

Provides ``DataValidator``, ``ValidationResult``, and ``SchemaValidator``
classes covering schema, type, range, uniqueness, referential integrity,
freshness, and format checks. Pure Python stdlib only.
"""

import math
import re
import time
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# ValidationResult
# ---------------------------------------------------------------------------

class ValidationResult:
    """
    Container for the outcome of a validation operation.

    Attributes:
        is_valid:  True only when there are no errors.
        errors:    List of error message strings.
        warnings:  List of non-fatal warning strings.
        metadata:  Arbitrary extra information attached by the validator.
    """

    def __init__(self):
        self.is_valid: bool = True
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.metadata: Dict[str, Any] = {}

    def add_error(self, message: str) -> "ValidationResult":
        self.errors.append(message)
        self.is_valid = False
        return self

    def add_warning(self, message: str) -> "ValidationResult":
        self.warnings.append(message)
        return self

    def merge(self, other: "ValidationResult") -> "ValidationResult":
        """Merge another ValidationResult into this one."""
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        self.metadata.update(other.metadata)
        if other.errors:
            self.is_valid = False
        return self

    def to_dict(self) -> Dict:
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "metadata": self.metadata,
        }

    def __bool__(self):
        return self.is_valid

    def __repr__(self):
        return (
            f"<ValidationResult valid={self.is_valid} "
            f"errors={len(self.errors)} warnings={len(self.warnings)}>"
        )


# ---------------------------------------------------------------------------
# DataValidator
# ---------------------------------------------------------------------------

class DataValidator:
    """
    High-level data validation utilities.

    All methods return a ``ValidationResult``. Methods can be composed by
    merging results::

        result = DataValidator.validate_required(row, ["pubkey", "amount_sats"])
        result.merge(DataValidator.validate_types(row, {"amount_sats": int}))
    """

    @staticmethod
    def validate_schema(data: Dict, schema: Dict) -> ValidationResult:
        """
        Validate a dict against a simple schema dict.

        The schema is a dict mapping field names to type names (strings) or
        Python types. Example::

            schema = {"pubkey": "str", "amount_sats": "int", "price": "float"}

        Args:
            data:   Dict to validate.
            schema: Expected types.

        Returns:
            ValidationResult.
        """
        result = ValidationResult()
        type_map = {
            "str": str, "int": int, "float": (float, int),
            "bool": bool, "list": list, "dict": dict,
        }
        for field, expected_type in schema.items():
            if field not in data:
                result.add_error(f"Missing required field: '{field}'")
                continue
            val = data[field]
            if isinstance(expected_type, str):
                py_type = type_map.get(expected_type)
                if py_type is None:
                    result.add_warning(f"Unknown type '{expected_type}' for field '{field}'")
                    continue
            else:
                py_type = expected_type
            if val is not None and not isinstance(val, py_type):
                result.add_error(
                    f"Field '{field}': expected {expected_type}, got {type(val).__name__}"
                )
        return result

    @staticmethod
    def validate_types(data: Dict, type_map: Dict) -> ValidationResult:
        """
        Check that dict values match a ``{field: python_type}`` mapping.

        Args:
            data:     Dict to check.
            type_map: Mapping of field name to expected Python type(s).

        Returns:
            ValidationResult.
        """
        result = ValidationResult()
        for field, expected in type_map.items():
            if field not in data:
                continue  # missing fields are a schema concern, not a type concern
            val = data[field]
            if val is not None and not isinstance(val, expected):
                result.add_error(
                    f"Type mismatch for '{field}': expected {expected}, "
                    f"got {type(val).__name__} (value={val!r})"
                )
        return result

    @staticmethod
    def validate_range(
        value: Any,
        min_val: Any = None,
        max_val: Any = None,
    ) -> bool:
        """
        Check that a value falls within [min_val, max_val].

        Args:
            value:   Value to test.
            min_val: Lower bound (inclusive), or None to skip.
            max_val: Upper bound (inclusive), or None to skip.

        Returns:
            True if within range.
        """
        if min_val is not None and value < min_val:
            return False
        if max_val is not None and value > max_val:
            return False
        return True

    @staticmethod
    def validate_required(
        data: Dict,
        required_fields: List[str],
    ) -> ValidationResult:
        """
        Check that all required fields are present and non-None.

        Args:
            data:            Dict to check.
            required_fields: List of required keys.

        Returns:
            ValidationResult.
        """
        result = ValidationResult()
        for field in required_fields:
            if field not in data:
                result.add_error(f"Required field missing: '{field}'")
            elif data[field] is None:
                result.add_error(f"Required field is None: '{field}'")
            elif data[field] == "":
                result.add_warning(f"Required field is empty string: '{field}'")
        return result

    @staticmethod
    def validate_unique(
        data: List[Dict],
        field: str,
    ) -> ValidationResult:
        """
        Check that all values of ``field`` in the list are unique.

        Args:
            data:  List of row dicts.
            field: Field to check for uniqueness.

        Returns:
            ValidationResult with errors for duplicate values.
        """
        result = ValidationResult()
        seen: Dict[Any, int] = {}
        duplicates = []
        for i, row in enumerate(data):
            val = row.get(field)
            if val in seen:
                duplicates.append((val, seen[val], i))
            else:
                seen[val] = i
        for val, first_idx, dup_idx in duplicates:
            result.add_error(
                f"Duplicate value '{val}' for field '{field}' "
                f"at indices {first_idx} and {dup_idx}"
            )
        result.metadata["duplicate_count"] = len(duplicates)
        return result

    @staticmethod
    def validate_referential(
        data: List[Dict],
        reference_data: List[Dict],
        key: str,
    ) -> ValidationResult:
        """
        Check that all values of ``key`` in ``data`` exist in ``reference_data``.

        Args:
            data:           Dataset to validate (child side of the FK).
            reference_data: Reference dataset (parent side of the FK).
            key:            Field name to check.

        Returns:
            ValidationResult.
        """
        result = ValidationResult()
        reference_values = {row.get(key) for row in reference_data}
        missing = []
        for i, row in enumerate(data):
            val = row.get(key)
            if val not in reference_values:
                missing.append((i, val))
        for idx, val in missing:
            result.add_error(
                f"Referential integrity violation at index {idx}: "
                f"'{key}'={val!r} not found in reference dataset"
            )
        result.metadata["violations"] = len(missing)
        return result

    @staticmethod
    def validate_consistency(
        data: List[Dict],
        rules: List[Callable[[Dict], Optional[str]]],
    ) -> ValidationResult:
        """
        Apply a list of consistency-check callables to each row.

        Each rule callable receives a row dict and should return ``None``
        if the row passes, or an error message string if it fails.

        Args:
            data:  List of row dicts.
            rules: List of ``(row) -> Optional[str]`` callables.

        Returns:
            ValidationResult.
        """
        result = ValidationResult()
        for i, row in enumerate(data):
            for rule in rules:
                msg = rule(row)
                if msg is not None:
                    result.add_error(f"Row {i}: {msg}")
        return result

    @staticmethod
    def validate_completeness(
        data: List[Dict],
        expected_count: int,
        tolerance: float = 0.0,
    ) -> ValidationResult:
        """
        Check that a dataset contains approximately the expected number of rows.

        Args:
            data:           List of row dicts.
            expected_count: Expected number of rows.
            tolerance:      Allowed fraction deviation (0.05 = ±5 %).

        Returns:
            ValidationResult.
        """
        result = ValidationResult()
        actual = len(data)
        result.metadata["actual_count"] = actual
        result.metadata["expected_count"] = expected_count

        if expected_count == 0:
            return result

        deviation = abs(actual - expected_count) / expected_count
        result.metadata["deviation"] = round(deviation, 4)

        if deviation > tolerance:
            result.add_error(
                f"Completeness check failed: expected {expected_count} rows, "
                f"got {actual} (deviation={deviation:.2%}, tolerance={tolerance:.2%})"
            )
        elif deviation > 0:
            result.add_warning(
                f"Row count {actual} differs slightly from expected {expected_count}"
            )
        return result

    @staticmethod
    def validate_freshness(
        data: List[Dict],
        max_age_seconds: int,
        timestamp_field: str = "timestamp",
    ) -> ValidationResult:
        """
        Check that rows contain timestamps within ``max_age_seconds`` of now.

        Args:
            data:              List of row dicts.
            max_age_seconds:   Maximum allowed age in seconds.
            timestamp_field:   Key for the Unix timestamp.

        Returns:
            ValidationResult.
        """
        result = ValidationResult()
        now = time.time()
        stale_count = 0
        for row in data:
            ts = row.get(timestamp_field)
            if ts is None:
                result.add_warning(f"Row missing '{timestamp_field}' field")
                continue
            age = now - float(ts)
            if age > max_age_seconds:
                stale_count += 1

        result.metadata["stale_count"] = stale_count
        result.metadata["total_count"] = len(data)

        if stale_count > 0:
            result.add_error(
                f"{stale_count}/{len(data)} rows are older than {max_age_seconds}s"
            )
        return result

    @staticmethod
    def validate_format(value: str, format_type: str) -> bool:
        """
        Validate a string against a named format.

        Supported formats: ``email``, ``url``, ``date`` (ISO 8601),
        ``hex``, ``hex64``, ``bitcoin-address``, ``nostr-pubkey``.

        Args:
            value:       String to validate.
            format_type: Name of the format to check against.

        Returns:
            True if valid.
        """
        PATTERNS: Dict[str, str] = {
            "email": r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
            "url": r"^https?://[^\s/$.?#].[^\s]*$",
            "date": r"^\d{4}-\d{2}-\d{2}$",
            "hex": r"^[0-9a-fA-F]+$",
            "hex64": r"^[0-9a-fA-F]{64}$",
            "nostr-pubkey": r"^[0-9a-fA-F]{64}$",
            "bitcoin-address": r"^(1|3|bc1)[a-zA-HJ-NP-Z0-9]{25,62}$",
            "iso-datetime": r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}",
            "uuid": r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
        }
        pattern = PATTERNS.get(format_type)
        if pattern is None:
            logger.warning("Unknown format type: '%s'", format_type)
            return True
        return bool(re.match(pattern, str(value)))


# ---------------------------------------------------------------------------
# SchemaValidator  (JSON Schema-like)
# ---------------------------------------------------------------------------

class SchemaValidator:
    """
    JSON Schema-inspired validator.

    Supports the following schema keywords:

    - ``type``                  – Python type name(s).
    - ``required``              – list of required keys.
    - ``minLength`` / ``maxLength``
    - ``minimum`` / ``maximum``
    - ``pattern``               – regex pattern for strings.
    - ``enum``                  – allowed values list.
    - ``items``                 – schema for list items.
    - ``properties``            – schemas for dict properties.
    - ``additionalProperties``  – bool or schema for extra keys.
    - ``format``                – named format (uses :meth:`DataValidator.validate_format`).

    Custom format validators can be registered with :meth:`register_format`.
    """

    _custom_formats: Dict[str, Callable[[str], bool]] = {}

    # Predefined additional formats
    _BUILTIN_FORMATS: Dict[str, Callable[[str], bool]] = {
        "bitcoin-address": lambda v: bool(re.match(
            r"^(1|3|bc1)[a-zA-HJ-NP-Z0-9]{25,62}$", str(v)
        )),
        "nostr-pubkey": lambda v: bool(re.match(r"^[0-9a-fA-F]{64}$", str(v))),
        "hex64": lambda v: bool(re.match(r"^[0-9a-fA-F]{64}$", str(v))),
        "iso-date": lambda v: bool(re.match(r"^\d{4}-\d{2}-\d{2}$", str(v))),
        "amount": lambda v: (
            isinstance(v, (int, float)) and float(v) >= 0
        ) if not isinstance(v, str) else bool(re.match(r"^\d+(\.\d+)?$", v)),
    }

    @classmethod
    def register_format(cls, name: str, validator_fn: Callable[[str], bool]):
        """
        Register a custom format validator.

        Args:
            name:         Format name (used in schema ``format`` keyword).
            validator_fn: Callable that accepts a string and returns bool.
        """
        cls._custom_formats[name] = validator_fn
        logger.debug("SchemaValidator: registered format '%s'", name)

    @classmethod
    def _check_format(cls, value: str, fmt: str) -> bool:
        # Custom formats override built-ins
        if fmt in cls._custom_formats:
            return cls._custom_formats[fmt](value)
        if fmt in cls._BUILTIN_FORMATS:
            return cls._BUILTIN_FORMATS[fmt](value)
        return DataValidator.validate_format(value, fmt)

    @classmethod
    def validate(cls, data: Any, schema: Dict, path: str = "") -> ValidationResult:
        """
        Recursively validate ``data`` against ``schema``.

        Args:
            data:   Python object to validate.
            schema: Schema dict.
            path:   Dot-separated path for nested error messages.

        Returns:
            ValidationResult.
        """
        result = ValidationResult()
        prefix = f"{path}: " if path else ""

        # -- type check --
        if "type" in schema:
            expected_type = schema["type"]
            type_map = {
                "string": str, "str": str,
                "integer": int, "int": int,
                "number": (int, float),
                "float": float,
                "boolean": bool, "bool": bool,
                "array": list, "list": list,
                "object": dict, "dict": dict,
                "null": type(None),
            }
            py_type = type_map.get(expected_type)
            if py_type and not isinstance(data, py_type):
                result.add_error(
                    f"{prefix}Expected type '{expected_type}', "
                    f"got '{type(data).__name__}'"
                )
                return result  # further checks won't make sense

        # -- enum check --
        if "enum" in schema and data not in schema["enum"]:
            result.add_error(
                f"{prefix}Value {data!r} not in allowed enum {schema['enum']}"
            )

        # -- string-specific checks --
        if isinstance(data, str):
            if "minLength" in schema and len(data) < schema["minLength"]:
                result.add_error(
                    f"{prefix}String length {len(data)} < minLength {schema['minLength']}"
                )
            if "maxLength" in schema and len(data) > schema["maxLength"]:
                result.add_error(
                    f"{prefix}String length {len(data)} > maxLength {schema['maxLength']}"
                )
            if "pattern" in schema and not re.match(schema["pattern"], data):
                result.add_error(
                    f"{prefix}String '{data}' does not match pattern '{schema['pattern']}'"
                )
            if "format" in schema and not cls._check_format(data, schema["format"]):
                result.add_error(
                    f"{prefix}String '{data}' does not match format '{schema['format']}'"
                )

        # -- numeric checks --
        if isinstance(data, (int, float)) and not isinstance(data, bool):
            if "minimum" in schema and data < schema["minimum"]:
                result.add_error(
                    f"{prefix}Value {data} < minimum {schema['minimum']}"
                )
            if "maximum" in schema and data > schema["maximum"]:
                result.add_error(
                    f"{prefix}Value {data} > maximum {schema['maximum']}"
                )

        # -- list / array checks --
        if isinstance(data, list):
            if "minItems" in schema and len(data) < schema["minItems"]:
                result.add_error(
                    f"{prefix}Array length {len(data)} < minItems {schema['minItems']}"
                )
            if "maxItems" in schema and len(data) > schema["maxItems"]:
                result.add_error(
                    f"{prefix}Array length {len(data)} > maxItems {schema['maxItems']}"
                )
            if "items" in schema:
                for i, item in enumerate(data):
                    child = cls.validate(item, schema["items"], path=f"{path}[{i}]")
                    result.merge(child)

        # -- dict / object checks --
        if isinstance(data, dict):
            if "required" in schema:
                for req_field in schema["required"]:
                    if req_field not in data or data[req_field] is None:
                        result.add_error(
                            f"{prefix}Required property '{req_field}' is missing"
                        )

            if "properties" in schema:
                for prop_name, prop_schema in schema["properties"].items():
                    if prop_name in data:
                        child_path = f"{path}.{prop_name}" if path else prop_name
                        child = cls.validate(data[prop_name], prop_schema, child_path)
                        result.merge(child)

            if "additionalProperties" in schema:
                ap = schema["additionalProperties"]
                defined_props = set(schema.get("properties", {}).keys())
                extra_keys = set(data.keys()) - defined_props
                if ap is False and extra_keys:
                    for ek in extra_keys:
                        result.add_error(
                            f"{prefix}Additional property '{ek}' is not allowed"
                        )
                elif isinstance(ap, dict):
                    for ek in extra_keys:
                        child = cls.validate(
                            data[ek], ap, path=f"{path}.{ek}"
                        )
                        result.merge(child)

        return result


# ---------------------------------------------------------------------------
# Predefined schema constants (handy for unit tests and pipeline steps)
# ---------------------------------------------------------------------------

PRICE_ROW_SCHEMA = {
    "type": "object",
    "required": ["timestamp", "price_usd"],
    "properties": {
        "timestamp": {"type": "integer", "minimum": 0},
        "price_usd": {"type": "number", "minimum": 0},
        "date": {"type": "string", "format": "iso-date"},
    },
    "additionalProperties": True,
}

DEPOSIT_ROW_SCHEMA = {
    "type": "object",
    "required": ["pubkey", "amount_sats", "created_at"],
    "properties": {
        "pubkey": {"type": "string", "format": "nostr-pubkey"},
        "amount_sats": {"type": "integer", "minimum": 1},
        "created_at": {"type": "integer", "minimum": 0},
    },
    "additionalProperties": True,
}

USER_SCHEMA = {
    "type": "object",
    "required": ["pubkey"],
    "properties": {
        "pubkey": {"type": "string", "format": "nostr-pubkey"},
        "auth_method": {"type": "string", "enum": ["lnurl", "nostr", "nwc"]},
        "created_at": {"type": "integer", "minimum": 0},
    },
    "additionalProperties": True,
}
