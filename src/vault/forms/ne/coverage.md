# Form DC 19:8 coverage map — intake → form (Nebraska)

How completely the current Vault intake fills the Nebraska **Petition and
Affidavit to Obtain Domestic Abuse Protection Order** (Form DC 19:8, Rev.
09/2025, Neb. Rev. Stat. §§ 26-101 et seq.), plus the shared DC 19:1 praecipe
respondent-service fields.

Audit artifact for legal review. **An attorney (Pranav) must confirm the
`needs legal review` rows** (the relationship basis, the filing-capacity election,
every item-7 relief box, and the SA/Harassment fallback). Unflagged != signed off.

Legend: ✅ mapped · 🟡 partial · ❌ not collected · ⚖️ needs legal review

> The NE intake (Tier-1 core + the shared interpreter/physical/vehicle gates + the
> NE block) fills the NE-specific items end to end. The form is **alive**: intake
> → jurisdiction-aware questions → filled petition.

## Item-by-item

| Section | Field | Intake source | State |
|---|---|---|---|
| caption | County / judge type / petitioner / respondent / additional petitioners | `ne.county` / `ne.judge_type` / `petitioner.legal_name` / `respondent.legal_name` / `protected_persons.children[]` | ✅ (additional 🟡 — NEG1) |
| 1 | Petitioner is 19+ / files for self / language | derived / derived / `petitioner.interpreter_language` | ✅⚖️ (variants — NEG2) |
| 2 | Contact information confidential | derived | ✅ |
| 3 | Relationship basis | `relationship.type` | ✅⚖️ |
| 4 | Respondent age / DOB / address | derived / `respondent.dob` / `respondent.last_known_address` | ✅ |
| 4 | Respondent description (sex/height/weight/eye/hair/race/marks) | `respondent.gender` / `.height` / `.weight` / `.eye_color` / `.hair_color` / `.race` / `.distinguishing_marks` | ✅ |
| 4 | Alias / phone / skin tone / DL / place of birth / other features | — | ❌ NEG3 |
| DC 19:1 | Employer / vehicle / weapon (service praecipe) | `respondent.employer_name` / `.vehicle_make_model` / `.vehicle_color` / `.vehicle_plate` / `firearm.respondent_has_access` | ✅ (workdays — NEG4) |
| 6 | Prior cases | `prior_orders.exists` / `ne.prior_cases_detail` | 🟡 existence + free text — NEG5 |
| 7 | Relief checklist | `ne.relief` | ✅⚖️ |
| 7 | Residence / stay-away / custody / pets details | `ne.residence_address` / `ne.stay_away_location` / `ne.custody_days` / `ne.pet_detail` / derived | ✅ |
| 8 | Abuse narrative (+ date) | `incidents[].narrative` / `incidents[].date` | ✅ (B/C — NEG6) |
| 9 | SA / Harassment fallback request | derived | ✅⚖️ |
| verification | Petitioner signature | `petitioner.legal_name` | ✅ |

## Gaps — status

- **NEG1** — the item-5 additional-petitioners table (age / relationship to each
  party / language); only names are collected.
- **NEG2** — the item-1 filing-capacity election is defaulted to "self as victim";
  the file-only-for-others and mixed variants are not modeled.
- **NEG3** — respondent alias / phone / skin tone / driver's license / place of
  birth / other distinguishing features (item 4).
- **NEG4** — the respondent's workdays and hours on the DC 19:1 praecipe.
- **NEG5** — the full item-6 case table (where / date / type / court / number);
  only protective-order existence + a free-text note are collected.
- **NEG6** — the item-8 B/C additional incidents (not collected separately from the
  most-recent/most-severe statement).

> The confidential DC 6:5.12 (SSN / gender / DOB) is intentionally never assembled
> — it is court-only and kept out of the public file.

**For Pranav:** confirm the `⚖️` rows — the relationship basis, the filing-capacity
election, every item-7 relief box, and the SA/Harassment fallback request. The
wiring is done.
