# Form C-2 coverage map — intake → form (Alabama)

How completely the current Vault intake fills the Alabama **Petition for
Protection from Abuse** (Form C-2, Ala. Code § 30-5-1 et seq., Rev. 10/2023).

Audit artifact for legal review. **An attorney (Pranav) must confirm the
`needs legal review` rows** (eligibility, the relationship basis, and every
acts/relief box). Unflagged != signed off.

Legend: ✅ mapped · 🟡 partial · ❌ not collected · ⚖️ needs legal review

> The AL intake (the AL block) fills the AL-specific items end to end. The form
> is **alive**: intake → jurisdiction-aware questions → filled petition.

## Item-by-item

| Section | Field | Intake source | State |
|---|---|---|---|
| caption | County / plaintiff / defendant (+ address / DOB / age) | `al.county` / `petitioner.legal_name` / `respondent.legal_name` / `.last_known_address` / `.dob` / derived | ✅ |
| caption | Defendant SSN (last 4) | — | ❌ **ALG1** (sensitive) |
| caption | Plaintiff address withheld (§ 30-5-5(f)(1)) | derived | ✅ |
| §I | Eligible adult victim (18+) | derived from `petitioner.dob` | ✅⚖️ |
| §I | Minor/guardian eligibility | — | ❌⚖️ **ALG2** |
| §I.1-6 | Relationship basis (ONE) | `relationship.type` | ✅⚖️ |
| resident | Plaintiff county / age | `al.county` / derived | ✅ |
| resident | Other civil/DR case / criminal charges | — | ❌ **ALG3** |
| page 2 | County where abuse occurred | `incidents[].location` | 🟡 confirm county |
| page 2 | Request type (protection/emergency/change) | `al.request_type` | ✅ |
| §II | Acts of abuse (checklist) | `al.abuse_acts` | ✅⚖️ |
| §III | Date / description of abuse | `incidents[].date` / `.narrative` | ✅ |
| §III | Why plaintiff fears further abuse | — | ❌ **ALG4** |
| §IV | Existing PO against defendant | `prior_orders.exists` | 🟡 existence only — **ALG3** |
| §IV | Existing PO against plaintiff | — | ❌ **ALG3** |
| §V | Children (under 19) | `protected_persons.children[]` | 🟡 names; DOB/custody history — **ALG5** |
| §V | Existing custody order | — | ❌ **ALG5** |
| §VI | Residence ownership/rental basis | `al.residence_basis` | ✅ |
| §VII | Ex parte relief (1-10) | `al.ex_parte_relief` | ✅⚖️ |
| §VII(9) | Property to protect from disposal | `al.property_description` | ✅ |
| §VII(10) | Other ex parte relief | `al.other_ex_parte` | ✅ |
| §VIII | Final relief (11-19) | `al.final_relief` | ✅⚖️ |
| §VIII(11) | Visitation type / arrangement | `al.visitation_type` / `al.visitation_terms` | ✅ |
| §VIII(15) | Vehicle to possess | `al.vehicle_description` | ✅ |
| §VIII(19) | Other final relief | `al.other_final` | ✅ |
| verification | Plaintiff signature | `petitioner.legal_name` | ✅ |

## Gaps — status

- **ALG1** — defendant SSN (last 4); never collected (sensitive).
- **ALG2** — the §I minor/guardian/emancipated eligibility boxes (a legal
  determination; the adult box is derived from the petitioner's age).
- **ALG3** — other civil/DR/criminal cases, the existing-order county/state, and
  any protection order against the plaintiff.
- **ALG4** — the §III "why I fear further abuse" prompt (not a separate intake
  question).
- **ALG5** — per-child DOB and the six-month custody/residence history (§V), and
  any existing custody order.

**For Pranav:** confirm the `⚖️` rows — eligibility, the §I.1-6 relationship
basis (ONE box), and every §II/§VII/§VIII box. The wiring is done.
