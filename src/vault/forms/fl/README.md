# FL protective-order forms

Blank, official Florida Supreme Court Approved Family Law Forms for the DV
injunction flow. Public documents. **Blank templates only — never commit a form
filled with a survivor's information.**

| Form | Title | Status |
|---|---|---|
| 12.980(a) | Petition for Injunction for Protection Against Domestic Violence | mapped (`form.py`) |
| 12.980(h) | Petitioner's Request for Confidential Filing of Address | not yet mapped (address is withheld by default) |
| 12.980(n) | Petition for Injunction for Protection Against Dating Violence | not mapped — separate injunction type (see note) |

## Notes

- 12.980(a) (Fla. Stat. § 741.30) covers the parties, the family/household
  relationship basis, a sworn statement of the abuse, a respondent description
  for service, firearms, and the relief requested. FL's relief list is its own,
  distinct from the other states'. See `coverage.md`.
- **Relationship basis is attorney-confirmed.** The DV injunction requires the
  parties to be family or household members or to have a child in common. A
  dating-only relationship with no cohabitation or child may need the **Dating
  Violence** petition, 12.980(n), instead — `relationship_basis` is flagged
  `needs_legal_review`.
- The survivor's home address is never collected, so it cannot reach the
  (public) petition; the confidential-address request (12.980(h)) is asserted by
  default.
- **Confirm the blank form revision** (`FORM_REVISION` in `form.py`) against the
  official fillable PDF before lea-be-core renders it. Source: flcourts.gov
  family-law forms.
- There is no filing fee for a DV injunction petition (Fla. Stat. § 741.30(2)(a)).
