# PFA coverage map — intake → form (Pennsylvania)

How completely the current Vault intake fills the Pennsylvania **Petition for
Protection from Abuse** (23 Pa.C.S. ch. 61).

Audit artifact for legal review. **An attorney (Pranav) must confirm the
`needs legal review` rows** (the relationship mapping and every item A-P relief
box). Unflagged != signed off.

Legend: ✅ mapped · 🟡 partial · ❌ not collected · ⚖️ needs legal review

> The PA intake section fills the PA-specific items end to end. The form is
> **alive**: intake → jurisdiction-aware questions → filled PFA petition.

## Item-by-item

| Item | Field | Intake source | State |
|---|---|---|---|
| 1 | Plaintiff name / DOB / address | `petitioner.legal_name` / `.dob` / `.safe_mailing_address` | ✅ |
| 2 | Defendant name / address | `respondent.legal_name` / `.last_known_address` | ✅ |
| 2 | Defendant identifiers: DOB/sex/race/height/weight/eyes/hair | `respondent.dob` / `.gender` / `.race` / `.height` / `.weight` / `.eye_color` / `.hair_color` | ✅ |
| 2 | Defendant SSN / driver's license | — | ❌ **PG1** |
| 2 | Defendant place of employment | `respondent.employer_name` | ✅ |
| 2 | Caution: weapon involved | `incidents[].weapon_involved` | ✅ |
| 3 | Filing on behalf of | fixed: myself | ✅ |
| 4, 8 | Persons protected / minor children | `protected_persons.children[]` | 🟡 names; ages/addresses — **PG2** |
| 5 | Relationship | `relationship.type` | ✅⚖️ |
| 6 | Prior court actions | `prior_orders.exists` | 🟡 PO existence only — **PG3** |
| 7 | Defendant criminal action | `respondent.prior_criminal_history` | 🟡 (probation/CPS not collected) |
| 11 | Most recent incident (date/place/description) | `incidents[].date` / `.location` / `.narrative` | ✅ |
| 12 | Prior acts of abuse | — | ❌ **PG4** |
| 13a/b | Weapon used / owns firearms | `incidents[].weapon_involved` / `firearm.respondent_has_access` | ✅ |
| 14 | Law-enforcement agency to serve | — | ❌ **PG5** |
| 15 | Immediate and present danger | fixed (asserted) | ✅ |
| A-P | Relief requested (+ evict residence, custody restrictions, financial losses, other) | `pa.relief` (+ `pa.evict_residence`, `pa.custody_restrictions`, `pa.financial_losses`, `pa.other_relief`) | ✅⚖️ |
| Verification | Plaintiff signature | `petitioner.legal_name` | ✅ |

## Gaps — status

- **PG1** — defendant SSN / driver's license (rarely known).
- **PG2** — per-child ages, addresses, custody detail (items 8-10).
- **PG3** — item 6 specifics (which action, when/where filed).
- **PG4** — item 12 prior-incident narrative (pattern frequency collected, not
  a separate statement).
- **PG5** — item 14 law-enforcement agency to receive the order.
- **Attachment A** — firearms/weapons/ammunition inventory (separate sheet).

**For Pranav:** confirm the `⚖️` rows — the relationship mapping and every item
A-P relief box. The wiring is done.
