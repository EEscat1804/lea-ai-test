# OR protective-order forms

Blank, official Oregon Judicial Department (OJD) forms for the Family Abuse
Prevention Act restraining-order flow. Public documents. **Blank templates only —
never commit a form filled with a survivor's information.**

| Form | Title | Status |
|---|---|---|
| (no printed number) | Petition for Restraining Order to Prevent Abuse (FAPA) | mapped (`form.py`) |

## Notes

- **Package name.** This directory is `oregon`, not `or`, because **`or` is a
  Python keyword** and cannot be an importable module name (`from vault.forms
  import or` is a syntax error). The jurisdiction code is still `"OR"` everywhere
  it matters (`SUPPORTED_JURISDICTIONS`, the `_ASSEMBLERS` key, `JURISDICTION`).
  **Indiana (`IN`) will need the same treatment** when it lands — `in` is also a
  keyword.
- **Petition for Restraining Order to Prevent Abuse** (Family Abuse Prevention
  Act, ORS 107.700; Circuit Court; OJD Official, rev. Jan 2026) covers the county,
  the parties and ages, the §3 relationship basis, the §4 abuse grounds (within
  the past 180 days), the §5 incident narrative, an imminent-danger declaration
  (§6), firearms (§7), existing orders (§8), and discretionary relief — move-out
  (§10), emergency money (§11), companion animals (§12), and custody assistance
  (§19). OR's abuse and relief lists are their own. See `coverage.md`.
- **No printed form number.** The footer reads only "FAPA Restraining Order –
  Petition / OJD Official (Jan 2026)". `FORM_ID` is descriptive
  (`"Petition for Restraining Order to Prevent Abuse"`) and flagged (ORG1) — no
  number was fabricated.
- **No respondent description or vehicle block.** The FAPA petition asks the
  respondent's name, age, and last-known residence only. OR is therefore **not**
  in `PHYSICAL_DESCRIPTION_STATES` or `VEHICLE_DESCRIPTION_STATES`. (The
  unconditional employer gate still runs, as for every state.)
- **Interpreter gate applies.** The caption has an interpreter request
  (Spanish / ASL / other), so OR is in the shared interpreter set and
  `petitioner.interpreter_language` is collected before the OR block.
- **§4 abuse + relief are checklists** modeled as multi-selects
  (`or.abuse_types`, `or.relief`) with sub-detail follow-ups: the move-out basis
  (§10), the emergency-money amount + reason (§11), and the animals to award
  (§12).
- **No SSN gate.** OR is not in the SSN-for-support set `{CA, FL, TX}`. The FAPA
  petition's emergency-money request is a one-time payment, not ongoing support,
  and does not ask for the petitioner's SSN.
- **Safe contact by design.** The form's own notice tells the petitioner to use a
  "contact address" / "contact phone" instead of a residential one, and §21 files
  a Confidential Information Form; intake holds only safe values, so
  `address_confidential` and `cif_petitioner` are asserted.
- **UCCJEA / joint-children section (§§13-20) is largely a gap.** The current
  intake does not collect the five-year residence history, parentage, or prior
  custody cases; those rows are flagged ORG10-ORG12. The relationship basis,
  abuse grounds, imminent-danger declaration, and every relief box are
  attorney-confirmed (`needs_legal_review`). Source: courts.oregon.gov (FAPA
  restraining order forms).
