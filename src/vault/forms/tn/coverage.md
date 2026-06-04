# Form #OP2018-1 coverage map — intake → form (Tennessee)

How completely the current Vault intake fills the Tennessee **Petition for Order
of Protection and Order for Hearing** (Form #OP2018-1, TCA § 36-3-601 et seq.,
rev. 04/30/2018).

Audit artifact for legal review. **An attorney (Pranav) must confirm the
`needs legal review` rows** (the relationship/eligibility basis, the ex parte
request, and every items 7-19 relief box). Unflagged != signed off.

Legend: ✅ mapped · 🟡 partial · ❌ not collected · ⚖️ needs legal review

> The TN intake (the `_tn_step` block + the shared physical-description and
> minor-filing gates) fills the TN-specific items end to end. TN is omitted from
> the vehicle gate (the form has no vehicle field). The form is **alive**: intake
> → jurisdiction-aware questions → filled petition.

## Item-by-item

| Section | Field | Intake source | State |
|---|---|---|---|
| caption | County | `tn.county` | ✅ |
| caption | Court designation | — | ❌ **TNG1** (set locally) |
| caption | Case # | — | ❌ assigned by the clerk |
| petitioner | Petitioner name | `petitioner.legal_name` | ✅ |
| petitioner | Address (withheld; safe mailing only) | derived / `petitioner.safe_mailing_address` | ✅ |
| petitioner | Under-18 / filed on behalf of a minor (§36-3-602) | `petitioner.minor_filing_path` | ✅⚖️ (shared minor gate) |
| petitioner | Children under 18 needing protection | `protected_persons.children[]` | 🟡 names; form wants age + relationship per child — **TNG2** |
| respondent | Name (+ DOB + address) | `respondent.legal_name` / `.dob` / `.last_known_address` | ✅ |
| respondent | Employer name | `respondent.employer_name` | ✅ |
| respondent | Employer phone | — | ❌ **TNG3** |
| respondent | Sex / Race / DOB | `respondent.gender` / `.race` / `.dob` | ✅ |
| respondent | Hair / Eyes / Height / Weight / Scars | `respondent.hair_color` / `.eye_color` / `.height` / `.weight` / `.distinguishing_marks` | ✅ (shared physical gate) |
| respondent | Social Security # | — | ❌ **TNG4** (form says "do not list"; sensitive) |
| respondent | Phone number | — | ❌ **TNG3** |
| warning | Weapon involved / has-owns a weapon | `incidents[].weapon_involved` / `firearm.respondent_has_access` | ✅ |
| 1 | Relationship / eligibility basis (a-i) | `relationship.type` | ✅⚖️ (g/h stalking/SA confirmed from narrative) |
| 2 | Children list + confidential addresses | `protected_persons.children[]` (+ derived) | 🟡 names + confidential default — **TNG2** |
| 3 | Children's previous addresses (6 mo) | — | ❌ **TNG2** |
| 4 | Other court cases | `prior_orders.exists` | 🟡 existence only — **TNG5** |
| 5 | Custody-rights claim by others | — | ❌ **TNG5** |
| 6 | Describe abuse (narrative / where-when / weapons) | `incidents[].narrative` / `.date` / `.location` / `.weapon_involved` | ✅ |
| 7 | No Contact (+ me / children) | `tn.relief` (+ `tn.no_contact_who`) | ✅⚖️ |
| 8 | Stay Away (+ home / workplace / anywhere) | `tn.relief` (+ `tn.stay_away_places`) | ✅⚖️ |
| 9 | Personal Conduct (+ property/utilities / animals) | `tn.relief` (+ `tn.personal_conduct_types`) | ✅⚖️ |
| 10 | Temporary Custody | `tn.relief` | ✅⚖️ |
| 11 | Child Support | `tn.relief` | ✅⚖️ |
| 12 | Petitioner (spousal) Support | `tn.relief` | ✅⚖️ |
| 13 | Move-out / Provide housing (+ which) | `tn.relief` (+ `tn.move_out_choice`) | ✅⚖️ |
| 14 | Counseling / Substance Abuse | `tn.relief` | ✅⚖️ |
| 15 | No Firearms (+ types / locations) | `tn.relief` / `firearm.types[]` / `firearm.locations[]` | ✅⚖️ |
| 16 | Animals / Pets | `tn.relief` | ✅⚖️ |
| 17 | Costs, fees, litigation taxes | `tn.relief` | ✅⚖️ |
| 18 | Transfer wireless number(s) (+ numbers) | `tn.relief` (+ `tn.wireless_numbers`) | ✅⚖️ partial — provider/account-holder detail not collected (TNG6) |
| 19 | Other Orders (general relief) | `tn.relief` (+ `tn.other_relief`) | ✅⚖️ |
| also-ask | Immediate Temporary Order of Protection (ex parte) | `tn.ex_parte` | ✅⚖️ |
| verification | Petitioner signature (sworn) | `petitioner.legal_name` | ✅ (notary/date at filing) |

## Gaps — status

- **TNG1** — the court designation (Circuit/Chancery/General Sessions); set
  locally at filing. Intake collects county only.
- **TNG2** — per-child detail (age, is-respondent-the-parent, needs-protection,
  address) and the children's 6-month address history; intake holds child names.
- **TNG3** — respondent's employer phone and personal phone; not collected.
- **TNG4** — respondent's Social Security number; the form says "Do not list it
  here" and it is sensitive — not collected.
- **TNG5** — the full other-court-cases detail (county/case#/kind) and the §5
  custody-rights-claimed-by-others question; intake holds `prior_orders.exists`.
- **TNG6** — the §18 wireless-transfer provider, current/new account holder, and
  billing number; intake collects the number(s) only.

**For Pranav:** confirm the `⚖️` rows — the §1 relationship/eligibility basis
(including the stalking/sexual-assault grounds), the ex parte request, and every
items 7-19 relief box. The wiring is done.
