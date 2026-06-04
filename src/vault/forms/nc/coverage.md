# AOC-CV-303 coverage map — intake → form (North Carolina)

How completely the current Vault intake fills the North Carolina **Complaint for
Domestic Violence Protective Order** (AOC-CV-303, G.S. 50B-1 et seq., Rev. 12/25).

Audit artifact for legal review. **An attorney (Pranav) must confirm the
`needs legal review` rows** (the relationship mapping and every relief box).
Unflagged != signed off.

Legend: ✅ mapped · 🟡 partial · ❌ not collected · ⚖️ needs legal review

> The NC intake section fills the NC-specific items end to end. The form is
> **alive**: intake → jurisdiction-aware questions → filled complaint.

## Item-by-item

| Item | Field | Intake source | State |
|---|---|---|---|
| caption | County / Plaintiff / Defendant (+ address) | `nc.county` / `petitioner.legal_name` / `respondent.legal_name` / `.last_known_address` | ✅ |
| interpreter | Interpreter / language | `petitioner.interpreter_language` | ✅ |
| 1, 2 | NC county / acts in NC | `nc.county` / fixed | ✅ |
| 3 | Relationship (50B basis) | `relationship.type` | ✅⚖️ |
| 4 | Other court proceeding | `prior_orders.exists` | 🟡 PO existence only — **NG1** |
| 5 | Abuse statement | `incidents[].narrative` | ✅ |
| 6, 9 | Child abuse / custody-risk statements | — | ❌ **NG2** |
| 7 | Danger of immediate injury | fixed (asserted) | ✅ |
| 8 | Minor children (custody) | `protected_persons.children[]` | 🟡 names; sex/DOB + AOC-CV-609 per child — **NG2** |
| 10 | Firearms / ammunition / permits | `firearm.respondent_has_access` / `.types[]` / `.locations[]` | ✅ |
| 11 | Used/threatened deadly weapon | `incidents[].weapon_involved` | ✅ |
| 12 | Defendant threatened suicide | — | ❌ **NG3** |
| relief 1-17 | Relief requested (+ residence address, stay-away places, vehicle, other) | `nc.relief` (+ `nc.residence_address`, `nc.stay_away_places`, `nc.vehicle`, `nc.other_relief`) | ✅⚖️ |
| signature | Plaintiff signature | `petitioner.legal_name` | ✅ |

## Gaps — status

- **NG1** — item 4 specifics (county/state/date/kind of other proceeding).
- **NG2** — child-specific statements (items 6, 9), per-child sex/DOB, and the
  AOC-CV-609 minor-child affidavit (separate form per child).
- **NG3** — item 12 (defendant's suicide threats).

**For Pranav:** confirm the `⚖️` rows — the 50B relationship mapping and every
relief box (1-17). The wiring is done.
