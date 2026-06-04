"""Oregon FAPA Restraining Order Petition (ORS 107.700) form package.

Named `oregon` rather than `or` because `or` is a Python keyword and cannot be an
importable module name. The jurisdiction code is "OR".
"""

from vault.forms.oregon.form import OR_FAPA_FIELDS, assemble

__all__ = ["OR_FAPA_FIELDS", "assemble"]
