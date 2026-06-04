# WI protective-order forms

Blank, official Wisconsin Circuit Court forms for the domestic-abuse TRO /
injunction flow. Public documents. **Blank templates only — never commit a form
filled with a survivor's information.**

| Form | Title | Status |
|---|---|---|
| CV-402 | Petition for TRO and/or Petition and Motion for Injunction Hearing (Domestic Abuse) | mapped (`form.py`) |
| CV-403 | Temporary Restraining Order and Notice of Injunction Hearing | not mapped — the order/notice |
| CV-437 | Wireless Telephone Transfer Service in Injunction Case | not mapped — phone-transfer add-on |
| GF-149 | Interpreter Request | not mapped — interpreter add-on |

## Notes

- CV-402 (§ 813.12 Wis. Stats.) covers the parties (with respondent
  identifiers), the relationship basis, the weapons caution, imminent danger, the
  abuse statement, other court cases, and the relief requested. WI's relief list
  is its own. See `coverage.md`.
- **TRO and injunction relief mirror each other:** the form repeats the same a-f
  options for the TRO (request 1) and the injunction (request 2). The single
  intake relief selection (`wi.relief`) populates both sub-lists.
- **No petitioner-address field:** CV-402 does not collect the petitioner's
  address at all, so it cannot reach the form.
- **Interpreter:** the form has an interpreter request (GF-149); WI is in the
  interpreter gate, and `petitioner.interpreter_language` maps to it.
- **Respondent identifiers** (sex/race/DOB/height/weight/hair/eyes/marks) come
  from the shared physical-description block (WI is a physical-description
  jurisdiction).
- Source: wicourts.gov forms (available in Spanish and Hmong). Drop the official
  blank fillable PDF here for lea-be-core's renderer.
