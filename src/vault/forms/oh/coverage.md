# Form 10.01-D coverage map — intake → form (Ohio)

How completely the current Vault intake fills the Ohio **Petition for Domestic
Violence Civil Protection Order** (Form 10.01-D, R.C. 3113.31, Amended April 15,
2021).

Audit artifact for legal review. **An attorney (Pranav) must confirm the
`needs legal review` rows** (the relationship basis and every relief box).
Unflagged != signed off.

Legend: ✅ mapped · 🟡 partial · ❌ not collected · ⚖️ needs legal review

> The OH intake (shared Tier-2 + the OH block) fills the OH-specific items end to
> end. The form is **alive**: intake → jurisdiction-aware questions → filled
> petition.

## Item-by-item

| Section | Field | Intake source | State |
|---|---|---|---|
| caption | County / petitioner (+ safe address / DOB) / respondent (+ address / DOB / adult) | `oh.county` / `petitioner.legal_name` / `.safe_mailing_address` / `.dob` / `respondent.legal_name` / `.last_known_address` / `.dob` / derived | ✅ |
| 1 | Interpreter (language / ASL) | `petitioner.interpreter_language` | ✅ |
| 2 | Ex parte request / full hearing | `oh.ex_parte` / derived | ✅ |
| 3 | Who needs protection (me / children / household / other) | `oh.who_needs_protection` | ✅ (free-text "other" — OHG1) |
| 4 | Victim's relationship to respondent | `relationship.type` | ✅⚖️ |
| 5 | Other family/household members | `protected_persons.children[]` | 🟡 names; DOB/relationship/lives-with — OHG2 |
| 6 | Abuse narrative (+ date) | `incidents[].narrative` / `incidents[].date` | ✅ |
| 7 | Optional aggravating factors | `oh.aggravating_factors` | ✅ |
| 7 | Respondent weapons/firearms access | `firearm.respondent_has_access` | ✅ |
| 8 | In fear / continuing danger | derived | ✅ |
| 9 (a-n) | Relief checklist | `oh.relief` | ✅⚖️ |
| 9 (d) | Exclusive-residence address | `oh.residence_address` | ✅ |
| 9 (i/j/k) | Pets / property division / vehicle | `oh.pets_detail` / `oh.property_detail` / `oh.vehicle_detail` | ✅ |
| 9 (m) | Wireless transfer (numbers / billing) | `oh.wireless_detail` | ✅ |
| 9 (n) | Additional provisions | `oh.additional_provisions` | ✅ |
| 13 | Other court cases | `prior_orders.exists` | 🟡 existence only — OHG3 |
| signature | Petitioner signature | `petitioner.legal_name` | ✅ |

## Gaps — status

- **OHG1** — the free-text "other" descriptor in item 3 (who needs protection).
- **OHG2** — per-person DOB / relationship-to-each-party / lives-with for the
  item-5 household-members table.
- **OHG3** — the full item-13 other-court-cases table (case name/number/court/
  type/result); only protective-order existence is collected.

> Custody / parenting-time relief (item 9 e/f) also requires **Form 10.01-F**,
> not assembled here. OH is in the physical-description / vehicle intake sets, so
> respondent physical/vehicle details are collected but have no field on this
> form.

**For Pranav:** confirm the `⚖️` rows — the relationship basis and every item-9
(a-n) relief box. The wiring is done.
