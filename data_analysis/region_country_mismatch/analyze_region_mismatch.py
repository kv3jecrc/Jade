"""
analyze_region_mismatch.py
===========================
Finds accounts whose Region__c value doesn't match what their
Shipping/BillingCountry would imply, in a Salesforce account export with
columns: Id, Name, ShippingCountry, BillingCountry, Region__c.

IMPORTANT: Region__c legitimately contains the literal string "NA"
(North America) -- read the input with keep_default_na=False, or pandas
will silently turn every NA-region row into a missing value.

Produces two outputs:
  - unambiguous_errors.csv   ShippingCountry == BillingCountry, so there's
                              no doubt which country should drive the
                              region, yet Region__c is still wrong. These
                              are the high-confidence data-entry errors.
  - genuine_mismatches.csv   All rows where Region__c doesn't match either
                              the shipping- or billing-country's expected
                              region. Includes the unambiguous set above,
                              plus cases where shipping != billing and
                              neither explains the assigned region -- less
                              clear-cut, since the correct region might be
                              driven by something outside this export
                              (e.g. the account owner's territory), so
                              these need human judgment.

Rows where Region__c matches the BILLING country's expected region (but
not shipping) are treated as explained, not flagged -- e.g. a Japanese
company billed in the US through a US reseller legitimately showing
Region = NA is a business rule, not a data error.
"""

import pandas as pd

INPUT_FILE = "attachment.txt"  # Tab-separated Salesforce export

NA_COUNTRIES = {"United States", "Canada"}
LATAM_COUNTRIES = {
    "Mexico", "Argentina", "Brazil", "Chile", "Colombia", "Peru", "Venezuela",
    "Ecuador", "Bolivia", "Paraguay", "Uruguay", "Costa Rica", "Panama",
    "Guatemala", "Honduras", "El Salvador", "Dominican Republic", "Jamaica",
    "Trinidad and Tobago", "Barbados", "Cayman Islands", "Aruba", "Martinique",
    "Saint Kitts and Nevis", "Virgin Islands, U.S.",
}
JPN_COUNTRIES = {"Japan"}
APAC_COUNTRIES = {
    "Australia", "New Zealand", "China", "Hong Kong", "Taiwan", "Singapore",
    "Malaysia", "Indonesia", "Philippines", "Thailand", "Viet Nam", "Vitenam",
    "Cambodia", "Myanmar", "India", "Pakistan", "Bangladesh", "Sri Lanka",
    "Korea, Republic of", "Fiji", "Papua New Guinea", "papau new guinea",
    "French Polynesia",
}
EMEA_COUNTRIES = {
    "Albania", "Algeria", "Andorra", "Angola", "Armenia", "Austria", "Bahrain",
    "Belgium", "Botswana", "Bulgaria", "Congo-Brazzaville", "Croatia", "Cyprus",
    "Czech Republic", "Denmark", "Egypt", "Estonia", "Eswatini", "Ethiopia",
    "Finland", "France", "Georgia", "Germany", "Ghana", "Greece", "Guinea",
    "Hungary", "Ireland", "Isle of Man", "Israel", "Italy", "Jordan",
    "Kazakhstan", "Kenya", "Kuwait", "Lebanon", "Lesotho", "Lithuania",
    "Luxembourg", "Madagascar", "Malawi", "Malta", "Mauritius", "Monaco",
    "Morocco", "Mozambique", "Namibia", "Netherlands", "Nigeria", "Norway",
    "Oman", "Palestinian Territory, Occupied", "Poland", "Portugal", "Qatar",
    "Reunion", "Romania", "Rwanda", "Saudi Arabia", "Serbia", "Slovakia",
    "Slovenia", "South Africa", "Spain", "Sweden", "Switzerland",
    "Tanzania, United Republic of", "Tunisia", "Türkiye", "Uganda",
    "Ukraine", "United Arab Emirates", "United Kingdom", "Zambia", "Zimbabwe",
    "Cote d'Ivoire",
}

COUNTRY_TO_REGION = {}
for group, name in (
    (NA_COUNTRIES, "NA"),
    (LATAM_COUNTRIES, "LATAM"),
    (JPN_COUNTRIES, "JPN"),
    (APAC_COUNTRIES, "APAC"),
    (EMEA_COUNTRIES, "EMEA"),
):
    for country in group:
        COUNTRY_TO_REGION[country] = name


def main():
    df = pd.read_csv(INPUT_FILE, sep="\t", dtype=str, keep_default_na=False)

    df["exp_ship"] = df["ShippingCountry"].map(COUNTRY_TO_REGION.get)
    df["exp_bill"] = df["BillingCountry"].map(COUNTRY_TO_REGION.get)

    known = df[df["exp_ship"].notna()]
    mismatched = known[known["exp_ship"] != known["Region__c"]].copy()

    # Explained: region matches the BILLING country instead of shipping
    # (e.g. reseller-billed accounts) -- not flagged as an error.
    mismatched["explained_by_billing"] = mismatched["exp_bill"] == mismatched["Region__c"]
    genuine = mismatched[~mismatched["explained_by_billing"]].copy()

    genuine[["Id", "Name", "ShippingCountry", "BillingCountry", "Region__c", "exp_ship"]].to_csv(
        "genuine_mismatches.csv", index=False
    )

    unambiguous = genuine[genuine["ShippingCountry"] == genuine["BillingCountry"]]
    unambiguous[["Id", "Name", "ShippingCountry", "Region__c", "exp_ship"]].rename(
        columns={"exp_ship": "Correct Region"}
    ).to_csv("unambiguous_errors.csv", index=False)

    print(f"Total rows: {len(df)}")
    print(f"Mismatched vs. shipping country: {len(mismatched)}")
    print(f"  explained by billing country: {mismatched['explained_by_billing'].sum()}")
    print(f"  unexplained (genuine_mismatches.csv): {len(genuine)}")
    print(f"  unambiguous (Shipping == Billing; unambiguous_errors.csv): {len(unambiguous)}")


if __name__ == "__main__":
    main()
