# NM protective-order forms

Blank, official New Mexico court forms for the Order of Protection flow. Public
documents. **Blank templates only — never commit a form filled with a survivor's
information.**

| Form | Title | Status |
|---|---|---|
| 4-961 | Petition for Order of Protection from Domestic Abuse | mapped (`form.py`) |
| 4-961A | Petitioner's name (sealed) | not mapped — address protection |
| 4-961B | Petitioner's address (sealed) | not mapped — address protection |

## Notes

- Form 4-961 (Family Violence Protection Act, §§ 40-13-1 to 40-13-8 NMSA 1978)
  covers the court-assistance request, the relationship basis, the respondent's
  firearms, children (UCCJEA), other cases, the domestic-abuse statement, the
  item-6 (**A-J**) requests to the court, and the respondent's location. NM's
  relief list is its own, distinct from the other states'. See `coverage.md`.
- **Address protection:** the petitioner can seal their name/address via Forms
  4-961A/4-961B. Intake only ever holds a safe mailing address, and the
  confidential-address request defaults on.
- **Interpreter:** item 1 has an interpreter request; NM is in the interpreter
  gate and `petitioner.interpreter_language` maps to it.
- **No filing fee:** § 40-13-3.1(A)(4) — a domestic-abuse victim is not charged
  for filing/issuance/service of a petition for an order of protection.
- NM is in none of the doc's physical-description / vehicle / minor-filing sets,
  so the petition takes a clean intake path (no respondent physical-description
  block on this form). Source: nmcourts.gov / NMRA.
