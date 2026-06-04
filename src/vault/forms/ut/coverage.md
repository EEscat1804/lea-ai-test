# Request for Protective Order coverage map — intake → form (Utah)

How completely the current Vault intake fills the Utah **Request for Protective
Order** (Utah Code 78B-7-601 et seq.; District Court; Rev. April 11, 2022).

Audit artifact for legal review. **An attorney (Pranav) must confirm the
`needs legal review` rows** (the relationship basis, the violent-past / imminent-
fear declarations, custody, and every items 8-25 relief box). Unflagged !=
signed off.

Legend: ✅ mapped · 🟡 partial · ❌ not collected · ⚖️ needs legal review

> The UT intake (the UT block + the shared physical-description and vehicle
> gates) fills the UT-specific items end to end. The form is **alive**: intake →
> jurisdiction-aware questions → filled request.

## Item-by-item

| Section | Field | Intake source | State |
|---|---|---|---|
| caption | County | `ut.county` | ✅ |
| caption | District number | — | ❌ **UTG2** (set by county at filing) |
| caption | Case number / Judge / Commissioner | — | ❌ assigned by the clerk |
| 1 | Petitioner (+ DOB) | `petitioner.legal_name` / `.dob` | ✅ |
| 1 | Petitioner address/phone (kept private) | derived (left blank) / `petitioner.safe_mailing_address` | ✅ |
| 1 | Petitioner's attorney | — | ❌ **UTG3** |
| 1 | Other people protected (name/age/relationship) | `protected_persons.children[]` | 🟡 names only — **UTG4** |
| 2 | Respondent (+ address) | `respondent.legal_name` / `.last_known_address` | ✅ |
| 2 | Sex* / Race* / DOB* | `respondent.gender` / `.race` / `.dob` | ✅ |
| 2 | Ht / Wt / Eyes / Hair / distinguishing features | `respondent.height` / `.weight` / `.eye_color` / `.hair_color` / `.distinguishing_marks` | ✅ (shared physical gate) |
| 2 | Other names used | — | ❌ **UTG5** |
| 2 | Full Social Security # | — | ❌ **UTG6** (sensitive) |
| 2 | Driver's license (state/expiry) | — | ❌ **UTG5** |
| 2 | Employer (name/address) | `respondent.employer_name` / `.employer_address` | ✅ |
| 2 | Other places to find respondent (table) | — | ❌ **UTG5** |
| 2 | Vehicle (make/model/color/plate) | `respondent.vehicle_make_model` / `.vehicle_color` / `.vehicle_plate` | ✅ (shared vehicle gate) |
| 2 | Used weapons / violent in past (+ detail) | `ut.respondent_violent_past` / `ut.respondent_violent_detail` | ✅⚖️ |
| 2 | On probation/parole (+ detail) | `ut.respondent_probation` / `ut.respondent_probation_detail` | ✅ |
| 3 | Relationship basis (a-i) | `relationship.type` | ✅⚖️ |
| 4 | Most recent abuse (date / where / police / narrative / weapon / witnesses / injury) | `incidents[].*` | ✅ |
| 4d | Police dept / arrested / case# / ticket | — | ❌ **UTG7** |
| 5 | Past abuse | `incidents[].*` (most recent only) | 🟡 single incident — **UTG7** |
| 6 | Imminent-fear declaration (+ detail) | `ut.fear_imminent` / `ut.fear_imminent_detail` | ✅⚖️ |
| 7 | Other court cases | `prior_orders.exists` | 🟡 existence only — **UTG7** |
| 8 | Personal Conduct | `ut.relief` | ✅⚖️ |
| 9 | No Contact | `ut.relief` | ✅⚖️ |
| 10 | Contact for Mediation | `ut.relief` | ✅⚖️ |
| 11 | Stay Away (+ distance, locations, other) | `ut.relief` (+ `ut.stay_away_distance`, `ut.stay_away_locations`, `ut.stay_away_other`) | ✅⚖️ |
| 12 | No Guns or Weapons (+ detail) | `ut.relief` (+ `ut.weapons_detail`) | ✅⚖️ |
| 13 | Property Control — petitioner (+ home, belongings) | `ut.relief` (+ `ut.property_home_address`, `ut.property_belongings`) | ✅⚖️ |
| 14 | Property Control — services | `ut.relief` | ✅⚖️ |
| 15 | No Harming Pets | `ut.relief` | ✅⚖️ |
| 16 | Transfer Wireless Number(s) (+ numbers) | `ut.relief` (+ `ut.wireless_numbers`) | ✅⚖️ |
| 17 | Child Custody & Parent-time (+ to, other name, parent-time) | `ut.relief` (+ `ut.custody_to`, `ut.custody_other_name`, `ut.parent_time`) | ✅⚖️ |
| 18 | No Alcohol or Drugs | `ut.relief` | ✅⚖️ |
| 19 | Supervised Visitation (+ supervisor) | `ut.relief` (+ `ut.supervised_visitation_detail`) | ✅⚖️ |
| 20 | Travel Restrictions | `ut.relief` | ✅⚖️ |
| 21 | Support & Expenses (a-f + amounts) | `ut.relief` (+ `ut.support_types`, `ut.child_support_amount`, `ut.spousal_support_amount`) | ✅⚖️ |
| 22 | Other Assistance (+ detail) | `ut.relief` (+ `ut.other_assistance_detail`) | ✅⚖️ |
| 23 | Law Enforcement to Assist (a-c) | `ut.relief` (+ `ut.law_enforcement_tasks`) | ✅⚖️ |
| 24 | Investigate Possible Child Abuse | `ut.relief` | ✅⚖️ |
| 25 | Guardian for children | `ut.relief` | ✅⚖️ |
| signature | Petitioner signature (sworn) | `petitioner.legal_name` | ✅ (city/date set at filing) |

## Gaps — status

- **UTG1** — the form has no printed number; `FORM_ID` is descriptive. Confirm the
  identifier with legal before filing-render.
- **UTG2** — the judicial district number; intake collects county only (the
  district is determined by county at filing).
- **UTG3** — petitioner's attorney name/phone; most survivors self-file.
- **UTG4** — per-protected-person detail (age, relationship); intake holds names.
- **UTG5** — respondent's other names, driver's license, "other places to find"
  table; intake collects none of these.
- **UTG6** — respondent's full Social Security number (sensitive); not collected.
- **UTG7** — police-response detail (department / arrest / case# / ticket), the
  separate past-abuse incident, and the full other-court-cases list; intake holds
  a single incident and `prior_orders.exists` only.

**For Pranav:** confirm the `⚖️` rows — the §3 relationship basis, the violent-
past and §6 imminent-fear declarations, custody, and every items 8-25 relief box.
The wiring is done.
