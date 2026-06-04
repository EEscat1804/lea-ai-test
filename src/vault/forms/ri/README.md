# RI protective-order forms

Blank, official Rhode Island Family Court forms for the protective-order
(Domestic Abuse Prevention / Sexual Assault Protective Orders) flow. Public
documents. **Blank templates only — never commit a form filled with a survivor's
information.**

| Form | Title | Status |
|---|---|---|
| FC-79 | Complaint for an Order of Protection and Motion for Temporary Ex Parte Order of Protection | mapped (`form.py`) |

## Notes

- **FC-79** (G.L. 1956 ch. 15 of tit. 15, *Domestic Abuse Prevention*, and ch.
  37.2 of tit. 11, *Sexual Assault Protective Orders*; rev. July 2025) covers the
  county and case type, the parties (name + DOB + address), the §5 relationship
  basis, the §7 abuse checklist, the requested relief, and the motion for an
  immediate ex parte order. RI's abuse and relief lists are their own. See
  `coverage.md`.
- **No respondent description or vehicle block.** FC-79 asks the defendant's name,
  DOB, and address only — no height/weight/eyes/hair/marks and no vehicle. RI is
  therefore **not** in `PHYSICAL_DESCRIPTION_STATES` or
  `VEHICLE_DESCRIPTION_STATES`; the shared describe-respondent and vehicle gates
  do not run. (The unconditional employer gate still runs, as for every state.)
- **Four-county caption.** The Family Court divisions are Newport, Washington,
  Kent, and Providence/Bristol; `ri.county` is a required enum over those.
- **Case type is a check-all** (`ri.case_type`): Domestic Abuse, Sexual
  Exploitation, Sexual Abuse, Domestic Abuse with Juvenile Involvement — flagged
  for attorney confirmation (it selects the governing statute).
- **§7 abuse + relief are checklists** modeled as multi-selects (`ri.abuse_types`,
  `ri.relief`) with sub-detail follow-ups: weapon detail (§7), the household to
  vacate, the children for temporary custody, and the pets to protect.
- **No SSN gate.** RI is not in the SSN-for-support set `{CA, FL, TX}`, so
  requesting child support does not gate the petitioner's SSN. FC-79 does not ask
  for the defendant's SSN at all.
- **Address confidentiality is attorney-confirmed** (`plaintiff_address`,
  `needs_legal_review`). FC-79 has no address-withheld checkbox; intake holds only
  a safe mailing address, so the §1 street-address mapping is flagged (RIG3).
- **Relationship basis is attorney-confirmed** (`relationship_basis`,
  `needs_legal_review`) — RI's §5 "substantive dating or engagement relationship
  within the past one (1) year" and minor-involvement variants in particular.
  Source: courts.ri.gov (Family Court forms).
