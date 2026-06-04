# DV-100 coverage map — intake → form (Alaska)

How completely the current Vault intake fills the Alaska **Petition for Domestic
Violence Protective Order (One Petitioner)** (DV-100, AS 18.66.100-.990, Civil
Rule 65.1, Rev. 1/26).

Audit artifact for legal review. **An attorney (Pranav) must confirm the
`needs legal review` rows** (the order type, the relationship, and every
protection box). Unflagged != signed off.

Legend: ✅ mapped · 🟡 partial · ❌ not collected · ⚖️ needs legal review

> The AK intake (the AK block) fills the AK-specific items end to end. The form
> is **alive**: intake → jurisdiction-aware questions → filled petition.

## Item-by-item

| Section | Field | Intake source | State |
|---|---|---|---|
| caption | Court location / petitioner (+ DOB) / respondent (+ DOB) | `ak.court_location` / `petitioner.legal_name` / `.dob` / `respondent.legal_name` / `.dob` | ✅ |
| 1 | Order type (ex parte / long-term) | `ak.order_type` | ✅⚖️ |
| 1 | Notified respondent before filing | — | ❌ **AKG1** |
| 2 | Relationship | `relationship.type` | ✅⚖️ |
| 3 | Children in household | `ak.children_in_household` | ✅ |
| 4 | Describe DV / weapon / injury / other instances | `incidents[].narrative` / `.weapon_involved` / `.injury` / `.pattern_frequency` | ✅ |
| 5 | Short-term protections (a-j) | `ak.protections` | ✅⚖️ |
| 5b | No-contact exceptions | `ak.contact_exceptions` | ✅ |
| 5c | Address confidential / respondent lives with petitioner | derived / `relationship.live_together_now` | ✅ |
| 5d | Stay-away locations / distances | `ak.stay_away_locations` | ✅ |
| 5g | Possession: residence / vehicle / personal items | `ak.residence_address` / `ak.vehicle_description` / `ak.personal_items` | ✅ (items 🟡 **AKG2**) |
| 5h | Spousal support detail | `ak.spousal_support` | ✅ |
| 6 | Long-term protections (a-f) | `ak.long_term_protections` | ✅⚖️ |
| 6c, 6d | Filing-costs amount / expenses detail | — / `ak.expenses` | 🟡 amount — **AKG3** |
| 7a | Temporary custody (+ children) | `ak.custody` / `protected_persons.children[]` | 🟡 per-child DOB/relationship — **AKG4** |
| 7c | Child support (+ employer) | `ak.child_support` / `respondent.employer_name` | 🟡 monthly take-home pay — **AKG3** |
| 8 | Other cases | `prior_orders.exists` | 🟡 PO existence only — **AKG5** |
| 9 | Law-enforcement assistance (a-e) | `ak.le_assistance` | ✅ |
| 10 | Respondent address / employer | `respondent.last_known_address` / `.employer_name` | ✅ |
| 10 | Respondent phone / email | — | ❌ **AKG6** |
| 11 | Petitioner safe mailing / phone / email (DV-128) | derived / `petitioner.safe_mailing_address` / `.safe_phone` / `.safe_email` | ✅ |
| verification | Petitioner signature | `petitioner.legal_name` | ✅ |

## Gaps — status

- **AKG1** — the item-1 "did you notify respondent before filing" question and
  the description of notification efforts.
- **AKG2** — the §5(g)(3) essential-items checkboxes (intake collects a free-text
  list instead of the specific boxes).
- **AKG3** — the filing-costs amount (6c), expense amounts, and the respondent's
  monthly take-home pay for child support (bring DR-305 + proof of income).
- **AKG4** — per-child DOB and petitioner/respondent relationship for the §7
  custody table, plus the existing-custody-order detail.
- **AKG5** — the full §8 other-cases list (only protective-order existence is
  collected).
- **AKG6** — respondent phone / email (§10).

**For Pranav:** confirm the `⚖️` rows — the order type, the AS 18.66 relationship
basis, and every §5/§6 protection box. The wiring is done.
