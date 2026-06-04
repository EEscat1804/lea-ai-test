# KY protective-order forms

Blank, official Kentucky Court of Justice forms for the order-of-protection flow.
Public documents. **Blank templates only — never commit a form filled with a
survivor's information.**

| Form | Title | Status |
|---|---|---|
| AOC-275.1 | Petition/Motion for Order of Protection (KRS 403 / 456) | mapped (`form.py`) |

## Notes

- AOC-275.1 (Rev. 6-23, KRS Chapter 403 / 456, FCRPP Part IV) covers the caption,
  the respondent identifier box (a full physical description), the §2 relationship
  basis, the §3 children block, the abuse narrative, the page-1 CAUTION flags, and
  the Motion-for-Relief checklist (emergency ex parte / temporary order plus the
  specific restraints). KY's relationship and relief lists are their own. See
  `coverage.md`.
- **Physical-description block:** the identifier box has Sex / Race / Birthdate /
  Height / Weight / Eyes / Hair (for LINK entry), so KY IS in
  `PHYSICAL_DESCRIPTION_STATES` and the shared gate feeds
  `respondent.height/weight/eye_color/hair_color/distinguishing_marks`; `_ky_step`
  adds the respondent dob / sex / race the box also needs.
- **No vehicle block — carve-out:** AOC-275.1 has no respondent vehicle field, so
  KY is intentionally removed from `VEHICLE_DESCRIPTION_STATES` (see the intake
  comment), like the OK / TN / NH carve-outs.
- **No minor-self-filing gate:** KY is not in `MINOR_FILING_STATES`; the
  "Petitioner filing on behalf of minor" checkbox is filing-on-behalf, not the
  shared minor-self-filing path.
- **No interpreter / disability field:** AOC-275.1 has neither, so KY is in
  neither gate.
- **Respondent SSN, no petitioner SSN:** the identifier box wants the
  *respondent's* SSN / driver's license (for LINK / criminal-history lookup), which
  intake does not collect (KYG2). The relief includes temporary child support, but
  the form has no *petitioner* SSN field, so KY is NOT in the SSN-for-support gate.
- **Confidential address:** the petitioner's residence is collected but the served
  respondent copy is blacked out (page 3 of the form is the redacted copy), so the
  petitioner address maps to the safe mailing address (flagged
  `needs_legal_review`); the page-4 stay-away note that address information will be
  available to the respondent is surfaced for the attorney.
- **Court of filing:** the Kentucky Court of Justice for the petitioner's county;
  `ky.county` records which.
- Source: kycourts.gov forms (AOC-275.1).
