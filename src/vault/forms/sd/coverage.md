# Form UJS-091A coverage map — intake → form (South Dakota)

How completely the current Vault intake fills the South Dakota **Petition and
Affidavit for a Protection Order (Domestic Abuse)** (Form UJS-091A / -091AJ
juvenile, SDCL ch. 25-10, Rev. 07/21).

Audit artifact for legal review. **An attorney (Pranav) must confirm the
`needs legal review` rows** (the relationship basis, the prior-PO / weapon-threat
history, and every items 1-11 relief box plus the ex parte request). Unflagged !=
signed off.

Legend: ✅ mapped · 🟡 partial · ❌ not collected · ⚖️ needs legal review

> The SD intake (the `_sd_step` block + the shared minor-filing gate) fills the
> SD-specific items end to end. SD is correctly absent from the physical/vehicle
> gates. The form is **alive**: intake → jurisdiction-aware questions → filled
> petition.

## Item-by-item

| Section | Field | Intake source | State |
|---|---|---|---|
| caption | County | `sd.county` | ✅ |
| caption | Judicial circuit | — | ❌ **SDG1** (set by county at filing) |
| caption | TPO No. | — | ❌ assigned by the clerk |
| caption | Petitioner / Respondent under-18 checkboxes | `petitioner.minor_filing_path` | ✅⚖️ (shared minor gate) |
| filer | Filer (petitioner or parent/guardian) | `petitioner.minor_filing_path` | 🟡⚖️ |
| residency | Petitioner county | `sd.county` | 🟡 from filing county |
| residency | Respondent county/state | `respondent.last_known_address` | 🟡 address, not parsed county — **SDG2** |
| residency | Protected parties county/state | — | ❌ **SDG2** |
| custody | Existing custody order (+ county/case #) | `sd.existing_custody_order` / `sd.custody_order_details` | ✅ |
| relationship | Relationship categories (check all) | `relationship.type` | ✅⚖️ |
| facts | Date of abuse | `incidents[].date` | ✅ |
| facts | Approximate time | — | ❌ **SDG3** |
| facts | Acts of domestic abuse (9 boxes) | `sd.abuse_acts` | ✅⚖️ |
| facts | Detailed description | `incidents[].narrative` | ✅ |
| history | Law enforcement called? | `incidents[].police_called` | ✅ |
| history | Respondent arrested? | `sd.respondent_arrested` | ✅ |
| history | Respondent in jail? | `sd.respondent_in_jail` | ✅ |
| history | Violated previous PO? (+ whom) | `sd.respondent_violated_po` / `sd.violated_po_whom` | ✅⚖️ |
| history | Found guilty of violating PO? (+ details) | `sd.respondent_convicted_po` / `sd.convicted_po_details` | ✅⚖️ |
| history | Possesses guns/weapons? | `firearm.respondent_has_access` | ✅ |
| history | Weapon used this incident? | `incidents[].weapon_involved` | ✅ |
| history | Threatened anyone with a weapon? | `sd.respondent_threatened_weapon` | ✅⚖️ |
| history | Other similar incidents | `incidents[].pattern_frequency` | 🟡 partial — **SDG3** |
| 1 | Restrain from abuse/threats/stalking | `sd.relief` | ✅⚖️ |
| 2 | Order duration (≤5 years) | `sd.relief` (+ `sd.duration`) | ✅⚖️ |
| 3 | Exclude respondent from residence | `sd.relief` (+ `sd.residence_address`) | ✅⚖️ |
| 4 | Stay-away distance + targets (A-E) | `sd.relief` (+ `sd.stay_away_distance`, `sd.stay_away_targets`, `sd.stay_away_other`) | ✅⚖️ |
| 5 | Temporary custody (+ children) | `sd.relief` / `protected_persons.children[]` | 🟡⚖️ names only — **SDG4** |
| 6 | Temporary visitation | `sd.relief` (+ `sd.visitation_detail`) | ✅⚖️ |
| 7 | Child / spousal support (+ amounts) | `sd.relief` (+ `sd.support_types`, `sd.child_support_amount`, `sd.spousal_support_amount`) | ✅⚖️ |
| 8 | Parenting classes (SDCL 25-10-5) | `sd.relief` | ✅⚖️ |
| 9 | Counseling (+ detail) | `sd.relief` (+ `sd.counseling_detail`) | ✅⚖️ |
| 10 | No contact (direct/indirect) | `sd.relief` | ✅⚖️ |
| 11 | Other relief (+ detail) | `sd.relief` (+ `sd.other_relief`) | ✅⚖️ |
| ex parte | Immediate TPO request (+ reasons) | `sd.ex_parte` / `sd.ex_parte_reasons` | ✅⚖️ |
| verification | Filer/Petitioner signature (sworn) | `petitioner.legal_name` | ✅ (notary/date at filing) |

## Gaps — status

- **SDG1** — the judicial circuit; determined by county at filing. Intake collects
  county only.
- **SDG2** — the respondent's residence parsed to county, and the protected
  parties' county/state of residence; intake holds the respondent's last-known
  address and no separate protected-party residence.
- **SDG3** — the clock time of the incident and the dedicated "other similar
  incidents" narrative; intake holds the date and the pattern/frequency only.
- **SDG4** — per-child detail (DOB, relationship to respondent) for the custody
  request; intake holds child names.

**For Pranav:** confirm the `⚖️` rows — the relationship basis, the prior-PO and
weapon-threat history, and every items 1-11 relief box plus the ex parte request.
The wiring is done.
