# OH protective-order forms

Blank, official Ohio Supreme Court forms for the domestic-violence civil
protection order flow. Public documents. **Blank templates only — never commit a
form filled with a survivor's information.**

| Form | Title | Status |
|---|---|---|
| 10.01-D | Petition for Domestic Violence Civil Protection Order | mapped (`form.py`) |
| 10.01-F | Information for Parenting Proceeding | not mapped — required if custody/parenting-time relief sought |

## Notes

- 10.01-D (R.C. 3113.31) covers the parties, an interpreter request, the ex parte
  request, who needs protection, the relationship basis, other protected
  household members, the abuse narrative, optional aggravating factors (item 7),
  and the item-9 (**a-n**) relief list. OH's relief list is its own, distinct
  from the other states'. See `coverage.md`.
- **Public record / address:** the form is a public record and instructs the
  petitioner to use a safe mailing address. Intake only ever holds a safe mailing
  address, so the home address is never collected.
- **Interpreter:** the form has a foreign-language / ASL interpreter request
  (item 1); OH is in the interpreter gate and `petitioner.interpreter_language`
  maps to it.
- **Custody/parenting-time relief** (item 9 e/f) also requires **Form 10.01-F**
  (Information for Parenting Proceeding), not mapped here.
- OH is in the doc's physical-description and vehicle sets, so intake collects
  respondent physical/vehicle details, but Form 10.01-D has no section for them,
  so they are not mapped here. Source: supremecourt.ohio.gov forms.
