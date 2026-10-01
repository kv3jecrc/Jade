# Region vs. Country Mismatch Analysis

Checks a Salesforce account export (`Id, Name, ShippingCountry,
BillingCountry, Region__c`) for accounts whose `Region__c` value doesn't
match what their country fields imply.

## Method

1. Map every country to one of 5 regions (`NA`, `LATAM`, `JPN`, `APAC`,
   `EMEA`) using standard geographic groupings.
2. Compute the region each row's `ShippingCountry` and `BillingCountry`
   would imply, and compare both to the actual `Region__c`.
3. A row where `Region__c` matches the **billing** country's region (but
   not shipping) is treated as explainable — many of these are
   reseller-billed accounts (e.g. a Japanese company billed through a US
   or German reseller) where Region legitimately follows the billing
   relationship rather than the ship-to address. These are not flagged.
4. Everything else is a mismatch. Within that set, rows where
   **Shipping country == Billing country** are unambiguous: there's only
   one country on the record, so there's no legitimate reason for
   `Region__c` to disagree with it.

## Results (from the 2026-10-01 export)

- 5,482 total rows
- 443 rows where Region doesn't match the shipping country
- 355 of those are explained by the billing country instead (reseller pattern)
- **88 rows remain unexplained** by either country field (`genuine_mismatches.csv`)
- **36 of those are unambiguous errors** — same country on both shipping
  and billing, region still wrong (`unambiguous_errors.csv`)

The single biggest pattern: **13 Japanese accounts have Region = NA
instead of JPN**, despite both shipping and billing country being Japan
(e.g. TOYOTA SYSTEMS CORPORATION, DAIWA LIFENEXT, HITACHI ACADEMY — all
routed through Japanese resellers like CTC/HI-SOL).

See `region_mismatch_report.xlsx` for both lists in spreadsheet form
(Sheet 1: the 36 unambiguous errors; Sheet 2: all 88 unexplained rows for
manual review of the ambiguous ones).

## Caveat

The 88-row "unexplained" set includes rows where shipping and billing
country differ and *neither* matches the assigned region. Those are less
certain than the 36 unambiguous ones, since the correct region could be
driven by something not present in this export (e.g. account
owner/territory assignment) rather than either address field. Treat
Sheet 1 as high-confidence; use judgment on Sheet 2.

## Re-running

```bash
pip install pandas openpyxl --break-system-packages
python analyze_region_mismatch.py   # expects attachment.txt (tab-separated) in this folder
```

(The source export itself isn't included in this folder since it's the
user's own Salesforce data, not a reusable sample — copy it in locally as
`attachment.txt` to re-run.)
