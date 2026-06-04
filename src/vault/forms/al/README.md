# AL protective-order forms

Blank, official Alabama Unified Judicial System forms for the Protection from
Abuse flow. Public documents. **Blank templates only — never commit a form
filled with a survivor's information.**

| Form | Title | Status |
|---|---|---|
| C-2 | Petition for Protection from Abuse | mapped (`form.py`) |
| CS-41 | Child Support Obligation Income Statement/Affidavit | not mapped — required if child support sought |
| CS-42 | Child Support Guidelines | not mapped — required if child support sought |
| CS-47 | Child Support Information Sheet | not mapped — required if child support sought |

## Notes

- C-2 (Ala. Code § 30-5-1 et seq.) covers eligibility (§I), the relationship
  basis, the acts-of-abuse checklist (§II), the abuse narrative (§III), prior
  orders (§IV), children (§V), residence ownership (§VI), the **ex parte** relief
  list (§VII, items 1-10), and the **final-hearing** relief list (§VIII, items
  11-19). AL's acts and relief lists are its own, distinct from the other
  states'. See `coverage.md`.
- **Address confidentiality is statutory:** Ala. Code § 30-5-5(f)(1) keeps the
  plaintiff's home/business address and phone off public court documents. Intake
  only ever holds a safe mailing address; the confidential note is asserted.
- **Eligibility (§I)** — the adult-victim box is checked when the petitioner is
  18+. The minor/guardian/emancipated boxes are a legal determination, flagged.
- **Relationship (§I.1-6)** — only ONE box may be checked; mapped from
  `relationship.type` and flagged `needs_legal_review`.
- Respondent **SSN last-4** is never collected (sensitive). Child support
  requires the CS-41/42/47 companion forms.
- AL is in the doc's minor-filing set (the §I minor/emancipated eligibility), so
  a minor petitioner takes the minor-filing path. Source: alacourt.gov forms.
