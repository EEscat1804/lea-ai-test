# CT protective-order forms

Blank, official Connecticut Judicial Branch forms for the Relief from Abuse
flow. Public documents. **Blank templates only — never commit a form filled with
a survivor's information.**

| Form | Title | Status |
|---|---|---|
| JD-FM-137 | Application for Relief from Abuse | mapped (`form.py`) |
| JD-FM-233 | Request for Orders of Maintenance | not mapped — support add-on (separate form) |
| JD-FM-188 | Request for Nondisclosure of Location Information | not mapped — address protection |

## Notes

- JD-FM-137 (C.G.S. §§ 46b-15 et al.) covers the parties (with a respondent
  description), the relationship basis, an attached affidavit of the abuse, CT's
  coded relief conditions, custody/visitation, and ex parte relief. CT's relief
  list (the **CT## codes**) is its own, distinct from the other states'. See
  `coverage.md`.
- **Relief codes** are mapped to the form's own identifiers (CT01, CT03, CT05,
  CT14, CT15, CT16, CT19, CT20, CT31) so the output is auditable box-by-box.
- **Address protection:** the form warns that any address given is disclosed to
  the respondent. Intake only ever holds a safe mailing address; the home and
  work addresses are never collected. JD-FM-188 is the nondisclosure path.
- **Maintenance/support** (the two "additional orders of maintenance" boxes) is a
  separate form, **JD-FM-233**, not mapped here.
- Respondent height/weight come from the shared physical-description intake block
  (CT is a physical-description jurisdiction).
- Source: jud.ct.gov forms. Drop the official blank fillable PDF here for
  lea-be-core's renderer.
