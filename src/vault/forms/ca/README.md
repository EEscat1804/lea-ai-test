# CA DVRO forms

Blank, official California Judicial Council forms for the DVRO flow. These are
public documents (judicial council mandatory/optional forms). **Blank templates
only — never commit a form filled with a survivor's information.**

| Form | Title | Rev. | Status |
|---|---|---|---|
| DV-100 | Request for Domestic Violence Restraining Order | 2025-01-01 | mapped (`form.py`) |
| DV-110 | Temporary Restraining Order | — | not yet mapped |
| DV-109 | Notice of Court Hearing | — | not yet mapped |
| CLETS-001 | Confidential Information for Law Enforcement | — | not yet mapped (respondent physical description lands here, not on DV-100) |
| DV-105 | Request for Child Custody and Visitation Orders | — | not yet mapped |

## How the pieces fit

- `vault.intake` collects the answers (jurisdiction-aware question flow).
- `vault.forms.ca` maps those answers onto DV-100's numbered items.
- `vault.petition.assemble_petition("CA", answers)` returns the field map.
- **lea-be-core** stamps the field map onto the fillable PDF and serves it.
  lea-ai never renders a PDF (Pyodide dependency budget + stateless contract).

Drop the official blank fillable PDFs here (e.g. `DV-100.pdf`) so lea-be-core's
renderer has a canonical source. Get them from the California Courts self-help
site (courts.ca.gov) — the mandatory-forms page.
