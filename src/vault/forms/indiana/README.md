# IN protective-order forms

Blank, official Indiana Office of Court Services forms for the order-for-protection
flow. Public documents. **Blank templates only — never commit a form filled with a
survivor's information.**

| Form | Title | Status |
|---|---|---|
| OJA-PO-0100 | Petition for an Order for Protection and Request for a Hearing (I.C. 34-26-5) | mapped (`form.py`) |
| PO-0104 | Confidential Form (address) | not mapped — confidential-address election recorded; clerk/advocate files it |

## Notes

- **Package name caveat:** the directory is `indiana`, not `in`, because the
  two-letter code "IN" is a Python keyword. The jurisdiction code stays `"IN"`. This
  mirrors the `oregon` keyword-collision precedent.
- OJA-PO-0100 (Rev. 05/25, I.C. 34-26-5) covers the caption, the §1 victim basis,
  the §2 relationship basis (family/household + stalking / sex-offense / harassment
  alternatives), the §3 respondent age, the §4 other cases, the §5 venue, the §6
  public mailing address, the §7 acts, the §8 incident narratives, and the §9 relief
  checklist (protective items + after-hearing custody/support items) with the §10 ex
  parte request. IN's lists are their own. See `coverage.md`.
- **No respondent physical-description block, no respondent vehicle block:** §3 asks
  only the respondent's age, and there is no vehicle field, so IN is in **neither**
  `PHYSICAL_DESCRIPTION_STATES` nor `VEHICLE_DESCRIPTION_STATES`. Only the
  unconditional shared employer gate precedes the IN block.
- **No minor-self-filing gate:** IN is not in `MINOR_FILING_STATES`; a minor appears
  via the §2 "minor child of a person in one of the … relationships" basis, not the
  shared minor-self-filing path.
- **No interpreter / disability field, no SSN gate:** OJA-PO-0100 has none of these
  fields; the §9 relief includes support, but there is no petitioner SSN field, so IN
  is not in the SSN-for-support gate.
- **Confidential address:** §6 prints a *public* mailing address ("This address will
  not be kept secret"); the confidential address goes on the separate Confidential
  Form (PO-0104) / the Attorney General's Address Confidentiality Program. So the
  petitioner address maps to the safe mailing address (flagged `needs_legal_review`,
  with a note that §6 is public), and `in.confidential_address` is derived `"checked"`
  to record the confidential form is used.
- **Two relief tiers:** §9 protective items (`in.relief`) may be granted without a
  hearing; the custody/support items (`in.hearing_relief`) require notice and a
  hearing within 30 days.
- **Ex parte:** by filing, the petition requests an immediate ex parte order
  (derived), with a hearing within 30 days required for certain relief.
- **Court of filing:** the county court (with division/room); `in.county` records
  which.
- Source: in.gov / courts.in.gov self-service forms (OJA-PO-0100).
