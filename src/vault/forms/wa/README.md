# WA protection-order forms

Blank, official Washington court forms for the protection-order flow. Public
documents. **Blank templates only — never commit a form filled with a
survivor's information.**

| Form | Title | Rev. | Status |
|---|---|---|---|
| PO 001 | Petition for Protection Order | 2026-01 | mapped (`form.py`) |
| PO 001 Att. A | Definitions | 2026-01 | static (always filed; no data) |
| PO 001 Att. C | Child Custody | 2026-01 | not yet mapped (if protecting respondent's children) |
| PO 001 Att. E | Firearms Identification | 2026-01 | partial (firearms access/types/locations) |
| PO 001 Att. B | Vulnerable Adult | 2026-01 | out of scope (not a DV-survivor path) |
| PO 001 Att. D | Non-parents / ICWA | 2026-01 | out of scope (parent filing for own children) |

## Notes

- WA's PO 001 is a **unified** petition (DV / sexual assault / stalking /
  vulnerable adult / anti-harassment, item 1). The Vault maps the **Domestic
  Violence** path (PTORPRT). Item 1 is fixed to DV and flagged for review.
- The WA intake section fills the WA-specific items (the A-Z restraints in item
  14, length of order, temporary-order request, jurisdiction basis, etc.). A few
  optional items remain — see `coverage.md`.
- Drop the official blank fillable PDFs here for lea-be-core's renderer. Source:
  courts.wa.gov forms.
