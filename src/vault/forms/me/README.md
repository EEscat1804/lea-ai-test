# ME protective-order forms

Blank, official Maine Judicial Branch forms for the protection-from-abuse (PFA)
flow. Public documents. **Blank templates only — never commit a form filled with
a survivor's information.**

| Form | Title | Status |
|---|---|---|
| PA-001 | Complaint for Protection from Abuse | mapped (`form.py`) |
| PA-005 | Protection Order Service Information (respondent physical description + vehicle) | mapped into PA-001 fields via the shared Tier-2 gates |
| PA-015 | Affidavit of Confidential Address | not mapped — the confidential-address election is recorded; advocate/attorney files it |
| CR-CV-FM-PC-200 | Social Security Number Confidential Disclosure | not mapped — separate confidential form, filed only for support/family matters |
| FM-050 | Child Support Affidavit | not mapped — filed with order (m) support when no child-support order exists |

## Notes

- PA-001 (Rev. 09/25, 19-A M.R.S. §§ 4101-4116) covers the parties, the §4
  relationship basis, the parents/children blocks (§§5-6), public assistance and
  other court cases (§§7-9), the §10 temporary (ex parte) order election, the §11
  weapons block, the §12 abuse narrative, and the orders a-q relief checklist.
  ME's relationship and relief lists are their own. See `coverage.md`.
- **Physical-description + vehicle blocks:** these live on the companion service
  sheet **PA-005**, filed with every PFA complaint, so ME IS in
  `PHYSICAL_DESCRIPTION_STATES` and `VEHICLE_DESCRIPTION_STATES` and the shared
  gates feed `respondent.height/weight/eye_color/hair_color/distinguishing_marks`
  and `respondent.vehicle_*`. The employer block (PA-005) is the unconditional
  shared employer gate.
- **Minor filing:** a Maine minor can file a PFA on their own behalf, so ME is in
  `MINOR_FILING_STATES` (the shared minor-filing gate fires for an under-18 filer).
- **No interpreter / disability field:** PA-001 / PA-005 carry only ADA-notice and
  Language-Services *footers* (referrals to a clerk), not fillable interpreter or
  accommodation fields, so ME is in neither the interpreter nor the disability gate.
- **No SSN gate:** order (m) requests ongoing support, but the petitioner SSN lives
  on a *separate* confidential form (CR-CV-FM-PC-200) filed only in support/family
  matters — the PA-001 itself has no SSN field, so ME is NOT added to the
  SSN-for-support gate. Support relief flags the FM-050 / CR-CV-FM-PC-200 follow-up
  for the advocate (MEG4/coverage).
- **Confidential address:** Maine offers a real mechanism — the Affidavit of
  Confidential Address (PA-015). Intake only ever holds a safe mailing address, so
  `address_confidential` is derived `"checked"`, the petitioner address maps to the
  safe mailing address, and both are flagged `needs_legal_review`.
- **Court of filing:** Maine PFAs are filed in the **District Court** by town
  location (not county); `me.court_location` records which.
- **Sworn / notarized:** signed under penalty of perjury, notarized (or e-filed
  with the on-form certification).
- Source: courts.maine.gov/forms (PA-001, PA-005, PA-015).
