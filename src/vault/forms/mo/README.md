# MO protective-order forms

Blank, official Missouri (State Judicial Records Committee) forms for the adult
order-of-protection flow. Public documents. **Blank templates only — never commit a
form filled with a survivor's information.**

| Form | Title | Status |
|---|---|---|
| AA40 | Petition for a Court Order of Protection - Adult (RSMo 455.010 et seq.) | mapped (`form.py`) |

## Notes

- AA40 (09-25, RSMo 455.010 et seq.) covers the county/venue, the §A party +
  respondent identifiers (a full physical description + a vehicle question), the §B
  acts and ex-parte basis, the §B narrative, and the §C relief (the "NOT to" list,
  the serious-danger 2-to-10-year finding, custody, support, property, counseling,
  and other requests). MO's lists are their own. See `coverage.md`.
- **Physical-description block:** the §A "Information about the person you need
  protection from" block has race / sex / height / weight / hair / eyes / identifying
  marks, so MO IS in `PHYSICAL_DESCRIPTION_STATES` and the shared gate feeds
  `respondent.height/weight/eye_color/hair_color/distinguishing_marks`; `_mo_step`
  adds the respondent age / sex / race the block also needs.
- **Vehicle block:** §B asks "What type of vehicle(s) does Respondent drive?
  (make, model, year, color, license plate)", so MO IS in
  `VEHICLE_DESCRIPTION_STATES` and the shared gate feeds `respondent.vehicle_*`.
- **Minor filing:** the form asks the petitioner's age / emancipation if under 17,
  and MO is in the doc's Q24 list, so MO stays in `MINOR_FILING_STATES`.
- **No interpreter / disability field:** AA40 has neither, so MO is in neither gate.
- **No SSN gate:** §C(4) requests child support / maintenance, but AA40 has no
  petitioner SSN field, so MO is not in the SSN-for-support gate (MOG2).
- **Address protection:** the form states "The person you need protection from will
  get a copy of this form"; address protection is Missouri's separate Address
  Confidentiality Program / Order-of-Protection Redacted Information Filing Sheet,
  plus §C(7) "close my voter's-registration address to the public". The petitioner
  address maps to the safe mailing address, flagged `needs_legal_review`.
- **Two relief tiers + serious danger:** §C(1) is the "NOT to" protective list;
  §C(2) is the optional serious-danger 2-to-10-year finding; §C(3-7) are the
  custody / support / property / counseling / other requests (`mo.additional_relief`).
- **Court of filing:** the Circuit Court for the county (City of St. Louis counts as
  a county); `mo.county` records which.
- Source: courts.mo.gov forms (AA40 / Petition for a Court Order of Protection -
  Adult).
