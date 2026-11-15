# CBWDD: Commercial Building Wind Damage Dataset from Hurricane Ian (2022)

Code used to compile the Commercial Building Wind Damage Dataset (CBWDD), which documents
Hurricane Ian (2022) wind-induced damage to 344 commercial buildings in Lee County, Florida.

The dataset is available on Figshare: https://doi.org/10.6084/m9.figshare.35012590

## Scripts

| Script | Description |
|---|---|
| `01_scrape_lcpa_records.py` | Retrieves building information (year built, retrofit years, number of storeys) from the Lee County Property Appraiser (LCPA) online Property Search Tool using Selenium |
| `02_geocode_addresses.py` | Converts building addresses to geographic coordinates using the Google Maps Geocoding API |
| `03_match_lcda_lcpa_records.py` | Matches Lee County Damage Assessment (LCDA) records to LCPA building records within 30 m |
| `04_interpolate_wind_speed.py` | Interpolates maximum sustained wind speed at building locations by Ordinary Kriging |
| `05_calculate_distances.py` | Calculates shoreline distance and Hurricane Ian track distance |
| `06_aggregate_hexagonal_bins.py` | Aggregates building locations into hexagonal bins with a side length of 0.6 km |

Input and output file paths are given as placeholders (e.g., `"<path to LCPA dataset>"`) and
should be replaced with your own file paths.

## Requirements

```
pip install -r requirements.txt
```

`01_scrape_lcpa_records.py` also requires the Firefox browser, and `02_geocode_addresses.py`
requires a Google Maps Platform API key.

## Data

Reproducing the full workflow requires the LCDA dataset, which is no longer publicly available.
The 2 km wind speed simulation grid used by `04_interpolate_wind_speed.py` is included in the
Figshare repository. Building characteristics derived from imagery were assigned with a custom
AI-assisted classification tool and reviewed manually; these steps are not part of this code.

## License

This code is released under the MIT License.
