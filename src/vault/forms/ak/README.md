# AK protective-order forms

Blank, official Alaska Court System forms for the DV protective-order flow.
Public documents. **Blank templates only — never commit a form filled with a
survivor's information.**

| Form | Title | Status |
|---|---|---|
| DV-100 | Petition for Domestic Violence Protective Order (One Petitioner) | mapped (`form.py`) |
| DV-127 | Confidential Law Enforcement Information Sheet | not mapped — required companion |
| DV-128 | Confidential Contact Information Sheet | not mapped — petitioner contact protection |
| DV-190 | Evidence cover sheet (telephonic/Zoom hearing) | not mapped |
| DR-305 | Child Support Guidelines Affidavit | not mapped — required if child support sought |

## Notes

- DV-100 (AS 18.66.100-.990, Civil Rule 65.1) covers the parties, the order type
  (20-day ex parte and/or long-term one-year), the relationship, the abuse
  description, short-term protections (§5), long-term protections (§6 — cannot be
  in the 20-day order), children/custody/support (§7), other cases (§8), and
  law-enforcement assistance (§9). AK's protection lists are its own. See
  `coverage.md`.
- **Form-number coincidence:** Alaska's "DV-100" is a different form from
  California's "DV-100" — they are disambiguated by jurisdiction.
- **Contact protection:** the petitioner's contact info goes on the confidential
  **DV-128** sheet, and §5(c) offers address confidentiality. Intake only ever
  holds a safe mailing address; both confidential options default on.
- **Companion forms:** DV-127 must be filed with the petition; DR-305 is needed
  when child support is requested; DV-190 for telephonic-hearing evidence.
- AK is in none of the doc's physical-description / vehicle / minor-filing sets,
  so the petition takes a clean intake path (no respondent physical-description
  block). Source: courts.alaska.gov / ak-courts.info forms.
