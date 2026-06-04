# LPOR B coverage map — intake → form (Louisiana)

How completely the current Vault intake fills the Louisiana **Petition for
Protection from Abuse** (LPOR B, La. R.S. 46:2131 et seq., v.15.1).

Audit artifact for legal review. **An attorney (Pranav) must confirm the
`needs legal review` rows** (the relationship basis, the venue basis, the abuse
manner, the confidential-address election, every §9 ex parte relief item, and every
§10 other request). Unflagged != signed off.

Legend: ✅ mapped · 🟡 partial · ❌ not collected · ⚖️ needs legal review

> The LA intake (Tier-1 core + the shared interpreter + employer gates + the LA
> block) fills the LA-specific items end to end. The form is **alive**: intake →
> jurisdiction-aware questions → filled petition.

## Item-by-item

| Section | Field | Intake source | State |
|---|---|---|---|
| caption | Court / parish / division-number | `la.court` / `la.parish` / clerk | ✅ (division — LAG2) |
| 1 | Petitioner name / DOB / protected children | `petitioner.legal_name` / `.dob` / `protected_persons.children[]` | ✅ (children 🟡 — LAG3) |
| 2 | Confidential address (§2a) / current address (§2b) | derived / `petitioner.safe_mailing_address` | ✅⚖️ |
| 3 | Interpreter request | `petitioner.interpreter_language` | ✅ |
| 4 | Defendant name / address / employer | `respondent.legal_name` / `.last_known_address` / `.employer_name` / `.employer_address` | ✅ |
| 5 | Venue basis | `la.venue` | ✅⚖️ |
| 6 | Relationship basis / children in common | `la.relationship_basis` / `relationship.children_in_common` | ✅⚖️ |
| 8a | Abuse manner | `la.abuse_types` | ✅⚖️ |
| 8b | Danger indicators | `la.danger_indicators` | ✅ |
| 8c | Narrative (+ date) | `incidents[].narrative` / `.date` | ✅ |
| 9 a-m | Ex parte TRO relief | `la.relief` | ✅⚖️ |
| 9 c/f/g | Stay-away residence / use-residence / property detail | `la.residence_address` / `la.use_residence_address` / `la.property_detail` | ✅ |
| 10 | Other (rule-to-show-cause) requests (+ other detail) | `la.other_requests` / `la.other_detail` | ✅⚖️ |
| 7 | Related legal action | `prior_orders.exists` | 🟡 existence — LAG4 |
| affirmation | Petitioner signature | `petitioner.legal_name` | ✅ |

## Gaps — status

- **LAG1** — LPOR B prints only a form version (v.15.1), no calendar revision date;
  `FORM_REVISION` records the version.
- **LAG2** — the division / number are assigned by the clerk at filing.
- **LAG3** — the §1b protected-children block wants name / DOB / relationship per
  child; only names are collected.
- **LAG4** — the §7 related-action Addendum (suit name / number / court / hearing
  dates) is not collected; only protective-order existence is mapped.

**For Pranav:** confirm the `⚖️` rows — the §6 relationship basis, the §5 venue
basis, the §8a abuse manner, the §2a confidential-address election, every §9 ex
parte relief item, and every §10 other request. The wiring is done.
