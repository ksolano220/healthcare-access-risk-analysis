"""
Generate synthetic healthcare data for all US counties.

Uses the Census county GeoJSON to get real FIPS codes and county names,
then generates realistic synthetic data for uninsured population,
total population, and hospital count.
"""

import csv
import json
import random
import ssl
from pathlib import Path
from urllib.request import urlopen

GEOJSON_URL = "https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json"

STATE_FIPS_TO_ABBR = {
    "01": "AL", "02": "AK", "04": "AZ", "05": "AR", "06": "CA",
    "08": "CO", "09": "CT", "10": "DE", "11": "DC", "12": "FL",
    "13": "GA", "15": "HI", "16": "ID", "17": "IL", "18": "IN",
    "19": "IA", "20": "KS", "21": "KY", "22": "LA", "23": "ME",
    "24": "MD", "25": "MA", "26": "MI", "27": "MN", "28": "MS",
    "29": "MO", "30": "MT", "31": "NE", "32": "NV", "33": "NH",
    "34": "NJ", "35": "NM", "36": "NY", "37": "NC", "38": "ND",
    "39": "OH", "40": "OK", "41": "OR", "42": "PA", "44": "RI",
    "45": "SC", "46": "SD", "47": "TN", "48": "TX", "49": "UT",
    "50": "VT", "51": "VA", "53": "WA", "54": "WV", "55": "WI",
    "56": "WY", "60": "AS", "66": "GU", "69": "MP", "72": "PR",
    "78": "VI",
}

# States with historically higher uninsured rates
HIGH_UNINSURED_STATES = {"TX", "FL", "GA", "MS", "OK", "NV", "AK", "NM", "WY"}
LOW_UNINSURED_STATES = {"MA", "VT", "HI", "MN", "IA", "WI", "CT", "RI", "DC"}


def fetch_geojson():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    with urlopen(GEOJSON_URL, context=ctx) as r:
        return json.loads(r.read())


def generate_row(fips, name, state_abbr, rng):
    # Population: log-normal distribution, median ~30k
    pop = int(rng.lognormvariate(10.3, 1.2))
    pop = max(500, min(pop, 10_000_000))

    # Uninsured rate varies by state
    if state_abbr in HIGH_UNINSURED_STATES:
        base_rate = rng.uniform(0.10, 0.25)
    elif state_abbr in LOW_UNINSURED_STATES:
        base_rate = rng.uniform(0.02, 0.08)
    else:
        base_rate = rng.uniform(0.05, 0.18)

    # Rural counties (smaller pop) tend to have higher uninsured rates
    if pop < 15000:
        base_rate *= rng.uniform(1.0, 1.3)

    base_rate = min(base_rate, 0.35)
    uninsured = int(pop * base_rate)

    # Hospital count: roughly 1 per 30k-60k people, with some randomness
    hospitals_per_capita = rng.uniform(20000, 70000)
    hospitals = max(0, int(pop / hospitals_per_capita))

    # Small rural counties sometimes have 0 hospitals
    if pop < 10000 and rng.random() < 0.4:
        hospitals = 0

    return {
        "fips": fips,
        "county": name,
        "state": state_abbr,
        "uninsured_population": uninsured,
        "total_population": pop,
        "hospital_count": hospitals,
    }


def main():
    print("Fetching county GeoJSON...")
    geojson = fetch_geojson()

    rng = random.Random(42)
    rows = []

    for feature in geojson["features"]:
        fips = feature["id"]
        props = feature["properties"]
        name = props["NAME"]
        state_fips = props["STATE"]
        state_abbr = STATE_FIPS_TO_ABBR.get(state_fips, "??")

        # Skip territories for cleaner analysis
        if state_abbr in ("AS", "GU", "MP", "VI"):
            continue

        rows.append(generate_row(fips, name, state_abbr, rng))

    out_path = Path("data/healthcare_data.csv")
    out_path.parent.mkdir(exist_ok=True)

    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["fips", "county", "state", "uninsured_population", "total_population", "hospital_count"],
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"Generated {len(rows)} counties → {out_path}")


if __name__ == "__main__":
    main()
