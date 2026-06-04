# NH protective-order forms

Blank, official New Hampshire Judicial Branch / Circuit Court forms for the
domestic-violence petition flow. Public documents. **Blank templates only — never
commit a form filled with a survivor's information.**

| Form | Title | Status |
|---|---|---|
| NHJB-2050-DF | Domestic Violence Petition (RSA 173-B) | mapped (`form.py`) |
| NHJB-2660-FP | UCCJEA Affidavit | not mapped — required when minor children in common |

## Notes

- NHJB-2050-DF (rev. 03/15/2024, RSA 173-B) covers the parties (a plaintiff
  demographic block — sex / race / ethnicity — and a defendant identity block),
  the relationship basis, other pending court actions, residence, the statement
  of facts, the financial-losses block, and the item-1 through item-15 relief
  list (protective orders 1-7 + additional orders 8-15). NH's relief list is its
  own, distinct from the other states'. See `coverage.md`.
- **No respondent physical-description block and no respondent-vehicle block:**
  the form has neither, so **NH is carved out of `PHYSICAL_DESCRIPTION_STATES` and
  `VEHICLE_DESCRIPTION_STATES`** in `vault.intake` (with comments) — the survivor
  is never asked the sheriff-service height/weight/vehicle questions the form has
  nowhere to print. Item 11's vehicle is the *plaintiff's* vehicle (a relief
  detail), not a respondent identifier.
- **No interpreter / disability field:** the form has neither, so NH is not in
  those gates.
- **No petitioner address:** the petition prints only the defendant's street
  address; the plaintiff's address is never printed on it, so intake collects no
  petitioner address for this form and none is mapped.
- **No SSN gate:** item 8 requests child support, but the form has no plaintiff
  SSN field, so NH is not added to the SSN-for-support gate.
- **In-person signature:** the petition must be signed at court and is not
  accepted by fax, e-mail, or U.S. mail.
- Source: courts.nh.gov self-help forms (NHJB-2050-DF).
