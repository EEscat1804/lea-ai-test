# MD protection-from-DV forms

Blank, official Maryland Judiciary forms for the FL § 4-504 flow. Public
documents. **Blank templates only — never commit a form filled with a
survivor's information.**

| Form | Title | Status |
|---|---|---|
| CC-DC-DV-001 | Petition for Protection from Domestic Violence | mapped (`form.py`) |
| CC-DC-DV-001A | Addendum — Description of Respondent | partial (DOB/sex/race/employer; physical not collected) |

## Notes

- CC-DC-DV-001 (Md. Family Law § 4-504) covers parties, the § 4-504
  relationship basis, an acts-of-abuse checklist, firearms, and an items 11-12
  relief list. The Vault maps the petition + the respondent-description addendum
  fields it has.
- **Protection:** the form itself says the petitioner need not give an address
  if listing it risks further abuse. Intake only ever holds a safe mailing
  address, and the confidential-address box is defaulted **on**. See
  `coverage.md`.
- The acts-of-abuse boxes and relief boxes are flagged `needs_legal_review`.
- Drop the official blank fillable PDFs here for lea-be-core's renderer. Source:
  mdcourts.gov forms.
