import numpy as np
import pandas as pd

# --- deps for kriging & projection ---
from pykrige.ok import OrdinaryKriging
from pyproj import CRS, Transformer

def windSpeedJDone(df):
    # --- Load your data ---
    # Load the simulated Hurricane Ian wind footprint (Done et al., 2020) for Lee County.
    # This dataset contains the 2 km simulation grid of Hurricane Ian's lifetime maximum 1-minute
    # sustained wind speed at 10 m above ground level. Each row is one grid point, with columns:
    #   - 'WKT'       : grid point location as a WKT POINT (longitude latitude), WGS 84 (EPSG:4326)
    #   - 'wind(m/s)' : maximum 1-minute sustained wind speed (m/s)
    #   - 'lat'       : latitude of the grid point (decimal degrees)
    #   - 'lon'       : longitude of the grid point (decimal degrees)
    # These grid points are used as the reference data for Ordinary Kriging below.
    df_wind = pd.read_csv("<path to wind speed dataset>")       # has 'lat','lon','wind(m/s)'

    # --- Basic checks ---
    required_df_cols = {'Latitude','Longitude'}
    required_w_cols = {'lat','lon','wind(m/s)'}
    if not required_df_cols.issubset(df.columns):
        raise ValueError(f"df is missing required columns: {required_df_cols - set(df.columns)}")
    if not required_w_cols.issubset(df_wind.columns):
        raise ValueError(f"df_wind is missing required columns: {required_w_cols - set(df_wind.columns)}")

    # Drop rows with missing coords/values
    df = df.dropna(subset=['Latitude','Longitude']).copy()
    df_wind = df_wind.dropna(subset=['lat','lon','wind(m/s)']).copy()

    # --- De-duplicate reference points exactly, averaging repeats ---
    df_wind = (
        df_wind
        .groupby(['lat','lon'], as_index=False, sort=False)['wind(m/s)']
        .mean()
    )

    # --- Choose a local projected CRS (UTM zone from mean lon/lat) ---
    mean_lat = float(df_wind['lat'].mean())
    mean_lon = float(df_wind['lon'].mean())

    # Compute UTM zone from longitude
    utm_zone = int(np.floor((mean_lon + 180) / 6) + 1)
    hemisphere = '326' if mean_lat >= 0 else '327'  # 326xx = north, 327xx = south
    epsg_code = int(f"{hemisphere}{utm_zone:02d}")  # e.g., Florida west ~ 32617

    crs_ll = CRS.from_epsg(4326)
    crs_xy = CRS.from_epsg(epsg_code)
    to_xy = Transformer.from_crs(crs_ll, crs_xy, always_xy=True)   # always_xy -> (lon, lat)

    # --- Project reference (training) points ---
    ref_x, ref_y = to_xy.transform(df_wind['lon'].to_numpy(), df_wind['lat'].to_numpy())
    ref_z = df_wind['wind(m/s)'].to_numpy().astype(float)

    # --- Project query (prediction) points ---
    qry_x, qry_y = to_xy.transform(df['Longitude'].to_numpy(), df['Latitude'].to_numpy())

    # --- Fit Ordinary Kriging ---
    # Notes:
    # - variogram_model can be: 'spherical', 'exponential', 'gaussian', 'power'
    # - If variogram_parameters=None, PyKrige will estimate from data (using nlags bins)
    variogram_model = 'spherical'
    nlags = 12
    enable_statistics = False  # turn on if you want kriging variance etc.

    OK = OrdinaryKriging(
        x=ref_x, y=ref_y, z=ref_z,
        variogram_model=variogram_model,
        variogram_parameters=None,   # let PyKrige fit automatically
        nlags=nlags,
        enable_statistics=enable_statistics,
        verbose=False
    )

    # --- Predict at scattered points (no grid) ---
    # 'points' returns (z, ss) where ss is kriging variance (if enable_statistics=True)
    z_pred, ss_pred = OK.execute('points', qry_x, qry_y)

    # --- Attach to df ---
    df['wind_speed_interp'] = np.asarray(z_pred, dtype=float)

    return df
