# AOC-275.1 coverage map — intake → form (Kentucky)

How completely the current Vault intake fills the Kentucky **Petition/Motion for
Order of Protection** (AOC-275.1, KRS Chapter 403 / 456, Rev. 6-23).

Audit artifact for legal review. **An attorney (Pranav) must confirm the
`needs legal review` rows** (the relationship basis, the emergency/ex-parte
election, the petitioner-address handling, and every Motion-for-Relief restraint).
Unflagged != signed off.

Legend: ✅ mapped · 🟡 partial · ❌ not collected · ⚖️ needs legal review

> The KY intake (Tier-1 core + the shared physical + employer gates + the KY block)
> fills the KY-specific items end to end. The form is **alive**: intake →
> jurisdiction-aware questions → filled petition.

## Item-by-item

| Section | Field | Intake source | State |
|---|---|---|---|
| caption | County / case number / court / division | `ky.county` / clerk | ✅ (case no. — KYG1) |
| petitioner | Name / residence / birthdate | `petitioner.legal_name` / `.safe_mailing_address` / `.dob` | ✅⚖️ (address) |
| respondent box | Name / address / sex / race / dob | `respondent.legal_name` / `.last_known_address` / `.gender` / `.race` / `.dob` | ✅ |
| respondent box | Height / weight / eyes / hair / marks | `respondent.height` / `.weight` / `.eye_color` / `.hair_color` / `.distinguishing_marks` | ✅ |
| respondent box | SSN / driver's license | — | ❌ KYG2 |
| respondent | Employer name / address | `respondent.employer_name` / `.employer_address` | ✅ |
| CAUTION | Weapon involved / armed & dangerous | `ky.caution` | ✅ |
| caption | Divorce / custody / visitation case | `prior_orders.exists` | 🟡 existence — KYG3 |
| 2 | Relationship basis | `ky.relationship_basis` | ✅⚖️ |
| narrative | Acts of DV / dating violence / stalking / SA (+ date / county) | `incidents[].narrative` / `.date` / `.location` | ✅ |
| 3 | Minor children | `protected_persons.children[]` | 🟡 names — KYG4 |
| Motion (1) | Emergency / temporary order (ex parte) | `ky.ex_parte` | ✅⚖️ |
| Motion | Relief restraints | `ky.relief` | ✅⚖️ |
| Motion | Stay-away location / vacate address / other | `ky.stay_away_location` / `ky.vacate_address` / `ky.relief_other_detail` | ✅ |
| Motion | Firearm access context | `firearm.respondent_has_access` | ✅ |
| verification | Petitioner signature | `petitioner.legal_name` | ✅ |

## Gaps — status

- **KYG1** — the case number / court / division are assigned by the clerk at
  filing.
- **KYG2** — the identifier box wants the respondent's SSN / driver's license (for
  LINK / criminal-history lookup); intake does not collect them. KY requests
  temporary child support but the form has no *petitioner* SSN field, so KY is not
  in the SSN-for-support gate.
- **KYG3** — the divorce / custody / visitation case wants the court name; only
  protective-order existence is mapped.
- **KYG4** — the §3 children table wants per-child birthdate / address / parent /
  seeking-protection; only names are collected.

**For Pranav:** confirm the `⚖️` rows — the §2 relationship basis, the
emergency/ex-parte election, the petitioner-address handling (served copy is
redacted; page-4 stay-away addresses are available to the respondent), and every
Motion-for-Relief restraint. The wiring is done.
