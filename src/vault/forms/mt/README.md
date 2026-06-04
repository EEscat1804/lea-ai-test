# MT protective-order forms

Blank, official Montana Attorney General's Office / Judicial Branch forms for the
temporary order of protection flow. Public documents. **Blank templates only —
never commit a form filled with a survivor's information.**

| Form | Title | Status |
|---|---|---|
| OVS 3 | Sworn Petition for Temporary Order of Protection and Request for Hearing | mapped (`form.py`) |
| OVS 3 — Appendix A | Temporary visitation schedule | not mapped — attach when item-11 visitation requested |

## Notes

- AGO Form OVS 3 (Revised 02/11, Mont. Code Ann. § 40-15-201) covers the parties,
  the protected persons (self / minor children / others), residence and living
  situation, the relationship basis, the recent- and past-abuse narrative,
  firearms, other court cases, and the item-1 through item-12 relief list. MT's
  relief list is its own, distinct from the other states'. See `coverage.md`.
- **No respondent DOB / physical-description / vehicle block:** the form has none
  of these, so MT is in none of the `PHYSICAL_DESCRIPTION_STATES` /
  `VEHICLE_DESCRIPTION_STATES` gates and `_mt_step` never asks respondent DOB. The
  "My vehicle" relief (item 4) is the *petitioner's* vehicle as a stay-away place,
  not a respondent identifier.
- **No interpreter / disability field:** the form has neither, so MT is not in
  those gates.
- **No SSN gate:** the form requests no child/spousal support and has no SSN
  field, so MT is not added to the SSN-for-support gate.
- **Address / home secrecy:** the caption holds the petitioner's contact address;
  intake only ever holds a safe mailing address, and item 4 lets the petitioner
  keep their home location off the form ("if you want the location of your home to
  be secret, do not list").
- **Court of filing:** Montana TOPs may be filed in Justice, City, Municipal,
  District, or Tribal court; `mt.court_type` records which.
- **Sworn / notarized:** the petition is signed under oath before a
  judge/clerk/notary.
- Source: dojmt.gov / Montana Judicial Branch protective-order forms (AGO OVS 3).
