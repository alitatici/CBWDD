import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, LineString
from shapely.wkt import loads as load_wkt
from geopy.distance import geodesic

def calculate_shoreline_distance(df):
    # 1. Read the shoreline dataset
    shoreline_df = pd.read_csv("<path to shoreline dataset>")  # should contain a 'WKT' column with the shoreline geometries
    shoreline_df["geometry"] = shoreline_df["WKT"].apply(load_wkt)
    shoreline_gdf = gpd.GeoSeries(shoreline_df["geometry"], crs="EPSG:4326")

    # Merge all multiline geometries into a single MultiLineString
    full_shoreline = shoreline_gdf.unary_union  # this combines all geometries into one MultiLineString

    # 2. Create GeoDataFrame from input df (must contain 'Latitude' and 'Longitude')
    gdf = gpd.GeoDataFrame(df.copy(), geometry=gpd.points_from_xy(df["Longitude"], df["Latitude"]), crs="EPSG:4326")

    # 3. Project to meters (Web Mercator)
    gdf = gdf.to_crs(epsg=3857)
    shoreline_geom_m = gpd.GeoSeries([full_shoreline], crs="EPSG:4326").to_crs(epsg=3857).iloc[0]

    # 4. Calculate distance in meters
    gdf["shoreline_distance_m"] = gdf.geometry.apply(lambda point: point.distance(shoreline_geom_m))

    # 4b. Convert to km
    gdf["Shoreline Distance (km)"] = round(gdf["shoreline_distance_m"] / 1000, 2)

    # 5. Return cleaned DataFrame
    return gdf.drop(columns=["geometry", "shoreline_distance_m"])

def distance_hurricane_ian_track(df):
    coords = [(-66.3, 12.3), (-67.2, 12.9), (-68.1, 13.7), (-69.3, 14.2), (-70.6, 14.6),
              (-71.7, 14.7), (-72.9, 14.7), (-74.4, 14.5), (-75.8, 14.4), (-77.2, 14.6),
              (-78.3, 14.6), (-79.4, 15.0), (-80.1, 15.8), (-80.9, 16.8), (-81.7, 17.7),
              (-82.4, 18.7), (-83, 19.7), (-83.3, 20.8), (-83.6, 21.8), (-83.6, 22.6),
              (-83.3, 23.5), (-83, 24.4), (-82.9, 24.6), (-82.9, 25.2), (-82.7, 26.0),
              (-82.4, 26.6), (-81.7, 27.2), (-81.1, 27.7), (-80.6, 28.4), (-80.1, 28.9),
              (-79.4, 29.6), (-79.1, 30.3), (-79, 31.5), (-79.2, 33.3), (-79.3, 34.4), (-79.7, 35.3)]

    hurricane_line = LineString(coords)

    def point_to_line_distance(row):
        point = Point(row['Longitude'], row['Latitude'])

        nearest_point_on_line = hurricane_line.interpolate(hurricane_line.project(point))

        dist = geodesic(
            (row['Latitude'], row['Longitude']),
            (nearest_point_on_line.y, nearest_point_on_line.x)
        ).km

        return round(dist, 2)

    df['Hurricane Track Distance (km)'] = df.apply(point_to_line_distance, axis=1)

    return df