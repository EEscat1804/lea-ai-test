# ID protective-order forms

Blank, official Idaho Court Assistance Office forms for the protection-order flow.
Public documents. **Blank templates only — never commit a form filled with a
survivor's information.**

| Form | Title | Status |
|---|---|---|
| CAO DV 1-1 | Sworn Petition for Protection Order (I.C. § 39-6304 / § 18-7907) | mapped (`form.py`) |

## Notes

- **Package name caveat:** the directory is `idaho`, not `id`, because the
  two-letter code "ID" shadows the Python builtin `id` (which `ruff`'s
  flake8-builtins rules flag on import). The jurisdiction code stays `"ID"`. This
  mirrors the `oregon` keyword-collision precedent.
- CAO DV 1-1 (07/01/2019) covers the parties, the §1 protected persons, the §2
  relationship basis, the §3 residence, the §4 children, the §5 other court cases,
  the §6 petition type (domestic violence / stalking / telephone threats /
  protected-class threats), the narrative, and the §7 relief
  (personal-conduct / stay-away / move-out / custody / counseling / other). ID's
  lists are their own. See `coverage.md`.
- **No respondent physical-description block, no respondent vehicle block —
  carve-outs:** CAO DV 1-1 has neither, so ID is removed from **both**
  `PHYSICAL_DESCRIPTION_STATES` and `VEHICLE_DESCRIPTION_STATES` (see the intake
  comments), like the NH / OK / TN / LA carve-outs. Only the unconditional shared
  employer gate precedes the ID block.
- **No minor-self-filing gate:** ID is not in `MINOR_FILING_STATES`; a minor
  appears as a protected person (§1), not via the shared minor-self-filing path.
- **No interpreter / disability field:** CAO DV 1-1 has only a disability-
  coordinator referral notice, not a fillable field, so ID is in neither gate.
- **No SSN gate:** the §7 relief has no support request and the form has no SSN
  field, so ID is not in the SSN-for-support gate.
- **Confidential address:** the form's header checkbox ("No address, email and
  telephone are given because I do not want my information on this petition"),
  echoed in §7b, is a real mechanism — so `address_confidential` is derived
  `"checked"`, the petitioner address maps to the safe mailing address, and both
  are flagged `needs_legal_review`.
- **Petition type:** ID is a combined DV / stalking / threats petition; §6 records
  which statute(s) apply (I.C. § 39-6304 vs § 18-7907).
- **Court of filing:** the District Court, Magistrate Division, for the
  petitioner's county; `id.county` records which.
- Source: courtselfhelp.idaho.gov (CAO DV 1-1).
