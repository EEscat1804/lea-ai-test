# SD protective-order forms

Blank, official South Dakota Unified Judicial System forms for the domestic-abuse
protection-order flow. Public documents. **Blank templates only — never commit a
form filled with a survivor's information.**

| Form | Title | Status |
|---|---|---|
| UJS-091A | Petition and Affidavit for a Protection Order (Domestic Abuse) — Adult | mapped (`form.py`) |
| UJS-091AJ | Same petition — Juvenile (petitioner under 18) | same mapping; minor path |

## Notes

- Form UJS-091A (SDCL ch. 25-10) covers the parties and SD residency basis, the
  relationship categories, an acts-of-domestic-abuse checklist, prior-PO and
  weapon history (yes/no/don't-know), the abuse narrative, and the items 1-11
  relief list plus the ex parte (immediate TPO) request. SD's relief and abuse
  lists are its own. See `coverage.md`.
- **Adult vs juvenile form.** UJS-091A is the adult petition; UJS-091AJ is used
  when the petitioner is under 18 (filed by a parent/legal guardian "Filer"). SD
  is in the shared `MINOR_FILING_STATES` set, so the minor-filing path runs; the
  same mapping serves both.
- **NOT in the physical-description or vehicle sets.** The form describes neither
  the respondent's appearance nor a vehicle, so SD is correctly absent from
  `PHYSICAL_DESCRIPTION_STATES` and `VEHICLE_DESCRIPTION_STATES` — those questions
  never fire for SD.
- **Items 1-11 relief is one checklist** modeled as a single multi-select
  (`sd.relief`) with sub-detail: duration (§2), residence to exclude (§3/4C),
  stay-away distance + targets (§4), visitation (§6), support sub-checklist +
  amounts (§7), counseling (§9), and other relief (§11). The ex parte request and
  its reasons are collected separately.
- **No SSN gate.** SD is not in the SSN-for-support set `{CA, FL, TX}`; the form
  takes proof of income at the hearing and asks for no SSN at all.
- **Confidential by design:** the petitioner's home address is never collected
  (safe mailing only); the confidential-address note defaults on.
- **Relationship + danger history are attorney-confirmed** (`relationship_basis`
  and the prior-PO / weapon-threat questions carry `needs_legal_review`). Source:
  ujs.sd.gov (protection order forms).
