# CV-402 coverage map — intake → form (Wisconsin)

How completely the current Vault intake fills the Wisconsin **Petition for TRO
and/or Petition and Motion for Injunction Hearing (Domestic Abuse)** (CV-402,
§ 813.12 Wis. Stats., Rev. 09/24).

Audit artifact for legal review. **An attorney (Pranav) must confirm the
`needs legal review` rows** (the relationship basis and every relief box).
Unflagged != signed off.

Legend: ✅ mapped · 🟡 partial · ❌ not collected · ⚖️ needs legal review

> The WI intake (shared Tier-2 + the WI block) fills the WI-specific items end to
> end. The form is **alive**: intake → jurisdiction-aware questions → filled
> petition.

## Item-by-item

| Section | Field | Intake source | State |
|---|---|---|---|
| caption | County / petitioner (+ DOB) / respondent (+ address) | `wi.county` / `petitioner.legal_name` / `.dob` / `respondent.legal_name` / `.last_known_address` | ✅ |
| caption | Interpreter party / language | `petitioner.interpreter_language` | ✅ |
| respondent | Sex / race / DOB / height / weight / hair / eyes / marks | `respondent.gender` / `.race` / `.dob` / `.height` / `.weight` / `.hair_color` / `.eye_color` / `.distinguishing_marks` | ✅ |
| relationship | Petitioner's relationship to respondent (+ item 1 a-f) | `relationship.type` | ✅⚖️ |
| caution | Weapon access / type / location / involved | `firearm.respondent_has_access` / `.types[]` / `.locations[]` / `incidents[].weapon_involved` | ✅ |
| item 2a | Petitioner not married to respondent | — | ❌ **WIG1** (legal determination) |
| item 3 | Imminent danger of physical harm | `wi.imminent_danger` | ✅ |
| item 4 | Statement of facts (date / location / narrative) | `incidents[].date` / `.location` / `.narrative` | ✅ |
| item 5 | Other court cases addressing contact | `prior_orders.exists` | 🟡 existence only — **WIG2** |
| request 1 | TRO relief (a-f) | `wi.relief` | ✅⚖️ |
| request 2 | Injunction relief (a-f) | `wi.relief` (same selection) | ✅⚖️ |
| request 1/2 | Other relief detail | `wi.relief_other` | ✅ |
| request 3 | Schedule injunction hearing if TRO denied | derived | ✅ |
| request 4 | Injunction duration (default four years) | `wi.injunction_duration` | ✅ |
| request 4-7 | Wireless transfer / 10-year / permanent / sheriff assist | `wi.additional_requests` | ✅⚖️ |
| signature | Filing as adult petitioner / signature | derived / `petitioner.legal_name` | ✅ |

## Gaps — status

- **WIG1** — the item-2a "not married to respondent" determination (a legal
  characterization; not inferred from the free-text relationship type).
- **WIG2** — the full item-5 other-court-cases detail (only protective-order
  existence is collected).

**For Pranav:** confirm the `⚖️` rows — the § 813.12 relationship basis and every
relief box (TRO 1a-f, injunction 2a-f, items 4-7). The single intake relief
selection intentionally populates both the TRO and injunction sub-lists. The
wiring is done.
