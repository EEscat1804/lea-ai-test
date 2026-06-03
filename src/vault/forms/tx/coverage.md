# TX Application coverage map — intake → form (Texas)

How completely the current Vault intake fills the Texas **Application for
Protective Order** + **Affidavit/Declaration** (Tex. Fam. Code; Penal Code
Title 5-6).

Audit artifact for legal review. **An attorney (Pranav) must confirm the
`needs legal review` rows** (the item-2 reason, the relationship mapping, every
item-8 term, the ex parte and children-order boxes). Unflagged != signed off.

Legend: ✅ mapped · 🟡 partial · ❌ not collected · ⚖️ needs legal review

> The TX intake section fills the TX-specific items end to end. The form is
> **alive**: intake → jurisdiction-aware questions → filled Application + Affidavit.

## Application

| Item | Field | Intake source | State |
|---|---|---|---|
| 1 | Applicant / Respondent / respondent address | `petitioner.legal_name` / `respondent.legal_name` / `.last_known_address` | ✅ |
| 1 | Applicant county of residence | — | ❌ **TG1** (only free-text safe address) |
| 2 | Reason: family violence | fixed (DV path) | ✅⚖️ |
| 3 | Relationship | `relationship.type` | ✅⚖️ |
| 4 | Children needing protection | `protected_persons.children[]` | 🟡 names; per-child parent/guardian flag — **TG2** |
| 5, 6 | Other adults / other court cases | — | ❌ **TG3** |
| 7 | Criminal Title 5/6 / FV finding / parental rights | `respondent.prior_criminal_history` / `.prior_dv_finding` / `.parental_rights_terminated` | ✅ |
| 8 a-n | Terms requested (+ stay-away who/distance, pet, other) | `tx.terms` (+ `tx.stay_away_*`, `tx.pet`, `tx.other_terms`) | ✅⚖️ |
| 9 | Exclusive residence / vacate | `tx.exclusive_residence` | ✅⚖️ |
| 10 | Spousal support | `tx.spousal_support` | ✅ |
| 11 | Wireless phone transfer | `tx.phone_transfer` | 🟡 box; specific numbers not collected — **TG4** |
| 12 | Children orders | `tx.children_orders` | ✅⚖️ |
| 13 | Temporary ex parte order | `tx.ex_parte` | ✅⚖️ |
| 13a | Ex parte + vacate residence | — | 🟡 partial (overlaps 9/13) — **TG5** |
| 14 | Keep info confidential | `tx.confidential` | ✅ |
| sig | Applicant signature | `petitioner.legal_name` | ✅ |

## Affidavit / Declaration

| Field | Intake source | State |
|---|---|---|
| Relationship with respondent | `relationship.type` | ✅ |
| Most recent incident statement | `incidents[].narrative` | ✅ |
| Incident date / weapon / firearms / police / injuries | `incidents[].date` / `.weapon_involved` / `firearm.respondent_has_access` / `incidents[].police_called` / `.injury` | ✅ |
| Prior family-violence conviction | `respondent.prior_dv_finding` | ✅ |
| Requesting exclusive residence | `tx.exclusive_residence` | ✅ |
| County / medical care / trafficking-SA convictions / prior-incident detail | — | ❌ **TG6** (mostly optional) |

## Gaps — status

- **TG1** — applicant county of residence (only free-text safe address collected).
- **TG2** — per-child "is respondent the parent/guardian" flag.
- **TG3** — other adults needing protection (item 5); other court cases (item 6).
- **TG4** — specific phone numbers to transfer (item 11 box is mapped).
- **TG5** — ex parte + vacate residence (item 13a) overlaps 9/13.
- **TG6** — affidavit detail: county, medical care, trafficking/SA conviction
  checkboxes, prior-incident sub-fields (mostly optional).

**For Pranav:** confirm the `⚖️` rows — item 2 reason, the relationship mapping,
every item-8 term, ex parte, and children orders. The wiring is done.
