# TN protective-order forms

Blank, official Tennessee court forms for the Order of Protection flow. Public
documents. **Blank templates only — never commit a form filled with a survivor's
information.**

| Form | Title | Status |
|---|---|---|
| OP2018-1 | Petition for Order of Protection and Order for Hearing | mapped (`form.py`) |

## Notes

- Form #OP2018-1 (TCA § 36-3-601 et seq.) covers the parties, a "Describe
  Respondent" block, the §1 relationship/eligibility basis, the children list, the
  abuse narrative, and the items 7-19 relief checklist plus the ex parte
  (Temporary Order of Protection) request. TN's relief list is its own. See
  `coverage.md`.
- **Shared physical-description + minor-filing gates apply.** TN is in
  `PHYSICAL_DESCRIPTION_STATES` (the form's Describe-Respondent block:
  hair/eyes/height/weight/scars) and `MINOR_FILING_STATES` (the form's TCA
  §36-3-602 under-18 filing path). The TN block adds the form's sex/race/DOB.
- **NOT in `VEHICLE_DESCRIPTION_STATES`.** The DVRO intake doc lists TN for
  Q41-43, but OP2018-1 has **no vehicle field**, so TN was omitted from that
  frozenset (with a comment tracing the omission) — the vehicle questions never
  fire for TN.
- **Items 7-19 relief is one checklist** modeled as a single multi-select
  (`tn.relief`) with sub-detail: no-contact targets (§7), stay-away places (§8),
  personal-conduct types (§9), move-out vs provide-housing (§13), wireless
  transfer (§18), and other/general relief (§19). The §15 firearms list maps from
  the shared firearm gate (`firearm.types[]` / `.locations[]`).
- **No SSN gate.** TN is not in the SSN-for-support set `{CA, FL, TX}`, so
  requesting child/spousal support does not gate the petitioner's SSN. The
  *respondent's* SSN is explicitly "Do not list it here" on the form — sensitive,
  not collected (TNG4).
- **Confidential by design:** the form lets the petitioner leave the children's
  addresses blank if listing them would create danger; the petitioner's own
  address is never collected (safe mailing only). Both confidential boxes default
  on.
- **Relationship/eligibility is attorney-confirmed** (`relationship_basis`,
  `needs_legal_review`) — including the §1(g) stalking and §1(h) sexual-assault
  grounds, which don't require a domestic relationship and are confirmed from the
  narrative. Source: tncourts.gov (Order of Protection forms).
