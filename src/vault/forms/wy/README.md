# WY protective-order forms

Blank, official Wyoming Judicial Branch forms for the DV order-of-protection
flow. Public documents. **Blank templates only — never commit a form filled with
a survivor's information.**

| Form | Title | Status |
|---|---|---|
| PO DV Form 03 | Petition for Domestic Violence Order of Protection | mapped (`form.py`) |

## Notes

- PO DV Form 03 (W.S. § 35-21-101 to 112) covers the parties (with full
  respondent identifiers), other court cases (¶3), the household-member
  relationship basis (¶6), children (¶7), the abuse description (¶8),
  weapons/firearms (¶9-10), and the paragraph-11 relief list (**A-T**), plus the
  hearing-appearance choice (¶12). WY's relief list is its own, distinct from the
  other states'. See `coverage.md`.
- **Household-member basis (¶6):** WY requires the parties to be "household
  members." `relationship_basis` is mapped from `relationship.type` and flagged
  `needs_legal_review`.
- **Address confidentiality:** the ¶1 box keeps the petitioner's (and children's)
  address/phone confidential. Intake only ever holds a safe mailing address; the
  box defaults on.
- **Respondent identifiers** (DOB/race/gender/height/weight/eyes/hair, vehicle
  plate, distinguishing marks) come from the shared physical-description and
  vehicle blocks (WY is in both sets) plus the WY block.
- Source: wyomingjudicialbranch.org / courts.state.wy.us self-help forms. Drop
  the official blank fillable PDF here for lea-be-core's renderer.
