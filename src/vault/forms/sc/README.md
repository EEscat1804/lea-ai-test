# SC protective-order forms

Blank, official South Carolina Judicial Branch forms for the family-court
order-of-protection flow. Public documents. **Blank templates only — never commit a
form filled with a survivor's information.**

| Form | Title | Status |
|---|---|---|
| SCCA 425 | Petition for Family Court Order of Protection (Protection from Domestic Abuse Act) | mapped (`form.py`) |
| SCCA 430 / 430S | Financial Declaration | not mapped — required when requesting child / financial support |
| SCCA 742 | Request for Emergency Hearing | not mapped — filed separately for a 24-hour hearing |

## Notes

- SCCA 425 (Revised 11/2025, Protection from Domestic Abuse Act) covers the
  caption, the §1 venue, the §2-§5 respondent information, the §6 protected persons,
  the §7 relationship basis, the §8 incident narrative, and the §9 relief checklist
  (items a-q). SC's lists are their own. See `coverage.md`.
- **No respondent physical-description block — carve-out:** §4 carries only the
  respondent's DOB / race / sex, **not** a height/weight/eyes/hair block, so SC is
  removed from `PHYSICAL_DESCRIPTION_STATES` (see the intake comment); `_sc_step`
  asks the respondent dob/race/sex the form does need.
- **No respondent vehicle block — carve-out:** SCCA 425 has no vehicle field, so SC
  is removed from `VEHICLE_DESCRIPTION_STATES`.
- **Minor filing:** a child under 18 who lives with the petitioner may be a
  protected person (§6b), and SC is in the doc's Q24 list, so SC stays in
  `MINOR_FILING_STATES`.
- **No interpreter / disability field:** SCCA 425 has neither, so SC is in neither
  gate.
- **Respondent SSN, no petitioner SSN:** the §3 Social Security Number is the
  *respondent's* (not collected by intake, SCG2). The §9 relief includes child /
  financial support (which require the separate Financial Declaration, SCCA 430),
  but the petition has no *petitioner* SSN field, so SC is NOT in the
  SSN-for-support gate.
- **Address protection:** the petition prints the respondent's address, not the
  petitioner's residence; South Carolina's address protection runs through the
  Family Court / Address Confidentiality Program (no on-form petitioner-address
  field to withhold).
- **Court of filing:** the Family Court for the petitioner's county / judicial
  circuit; `sc.county` records which.
- Source: sccourts.org forms (SCCA 425).
