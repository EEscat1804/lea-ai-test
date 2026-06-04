# SCCA 425 coverage map — intake → form (South Carolina)

How completely the current Vault intake fills the South Carolina **Petition for
Family Court Order of Protection** (SCCA 425, Protection from Domestic Abuse Act,
Revised 11/2025).

Audit artifact for legal review. **An attorney (Pranav) must confirm the
`needs legal review` rows** (the venue, the relationship basis, and every §9 a-q
relief box). Unflagged != signed off.

Legend: ✅ mapped · 🟡 partial · ❌ not collected · ⚖️ needs legal review

> The SC intake (Tier-1 core + the shared minor + employer gates + the SC block)
> fills the SC-specific items end to end. The form is **alive**: intake →
> jurisdiction-aware questions → filled petition.

## Item-by-item

| Section | Field | Intake source | State |
|---|---|---|---|
| caption | County / docket number | `sc.county` / clerk | ✅ (docket — SCG1) |
| 1 | Venue | `sc.venue` | ✅⚖️ |
| 2 | Respondent name / address | `respondent.legal_name` / `.last_known_address` | ✅ |
| 3 | Respondent SSN | — | ❌ SCG2 |
| 4 | Respondent DOB / race / sex | `respondent.dob` / `.race` / `.gender` | ✅ |
| 5 | Prior DV convictions / orders | `prior_orders.exists` | 🟡 existence — SCG3 |
| (service) | Respondent employer | `respondent.employer_name` / `.employer_address` | ✅ |
| 6 | Petitioner / protected child | `petitioner.legal_name` / `protected_persons.children[]` | ✅ (child 🟡 — SCG4) |
| 7 | Relationship basis | `sc.relationship_basis` | ✅⚖️ |
| 8 | Narrative (+ date / location) | `incidents[].narrative` / `.date` / `.location` | ✅ |
| 9 a-q | Relief | `sc.relief` | ✅⚖️ |
| 9 d/e/h/l/q | Stay-away / custody / home / property / other detail | `sc.stay_away_location` / `sc.custody_detail` / `sc.home_address` / `sc.property_detail` / `sc.relief_other_detail` | ✅ |
| verification | Petitioner signature | `petitioner.legal_name` | ✅ |

## Gaps — status

- **SCG1** — the docket number is assigned by the clerk at filing.
- **SCG2** — the §3 SSN is the respondent's; intake does not collect it. The §9
  support relief requires the separate Financial Declaration (SCCA 430), and the
  petition has no petitioner SSN field, so SC is not in the SSN-for-support gate.
- **SCG3** — the §5 prior-DV question wants the date(s); only existence is mapped.
- **SCG4** — the §6b protected-child block lists children; only names are collected.

**For Pranav:** confirm the `⚖️` rows — the §1 venue, the §7 relationship basis,
and every §9 a-q relief box. The wiring is done.
