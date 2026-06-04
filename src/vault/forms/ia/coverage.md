# Form 11 coverage map — intake → form (Iowa)

How completely the current Vault intake fills the Iowa **Petition for Relief from
Domestic Abuse** (Rule 17.10—Form 11, Iowa Code chapter 236, November 2022).

Audit artifact for legal review. **An attorney (Pranav) must confirm the
`needs legal review` rows** (the relationship basis, the abuse types, the
temporary/final order election, the confidentiality requests, and every §23C
item-1 through item-13 relief box). Unflagged != signed off.

Legend: ✅ mapped · 🟡 partial · ❌ not collected · ⚖️ needs legal review

> The IA intake (Tier-1 core + the shared minor + employer gates + the IA block)
> fills the IA-specific items end to end. The form is **alive**: intake →
> jurisdiction-aware questions → filled petition.

## Item-by-item

| Section | Field | Intake source | State |
|---|---|---|---|
| caption / 2 | County / civil number | `ia.county` / clerk | ✅ (civil no. — IAG2) |
| 1/3 | Plaintiff name / mailing address | `petitioner.legal_name` / `.safe_mailing_address` | ✅⚖️ (address) |
| 4/6 | Defendant name / address / employer | `respondent.legal_name` / `.last_known_address` / `.employer_name` / `.employer_address` | ✅ |
| 5 | Defendant minor / year of birth | `ia.defendant_minor` / `respondent.dob` | ✅ (year — IAG3) |
| 7 | Relationship (free text + basis) | `relationship.type` / `ia.relationship_basis` | ✅⚖️ |
| 8 | Abuse types (physical / sexual / threats) | `ia.abuse_types` | ✅⚖️ |
| 9A | Recent abuse narrative (+ date / location) | `incidents[].narrative` / `.date` / `.location` | ✅ |
| 9B | Past abuse | — | ❌ IAG4 |
| 10 | Firearms access / detail | `firearm.respondent_has_access` / `firearm.locations[]` | ✅ |
| 11 | Children in common | `protected_persons.children[]` | 🟡 names — IAG5 |
| 23 A/B | Temporary / final order election | `ia.order_request` | ✅⚖️ |
| 23C 1-13 | Order checklist | `ia.relief` | ✅⚖️ |
| 23C 7/10/13 | Home address / support detail / other | `ia.home_address` / `ia.support_detail` / `ia.relief_other_detail` | ✅ (support SSN — IAG6) |
| 20 | Possession requests (+ residence / vehicle / pet detail) | `ia.possession_requests` / `ia.residence_detail` / `ia.vehicle_detail` / `ia.pet_detail` | ✅ |
| 22 | Counseling | `ia.counseling` | ✅ |
| 24 | Confidentiality / sealing | `ia.confidential_requests` | ✅⚖️ |
| 15-18 | Residence history / custody tables | `prior_orders.exists` (§17 only) | 🟡 existence — IAG7 |
| 27 | Plaintiff signature | `petitioner.legal_name` | ✅ |

## Gaps — status

- **IAG1** — Form 11 has no short form number; `FORM_ID` is the descriptive
  "Rule 17.10 Form 11".
- **IAG2** — the civil number is filled in by the clerk of court.
- **IAG3** — §5B wants the defendant's year of birth; intake holds a full date.
- **IAG4** — the §9B past-abuse narrative is not collected separately from the
  most-recent statement.
- **IAG5** — the §11 children table wants initials / birth year / county-state
  (full detail goes on the Protected Information Disclosure form); only names are
  collected.
- **IAG6** — §19/§23 financial support: the income/amount tables and the
  petitioner SSN are not collected here (SSN goes on the Protected Information
  Disclosure form), so IA is not in the SSN-for-support gate.
- **IAG7** — the §15-18 5-year residence-history and third-party-custody tables
  are not collected; only §17 other-order existence is mapped.

**For Pranav:** confirm the `⚖️` rows — the relationship basis (§7B), the abuse
types (§8), the temporary/final order election (§23A/B), the §24 confidentiality
requests, and every §23C item-1 through item-13 relief box. The wiring is done.
