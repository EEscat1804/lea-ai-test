# CAO DV 1-1 coverage map — intake → form (Idaho)

How completely the current Vault intake fills the Idaho **Sworn Petition for
Protection Order** (CAO DV 1-1, I.C. § 39-6304 / § 18-7907, 07/01/2019).

Audit artifact for legal review. **An attorney (Pranav) must confirm the
`needs legal review` rows** (the relationship basis, the petition type, the
confidential-address election, the §7a personal-conduct order, and every §7 relief
box). Unflagged != signed off.

Legend: ✅ mapped · 🟡 partial · ❌ not collected · ⚖️ needs legal review

> The ID intake (Tier-1 core + the shared employer gate + the ID block) fills the
> ID-specific items end to end. The form is **alive**: intake → jurisdiction-aware
> questions → filled petition.

## Item-by-item

| Section | Field | Intake source | State |
|---|---|---|---|
| caption | County / case number | `id.county` / clerk | ✅ (case no. — IDG1) |
| header | Address withheld | derived | ✅⚖️ |
| parties | Petitioner / address / phone / respondent / employer | `petitioner.legal_name` / `.safe_mailing_address` / `.safe_phone` / `respondent.legal_name` / `.employer_name` / `.employer_address` | ✅⚖️ (address) |
| 1/4 | Protected minor children | `protected_persons.children[]` | 🟡 names — IDG2 |
| 2 | Relationship basis | `id.relationship_basis` | ✅⚖️ |
| 6 | Petition type (DV / stalking / phone threats / protected-class) | `id.petition_type` | ✅⚖️ |
| 6/narrative | Recent acts (+ date / location / witnesses / weapon / injury) | `incidents[].narrative` / `.date` / `.location` / `.witnesses_present` / `.weapon_involved` / `.injury` | ✅ |
| 5B | Past acts | — | ❌ IDG3 |
| 5 | Other court cases / prior orders | `prior_orders.exists` / `id.other_cases` | 🟡 existence + free text — IDG4 |
| 7a | Personal Conduct Order | derived | ✅⚖️ |
| 7 | Relief (stay-away / move-out / custody / counseling / other) | `id.relief` | ✅⚖️ |
| 7b | Stay-away places (+ distance) | `id.stay_away_places` / `id.stay_away_feet` | ✅ |
| 7c/7e/7f | Move-out address / counseling / other detail | `id.move_out_address` / `id.counseling_detail` / `id.relief_other_detail` | ✅ |
| verification | Petitioner signature | `petitioner.legal_name` | ✅ |

## Gaps — status

- **IDG1** — the case number is assigned by the clerk at filing.
- **IDG2** — the §4 children table wants per-child DOB / sex / relationship /
  6-month residence; only names are collected.
- **IDG3** — the §5 past-acts narrative is not collected separately from the
  most-recent statement.
- **IDG4** — the §5 other-cases / prior-order detail (county / date / parties);
  only existence + a free-text note are collected.

**For Pranav:** confirm the `⚖️` rows — the §2 relationship basis, the §6 petition
type, the confidential-address election, the §7a personal-conduct order, and every
§7 relief box. The wiring is done.
