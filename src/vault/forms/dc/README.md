# DC protective-order forms

Blank, official Superior Court of the District of Columbia (Domestic Violence
Division) forms for the Civil Protection Order (CPO) flow. Public documents.
**Blank templates only — never commit a form filled with a survivor's
information.**

| Form | Title | Status |
|---|---|---|
| (no printed number) | Petition and Affidavit for Civil Protection Order | mapped (`form.py`) |
| Confidential Address Form | Substitute-address request | not mapped (address withheld by design) |

## Notes

- The petition (D.C. Code § 16-1001 et seq.) requests a **12-month CPO** and
  covers the parties, the § 16-1001 relationship/eligibility basis, the DC
  nexus, an affidavit of the acts, and a 1-16 relief list with many
  sub-checkboxes. DC's relief list is its own. See `coverage.md`.
- **Eligibility is broader than a domestic relationship.** Item 1 also allows a
  CPO on a **stalking**, **§ 16-1001(6)(B)**, or **sexual-assault** basis with no
  domestic relationship. Whether one of those applies is a legal determination —
  `relationship_basis` is flagged `needs_legal_review` and those bases are not
  inferred from intake.
- **Confidential address by design:** the form offers a substitute address /
  Confidential Address Form. Intake only ever holds a safe mailing address, and
  the substitute-address box defaults on.
- **No firearms section** on this petition, so the module maps none.
- **No printed form number or revision** on the DC petition — `FORM_ID` is the
  descriptive `DC-CPO-Petition` and `FORM_REVISION` is `n/a`. Confirm against the
  blank PDF dropped here for lea-be-core's renderer. Source:
  dccourts.gov (Domestic Violence Division).
