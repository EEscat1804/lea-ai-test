"""Per-jurisdiction DVRO petition form mappings.

Each US jurisdiction has its own court form(s). DV law and the forms differ
per state, so every jurisdiction gets its own module here rather than a
shared generic template — wrong-jurisdiction output is a hard fail (see
CLAUDE.md, "Multi-state branching").

A form module exposes `assemble(answers) -> dict` which maps completed Vault
intake answers onto that jurisdiction's form fields. Modules never render a
PDF and never guess: missing data is surfaced as `[FACT NEEDED]`, and any
mapping a licensed attorney must confirm is flagged for review.

CA (DV-100) is the reference implementation. Add a state by landing both its
intake graph (in `vault.intake`) and its form module here in the same PR.
"""

from __future__ import annotations
