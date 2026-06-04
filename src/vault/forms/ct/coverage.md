# JD-FM-137 coverage map — intake → form (Connecticut)

How completely the current Vault intake fills the Connecticut **Application for
Relief from Abuse** (JD-FM-137, C.G.S. §§ 46b-15 et al., Rev. 10-21).

Audit artifact for legal review. **An attorney (Pranav) must confirm the
`needs legal review` rows** (the relationship basis and every relief box).
Unflagged != signed off.

Legend: ✅ mapped · 🟡 partial · ❌ not collected · ⚖️ needs legal review

> The CT intake (shared Tier-2 + the CT block) fills the CT-specific items end to
> end. The form is **alive**: intake → jurisdiction-aware questions → filled
> application.

## Item-by-item

| Section | Field | Intake source | State |
|---|---|---|---|
| caption | Judicial district / court location | `ct.judicial_district` | ✅ |
| applicant | Name / DOB / mailing (safe) / interpreter | `petitioner.legal_name` / `.dob` / `.safe_mailing_address` / `.interpreter_language` | ✅ |
| respondent | Interpreter needed / language | — | ❌ **CTG2** |
| applicant | Sex / race / home address / work address | — | ❌ **CTG1** (home address withheld by design) |
| respondent | Name / DOB / sex / race / address | `respondent.legal_name` / `.dob` / `.gender` / `.race` / `.last_known_address` | ✅ |
| respondent | Height / weight (other identifiers) | `respondent.height` / `.weight` | ✅ |
| respondent | Telephone | — | ❌ **CTG2** |
| relationship | Respondent is (select all that apply) | `relationship.type` | ✅⚖️ |
| other cases | Other protective/restraining order | `prior_orders.exists` | 🟡 existence only; docket/court — **CTG3** |
| other cases | Dissolution/custody/visitation action | — | ❌ **CTG3** |
| firearms | Possesses firearm(s) (Q3) | `firearm.respondent_has_access` | ✅ |
| firearms | Permit / eligibility cert / ammunition (Q1, Q2, Q4) | — | ❌ **CTG4** |
| affidavit | Date / location / narrative | `incidents[].date` / `.location` / `.narrative` | ✅ |
| relief 1 | Conditions CT01/CT03/CT05/CT14/CT15/CT16/CT19/CT31 | `ct.relief` | ✅⚖️ |
| relief 1 | CT19 children table | `protected_persons.children[]` | 🟡 names; sex/DOB per child — **CTG5** |
| relief 2 | CT20 custody (+ table) / CT21 with visitation (+ terms) / CT22 without visitation | `ct.relief` / `protected_persons.children[]` / `ct.visitation` / `ct.visitation_terms` | ✅⚖️ |
| relief 3 | Further order (+ detail) | `ct.relief` / `ct.further_order_detail` | ✅⚖️ |
| relief 4, 5 | Send order to applicant's / children's school | — | ❌ **CTG6** |
| relief 6 | Ex parte (immediate) relief | `ct.ex_parte` | ✅ |
| verification | Applicant signature | `petitioner.legal_name` | ✅ |

## Gaps — status

- **CTG1** — applicant sex / race, and the home and work addresses (the latter
  withheld by design; the form discloses any address to the respondent).
- **CTG2** — respondent telephone.
- **CTG3** — docket numbers / court locations for an existing order, and any
  dissolution/custody/visitation case.
- **CTG4** — the optional firearm questions other than possession (permit,
  eligibility/ammunition certificate, ammunition).
- **CTG5** — per-child sex/DOB for the CT19 (protect) and CT20 (custody) tables.
- **CTG6** — the school-notification items (4, 5).

## Note

- Maintenance/support is a separate form (**JD-FM-233**), not assembled here.

**For Pranav:** confirm the `⚖️` rows — the relationship basis and every relief
condition box (CT01-CT31, custody, visitation, further order). The wiring is done.
