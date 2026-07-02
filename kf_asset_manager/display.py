"""Display IDs — human-friendly labels for the UI, DERIVED from internal IDs.

The internal ID (e.g. ``KF-D-000087``) is the only identifier: immutable, opaque,
used in relationships, manifest, database, and Shopify references. A Display ID
(``D87`` / ``Design #87``) is *purely a UI convenience*. It is derived on the fly,
never stored as an identity, and must never be used to look anything up.
"""

import re

ENTITY_WORD = {"FAM": "Family", "D": "Design", "AST": "Asset", "PRD": "Product"}
ENTITY_SHORT = {"FAM": "F", "D": "D", "AST": "A", "PRD": "P"}

_RX = re.compile(r"^KF-([A-Z]+)-0*(\d+)$")


def parse_internal(internal_id):
    """('KF-D-000087') -> ('D', 87); returns (None, None) if not a KF internal ID."""
    m = _RX.match(internal_id or "")
    if not m:
        return None, None
    return m.group(1), int(m.group(2))


def short(internal_id):
    """Compact display form: KF-D-000087 -> 'D87'. Falls back to the input."""
    ent, n = parse_internal(internal_id)
    if ent is None:
        return internal_id
    return f"{ENTITY_SHORT.get(ent, ent)}{n}"


def label(internal_id):
    """Friendly display form: KF-D-000087 -> 'Design #87'. Falls back to the input."""
    ent, n = parse_internal(internal_id)
    if ent is None:
        return internal_id
    return f"{ENTITY_WORD.get(ent, ent)} #{n}"
