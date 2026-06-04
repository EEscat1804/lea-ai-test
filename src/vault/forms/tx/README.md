# TX protective-order forms

Blank, official Texas protective-order forms. Public documents. **Blank
templates only — never commit a form filled with a survivor's information.**

| Form | Title | Status |
|---|---|---|
| Application for Protective Order | Tex. Fam. Code / Penal Code Title 5-6 | mapped (`form.py`) |
| Affidavit / Declaration | sworn statement (part of the packet) | mapped (within `form.py`) |

## Notes

- The TX packet is large (14 pages): the **Application** (parties, reasons,
  relationship, children, criminal history, the terms-and-conditions in item
  8 a-n, property/support/children orders, ex parte, confidentiality) plus a
  sworn **Affidavit** (notarized, confidential DOB/address) **or Declaration**
  (public, no notary). The Vault maps the Application + the Affidavit/Declaration
  statement fields.
- The TX intake section fills the TX-specific items — TX's terms list (item 8
  a-n) is its own, distinct from CA's and WA's. See `coverage.md`.
- "Keep information confidential" (item 14) defaults to a recommended **yes** in
  intake — survivors usually want their address off the public order.
- Drop the official blank fillable PDFs here for lea-be-core's renderer. Source:
  txcourts.gov / TexasLawHelp forms.
