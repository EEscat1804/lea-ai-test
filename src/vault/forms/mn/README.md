# MN protective-order forms

Blank, official Minnesota Judicial Branch forms for the order-for-protection (OFP)
flow. Public documents. **Blank templates only — never commit a form filled with a
survivor's information.**

| Form | Title | Status |
|---|---|---|
| OFP102 | Petition for Order for Protection (Minn. Stat. § 518B.01) | mapped (`form.py`) |
| OFP107-P | Confidential Address/Phone Request | not mapped — confidential-address election is recorded; clerk/advocate files it |
| OFP102-PP / -BAC / -OMC | Person / children attachments | not mapped — overflow attachments |

## Notes

- OFP102 (Rev. 7/25, Minn. Stat. § 518B.01) covers the parties, the §1
  confidential-address election, the #3/#7 who-needs-protection and relationship
  blocks, the #6 respondent information, the #11-#13 narrative and immediate-danger
  statement, the #15 ex parte relief (items a-j), and the #16-#22 relief-requiring-
  a-hearing items. MN's lists are their own. See `coverage.md`.
- **No respondent physical-description block — carve-out:** OFP102 #6 carries only
  the respondent's race / gender / DOB, **not** a height/weight/eyes/hair block, so
  MN is removed from `PHYSICAL_DESCRIPTION_STATES` (see the intake comment);
  `_mn_step` asks the respondent dob/gender/race the form does need.
- **No respondent vehicle block:** OFP102 has none, so MN is not in
  `VEHICLE_DESCRIPTION_STATES`.
- **Minor filing:** a minor may be a protected person and MN is in the doc's Q24
  list, so MN stays in `MINOR_FILING_STATES`.
- **No interpreter / disability field:** OFP102 has no fillable interpreter or
  accommodation field, so MN is in neither gate.
- **No SSN gate:** #17 requests financial support, but OFP102 has no petitioner SSN
  field, so MN is not added to the SSN-for-support gate (MNG4).
- **Confidential address:** §1 is a real mechanism — "I am requesting that my
  address be kept confidential by submitting the … Confidential Address/Phone
  Request form (OFP107-P)". So `address_confidential` is derived `"checked"`, the
  petitioner address maps to the safe mailing address, and both are flagged
  `needs_legal_review`.
- **Two relief tiers:** #15 (a-j) is ex parte relief that does not require a
  hearing; #16-#22 require a hearing — both are mapped, separated by membership set.
- **Court of filing:** the District Court for the petitioner's county; `mn.county`
  records which.
- Source: mncourts.gov/forms (OFP102).
