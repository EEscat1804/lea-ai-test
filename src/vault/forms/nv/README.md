# NV protective-order forms

Blank, official Nevada Supreme Court self-help forms for the domestic-violence
protection order flow. Public documents. **Blank templates only — never commit a
form filled with a survivor's information.**

| Form | Title | Status |
|---|---|---|
| Application for Protection Order – DV | Application for Protection Order Against Domestic Violence (© 2022) | mapped (`form.py`) |
| UCCJEA Declaration | Child custody jurisdiction declaration | not mapped — required when temporary custody sought |

## Notes

- The application (© 2022 Nevada Supreme Court, NRS 33) covers the court/parties,
  an interpreter request, who needs protection, the abuse grounds, the
  relationship basis, other court cases, firearms, the most-recent event, the
  item-10 temporary-protections list, the page-7 custody/pets requests, and the
  item-11 order length (45-day vs. extended) with its extended-relief list. NV's
  relief list is its own, distinct from the other states'. See `coverage.md`.
- **No printed form number:** the document carries only its title and "© 2022
  Nevada Supreme Court", so `FORM_ID` is descriptive and the missing number is
  flagged as gap **NVG1** — we never fabricate one.
- **Interpreter:** item 1 has a foreign-language interpreter request, so **NV is
  added to the interpreter gate** and `petitioner.interpreter_language` maps to it.
- **Address confidentiality:** item 10 warns the adverse party receives a copy and
  instructs the applicant not to list confidential addresses ("is your address
  confidential? Yes — leave address blank"). Intake only ever holds a safe mailing
  address, so `address_confidential` defaults on and the home address is never
  written.
- **No physical-description / vehicle block:** the form has neither, so NV is in
  neither shared gate.
- **No SSN gate:** the item-11 financial relief (rent/support/child support) is
  requested by checkbox, but the SSN goes on a *separate* financial form, not this
  application, so NV is not added to the SSN-for-support gate.
- **Custody:** temporary custody also requires a **UCCJEA Declaration**, not
  assembled here.
- **Verified under penalty of perjury** (NV law) — signed at filing.
- Source: selfhelp.nvcourts.gov protection-order forms.
