# OK protective-order forms

Blank, official Oklahoma Administrative Office of the Courts (AOC) forms for the
protective-order (Protection from Domestic Abuse Act) flow. Public documents.
**Blank templates only — never commit a form filled with a survivor's
information.**

| Form | Title | Status |
|---|---|---|
| (no printed number) | Petition for Protective Order (22 O.S. 60.1) | mapped (`form.py`) |

## Notes

- **Petition for Protective Order** (Protection from Domestic Abuse Act, 22 O.S.
  § 60.1; District Court; AOC form effective Nov 1, 2023) covers the county, the
  parties, a "Defendant Identifiers" description block, the §1 relationship basis,
  the §2 jurisdiction statement, the §3 actions of the defendant, the §4 incident
  narrative, and the §6 relief checklist (items 1-15) with the emergency ex parte
  election. OK's actions and relief lists are their own. See `coverage.md`.
- **No printed form number.** The footer reads "AOC Form – Petition for Protective
  Order. 22 O.S. 60.1." `FORM_ID` is descriptive
  (`"Petition for Protective Order"`) and flagged (OKG1) — no number was
  fabricated.
- **Has a defendant description block.** The "Defendant Identifiers" box asks
  sex / race / DOB / height / weight / eyes / hair / distinguishing features
  (plus driver's license). OK is therefore in `PHYSICAL_DESCRIPTION_STATES`; the
  shared height/weight/eyes/hair/marks gate runs, and the OK block adds sex / race
  / DOB. The driver's license is not collected (OKG4).
- **No vehicle field — OK removed from `VEHICLE_DESCRIPTION_STATES`.** The source
  doc lists OK among the Q41-43 vehicle states, but the actual AOC petition has no
  vehicle block, so OK is carved out of the vehicle gate (same as TN). See the
  comment in `vault.intake`.
- **§3 actions + §6 relief are checklists** modeled as multi-selects
  (`ok.actions`, `ok.relief`) with sub-detail follow-ups: the move-out residence
  (item 4), the civil-standby address (item 6), the utilities/wireless transfer
  (item 12), the attorney-fees amount (item 15), and a free-text additional-relief
  request. The §2 jurisdiction statement is a third multi-select
  (`ok.jurisdiction_basis`).
- **Emergency ex parte election** (`ok.ex_parte`) maps the §6 A-vs-B choice
  (no ex parte vs. emergency ex parte order).
- **No petitioner address on the form.** The AOC petition prints only the
  defendant's address, so there is no petitioner residential address to withhold
  and no `address_confidential` assertion is needed.
- **No SSN gate.** OK is not in the SSN-for-support set `{CA, FL, TX}`, and the
  AOC petition requests attorney's fees / court costs, not ongoing child or
  spousal support. The defendant's SSN is not asked by the form.
- **Police-report requirement is left to the attorney/advocate.** Appendix 1
  requires a non-family / non-dating petitioner to attach a police report for some
  crimes; this conditional eligibility check is flagged, not automated (OKG6/OKG7).
- **Relationship basis and every action / relief box are attorney-confirmed**
  (`needs_legal_review`) — OK's §1A intimate-partner vs. family-household
  categories and the §1B/§1C/§1D victim characterization in particular. Source:
  oscn.net (AOC protective-order forms).
