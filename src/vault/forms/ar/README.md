# AR protective-order forms

Blank, official Arkansas Circuit Court forms for the Order of Protection flow.
Public documents. **Blank templates only — never commit a form filled with a
survivor's information.**

| Form | Title | Status |
|---|---|---|
| (no printed number) | Petition and Affidavit for an Order of Protection | mapped (`form.py`) |

## Notes

- The petition (A.C.A. § 9-15-101 et seq., Domestic Abuse Act) covers the parties
  (with full identifiers), the relationship basis, the most-recent-act affidavit,
  law-enforcement reporting, prior violence, minor children, and an **item-8**
  list of ex parte order provisions, plus a law-enforcement NOTICE page. AR's
  relief list (item 8) is its own, distinct from the other states'. See
  `coverage.md`.
- **Address protection:** the form lets the petitioner omit an address (a mailing
  address is provided instead). Intake only ever holds a safe mailing address,
  and the omit-address box defaults on. Item 8 also offers "exclude petitioner's
  address from notice."
- **Respondent identifiers** (sex/race/DOB/height/weight/eyes/hair/distinguishing)
  come from the shared physical-description block (AR is a physical-description
  jurisdiction) plus the AR block; they populate both the caption and the NOTICE
  page.
- **Item 6** (respondent previously arrested/convicted of violence) maps from the
  shared prior-criminal-history question (AR was added to that gate).
- **No printed form number** on the AR petition — `FORM_ID` is the descriptive
  `AR-OP-Petition`. Confirm the official identifier and current revision against
  the blank PDF. Source: Arkansas Judiciary / arcourts.gov forms.
