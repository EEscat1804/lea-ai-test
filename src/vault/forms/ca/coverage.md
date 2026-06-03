# DV-100 coverage map — intake → form

How completely the current Vault intake graph fills California form **DV-100**
(_Request for Domestic Violence Restraining Order_, Rev. Jan 1 2025).

This is the audit artifact for legal review. **An attorney (Pranav / managing
attorney) must confirm the `needs legal review` rows before any assembled
DV-100 is treated as correct.** Unflagged rows are mechanically obvious, not
legally signed off — ABA-512-style verification still applies.

Legend: ✅ mapped from intake · 🟡 partial · ❌ not collected yet · ⚖️ needs legal review

## Item-by-item

| Item | Field | Intake source | State |
|---|---|---|---|
| 1a | Petitioner name | `petitioner.legal_name` | ✅ |
| 1b | Petitioner age | derived from `petitioner.dob` | ✅ |
| 1c | Address for court papers | `petitioner.safe_mailing_address` | 🟡⚖️ one free-text string; form needs Address/City/State/Zip split |
| 1d | Phone / email | `petitioner.safe_phone`, `petitioner.safe_email` | ✅ |
| 2a | Respondent name | `respondent.legal_name` | ✅ |
| 2b–2e | Respondent age / DOB / gender / race | `respondent.age` / `.dob` / `.gender` / `.race` | ✅ |
| 3a | Child together | `relationship.children_in_common` | ✅⚖️ |
| 3b/3d/3e | Married / dating / engaged | `relationship.type` enum | ✅⚖️ |
| 3c | *Used to be* married | `relationship.type` + `relationship.marriage_intact` | ✅⚖️ |
| 3g | Live / used to live together | `relationship.live_together_now` / `...past` | ✅⚖️ |
| 4a | Other restraining orders | `prior_orders.exists` | 🟡 existence only, no order/expiry dates |
| 4b | Other court case | — | ❌ **gap G4** |
| 5a–5g | Most recent abuse | `incidents[].*` | ✅ |
| 6a–7g | 2nd / 3rd abuse incidents | `incident_2.*`, `incident_3.*` (optional) | ✅ |
| 8 | Other protected people (+ why) | `protected_persons.children[]`, `protected_persons.why` | 🟡 names + why; per-person age/relationship/lives-with stay optional |
| 9 | Firearms | `firearm.respondent_has_access` / `types[]` / `locations[]` | ✅ |
| 10, 11 | No-abuse / no-contact | `selected_reliefs_intents` | ✅⚖️ |
| 12 | Stay-away (+ places, distance) | `selected_reliefs_intents`, `relief.stay_away_places`, `relief.stay_away_distance_yards` | ✅⚖️ |
| 13 | Move-out (+ address) | `selected_reliefs_intents`, `relief.move_out_address` | ✅⚖️ |
| 16 | Protect animals (+ list) | `selected_reliefs_intents`, `relief.animals[]` | ✅⚖️ |
| 17 | Control of property (+ describe/why) | `selected_reliefs_intents`, `relief.property_describe`, `relief.property_why` | ✅⚖️ |
| 18, 19 | No insurance changes / record comms | `selected_reliefs_intents` | ✅⚖️ |
| 22, 23 | Pay debts / pay expenses (+ itemized) | `selected_reliefs_intents`, `relief.debts`, `relief.expenses` | ✅⚖️ |
| 24 | Child support | `selected_reliefs_intents` | ✅⚖️ (gates `petitioner.ssn`) |
| 25 | Spousal support | `selected_reliefs_intents` | ✅⚖️ |
| 26, 27 | Lawyer's fees / batterer program | `selected_reliefs_intents` | ✅⚖️ |
| 28 | Transfer wireless phone (+ numbers) | `selected_reliefs_intents`, `relief.transfer_phone_numbers` | ✅⚖️ |
| 20, 21 | Property restraint / extend service deadline | — | ❌ situational, not in request set (G20-21) |
| 29–31 | No firearms / body armor / cannot look for protected people | — automatic if granted — | n/a (not requested) |
| 33 | Signature block (printed name) | `petitioner.legal_name` | ✅ (date + signature applied at filing) |

## Gaps — status

The DV-100 now fills end to end from intake. Closed this round:

- **G10 — orders requested (10–28). ✅** `selected_reliefs_intents` + follow-ups.
- **G2 — respondent identity (2b–2e). ✅** `respondent.age/.dob/.gender/.race`.
- **G3 — current vs former marriage (3c). ✅** `relationship.marriage_intact`.
- **G6 — additional incidents (6, 7). ✅** optional `incident_2.*` / `incident_3.*`.
- **G17 / G22 / G28 — order details. ✅** property describe/why, itemized
  debts/expenses, phone numbers to transfer.

Remaining (lower priority, mostly optional on the form):

- **G8 — protected-people per-person detail.** Names + a "why" are collected;
  per-person age/relationship/lives-with are still optional. Close if legal wants
  them structured.
- **G4 — other court case (4b).** Not collected (custody/divorce/criminal case
  cross-reference).
- **G20-21 — property restraint / extend-service-deadline.** Situational; not in
  the requested-orders set.
- **1c address split.** One free-text address; lea-be-core (or a parse step)
  must split into Address/City/State/Zip.

**For Pranav:** confirm the `⚖️` rows — every order-box and relationship-box
mapping. That's the legal sign-off; the wiring is done.

## Notes for legal review

- The `value: "[FACT NEEDED]"` marker means a *required* field had no answer —
  it blocks filing and is listed in the assembler's `gaps`. Nothing is guessed.
- `review_items` in the assembler output lists every ⚖️ row above, so the
  reviewer sees exactly what to confirm.
- Respondent physical-description fields collected at intake are **not** DV-100
  fields — verify they route to CLETS-001 before wiring that form.
