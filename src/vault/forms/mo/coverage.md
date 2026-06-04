# AA40 coverage map — intake → form (Missouri)

How completely the current Vault intake fills the Missouri **Petition for a Court
Order of Protection - Adult** (SJRC AA40, RSMo 455.010 et seq., 09-25).

Audit artifact for legal review. **An attorney (Pranav) must confirm the
`needs legal review` rows** (the venue, the relationship basis, the acts, the
ex-parte basis, the serious-danger finding, and every §C relief box). Unflagged !=
signed off.

Legend: ✅ mapped · 🟡 partial · ❌ not collected · ⚖️ needs legal review

> The MO intake (Tier-1 core + the shared physical / vehicle / minor + employer
> gates + the MO block) fills the MO-specific items end to end. The form is
> **alive**: intake → jurisdiction-aware questions → filled petition.

## Item-by-item

| Section | Field | Intake source | State |
|---|---|---|---|
| caption | County / case number | `mo.county` / clerk | ✅ (case no. — MOG1) |
| top | Venue (I live / abuse here / served here) | `mo.venue` | ✅⚖️ |
| A | Petitioner / address | `petitioner.legal_name` / `.safe_mailing_address` | ✅⚖️ (address) |
| A | Respondent name / address / age / sex / race | `respondent.legal_name` / `.last_known_address` / `.age` / `.gender` / `.race` | ✅ |
| A | Height / weight / hair / eyes / marks | `respondent.height` / `.weight` / `.hair_color` / `.eye_color` / `.distinguishing_marks` | ✅ |
| A | Employer / vehicle / firearm | `respondent.employer_*` / `.vehicle_*` / `firearm.respondent_has_access` | ✅ |
| A | Relationship basis | `mo.relationship_basis` | ✅⚖️ |
| B | Acts | `mo.abuse_acts` | ✅⚖️ |
| B | Ex parte basis | `mo.ex_parte_basis` | ✅⚖️ |
| B | Narrative (+ dates / locations) | `incidents[].narrative` / `.date` / `.location` | ✅ |
| C1 | Relief ("NOT to") | `mo.relief` | ✅⚖️ |
| C1 | School / work address / stay-away feet | `mo.school_address` / `mo.work_address` / `mo.stay_distance_feet` | ✅ |
| C2 | Serious-danger 2-to-10-year request | `mo.serious_danger` | ✅⚖️ |
| C3-7 | Additional relief (custody / support / property / counseling / other) | `mo.additional_relief` | ✅⚖️ |
| C3/4/5 | Custody / support / property detail | `mo.custody_detail` / `mo.support_detail` / `mo.property_detail` | ✅ (support SSN — MOG2) |
| verification | Petitioner signature | `petitioner.legal_name` | ✅ |

## Gaps — status

- **MOG1** — the case number is assigned by the court at filing.
- **MOG2** — §C(4) child support / maintenance amounts are partially mapped via
  `mo.support_detail`; the petitioner SSN is not on AA40, so MO is not in the
  SSN-for-support gate.

**For Pranav:** confirm the `⚖️` rows — the venue, the §A relationship basis, the
§B acts, the §B ex-parte basis, the §C2 serious-danger finding, and every §C1 /
§C3-7 relief box. The wiring is done.
