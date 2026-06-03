# NY family-offense forms

Blank, official New York Unified Court System forms for the family-offense flow.
Public documents. **Blank templates only — never commit a form filled with a
survivor's information.**

| Form | Title | Status |
|---|---|---|
| UCS-FC8-2 | Family Offense Petition | mapped (`form.py`) |
| UCS-FC GF-21 | Request for Address Confidentiality | referenced (survivor keeps address off the petition) |

## Notes

- UCS-FC8-2 (FCA 812, 818, 821) covers parties, the FCA 812 relationship basis,
  the offense details, household members, a safety/firearms section, and an
  item-10 list of relief requested.
- **Address confidentiality:** the form lets the petitioner keep their address
  off the petition; the Vault defaults this to **Yes**. The petitioner's address
  is filed separately on **UCS-FC GF-21**, not on the public petition.
- **Item 4 offense checklist is NOT mapped** — choosing which penal-law offense
  applies is a legal characterization for the attorney. The Vault maps the
  survivor's narrative + incident details, not the offense classification. See
  `coverage.md`.
- Drop the official blank fillable PDFs here for lea-be-core's renderer. Source:
  nycourts.gov / nycourthelp.gov forms.
