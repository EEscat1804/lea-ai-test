# Form 4-961 coverage map — intake → form (New Mexico)

How completely the current Vault intake fills the New Mexico **Petition for Order
of Protection from Domestic Abuse** (Form 4-961, §§ 40-13-1 to 40-13-8 NMSA 1978).

Audit artifact for legal review. **An attorney (Pranav) must confirm the
`needs legal review` rows** (the relationship basis and every relief box).
Unflagged != signed off.

Legend: ✅ mapped · 🟡 partial · ❌ not collected · ⚖️ needs legal review

> The NM intake (`_nm_step` + the shared interpreter block) fills the NM-specific
> items end to end. The form is **alive**: intake → jurisdiction-aware questions
> → filled petition.

## Item-by-item

| Section | Field | Intake source | State |
|---|---|---|---|
| caption | County / judicial district / petitioner / respondent | `nm.county` / `nm.judicial_district` / `petitioner.legal_name` / `respondent.legal_name` | ✅ |
| 1 | Interpreter (language) | `petitioner.interpreter_language` | ✅ |
| 2A | Relationship basis | `relationship.type` | ✅⚖️ |
| 2B | Respondent's firearms | `firearm.types[]` / `firearm.respondent_has_access` | ✅ |
| 3 | Minor children (UCCJEA) | `protected_persons.children[]` | 🟡 names; DOB/relationship/residence history — **NMG1** |
| 4 | Other cases | `prior_orders.exists` | 🟡 existence only — **NMG2** |
| 5A | Domestic-abuse acts (+ date / place) | `incidents[].narrative` / `.date` / `.location` | ✅ |
| 5C | Others present | `incidents[].witnesses_present` | ✅ |
| 5D | Drugs/alcohol role | `nm.drugs_alcohol` | ✅ |
| 5E | Weapons used | `incidents[].weapon_involved` | ✅ |
| 5F | Prior abuse | `nm.prior_abuse` | ✅ |
| 6 (A-J) | Requests to the court | `nm.relief` | ✅⚖️ |
| 6 B1/D | Residence to leave / retrieval address | `nm.residence_address` / `nm.retrieve_address` | ✅ |
| 6 G | Support for children / petitioner | `nm.support_types` | ✅ |
| 6 F/I | Children contact / other relief | `nm.children_contact` / `nm.other_relief` | ✅ |
| 7 | Petitioner address (sealed) + safe mailing | derived / `petitioner.safe_mailing_address` | ✅ |
| 9 | Respondent address / DOB / work / in jail | `respondent.last_known_address` / `.dob` / `.employer_address` / `nm.respondent_in_jail` | ✅ |
| verification | Petitioner signature | `petitioner.legal_name` | ✅ |

## Gaps — status

- **NMG1** — per-child DOB / relationship-to-each-party / residence history and
  other-custodian info (item 3, UCCJEA).
- **NMG2** — the full item-4 other-cases list (type/year/case#/where); only
  protective-order existence is collected.

> Item 5B (credible-threat statement) and item 8 (notice-to-respondent) are
> narrative/safety determinations left to the petitioner/advocate, not auto-filled.

**For Pranav:** confirm the `⚖️` rows — the § 40-13 relationship basis (including
the sexual-assault / stalking bases) and every item-6 (A-J) relief box. The
wiring is done.
