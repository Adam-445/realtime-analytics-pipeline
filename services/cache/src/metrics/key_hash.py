import hashlib
from typing import Dict, Tuple

DIMENSION_SEPARATOR = "|"
KV_SEPARATOR = "="


def stable_dimensions_tuple(dimensions: Dict[str, str]) -> Tuple[Tuple[str, str], ...]:
    return tuple(sorted(dimensions.items()))


def dimensions_hash(dimensions: Dict[str, str], prefix_len: int = 10) -> str:
    stable = stable_dimensions_tuple(dimensions)
    joined = DIMENSION_SEPARATOR.join(f"{k}{KV_SEPARATOR}{v}" for k, v in stable)
    sha1 = hashlib.sha1(joined.encode("utf-8")).hexdigest()
    return sha1[:prefix_len]
