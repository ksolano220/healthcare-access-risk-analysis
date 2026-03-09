"""
Build an interactive choropleth map of healthcare access risk by county.

Reads the analysis output and generates a self-contained HTML file
using Folium. Counties are colored by access risk score with hover
tooltips showing key metrics.
"""

import json
import ssl
from urllib.request import urlopen

import folium
import pandas as pd

GEOJSON_URL = "https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json"


def fetch_geojson():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    with urlopen(GEOJSON_URL, context=ctx) as r:
        return json.loads(r.read())


def main():
    # Load analysis results
    df = pd.read_csv("outputs/top_risk_counties.csv", dtype={"fips": str})

    # Ensure FIPS codes are zero-padded to 5 digits
    df["fips"] = df["fips"].str.zfill(5)

    print(f"Loaded {len(df)} counties")
    print(f"Risk score range: {df['access_risk_score'].min():.2f} to {df['access_risk_score'].max():.2f}")

    # Fetch county boundaries
    print("Fetching county GeoJSON...")
    geojson = fetch_geojson()

    # Build lookup for tooltip data
    tooltip_data = df.set_index("fips").to_dict("index")

    # Create base map centered on continental US
    m = folium.Map(
        location=[39.5, -98.35],
        zoom_start=4,
        tiles="CartoDB positron",
        min_zoom=3,
        max_zoom=10,
    )

    # Choropleth layer: counties colored by access risk score
    folium.Choropleth(
        geo_data=geojson,
        data=df,
        columns=["fips", "access_risk_score"],
        key_on="feature.id",
        fill_color="RdYlGn_r",
        fill_opacity=0.7,
        line_opacity=0.2,
        line_weight=0.5,
        legend_name="Healthcare Access Risk Score",
        nan_fill_color="#f0f0f0",
    ).add_to(m)

    # Tooltip layer: hover to see county details
    tooltip_layer = folium.GeoJson(
        geojson,
        style_function=lambda f: {
            "fillOpacity": 0,
            "weight": 0,
            "color": "transparent",
        },
        tooltip=folium.GeoJsonTooltip(
            fields=["NAME"],
            aliases=[""],
            sticky=True,
            style="""
                background-color: white;
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 8px 12px;
                font-family: system-ui, -apple-system, sans-serif;
                font-size: 13px;
                box-shadow: 0 2px 6px rgba(0,0,0,0.15);
            """,
        ),
    )

    # Enrich GeoJSON features with our data for richer tooltips
    for feature in tooltip_layer.data["features"]:
        fips = feature["id"]
        props = feature["properties"]

        if fips in tooltip_data:
            row = tooltip_data[fips]
            risk_tier = row.get("risk_tier", "—")
            uninsured_rate = row.get("uninsured_rate", 0)
            hosp_per_100k = row.get("hospitals_per_100k", 0)
            priority_rank = row.get("priority_rank", "—")
            population = row.get("total_population", 0)
            state = row.get("state", "")

            props["NAME"] = (
                f"<b>{props['NAME']} County, {state}</b><br>"
                f"Risk Tier: <b>{risk_tier}</b><br>"
                f"Uninsured Rate: {uninsured_rate:.1f}%<br>"
                f"Hospitals per 100k: {hosp_per_100k:.1f}<br>"
                f"Population: {population:,}<br>"
                f"Priority Rank: #{int(priority_rank) if priority_rank != '—' else '—'}"
            )
        else:
            props["NAME"] = f"{props['NAME']} County — No data"

    tooltip_layer.add_to(m)

    # Save
    output_path = "outputs/map.html"
    m.save(output_path)
    print(f"\nMap saved → {output_path}")
    print("Open in a browser to view the interactive map.")


if __name__ == "__main__":
    main()
