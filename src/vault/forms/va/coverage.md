# DC-383 coverage map — intake → form (Virginia)

How completely the current Vault intake fills Virginia form **DC-383**
(_Petition for Protective Order_, Va. Code §§ 19.2-152.9 / 19.2-152.10,
Rev. 07/24).

Audit artifact for legal review. **An attorney (Pranav) must confirm the
`needs legal review` rows** (the requested-conditions boxes, the preliminary-
order request, the cohabitation eligibility box). Unflagged != signed off.

Legend: ✅ mapped · 🟡 partial · ❌ not collected · ⚖️ needs legal review

> DC-383 is short; the form fills end to end from intake. Most gaps are optional
> on the form or belong on the **DC-621** addendum.

## Item-by-item

| Field | Intake source | State |
|---|---|---|
| Petitioner | `petitioner.legal_name` | ✅ |
| Respondent | `respondent.legal_name` | ✅ |
| Respondent address/location | `respondent.last_known_address` | ✅ |
| Respondent telephone | — | ❌ **VG1** |
| Description: race / sex / DOB | `respondent.race` / `.gender` / `.dob` | ✅ |
| Description: height / weight / eyes / hair | `respondent.height` / `.weight` / `.eye_color` / `.hair_color` | ✅ |
| Description: SSN / driver's license | — | ❌ **VG1** (rarely known) |
| 1 — Warrant/petition for criminal offense | — | ❌ **VG2** (optional) |
| 2 — Act of violence statement | `incidents[].narrative` | ✅ |
| 3 — Cohabited >12 months ago | — | ❌⚖️ **VG3** (narrow eligibility box) |
| 4 — Protective order in effect | `prior_orders.exists` | 🟡 existence vs "currently in effect" |
| 5 — Respondent possesses firearms | `firearm.respondent_has_access` | ✅ |
| Preliminary protective order | `va.preliminary_order` | ✅⚖️ |
| Condition: no violence/force/threat | `va.conditions` | ✅⚖️ |
| Condition: no contact w/ petitioner | `va.conditions` | ✅⚖️ |
| Condition: no contact w/ family/household | `va.conditions` | ✅⚖️ |
| Family/household member names | `protected_persons.children[]` | 🟡 names; DC-621 wants per-member DOB/gender/race |
| Condition: companion animal (+ desc) | `va.conditions` / `va.companion_animal` | ✅⚖️ |
| Condition: other (+ detail) | `va.conditions` / `va.other_conditions` | ✅⚖️ |
| Signature (printed name) | `petitioner.legal_name` | ✅ |

## Gaps — status

- **VG1 — respondent phone / SSN / driver's license.** Rarely known; not
  collected. Low priority.
- **VG2 — item 1 (criminal warrant).** Optional factual checkbox.
- **VG3 — item 3 (cohabitation >12 months ago).** Narrow VA eligibility box;
  needs a targeted question + legal confirmation.
- **DC-621 addendum.** Petitioner identifying info and per-member DOB/gender/race
  live on the separate Non-Disclosure Addendum — not yet mapped.

**For Pranav:** confirm the `⚖️` rows — the requested-conditions boxes, the
preliminary-order request, and the item-3 cohabitation box. The wiring is done.
