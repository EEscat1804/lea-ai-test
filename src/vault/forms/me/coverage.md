# Form PA-001 coverage map — intake → form (Maine)

How completely the current Vault intake fills the Maine **Complaint for Protection
from Abuse** (Form PA-001, 19-A M.R.S. §§ 4101-4116, Rev. 09/25), plus the
respondent identifiers that ride on the companion service sheet (PA-005).

Audit artifact for legal review. **An attorney (Pranav) must confirm the
`needs legal review` rows** (the relationship basis, the temporary/ex-parte order
election, the confidential-address election, and every order a-q relief box).
Unflagged != signed off.

Legend: ✅ mapped · 🟡 partial · ❌ not collected · ⚖️ needs legal review

> The ME intake (Tier-1 core + the shared physical / vehicle / minor gates + the
> ME block) fills the ME-specific items end to end. The form is **alive**: intake →
> jurisdiction-aware questions → filled complaint.

## Item-by-item

| Section | Field | Intake source | State |
|---|---|---|---|
| caption | District Court location (town) / docket | `me.court_location` / clerk | ✅ (docket — MEG1) |
| 1 | Plaintiff name / gender / DOB / address / phone | `petitioner.legal_name` / `.gender` / `.dob` / `.safe_mailing_address` / `.safe_phone` | ✅⚖️ (address) |
| 1 | Confidential address (PA-015) | derived | ✅⚖️ |
| 1A | Minor child(ren) on whose behalf | `protected_persons.children[]` | 🟡 names — MEG2 |
| 2 | Defendant name / gender / DOB / race / address | `respondent.legal_name` / `me`→`respondent.gender` / `.dob` / `.race` / `.last_known_address` | ✅ |
| 2 (PA-005) | Defendant height / weight / eyes / hair / marks | `respondent.height` / `.weight` / `.eye_color` / `.hair_color` / `.distinguishing_marks` | ✅ |
| 2 (PA-005) | Defendant employer + work address | `respondent.employer_name` / `.employer_address` | ✅ |
| 2 (PA-005) | Defendant vehicle make/model / color / plate | `respondent.vehicle_make_model` / `.vehicle_color` / `.vehicle_plate` | ✅ |
| 3 | Defendant military service | `me.defendant_military` | ✅ |
| 4 | Relationship basis | `me.relationship_basis` | ✅⚖️ |
| 5/6 | Parents of children / custody / residence | `protected_persons.children[]` / — | 🟡 names — MEG2 / ❌ MEG3 |
| 7 | Public assistance / DHHS support | — | ❌ MEG4 |
| 8/9 | Other court cases | `prior_orders.exists` / `me.other_cases_detail` | 🟡 existence + free text — MEG5 |
| 10 | Temporary (ex parte) order election | `me.temporary_order` | ✅⚖️ |
| 11 | Weapon access / location / ever-used | `me.weapon_access` / `me.weapon_detail` / `firearm.locations[]` / `me.weapon_ever_used` / `me.weapon_used_detail` | ✅ |
| 12 | Abuse narrative (+ date / location / witnesses / injury) | `incidents[].narrative` / `.date` / `.location` / `.witnesses_present` / `.injury` | ✅ |
| a-q | Relief checklist | `me.relief` | ✅⚖️ |
| h/i/e/q | Order details (residence / property+pets / distance / other) | `me.residence_address` / `me.property_detail` / `me.stay_distance_detail` / `me.relief_other_detail` | ✅ |
| verification | Plaintiff signature | `petitioner.legal_name` | ✅ |

## Gaps — status

- **MEG1** — the docket number is assigned by the clerk at filing.
- **MEG2** — per-minor DOB / gender / present-address for the §1A and §5
  children tables; only names are collected.
- **MEG3** — the §6 custody/residence tables (primary residence, third-party
  custody, 5-year residence history) are not collected.
- **MEG4** — the §7 public-assistance / DHHS child-support contact is not
  collected; order (m) support additionally requires the FM-050 Child Support
  Affidavit and the CR-CV-FM-PC-200 SSN disclosure, filed separately by the
  advocate/attorney (the PA-001 has no SSN field, so ME is not in the SSN gate).
- **MEG5** — the §§8-9 custody/divorce/probate/criminal case detail tables; only
  protective-order existence + a free-text note are collected.

**For Pranav:** confirm the `⚖️` rows — the relationship basis (§4), the temporary
(ex parte) order election (§10), the confidential-address election (PA-015), and
every order a-q relief box. The wiring is done.
