# Form NHJB-2050-DF coverage map — intake → form (New Hampshire)

How completely the current Vault intake fills the New Hampshire **Domestic
Violence Petition** (Form NHJB-2050-DF, RSA 173-B, rev. 03/15/2024).

Audit artifact for legal review. **An attorney (Pranav) must confirm the
`needs legal review` rows** (the relationship basis, the immediate-danger
allegation, and every item-1 through item-15 relief box). Unflagged != signed off.

Legend: ✅ mapped · 🟡 partial · ❌ not collected · ⚖️ needs legal review

> The NH intake (Tier-1 core + the NH block) fills the NH-specific items end to
> end. The form is **alive**: intake → jurisdiction-aware questions → filled
> petition.

## Item-by-item

| Section | Field | Intake source | State |
|---|---|---|---|
| caption | Court name | `nh.court_name` | ✅ |
| plaintiff | Name / DOB / sex / race / ethnicity | `petitioner.legal_name` / `.dob` / `.sex` / `.race` / `.ethnicity` | ✅ |
| defendant | Name / DOB / sex / address | `respondent.legal_name` / `respondent.dob` / `respondent.sex` / `respondent.last_known_address` | ✅ |
| relationship | Relationship to defendant | `relationship.type` | ✅⚖️ |
| facts | Immediate danger of abuse | derived | ✅⚖️ |
| facts | Statement of facts (+ date) | `incidents[].narrative` / `incidents[].date` | ✅ |
| facts | See attached additional page(s) | — | ❌ NHG2 |
| court actions | Divorce / custody / protective order / none / other | `nh.court_actions` | ✅ |
| court actions | Court(s) handling / represented by lawyer | `nh.court_list` / `nh.represented_by_lawyer` | ✅ |
| residence | Own or rent / in whose name | `nh.residence_type` / `nh.residence_holder` | ✅ |
| children | Children living in household | `protected_persons.children[]` | 🟡 names; DOB/resides-with — NHG3 |
| losses | Financial losses (+ other) | `nh.financial_losses` / `nh.financial_losses_other` | ✅ |
| 1-15 | Relief checklist | `nh.relief` | ✅⚖️ |
| 5 | Firearms / weapons to relinquish | `nh.firearms_detail` | ✅ |
| 11 | Plaintiff's vehicle for exclusive use | `nh.vehicle_detail` | ✅ |
| 15 | Other relief | `nh.other_relief` | ✅ |
| signature | Plaintiff signature | `petitioner.legal_name` | ✅ |

## Gaps — status

- **NHG1** — the form prints no plaintiff street address (NH keeps it off the
  petition); intake collects no petitioner address for this form, so none is
  mapped. (Closed by design — recorded so the absence is auditable.)
- **NHG2** — the "see attached additional page(s)" overflow flag is not collected;
  the narrative is mapped in full to the statement-of-facts field instead.
- **NHG3** — per-child DOB and primary-residence (plaintiff / defendant / joint)
  for the children-in-household table; only names are collected. Minor children in
  common also require a UCCJEA Affidavit (NHJB-2660-FP), not assembled here.

> NH's form has no respondent physical-description or vehicle block, so NH is
> carved out of those shared Tier-2 gates — the survivor is never asked for
> details the form cannot carry.

**For Pranav:** confirm the `⚖️` rows — the relationship basis, the
immediate-danger allegation, and every item-1 through item-15 relief box. The
wiring is done.
