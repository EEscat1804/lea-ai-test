# IA protective-order forms

Blank, official Iowa Judicial Branch forms for the domestic-abuse relief flow.
Public documents. **Blank templates only — never commit a form filled with a
survivor's information.**

| Form | Title | Status |
|---|---|---|
| Rule 17.10 Form 11 | Petition for Relief from Domestic Abuse (Iowa Code ch. 236) | mapped (`form.py`) |
| Protected Information Disclosure | Confidential names / birthdates / SSNs | not mapped — separate confidential form for protected info |

## Notes

- Form 11 (November 2022, Iowa Code chapter 236) covers the county, the parties,
  the §7 relationship basis, the §8 abuse types, the §9 recent/past narrative, the
  §10 firearms block, the §11 children block, the §20 additional-possession
  requests, the §22 counseling request, the §23 temporary/final order election and
  order checklist (items 1-13), and the §24 confidentiality/sealing requests. IA's
  relationship and relief lists are their own. See `coverage.md`.
- **No respondent physical-description block, no respondent vehicle block:** the §5
  block is only the defendant's age/year-of-birth, and the §20 "Vehicle" possession
  item is the *petitioner's* family car (a relief item), so IA is in **neither**
  `PHYSICAL_DESCRIPTION_STATES` nor `VEHICLE_DESCRIPTION_STATES`. Only the
  unconditional shared employer gate precedes the IA block.
- **Minor filing:** a protected person may be a minor and IA is in the doc's Q24
  list, so IA stays in `MINOR_FILING_STATES` (the shared minor-filing gate fires
  for an under-18 filer).
- **No interpreter / disability field:** Form 11 carries only a disability-
  coordinator referral notice, not a fillable interpreter or accommodation field,
  so IA is in neither gate.
- **No SSN gate:** §19/§23 request ongoing financial support, but protected
  information (full names, birthdates, SSNs) goes on a *separate* Protected
  Information Disclosure form — Form 11 itself has no SSN field, so IA is NOT added
  to the SSN-for-support gate (IAG6).
- **Confidential address:** §3 explicitly allows a safe mailing address (shelter /
  PO box), and §24 offers seal-file / remove-address / seal-children requests, so
  the petitioner address maps to the safe mailing address (flagged
  `needs_legal_review`) and `ia.confidential_requests` records the §24 election.
- **Court of filing:** the Iowa District Court for the petitioner's county;
  `ia.county` records which.
- **Order type:** a Temporary Protective Order lasts until the hearing (within 15
  days); a Final Protective Order lasts up to one year — §23A/§23B record which.
- Source: iowacourts.gov/for-the-public/court-forms (Rule 17.10 Form 11).
