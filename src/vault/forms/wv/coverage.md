# MDVTPET coverage map — intake → form (West Virginia)

How completely the current Vault intake fills the West Virginia **Domestic
Violence Petition for Temporary Emergency Protective (TEPO) Order** (MDVTPET,
W. Va. Code § 48-27, Rev. 04/24/2017) and its companion CCIS (MDVINFO).

Audit artifact for legal review. **An attorney (Pranav) must confirm the
`needs legal review` rows** (the relationship basis, the requested duration, and
every acts/relief box). Unflagged != signed off.

Legend: ✅ mapped · 🟡 partial · ❌ not collected · ⚖️ needs legal review

> The WV intake (shared Tier-2 + the WV block) fills the WV-specific items end to
> end. The form is **alive**: intake → jurisdiction-aware questions → filled
> petition.

## Item-by-item

| Section | Field | Intake source | State |
|---|---|---|---|
| CCIS | County / petitioner (+ phone / DOB) | `wv.county` / `petitioner.legal_name` / `.safe_phone` / `.dob` | ✅ |
| CCIS | Petitioner SSN / street address | — | ❌ **WVG1** (sealed / sensitive) |
| CCIS | Confidential-address seal | derived | ✅ |
| CCIS | Disability accommodations | `petitioner.disability_accommodation` | ✅ |
| CCIS | Respondent (+ address / sex / race / DOB / ht / wt / eyes / hair / marks / employer) | `respondent.legal_name` / `.last_known_address` / `.gender` / `.race` / `.dob` / `.height` / `.weight` / `.eye_color` / `.hair_color` / `.distinguishing_marks` / `.employer_name` | ✅ |
| CCIS | Respondent SSN / driver's license | — | ❌ **WVG2** |
| item 3/4 | Petitioner county / respondent county | `wv.county` / — | 🟡 respondent county — **WVG3** |
| relationship | Relationship between respondent and petitioner | `relationship.type` | ✅⚖️ |
| item 5 | Abused/threatened by respondent | derived | ✅ |
| item 6 | Children protected | `protected_persons.children[]` | 🟡 names; DOB/address/relationship — **WVG4** |
| item 7 | Date / location of the abuse | `incidents[].date` / `.location` | ✅ |
| item 8 | Acts checklist | `wv.abuse_acts` | ✅⚖️ |
| item 8 | Abuse narrative | `incidents[].narrative` | ✅ |
| — | Separate protective order in effect | `prior_orders.exists` | 🟡 existence only — **WVG3** |
| firearms | Respondent owns firearms (+ type/location) | `firearm.respondent_has_access` / `.types[]` / `.locations[]` | ✅ |
| item 9-10 | § 505 duration reasons | `wv.duration_reasons` | ✅⚖️ |
| relief | Requested PO duration (90/180/1yr/longer) | `wv.po_duration` | ✅⚖️ |
| permissive | Relief (1-5 + LE accompany / enter residence) | `wv.permissive_relief` | ✅⚖️ |
| permissive 4/5 | Custody children / visitation changes | `protected_persons.children[]` / `wv.visitation_detail` | ✅ |
| verification | Petitioner signature | `petitioner.legal_name` | ✅ |

## Gaps — status

- **WVG1** — petitioner SSN and street address (sealed by design / sensitive).
- **WVG2** — respondent SSN and driver's license.
- **WVG3** — the respondent's county (item 4) and the county/state of any
  separate protective order.
- **WVG4** — per-child DOB/address and relationship-to-each-party (item 6).

> **Mandatory relief** (refrain from abuse, firearm prohibition, statewide
> effect) is automatic on grant and is not a requested item.

**For Pranav:** confirm the `⚖️` rows — the § 48-27 relationship basis, the
requested duration with its § 505 reasons, and every item-8 / permissive-relief
box. The wiring is done.
