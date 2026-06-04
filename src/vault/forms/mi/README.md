# MI protective-order forms

Blank, official Michigan SCAO forms for the personal-protection-order (PPO) flow.
Public documents. **Blank templates only — never commit a form filled with a
survivor's information.**

| Form | Title | Status |
|---|---|---|
| CC 375 | Petition for Personal Protection Order (Domestic Relationship) | mapped (`form.py`) |

## Notes

- CC 375 (Rev. 3/23, MCL 600.2950 / 600.2950a, MCR 3.703) covers the parties, the
  §1 domestic relationship basis, the §2 firearm-in-employment note, the §3
  other-actions disclosure, the §4 narrative, the §5 relief checklist (items a-l
  with the §5e stalking sub-acts and §5j animal sub-acts), and the §6 ex parte
  election. MI's relationship and relief lists are their own. See `coverage.md`.
- **No respondent physical-description block, no vehicle block:** CC 375 prints only
  the parties' names / addresses / ages, so MI is in **neither**
  `PHYSICAL_DESCRIPTION_STATES` nor `VEHICLE_DESCRIPTION_STATES` and the survivor is
  never asked for height/weight/vehicle. Only the unconditional shared employer gate
  precedes the MI block.
- **No minor-self-filing gate:** MI is **not** in `MINOR_FILING_STATES`. A minor MI
  petitioner files through a "next friend" (§7) — a distinct mechanism, not the
  shared minor-self-filing path; the next-friend block is left for the
  advocate/attorney (MIG5).
- **No interpreter / disability field, no SSN gate:** CC 375 has none of these
  fields and requests no support, so MI is in none of those gates.
- **Respondent firearm-in-employment (§2):** MI is not in the {FL, NY, TX}
  law-enforcement gate, so `_mi_step` asks `mi.respondent_carries_firearm`
  (yes / no / unknown) directly.
- **Confidential address:** CC 375 prints the petitioner's contact address and is
  served on the respondent; there is **no** confidential-address affidavit on the
  form (Michigan handles address confidentiality through separate MCR procedures).
  The petitioner address maps to the safe mailing address, flagged
  `needs_legal_review`, with the confidentiality gap noted (MIG3).
- **Court of filing:** the Circuit Court for the petitioner's county; `mi.county`
  records which (the judicial circuit follows from the county).
- Source: courts.michigan.gov / SCAO Form CC 375.
