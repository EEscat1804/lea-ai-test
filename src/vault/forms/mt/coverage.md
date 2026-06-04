# Form OVS 3 coverage map — intake → form (Montana)

How completely the current Vault intake fills the Montana **Sworn Petition for
Temporary Order of Protection and Request for Hearing** (AGO Form OVS 3, Mont.
Code Ann. § 40-15-201, Revised 02/11).

Audit artifact for legal review. **An attorney (Pranav) must confirm the
`needs legal review` rows** (the relationship basis, the immediate-danger
allegation, and every item-1 through item-12 relief box). Unflagged != signed off.

Legend: ✅ mapped · 🟡 partial · ❌ not collected · ⚖️ needs legal review

> The MT intake (Tier-1 core + the MT block) fills the MT-specific items end to
> end. The form is **alive**: intake → jurisdiction-aware questions → filled
> petition.

## Item-by-item

| Section | Field | Intake source | State |
|---|---|---|---|
| caption | Court type / county / petitioner (+ address / phone) / respondent | `mt.court_type` / `mt.county` / `petitioner.legal_name` / `.safe_mailing_address` / `.safe_phone` / `respondent.legal_name` | ✅ |
| 1 | In danger of harm (TOP request) | derived | ✅⚖️ |
| 2 | Protected: self / children / others | derived / `protected_persons.children[]` / `mt.other_protected` | ✅ (children 🟡 — MTG2) |
| 3 | Residence / abuse location | `respondent.last_known_address` / `incidents[].location` | 🟡 city/county/state — MTG1 |
| 3 | Living situation (+ return reason) | `mt.living_situation` / `mt.return_reason` | ✅ |
| 4 | Relationship basis | `relationship.type` | ✅⚖️ (alt. bases — MTG3) |
| 5A | Recent abuse (date / who / where / narrative / weapon / injury / police) | `incidents[].date` / `.witnesses_present` / `.location` / `.narrative` / `.weapon_involved` / `.injury` / `.police_called` | ✅ |
| 5B | Past abuse | — | ❌ MTG4 |
| 6 | Firearms possessed / location | `firearm.respondent_has_access` / `firearm.locations[]` | ✅ |
| 7 | Other court cases | `prior_orders.exists` / `mt.other_cases` | 🟡 existence + free text — MTG5 |
| 1-12 | Relief checklist | `mt.relief` | ✅⚖️ |
| 4 | Stay-away distance + places | `mt.stay_away_feet` / `mt.stay_away_places` | ✅ |
| 5/7/10 | Firearms / possession / other-safety details | `mt.firearms_relief_detail` / `mt.possession_detail` / `mt.other_safety_detail` | ✅ |
| 11 | Parenting (choose one) | `mt.parenting` | ✅ (Appendix A — MTG6) |
| verification | Petitioner signature | `petitioner.legal_name` | ✅ |

## Gaps — status

- **MTG1** — the residence block wants city / county / state separately for the
  petitioner, the respondent, and the abuse location; intake maps single address /
  location strings instead.
- **MTG2** — per-child age / relationship-to-each-party / lives-with for the
  protected-children table; only names are collected.
- **MTG3** — the sexual-assault/stalking basis and the parent-of-child-under-16
  contact basis (para 4) are alternatives to the relationship checklist; only the
  intake `relationship.type` is mapped.
- **MTG4** — the past-abuse narrative (para 5B) is not collected separately from
  the most-recent statement.
- **MTG5** — the family-law and criminal-case detail tables (county / court /
  pending / parenting-plan) in para 7; only protective-order existence + a free-text
  note are collected.
- **MTG6** — Appendix A (the temporary visitation schedule and the full children
  table) is not assembled; `mt.parenting` records only which item-11 option was
  chosen.

**For Pranav:** confirm the `⚖️` rows — the relationship basis, the
immediate-danger allegation, and every item-1 through item-12 relief box. The
wiring is done.
