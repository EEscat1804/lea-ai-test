# UT protective-order forms

Blank, official Utah District Court forms for the protective-order (Cohabitant
Abuse Act) flow. Public documents. **Blank templates only — never commit a form
filled with a survivor's information.**

| Form | Title | Status |
|---|---|---|
| (no printed number) | Request for Protective Order | mapped (`form.py`) |

## Notes

- The **Request for Protective Order** (Utah Code 78B-7-601 et seq.) covers the
  parties, a "Describe Respondent" block, the §3 relationship basis, the most
  recent and past abuse, an imminent-fear declaration (§6), and a large items
  8-25 relief checklist. UT's relief list is its own. See `coverage.md`.
- **No printed form number.** The form is identified only by its title and
  revision footer (*Approved Board of District Court Judges May 21, 2008; Revised
  by Forms Committee April 11, 2022*). `FORM_ID` is descriptive
  (`"Request for Protective Order"`) and flagged for confirmation (UTG1) — no
  number was fabricated.
- **Shared Describe-Respondent + vehicle gates apply.** UT is in both
  `PHYSICAL_DESCRIPTION_STATES` and `VEHICLE_DESCRIPTION_STATES`, so the shared
  height/weight/eyes/hair/marks and vehicle questions run before the UT block.
  The UT block adds the form's required* sex/race/DOB and the violent-past +
  probation/parole questions.
- **Items 8-25 relief is one big checklist** modeled as a single multi-select
  (`ut.relief`) with sub-detail follow-ups: stay-away distance + locations
  (§11), weapons (§12), property control (§13), custody & parent-time (§17),
  supervised visitation (§19), support sub-checklist + amounts (§21), wireless
  transfer (§16), law-enforcement tasks (§23), and other assistance (§22).
- **No SSN gate.** UT is not in the SSN-for-support set `{CA, FL, TX}`, so
  requesting child/spousal support does not gate the petitioner's SSN. The
  *respondent's* SSN field on the form is sensitive and not collected (UTG6).
- **Confidential address by design:** the form says the petitioner may leave
  their address/phone blank to keep it private. Intake only ever holds a safe
  mailing address; the `address_confidential` note is asserted.
- **Relationship basis is attorney-confirmed** (`relationship_basis`,
  `needs_legal_review`) — UT's §3 "related by blood/marriage/adoption" and
  "consensual sexual relationship" categories in particular. Source:
  utcourts.gov (protective orders).
