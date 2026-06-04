# CO protective-order forms

Blank, official Colorado Judicial Branch forms for the Civil Protection Order
(CPO) flow. Public documents. **Blank templates only — never commit a form
filled with a survivor's information.**

| Form | Title | Status |
|---|---|---|
| JDF 402 | Complaint/Motion for Civil Protection Order | mapped (`form.py`) |
| JDF 404 | Affidavit Regarding Children | not mapped — required when children are protected persons |

## Notes

- JDF 402 (C.R.S. § 13-14-101 et seq.) covers the parties, the statutory basis
  (item 1), residence/relationship (item 2), other protected persons, the
  incidents, imminent danger, an address-confidentiality request (item 6), and an
  item-7 relief list (a-i). CO's basis and relief lists are its own, distinct
  from the other states'. See `coverage.md`.
- **Basis (item 1)** is a statutory characterization (domestic abuse / stalking /
  sexual assault / unlawful sexual contact / elder-at-risk / physical assault) —
  collected as `co.basis` and flagged `needs_legal_review`.
- **Court type** (Municipal / County / District / Juvenile / Probate) is a
  procedural determination — flagged `needs_legal_review`, not inferred.
- **Address confidentiality:** section 6 lets the petitioner omit their address
  and phone. Intake only ever holds a safe mailing address, and the omit box
  defaults on.
- **Children:** JDF 404 (Affidavit Regarding Children) is also required when
  children are protected persons.
- Respondent height/weight come from the shared physical-description intake block
  (CO is a physical-description jurisdiction), though JDF 402 has no respondent
  description section, so they are not mapped here.
- Source: coloradojudicial.gov / courts.state.co.us self-help forms. Drop the
  official blank fillable PDF here for lea-be-core's renderer.
