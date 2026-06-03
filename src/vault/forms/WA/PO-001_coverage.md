# PO 001 coverage map — intake → form (Washington)

How completely the current Vault intake fills Washington form **PO 001**
(_Petition for Protection Order_, RCW 7.105.100, Rev. 01/2026), **Domestic
Violence path (PTORPRT)**.

Audit artifact for legal review. **An attorney (Pranav) must confirm the
`needs legal review` rows** (item 1 order type, the relationship box, every
item-14 restraint box, the temporary-order/weapons/length requests). Unflagged
!= signed off.

Legend: ✅ mapped · 🟡 partial · ❌ not collected · ⚖️ needs legal review

> The WA intake section now fills the WA-specific items end to end. The form is
> **alive**: intake → jurisdiction-aware questions → filled PO 001.

## Item-by-item

| Item | Field | Intake source | State |
|---|---|---|---|
| caption | Petitioner name / DOB | `petitioner.legal_name` / `.dob` | ✅ |
| caption | Respondent name / DOB | `respondent.legal_name` / `.dob` | ✅ |
| 1 | Order type | fixed: Domestic Violence (PTORPRT) | ✅⚖️ |
| 3 | Restrained person name / age band | `respondent.legal_name` / `respondent.age_band` | ✅ |
| 4 | Protected person (me) / children | `petitioner.legal_name` / `protected_persons.children[]` | 🟡 names; per-child detail ❌ **WG2** |
| 5 | Service mail / email | `petitioner.safe_mailing_address` / `.safe_email` | ✅ |
| 6, 7 | Interpreter / accommodations | `petitioner.interpreter_language` / `.disability_accommodation` | ✅ |
| 8 | Relationship of parties | `relationship.type` | ✅⚖️ |
| 9 | Connection to WA (jurisdiction) | `wa.jurisdiction_basis` | ✅ |
| 10 | Restrained person residence | `respondent.last_known_address` | 🟡 free-text |
| 11 | Other court cases | `prior_orders.exists` | 🟡 existence only |
| 12 | Temporary (immediate) order | `wa.temporary_order` | ✅⚖️ |
| 13 | Immediate weapons surrender | `wa.weapons_surrender` | ✅⚖️ |
| 14 A–Z | **Restraints requested** | `wa.restraints` (+ `wa.stay_away_*`, `wa.belongings`, `wa.vehicle_use`, `wa.pets`) | ✅⚖️ |
| 15 | Law-enforcement help | — | ❌ **WG6b** |
| 16 | Length of order | `wa.order_length` | ✅⚖️ |
| 17 | Firearms restoration notice | `wa.firearms_restoration_notice` | ✅ |
| 18 | Most recent incident (date + statement) | `incidents[].date` / `.narrative` | ✅ |
| 19 | Past incidents | `wa.past_incidents` | ✅ |
| 20, 21, 22 | Medical / suicidal / substance abuse | — | ❌ **WG9** (optional free-text) |
| 23 | Minors needing protection (detail) | `protected_persons.children[]` | 🟡 presence only **WG2** |
| 24 | Supporting evidence types | `wa.evidence_types` | ✅ |
| 14-O / Att. E | Firearms access / types / locations | `firearm.respondent_has_access` / `.types[]` / `.locations[]` | ✅ |
| sig | Petitioner printed name | `petitioner.legal_name` | ✅ |

## Gaps — status

Closed in Phase 2: respondent identity (WG1), interpreter/accommodations (WG3),
jurisdiction basis (WG4), temporary order + weapons + length (WG5), the A–Z
restraints + details (WG6), restoration notice (WG7), past incidents (WG8),
evidence (WG10).

Remaining (lower priority / optional on the form):

- **WG6b — law-enforcement help (item 15).** Not collected; a short follow-up.
- **WG2 — per-child detail (items 4, 23).** Names collected; age/gender/race/
  lives-with/relationship per child not yet structured.
- **WG9 — items 20/21/22.** Petitioner medical, restrained-person suicidal
  behavior, substance abuse — optional free-text on the form.
- **10/11 partial.** Residence free-text vs in/out-of-WA; other-court-cases is
  existence-only vs WA's per-case table.

**For Pranav:** confirm the `⚖️` rows — item 1 order type, the relationship box,
and every item-14 restraint mapping. The wiring is done.

## Attachments (separate forms, later)

- **A: Definitions** — static, always filed, no data.
- **C: Child Custody** — if protecting the respondent's children.
- **E: Firearms ID** — partial today (access/types/locations).
- **B: Vulnerable Adult** / **D: Non-parents/ICWA** — out of scope for a DV
  survivor protecting themselves / their own children.
