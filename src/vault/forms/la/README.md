# LA protective-order forms

Blank, official Louisiana Uniform Abuse Prevention Order forms for the
protection-from-abuse flow. Public documents. **Blank templates only — never
commit a form filled with a survivor's information.**

| Form | Title | Status |
|---|---|---|
| LPOR B | Petition for Protection from Abuse (La. R.S. 46:2131 et seq.) | mapped (`form.py`) |
| Confidential Address Form | §2a confidential address (La. R.S. 46:2134(B)) | not mapped — confidential-address election is recorded; clerk/advocate files it |
| LPOR B-R | Petition filed by the defendant-in-reconvention in a pending action | not mapped — alternate petition, attorney-routed |

## Notes

- LPOR B (v.15.1, La. R.S. 46:2131 et seq. / 46:2151) covers the caption, the §1
  protected persons, the §2 confidential-address election, the §3
  interpreter/criminal-history requests, the §4 defendant address, the §5 venue
  basis, the §6 relationship basis, the §8 abuse manner and danger indicators, the
  §8c narrative, the §9 ex parte TRO relief (items a-m), and the §10 other
  (rule-to-show-cause) requests. LA's lists are their own. See `coverage.md`.
- **No respondent physical-description block, no respondent vehicle block — carve-
  outs:** LPOR B has neither (¶4 is just the defendant's address/parish), so LA is
  removed from **both** `PHYSICAL_DESCRIPTION_STATES` and
  `VEHICLE_DESCRIPTION_STATES` (see the intake comments), like the OK / TN / NH /
  KY carve-outs.
- **Interpreter field:** §3a is a fillable interpreter request, so LA IS added to
  the interpreter gate (`petitioner.interpreter_language`). LPOR B has no
  disability-accommodation field, so LA is not in the disability gate.
- **No minor-self-filing gate:** LA is not in `MINOR_FILING_STATES`; minors appear
  as protected persons (§1b) or via the "Parent/Guardian if defendant is a minor"
  caption line, not the shared minor-self-filing path.
- **No SSN gate:** §10 requests child / spousal support, but LPOR B has no
  petitioner SSN field, so LA is not added to the SSN-for-support gate.
- **Confidential address:** §2a is a real mechanism — "Petitioner requests that
  his/her address … remain confidential … pursuant to La. R.S. 46:2134(B)" (a
  separate Confidential Address Form). Intake only ever holds a safe mailing
  address, so `address_confidential` is derived `"checked"`, the petitioner address
  maps to the safe mailing address, and both are flagged `needs_legal_review`.
- **Court of filing:** the district / city court for the petitioner's parish;
  `la.parish` records which.
- Source: Louisiana Protective Order Registry / LASC Uniform Abuse Prevention Order
  forms (LPOR B).
