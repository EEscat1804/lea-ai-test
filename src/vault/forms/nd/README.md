# ND protective-order forms

Blank, official North Dakota court forms for the Civil Protection Order flow.
Public documents. **Blank templates only — never commit a form filled with a
survivor's information.**

| Form | Title | Status |
|---|---|---|
| Petition CPO | Petition for Civil Protection Order | mapped (`form.py`) |
| Confidential Information Form | Petitioner address/phone (kept from respondent) | not mapped — address protection |

## Notes

- The petition (N.D.C.C. Ch. 14-07.7) is a **combined** petition for three order
  types — **Domestic Violence Protection Order**, **Sexual Assault Restraining
  Order**, and **Disorderly Conduct Restraining Order**. The petitioner may
  select more than one; the court issues the single order giving the most
  protection they qualify for. It covers the parties, the order type(s), venue,
  the relationship basis, respondent descriptive info, the incident statements
  (most-recent + past), and the requested temporary relief. ND's relief list is
  its own, distinct from the other states'. See `coverage.md`.
- **Address protection:** the petitioner keeps their address on a separate
  Confidential Information Form. Intake only ever holds a safe mailing address,
  and the confidential-address request defaults on.
- **Respondent identifiers** (gender/race/height/weight/eyes/hair/marks, vehicle,
  plate) come from the shared physical-description and vehicle blocks (ND is in
  both sets) plus the ND block.
- Respondent **SSN** and driver's license are never collected (sensitive).
- Source: ndcourts.gov/legal-self-help. Drop the official blank fillable PDF here
  for lea-be-core's renderer.
