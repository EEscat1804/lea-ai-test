# Form 450 coverage map — intake → form (Delaware)

How completely the current Vault intake fills the Delaware **Petition for Order
of Protection from Abuse** (Family Court Form 450, 10 Del. C. § 1041 et seq.,
Rev. 3/26).

Audit artifact for legal review. **An attorney (Pranav) must confirm the
`needs legal review` rows** (the relationship basis and every relief / abuse /
aggravating box). Unflagged != signed off.

Legend: ✅ mapped · 🟡 partial · ❌ not collected · ⚖️ needs legal review

> The DE intake (shared Tier-2 + the DE block) fills the DE-specific items end to
> end. The form is **alive**: intake → jurisdiction-aware questions → filled
> petition.

## Item-by-item

| Section | Field | Intake source | State |
|---|---|---|---|
| caption | County / Petitioner (+ DOB / phone / email / safe mailing) | `de.county` / `petitioner.legal_name` / `.dob` / `.safe_phone` / `.safe_email` / `.safe_mailing_address` | ✅ |
| caption | Petitioner interpreter / language | `petitioner.interpreter_language` | ✅ |
| caption | Respondent (+ DOB / address) | `respondent.legal_name` / `.dob` / `.last_known_address` | ✅ |
| caption | Respondent phone / email | — | ❌ **DEG1** |
| caption | Child(ren) | `protected_persons.children[]` | 🟡 names; form wants per-child DOB / is-respondent's-child / relationship — **DEG2** |
| 1 | Confidential address (residence; children's) | derived (defaulted on; children when present) | ✅ |
| 2 | Relationship basis | `relationship.type` | ✅⚖️ |
| 3 | Acts of abuse (a-k) | `de.abuse_acts` | ✅⚖️ |
| 3 | Statement (date / location / narrative / injury / witnesses / weapon) | `incidents[].*` | ✅ |
| 4 | Respondent DE resident / connection to DE | `de.respondent_is_de_resident` / `de.de_connection` | ✅ |
| 5 | Firearms (describe / location) | `firearm.respondent_has_access` / `.types[]` / `.locations[]` | ✅ |
| protective | No abuse / stay away (+ places + other) / no contact | `de.relief` (+ `de.stay_away_places`, `de.stay_away_other`) | ✅⚖️ |
| protective | Extended duration (>2yr) + aggravating factors (1-6) | `de.extended_duration` / `de.aggravating_factors` | ✅⚖️ |
| ancillary | Exclusive residence (+ address) | `de.relief` (+ `de.residence_address`) | ✅⚖️ |
| ancillary | Compensation / reimburse / personal property / companion animal / return documents (+ details) | `de.relief` (+ `de.compensation_losses`, `de.reimburse_expenses`, `de.personal_property`, `de.companion_animal`, `de.return_documents`) | ✅⚖️ |
| ancillary | Custody | `de.relief` / `protected_persons.children[]` | 🟡 needs **Form 346** — **DEG2** |
| ancillary | Child support (employer / location) | `de.relief` / `respondent.employer_name` / `.employer_address` | ✅⚖️ |
| ancillary | Child support income / occupation; spousal-support amount | — | ❌ **DEG3** |
| ancillary | DV treatment evaluation / other (+ detail) | `de.relief` (+ `de.other_relief`) | ✅⚖️ |
| verification | Petitioner signature | `petitioner.legal_name` | ✅ |

## Gaps — status

- **DEG1** — respondent phone / email (caption); intake collects neither.
- **DEG2** — per-child detail (DOB, whether the respondent's child, relationship)
  and the **Form 346** Custody Separate Statement required when custody is sought.
- **DEG3** — respondent income / occupation and the spousal-support amount for
  the support requests; intake holds employer name/address only.

**For Pranav:** confirm the `⚖️` rows — the § 1041 relationship basis and every
abuse / relief / aggravating-factor box. The wiring is done.
