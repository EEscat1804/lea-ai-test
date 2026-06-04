# PO DV Form 03 coverage map — intake → form (Wyoming)

How completely the current Vault intake fills the Wyoming **Petition for Domestic
Violence Order of Protection** (PO DV Form 03, W.S. § 35-21-101 to 112, Last Form
Revision October 2025).

Audit artifact for legal review. **An attorney (Pranav) must confirm the
`needs legal review` rows** (the household-member relationship basis and every
relief box). Unflagged != signed off.

Legend: ✅ mapped · 🟡 partial · ❌ not collected · ⚖️ needs legal review

> The WY intake (shared Tier-2 + the WY block) fills the WY-specific items end to
> end. The form is **alive**: intake → jurisdiction-aware questions → filled
> petition.

## Item-by-item

| Section | Field | Intake source | State |
|---|---|---|---|
| ¶1 | County / judicial district / petitioner (+ DOB) | `wy.county` / `wy.judicial_district` / `petitioner.legal_name` / `.dob` | ✅ |
| ¶1 | Petitioner description (race/gender/ht/wt/eyes/hair) | — | ❌ **WYG1** |
| ¶1 | Confidential address/phone | derived | ✅ |
| ¶2 | Respondent (+ address / DOB / race / gender) | `respondent.legal_name` / `.last_known_address` / `.dob` / `.race` / `.gender` | ✅ |
| ¶2 | Respondent ht/wt/eyes/hair / employer / vehicle plate + desc / marks | `respondent.height` / `.weight` / `.eye_color` / `.hair_color` / `.employer_name` / `.vehicle_plate` / `.vehicle_make_model` / `.distinguishing_marks` | ✅ |
| ¶2 | Respondent DL / state-country of birth | — | ❌ **WYG2** |
| ¶3 | Respondent on DV probation / other cases | `wy.respondent_probation` / `prior_orders.exists` | 🟡 case list — **WYG3** |
| ¶5 | Petitioner county / abuse location | `wy.county` / `incidents[].location` | ✅ |
| ¶6 | Household-member relationship | `relationship.type` | ✅⚖️ |
| ¶7 | Minor children | `protected_persons.children[]` | 🟡 names; DOB/race/gender/residence — **WYG4** |
| ¶8 | Abuse date / narrative | `incidents[].date` / `.narrative` | ✅ |
| ¶9-10 | Weapons used / firearms (+ types + locations) | `incidents[].weapon_involved` / `firearm.respondent_has_access` / `.types[]` / `.locations[]` | ✅ |
| ¶11 A-T | Relief checklist | `wy.relief` | ✅⚖️ |
| ¶11 D | Stay-away distance + places | `wy.stay_away_distance` / `wy.stay_away_places` | ✅ |
| ¶11 G/J/K | Property / pets / wireless detail | `wy.property_possession_detail` / `wy.pets_detail` / `wy.wireless_numbers` | ✅ |
| ¶11 L/O | Custody-to / visitation terms / supervised detail | `wy.custody_to` / `wy.visitation_terms` / `wy.supervised_detail` | ✅ |
| ¶11 Q/T | Support / other-assistance detail | `wy.support_detail` / `wy.other_assistance` | ✅ |
| ¶12 | Hearing appearance (in person / virtual) | `wy.appearance` | ✅ |
| verification | Petitioner signature | `petitioner.legal_name` | ✅ |

## Gaps — status

- **WYG1** — the petitioner's own physical description (race/gender/height/etc.).
- **WYG2** — the respondent's driver's license and state/country of birth.
- **WYG3** — the full ¶3 other-court-cases list (only protective-order existence
  and the DV-probation flag are collected).
- **WYG4** — per-child DOB/race/gender and the residence/lives-with detail (¶7).

**For Pranav:** confirm the `⚖️` rows — the ¶6 household-member relationship basis
and every ¶11 (A-T) relief box. The wiring is done.
