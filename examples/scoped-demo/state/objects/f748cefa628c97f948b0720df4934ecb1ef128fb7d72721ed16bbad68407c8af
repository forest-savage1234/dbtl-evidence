"""Bounded, unambiguous JSON evidence reads shared by new import contracts."""
import json
from .core import IntegrityError


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result: raise IntegrityError("Duplicate JSON key: "+key)
        result[key] = value
    return result


def read_json(db, key, *, maximum=1024*1024):
    path = db.objects.verify(key)
    if path.stat().st_size > maximum: raise IntegrityError("Evidence JSON exceeds contract size limit")
    try:
        value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_object,
                           parse_constant=lambda _: (_ for _ in ()).throw(IntegrityError("Nonfinite JSON")))
    except (UnicodeError, ValueError, RecursionError) as exc: raise IntegrityError("Invalid evidence JSON") from exc
    if not isinstance(value, dict): raise IntegrityError("Evidence JSON must be an object")
    return value
