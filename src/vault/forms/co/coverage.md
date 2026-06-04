# JDF 402 coverage map — intake → form (Colorado)

How completely the current Vault intake fills the Colorado **Complaint/Motion for
Civil Protection Order** (JDF 402, C.R.S. § 13-14-101 et seq., Rev. December 19,
2022).

Audit artifact for legal review. **An attorney (Pranav) must confirm the
`needs legal review` rows** (the court type, the statutory basis, the
relationship, and every relief box). Unflagged != signed off.

Legend: ✅ mapped · 🟡 partial · ❌ not collected · ⚖️ needs legal review

> The CO intake (shared Tier-2 + the CO block) fills the CO-specific items end to
> end. The form is **alive**: intake → jurisdiction-aware questions → filled
> motion.

## Item-by-item

| Section | Field | Intake source | State |
|---|---|---|---|
| caption | Court type | — | ❌⚖️ clerk/attorney selects — **COG-court** |
| caption | County / petitioner (+ DOB) / respondent (+ DOB) | `co.county` / `petitioner.legal_name` / `.dob` / `respondent.legal_name` / `.dob` | ✅ |
| caption | Filing type (Motion) | derived | ✅ |
| caption | Filer address / phone | — | ❌ omitted by design (section 6) |
| 1 | Basis (domestic abuse / stalking / sexual assault / unlawful sexual contact / elder-at-risk / physical assault) | `co.basis` | ✅⚖️ |
| 2 | Petitioner county / relationship ("I know because") | `co.county` / `relationship.type` | ✅⚖️ |
| 2 | Respondent county | — | ❌ **COG1** |
| 3 | Other protected persons | `protected_persons.children[]` | 🟡 names; DOB/sex/race + JDF 404 — **COG2** |
| 4a | Most recent incident (date / location / narrative) | `incidents[].date` / `.location` / `.narrative` | ✅ |
| 4b, 4c | Most serious / other past incidents | — | ❌ **COG3** |
| 4d | Other protection orders in effect | `prior_orders.exists` | 🟡 existence only — **COG3** |
| 5 | Imminent danger (life/health; harm if not excluded) | `co.imminent_danger` | ✅ |
| 6 | Omit address and phone | derived (defaulted on) | ✅ |
| 7a | Refrain from contact/harass/injure/stalk/... | `co.relief` | ✅⚖️ |
| 7b | No contact / limited contact (+ terms) | `co.relief` / `co.limited_contact_terms` | ✅⚖️ |
| 7c | Excluded from home (+ address) | `co.relief` / `co.home_address` | ✅⚖️ |
| 7d | Stay away (+ distance + home/work/school/other) | `co.relief` / `co.stay_away_distance_yards` / `co.stay_away_places` | ✅⚖️ |
| 7e | No contact w/ children + care/control OR care/control + parenting time (+ terms) | `co.relief` / `co.parenting_time_terms` | ✅⚖️ |
| 7f | Protect animals (+ arrangements) | `co.relief` / `co.animal_arrangements` | ✅⚖️ |
| 7g | No firearm + relinquish (DV order) | `co.relief` | ✅⚖️ |
| 7h | No interference at work/school | `co.relief` | ✅⚖️ |
| 7i | Other (+ detail) | `co.relief` / `co.other_relief` | ✅⚖️ |
| verification | Petitioner signature / mailing address (safe) | `petitioner.legal_name` / `.safe_mailing_address` | ✅ |

## Gaps — status

- **COG-court** — the court type (Municipal/County/District/Juvenile/Probate) is
  a procedural determination, left to the clerk/attorney.
- **COG1** — the respondent's county of residence/employment (item 2).
- **COG2** — per-person DOB/sex/race for the protected-persons table and the
  **JDF 404** Affidavit Regarding Children.
- **COG3** — the most-serious (4b) and other (4c) incident slots, and the issuing
  court/state/date for any other protection order (4d).

**For Pranav:** confirm the `⚖️` rows — the court type, the § 13-14-101 statutory
basis, the relationship, and every item-7 relief box. The wiring is done.
