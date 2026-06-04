# VT protective-order forms

Blank, official Vermont Superior Court (Family Division) forms for the Relief
From Abuse (RFA) flow. Public documents. **Blank templates only — never commit a
form filled with a survivor's information.**

| Form | Title | Status |
|---|---|---|
| 400-00150C | Complaint for Relief from Abuse | mapped (`form.py`) |

## Notes

- Form 400-00150C (15 V.S.A. § 1101 et seq.) covers the parties, the relationship
  basis, an existing-proceedings matrix, an item-1 acts-of-abuse checklist, the
  residence/support facts (items 2-6), and **two distinct relief lists** — a
  Request for Emergency Relief and a Request for Final Order. VT's acts and relief
  lists are its own. See `coverage.md`.
- **Two relief lists, not one.** Emergency Relief and Final Order overlap but
  differ: the Final Order adds temporary living expenses, temporary child support,
  and pet *possession*; the Emergency Relief instead has a "refrain from cruelly
  treating pets" box. They are modeled as separate intake multi-selects
  (`vt.emergency_relief`, `vt.final_relief`) and separate form membership dicts.
- **14 units (counties):** Addison, Bennington, Caledonia, Chittenden, Essex,
  Franklin, Grand Isle, Lamoille, Orange, Orleans, Rutland, Washington, Windham,
  Windsor (`vt.unit`).
- **Narrative is on a separate affidavit.** The form face says "The facts to
  support this request for relief can be found on the Plaintiff's accompanying
  affidavit." The narrative still maps (`affidavit_narrative`) for that affidavit.
- **Confidential address by design:** intake only ever holds a safe mailing
  address; the survivor's home address is never collected. The caption's physical
  address field is the *defendant's* (for service), mapped from
  `respondent.last_known_address`. The `address_confidential` box defaults on.
- **Relationship basis is attorney-confirmed** (`relationship_basis`,
  `needs_legal_review`) — VT's "family member" and "other (describe)" categories
  in particular.
- **No physical-description / vehicle / interpreter / disability fields** — VT is
  in none of those shared Tier-2 sets, so the VT flow skips them. Source:
  vermontjudiciary.org (Family Division forms).
