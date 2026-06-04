# DE protective-order forms

Blank, official Delaware Family Court forms for the PFA (Protection From Abuse)
flow. Public documents. **Blank templates only — never commit a form filled with
a survivor's information.**

| Form | Title | Status |
|---|---|---|
| Form 450 | Petition for Order of Protection from Abuse | mapped (`form.py`) |
| Form 540 | Court Addendum (extra space for the abuse statement) | not mapped (overflow only) |
| Form 346 | Custody Separate Statement | not mapped — required when custody relief is sought |

## Notes

- Form 450 (10 Del. C. § 1041 et seq.) covers the parties, a confidential-address
  request, the § 1041 relationship basis, an a-k acts-of-abuse checklist, the
  court's jurisdiction over a non-resident respondent, firearms, and a
  PROTECTIVE + ANCILLARY relief list. DE's abuse and relief lists are its own.
  See `coverage.md`.
- **Three counties:** New Castle / Kent / Sussex (`de.county`).
- **Confidential address by design:** the form says "DO NOT LIST ADDRESS" when a
  confidential address is requested. Intake only ever holds a safe mailing
  address, and the item-1 confidential boxes default on.
- **Relationship basis is attorney-confirmed** (`relationship_basis`,
  `needs_legal_review`) — DE's "substantive dating relationship" and "family
  member" categories in particular.
- **Duration:** protective relief is up to two years by default; longer (up to a
  permanent order, § 1045(f)) requires the aggravating factors (1-6).
- **Custody:** checking the custody relief also requires **Form 346**.
- The first two pages of the official PDF are a resources sheet kept by the
  petitioner and not filed. Source: courts.delaware.gov/family/pfa.
