# MS protective-order forms

Blank, official Mississippi forms for the domestic-abuse-protection-order flow.
Public documents. **Blank templates only — never commit a form filled with a
survivor's information.**

| Form | Title | Status |
|---|---|---|
| (no number) | Petition for Domestic Abuse Protection Order (M.C.A. § 93-21-1) | mapped (`form.py`) |
| SF1 | Supplement — additional protected persons | not mapped — overflow attachment |
| SF2 | Supplement — confidential address (§ 93-21-9(7)) | not mapped — confidential-address election recorded; clerk/advocate files it |
| SF3 / SF4 | Supplement — facts / children in common | not mapped — overflow attachments |

## Notes

- The petition (M.C.A. § 93-21-1 et seq.) covers the caption, the emergency-relief
  election, the §1 protected persons and relationship basis, the §2
  confidential-address election, the §3 venue, the §4 respondent information (a full
  physical-description block + caution / medical flags), the §5 acts of abuse, the
  §6 narrative, the §7-§8 divorce / children blocks, the §9 relief checklist (plus
  Chancery/County-only relief), and the §10 other-cases disclosure. MS's lists are
  their own. See `coverage.md`.
- **No form number / no revision date — gap:** the petition prints neither a form
  number nor a revision date, so `FORM_ID` is the descriptive title, `FORM_REVISION`
  is `"unknown"`, and both are flagged MSG1.
- **Physical-description block:** the §4 block has eye color / hair / height /
  weight / SSN / DL / features, so MS IS in `PHYSICAL_DESCRIPTION_STATES` and the
  shared gate feeds `respondent.height/weight/eye_color/hair_color/distinguishing_marks`;
  `_ms_step` adds the respondent dob / sex / race the block also needs.
- **No vehicle block — carve-out:** the §4 block has no respondent vehicle field, so
  MS is removed from `VEHICLE_DESCRIPTION_STATES` (see the intake comment), like the
  OK / TN / NH / KY / LA / ID carve-outs.
- **No minor-self-filing gate:** MS is not in `MINOR_FILING_STATES`; minors appear
  as protected persons (§1a), not via the shared minor-self-filing path.
- **No interpreter / disability field:** the petition has neither, so MS is in
  neither gate.
- **Respondent SSN, no petitioner SSN:** the §4 block wants the *respondent's* SSN /
  driver's license (not collected by intake, MSG4). The Chancery/County-only relief
  includes support, but there is no *petitioner* SSN field, so MS is NOT in the
  SSN-for-support gate.
- **Confidential address:** §2 is a real mechanism — "Petitioner requests his/her
  address remain confidential", with the address on Supplemental Form #2 (SF2,
  § 93-21-9(7)). So `address_confidential` is derived `"checked"`, the petitioner
  address maps to the safe mailing address, and both are flagged `needs_legal_review`.
- **Chancery/County-only relief:** the §9 continuation (custody / support /
  visitation / restitution) may only be requested in Chancery or County Court;
  `ms.court_type` records which, and `_ms_step` asks the Chancery/County relief only
  when applicable.
- **Court of filing:** chancery / county / justice / municipal court for the
  petitioner's county; `ms.county` + `ms.court_type` record which.
- Source: Mississippi Attorney General / MS Protective Order Registry (M.C.A.
  § 93-21-1).
