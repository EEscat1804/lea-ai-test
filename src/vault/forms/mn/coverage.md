# OFP102 coverage map — intake → form (Minnesota)

How completely the current Vault intake fills the Minnesota **Petition for Order
for Protection (OFP)** (OFP102, Minn. Stat. § 518B.01, Rev. 7/25).

Audit artifact for legal review. **An attorney (Pranav) must confirm the
`needs legal review` rows** (the relationship basis, the immediate-danger
statement, the confidential-address election, every #15 ex parte relief item, and
every #16-#22 hearing-relief item). Unflagged != signed off.

Legend: ✅ mapped · 🟡 partial · ❌ not collected · ⚖️ needs legal review

> The MN intake (Tier-1 core + the shared minor + employer gates + the MN block)
> fills the MN-specific items end to end. The form is **alive**: intake →
> jurisdiction-aware questions → filled petition.

## Item-by-item

| Section | Field | Intake source | State |
|---|---|---|---|
| caption | County / judicial district / file number | `mn.county` / clerk | ✅ (district — MNG1) |
| 1 | Petitioner name / gender / race / DOB | `petitioner.legal_name` / `.gender` / `.race` / `.dob` | ✅ (gender/race — MNG2) |
| 1 | Confidential address (OFP107-P) / address | derived / `petitioner.safe_mailing_address` | ✅⚖️ |
| 3 | Other persons who need protection | `protected_persons.children[]` | 🟡 names — MNG3 |
| 6 | Respondent name / address / gender / race / DOB / employer | `respondent.legal_name` / `.last_known_address` / `.gender` / `.race` / `.dob` / `.employer_name` / `.employer_address` | ✅ |
| 7 | Relationship basis | `mn.relationship_basis` | ✅⚖️ |
| 11 | Narrative (+ date / witnesses / weapons / injuries / police) | `incidents[].narrative` / `.date` / `.witnesses_present` / `.weapon_involved` / `.injury` / `.police_called` | ✅ |
| 13 | Immediate danger | `mn.immediate_danger` | ✅⚖️ |
| 15 a-j | Ex parte relief | `mn.relief` | ✅⚖️ |
| 15 e/g/j | Other location / pet / other detail | `mn.other_location` / `mn.pet_detail` / `mn.relief_other_detail` | ✅ |
| 16-22 | Hearing relief (custody / support / property / restitution / counseling / firearms / extended) | `mn.hearing_relief` | ✅⚖️ |
| 17 | Support detail / incomes | `mn.support_detail` | ✅ (SSN — MNG4) |
| 8-10 | Other cases | `prior_orders.exists` / `mn.other_cases` | 🟡 existence + free text — MNG5 |
| verification | Petitioner signature | `petitioner.legal_name` | ✅ |

## Gaps — status

- **MNG1** — the judicial district / court file number are assigned by the clerk
  at filing.
- **MNG2** — the #1 petitioner gender / race (federal-reporting demographics) are
  not collected by Tier-1 intake.
- **MNG3** — the #3 other-protected-person blocks want per-person DOB / race /
  gender / relationship; only names are collected.
- **MNG4** — #17 financial support: the income tables are partially mapped via
  `mn.support_detail`, and the petitioner SSN is not on OFP102, so MN is not in the
  SSN-for-support gate.
- **MNG5** — the #8-#10 prior-OFP / other-case tables are not collected; only
  protective-order existence + a free-text note are mapped.

**For Pranav:** confirm the `⚖️` rows — the #7 relationship basis, the #13
immediate-danger statement, the confidential-address election, every #15 ex parte
relief item, and every #16-#22 hearing-relief item. The wiring is done.
