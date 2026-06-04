# MS petition coverage map — intake → form (Mississippi)

How completely the current Vault intake fills the Mississippi **Petition for
Domestic Abuse Protection Order** (M.C.A. § 93-21-1 et seq.).

Audit artifact for legal review. **An attorney (Pranav) must confirm the
`needs legal review` rows** (the relationship basis, the emergency-relief election,
the acts of abuse, the confidential-address election, every §9 relief box, and the
Chancery/County-only relief). Unflagged != signed off.

Legend: ✅ mapped · 🟡 partial · ❌ not collected · ⚖️ needs legal review

> The MS intake (Tier-1 core + the shared physical + employer gates + the MS block)
> fills the MS-specific items end to end. The form is **alive**: intake →
> jurisdiction-aware questions → filled petition.

## Item-by-item

| Section | Field | Intake source | State |
|---|---|---|---|
| caption | Court type / county / cause number | `ms.court_type` / `ms.county` / clerk | ✅ (cause no. — MSG2) |
| top | Emergency relief requested | `ms.emergency_relief` | ✅⚖️ |
| 1 | Petitioner / DOB / protected children | `petitioner.legal_name` / `.dob` / `protected_persons.children[]` | ✅ (children 🟡 — MSG3) |
| 1 | Relationship basis | `ms.relationship_basis` | ✅⚖️ |
| 2 | Confidential address (SF2) / address | derived / `petitioner.safe_mailing_address` | ✅⚖️ |
| 3 | Abuse location / respondent location | `incidents[].location` / `respondent.last_known_address` | ✅ |
| 4 | Respondent name / address / dob / sex / race | `respondent.legal_name` / `.last_known_address` / `.dob` / `.gender` / `.race` | ✅ |
| 4 | Height / weight / eyes / hair / features | `respondent.height` / `.weight` / `.eye_color` / `.hair_color` / `.distinguishing_marks` | ✅ |
| 4 | SSN / driver's license | — | ❌ MSG4 |
| 4 | Employer | `respondent.employer_name` | ✅ |
| 4 | Caution / medical conditions | `ms.caution` | ✅ |
| 5 | Acts of abuse | `ms.abuse_acts` | ✅⚖️ |
| 6 | Narrative (+ date) | `incidents[].narrative` / `.date` | ✅ |
| 7/8 | Divorce / children in common | `prior_orders.exists` / `relationship.children_in_common` | 🟡 / ✅ (MSG5) |
| 9 | Relief | `ms.relief` | ✅⚖️ |
| 9 | Residence address / belongings location | `ms.residence_address` / `ms.belongings_location` | ✅ |
| 9 (cont.) | Chancery/County relief (custody / support / visitation / restitution) | `ms.chancery_relief` | ✅⚖️ |
| 10 | Other cases | `prior_orders.exists` / `ms.other_cases` | 🟡 existence + free text — MSG5 |
| verification | Petitioner signature | `petitioner.legal_name` | ✅ |

## Gaps — status

- **MSG1** — the petition prints no form number and no revision date; `FORM_ID` is
  descriptive and `FORM_REVISION` is `"unknown"`.
- **MSG2** — the cause number is assigned by the clerk at filing.
- **MSG3** — the §1 protected-person blocks want per-person DOB / sex / race /
  relationship; only names are collected.
- **MSG4** — the §4 block wants the respondent's SSN / driver's license; intake
  does not collect them. The Chancery/County-only relief includes support, but the
  form has no *petitioner* SSN field, so MS is not in the SSN-for-support gate.
- **MSG5** — the §7 divorce detail and the §10 other-case detail are not collected;
  only protective-order / divorce existence + a free-text note are mapped.

**For Pranav:** confirm the `⚖️` rows — the §1 relationship basis, the
emergency-relief election, the §5 acts of abuse, the §2 confidential-address
election, every §9 relief box, and the §9 Chancery/County-only relief. The wiring
is done.
