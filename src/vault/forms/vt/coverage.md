# Form 400-00150C coverage map — intake → form (Vermont)

How completely the current Vault intake fills the Vermont **Complaint for Relief
from Abuse** (form 400-00150C, 15 V.S.A. § 1101 et seq., Rev. 08/2017).

Audit artifact for legal review. **An attorney (Pranav) must confirm the
`needs legal review` rows** (the relationship basis, item 1 acts, item 2/3 facts,
and every emergency/final relief box). Unflagged != signed off.

Legend: ✅ mapped · 🟡 partial · ❌ not collected · ⚖️ needs legal review

> The VT intake (the VT block — no shared Tier-2 gates apply) fills the
> VT-specific items end to end. The form is **alive**: intake →
> jurisdiction-aware questions → filled complaint.

## Item-by-item

| Section | Field | Intake source | State |
|---|---|---|---|
| caption | Unit (county) | `vt.unit` | ✅ |
| caption | Plaintiff (+ DOB) | `petitioner.legal_name` / `.dob` | ✅ |
| caption | Plaintiff address (withheld; safe mailing only) | derived (defaulted on) / `petitioner.safe_mailing_address` | ✅ |
| caption | Defendant (+ DOB + full physical address) | `respondent.legal_name` / `.dob` / `.last_known_address` | ✅ |
| relationship | Relationship of the parties | `relationship.type` | ✅⚖️ |
| proceedings | Existing order/proceeding matrix (7 types) | `vt.existing_proceedings` | ✅ |
| proceedings | State(s) / County of that case | `vt.existing_proceedings_where` | ✅ |
| proceedings | Attorney for Plaintiff / Defendant | — | ❌ **VTG1** |
| 1 | Date of abuse | `incidents[].date` | ✅ |
| 1 | Directed at Plaintiff / child(ren) | derived from `vt.includes_children` | 🟡⚖️ plaintiff always; children via flag |
| 1 | Names of child(ren) | `protected_persons.children[]` | 🟡 names; form wants per-child DOB + relationship — **VTG2** |
| 1 | Acts (physical harm / fear / child abuse / stalking / sexual assault) | `vt.abuse_acts` | ✅⚖️ |
| 1 | Stalking date(s) | `vt.stalking_dates` | ✅⚖️ |
| 2 | Danger of further abuse | derived (asserted by filing) | ✅⚖️ |
| 3 | Defendant incarcerated/convicted (§ 1103(c)(1)(B)) | `vt.defendant_incarcerated` | ✅⚖️ |
| 4 | Forced from residence / residence to leave (+ owned/rented + in whose name) | `vt.residence_address` / `vt.residence_tenure` / `vt.residence_in_name` | ✅ |
| 5 | Defendant duty to support | `vt.final_relief` (child_support / living_expenses) | 🟡⚖️ inferred from relief |
| 6 | Recipient of public assistance | `vt.public_assistance` | ✅ |
| emergency | No abuse / refrain stalking-SA / leave residence / parental rights / no pet cruelty / stay away / no contact / other | `vt.emergency_relief` (+ `vt.stay_away_distance`, `vt.emergency_other`) | ✅⚖️ |
| final | No abuse / refrain stalking-SA / leave residence / parental rights / pet possession / stay away / no contact / living expenses / child support / other | `vt.final_relief` (+ `vt.stay_away_distance`, `vt.final_other`) | ✅⚖️ |
| relief | Parental rights & responsibilities per-child detail | `protected_persons.children[]` | 🟡 names only; form wants name + DOB + rel-to-plaintiff + rel-to-defendant — **VTG2** |
| affidavit | Abuse narrative | `incidents[].narrative` | ✅ (separate affidavit) |
| signature | Plaintiff signature / date | `petitioner.legal_name` | ✅ (date set at filing) |

## Gaps — status

- **VTG1** — attorney-for-plaintiff / attorney-for-defendant names; intake
  collects neither (most survivors self-file).
- **VTG2** — per-child detail (DOB, relationship to plaintiff, relationship to
  defendant) for both the item-1 child list and the parental-rights relief; intake
  holds child names only.

**For Pranav:** confirm the `⚖️` rows — the relationship basis, the item-1 acts,
the item-2 danger and item-3 incarceration facts, and every emergency / final
relief box. The wiring is done.
