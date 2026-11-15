import googlemaps
import pandas

gmaps_key = googlemaps.Client(key="API-KEY")

dataFrame = pandas.read_csv("<path to dataset with an 'Address' column>")
dataFrame["LAT"] = None
dataFrame["LON"] = None

for i in range(0, len(dataFrame)):
    address = dataFrame["Address"][i]  # Access the address directly
    geocode_result = gmaps_key.geocode(address)

    lat = geocode_result[0]["geometry"]["location"]["lat"]
    lng = geocode_result[0]["geometry"]["location"]["lng"]
    dataFrame.iat[i, dataFrame.columns.get_loc("LAT")] = lat
    dataFrame.iat[i, dataFrame.columns.get_loc("LON")] = lng
    print(lat, lng)

# Save to CSV
dataFrame.to_csv("<path to output file>", index=False)