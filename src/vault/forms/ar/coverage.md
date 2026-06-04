# AR Order of Protection coverage map — intake → form (Arkansas)

How completely the current Vault intake fills the Arkansas **Petition and
Affidavit for an Order of Protection** (A.C.A. § 9-15-101 et seq., Rev. August
2023).

Audit artifact for legal review. **An attorney (Pranav) must confirm the
`needs legal review` rows** (the relationship basis, the ex parte basis, and
every item-8 relief box). Unflagged != signed off.

Legend: ✅ mapped · 🟡 partial · ❌ not collected · ⚖️ needs legal review

> The AR intake (shared Tier-2 + the AR block) fills the AR-specific items end to
> end. The form is **alive**: intake → jurisdiction-aware questions → filled
> petition.

## Item-by-item

| Section | Field | Intake source | State |
|---|---|---|---|
| caption | County | `ar.county` | ✅ |
| petitioner | Name / age / DOB / interpreter / phone / email / mailing (safe) | `petitioner.legal_name` / derived / `.dob` / `.interpreter_language` / `.safe_phone` / `.safe_email` / `.safe_mailing_address` | ✅ |
| petitioner | Omit-address box | derived (defaulted on) | ✅ |
| petitioner | Race / sex / DL# / work | — | ❌ **ARG1** |
| respondent | Name / age / DOB / race / sex / home address / work | `respondent.legal_name` / derived / `.dob` / `.race` / `.gender` / `.last_known_address` / `.employer_name` / `.employer_address` | ✅ |
| respondent | Height / weight / eyes / hair / distinguishing | `respondent.height` / `.weight` / `.eye_color` / `.hair_color` / `.distinguishing_marks` | ✅ |
| respondent | Phone / email / DL# | — | ❌ **ARG2** |
| 1 | Filing on behalf of myself | derived | ✅ |
| 2 | Relationship basis (mark all) | `relationship.type` | ✅⚖️ |
| 3 | Ex parte basis | derived (asserted) | ✅⚖️ |
| 3 | Most recent act — date / location / description | `incidents[].date` / `.location` / `.narrative` | ✅ |
| 4 | Reported to law enforcement | `incidents[].police_called` | 🟡 agency/date/action — **ARG3** |
| 5 | Additional acts | — | ❌ **ARG3** |
| 6 | Respondent prior violence | `respondent.prior_criminal_history` | 🟡 when/where/what — **ARG3** |
| 7 | Minor children in common | `protected_persons.children[]` | 🟡 names; ages/addresses — **ARG4** |
| 8 | Exclude residence (+ address + owner) | `ar.relief` / `ar.residence_address` / `ar.residence_owner` | ✅⚖️ |
| 8 | Exclude work/school/other (+ location) | `ar.relief` / `ar.workplace` | ✅⚖️ |
| 8 | No contact (+ conditions) | `ar.relief` / `ar.contact_conditions` | ✅⚖️ |
| 8 | No phone disconnect / custody / exclude address / pay fees | `ar.relief` | ✅⚖️ |
| 8 | Child support / spousal support | `ar.relief` | 🟡 respondent weekly take-home pay — **ARG5** |
| 10, 11 | Existing custody order / prior cases | — | ❌ **ARG6** |
| NOTICE | Caution: possesses a firearm | `firearm.respondent_has_access` | ✅ |
| NOTICE | Caution: history of extreme violence | — | ❌ **ARG7** |
| verification | Petitioner signature | `petitioner.legal_name` | ✅ |

## Gaps — status

- **ARG1** — petitioner race / sex / driver's license / place of work.
- **ARG2** — respondent phone / email / driver's license.
- **ARG3** — law-enforcement agency/date/action (item 4), additional acts (item
  5), and the when/where/what detail for prior violence (item 6).
- **ARG4** — per-child age/address for the item-7 table.
- **ARG5** — respondent's weekly take-home pay for the child/spousal support
  requests.
- **ARG6** — existing custody order (item 10) and prior circuit-court cases
  (item 11).
- **ARG7** — the "history of extreme violence" caution on the NOTICE page.

**For Pranav:** confirm the `⚖️` rows — the § 9-15 relationship basis, the ex
parte basis, and every item-8 relief box. The wiring is done.
