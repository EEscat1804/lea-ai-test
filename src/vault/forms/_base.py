"""Shared scaffolding for per-jurisdiction form mappings.

Each state's module (`ca_dv100`, `wa_po001`, …) declares a table of `FormField`s
and calls `assemble_form` to turn intake answers into the structured, auditable
`item -> value` map that lea-be-core stamps onto the official PDF.

The contract every form module keeps:
- never render a PDF (Pyodide budget + stateless contract),
- never guess — a required field with no answer is `[FACT NEEDED]`,
- flag any mapping an attorney must confirm with `needs_legal_review=True`.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

# Marker vocabulary — every uncertain/absent value is tagged so a reviewer
# (and lea-be-core) can see it, never trusted silently.
FACT_NEEDED = "[FACT NEEDED]"

# Field resolution statuses.
STATUS_FILLED = "filled"  # mapped from an intake answer
STATUS_FACT_NEEDED = "fact_needed"  # required, intake collects it, but absent here
STATUS_NOT_COLLECTED = "not_collected"  # the intake graph does not gather this yet


@dataclass(frozen=True)
class FormField:
    """One mappable field (or checkbox) on a court form.

    `item` mirrors the form's own numbering (e.g. "1a", "14D", "5c") so the
    output is auditable against the paper form box-by-box.
    """

    item: str
    name: str
    # Intake answer key this field reads from. None => intake does not collect
    # it yet (status becomes `not_collected`).
    source: str | None = None
    # Computed fields (age from DOB, relationship checkboxes) supply a derive
    # fn instead of a flat source. Returns the value, or None if the inputs
    # it needs are absent.
    derive: Callable[[dict[str, Any]], str | None] | None = None
    required: bool = False
    # True => an attorney must confirm this intake answer maps to this box.
    needs_legal_review: bool = False
    note: str = ""


Resolver = Callable[[FormField, dict[str, Any]], tuple[Any, str]]


def resolve_basic(f: FormField, answers: dict[str, Any]) -> tuple[Any, str]:
    """Resolve one field by derive fn or plain source lookup."""
    if f.derive is not None:
        derived = f.derive(answers)
        if derived is not None:
            return derived, STATUS_FILLED
        return _absent(f)

    if f.source is None:
        return None, STATUS_NOT_COLLECTED

    if f.source in answers:
        return answers[f.source], STATUS_FILLED

    return _absent(f)


def _absent(f: FormField) -> tuple[Any, str]:
    return (FACT_NEEDED if f.required else None), (
        STATUS_FACT_NEEDED if f.required else STATUS_NOT_COLLECTED
    )


def assemble_form(
    *,
    form_id: str,
    revision: str,
    jurisdiction: str,
    fields: tuple[FormField, ...],
    answers: dict[str, Any],
    resolve: Resolver = resolve_basic,
) -> dict[str, Any]:
    """Map intake answers onto a form's fields.

    Returns the auditable map — never a PDF. `gaps` lists required fields with
    no answer (these block filing); `review_items` lists mappings an attorney
    must confirm. A state with a non-standard field (e.g. CA's relief
    checkboxes) passes its own `resolve`.
    """
    out_fields: dict[str, dict[str, Any]] = {}
    gaps: list[str] = []
    review_items: list[str] = []

    for f in fields:
        value, status = resolve(f, answers)
        out_fields[f.item] = {
            "name": f.name,
            "value": value,
            "status": status,
            "source": f.source,
        }
        if status == STATUS_FACT_NEEDED:
            gaps.append(f.item)
        if f.needs_legal_review:
            review_items.append(f.item)

    return {
        "form": form_id,
        "revision": revision,
        "jurisdiction": jurisdiction,
        "fields": out_fields,
        "gaps": gaps,
        "review_items": review_items,
    }
