# DC CPO petition coverage map — intake → form (District of Columbia)

How completely the current Vault intake fills the Superior Court of D.C.
**Petition and Affidavit for Civil Protection Order** (D.C. Code § 16-1001 et
seq.).

Audit artifact for legal review. **An attorney (Pranav) must confirm the
`needs legal review` rows** (the relationship/eligibility basis and every relief
box). Unflagged != signed off.

Legend: ✅ mapped · 🟡 partial · ❌ not collected · ⚖️ needs legal review

> The DC intake (shared Tier-2 + the DC block) fills the DC-specific items end to
> end. The form is **alive**: intake → jurisdiction-aware questions → filled
> petition.

## Item-by-item

| Section | Field | Intake source | State |
|---|---|---|---|
| caption | Petitioner / substitute address / respondent (+ address) | `petitioner.legal_name` / derived + `petitioner.safe_mailing_address` / `respondent.legal_name` / `.last_known_address` | ✅ |
| 1 | Relationship / eligibility basis | `relationship.type` | ✅⚖️ |
| 2, 3 | DC nexus / incident in DC | `dc.petitioner_dc_nexus` / `dc.incident_in_dc` | ✅ |
| 4 | Affidavit — incident A (date / location / narrative) | `incidents[].date` / `.location` / `.narrative` | ✅ |
| 4 | Incidents B-D (overflow) | — | ❌ **DCG1** |
| relief 1 | Not abuse/threaten/stalk/harass | `dc.relief` | ✅⚖️ |
| relief 2 | Stay away (+ person/work/home/vehicle/school/other places/persons) | `dc.relief` / `dc.stay_away_places` (+ `dc.stay_away_other_places`, `dc.stay_away_other_persons`) | ✅⚖️ |
| relief 3 | No contact (+ phone/writing/electronic/any) | `dc.relief` / `dc.contact_methods` | ✅⚖️ |
| relief 4 | Temporary custody | `dc.relief` / `protected_persons.children[]` | 🟡 names; items 4a-4e + birth certificates not collected — **DCG2** |
| relief 5 | Respondent visitation | `dc.relief` | ✅⚖️ |
| relief 6 | Child support (DC Guideline) | `dc.relief` | 🟡 income / 6a-6d not collected — **DCG3** |
| relief 7 | Vacate the home (+ ownership basis) | `dc.relief` / `dc.vacate_home_basis` | ✅⚖️ |
| relief 8 | Financial assistance / spousal support | `dc.relief` | ✅⚖️ |
| relief 9 | Possession of jointly owned property (+ description) | `dc.relief` / `dc.property_description` | ✅⚖️ |
| relief 10 | No removal from health insurance | `dc.relief` | ✅⚖️ |
| relief 11 | Reimburse costs / property damage (+ detail) | `dc.relief` / `dc.damaged_property` | ✅⚖️ |
| relief 12 | Counseling (+ alcohol/drug/DV/parenting/family-violence/other) | `dc.relief` / `dc.counseling_types` | ✅⚖️ |
| relief 13 | Order police to assist (+ four actions) | `dc.relief` / `dc.police_actions` | ✅⚖️ |
| relief 14 | Attorney's fees and costs | `dc.relief` | ✅⚖️ |
| relief 15 | Other (+ detail) | `dc.relief` / `dc.other_relief` | ✅⚖️ |
| relief 16 | Emergency Temporary Protection Order | `dc.relief` | ✅⚖️ |
| verification | Petitioner signature | `petitioner.legal_name` | ✅ |

## Gaps — status

- **DCG1** — affidavit incident slots B-D (intake collects one incident; DC
  provides four).
- **DCG2** — custody sub-questions 4a-4e (children's current/past addresses, who
  they lived with, other custody cases, other claimants) and birth certificates.
- **DCG3** — child-support detail (respondent's annual gross income, items 6a-6d:
  prior cases, public assistance, employment, special costs).

## Open question

- **Form number / revision:** the DC petition shows no printed number or revision
  date. `FORM_ID` is the descriptive `DC-CPO-Petition`; confirm the official
  identifier and current revision against the blank PDF.

**For Pranav:** confirm the `⚖️` rows — the § 16-1001 relationship/eligibility
basis (including the stalking / § 16-1001(6)(B) / sexual-assault bases) and every
relief box. The wiring is done.
