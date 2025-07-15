import json
import os

import pandas as pd

# Define absolute paths
base_dir = "/home/ers/workspace/market-analyzer"
csv_file_path = os.path.join(base_dir, "data", "sales_data.csv")
geojson_file_path = os.path.join(base_dir, "resources", "communes-occitanie.geojson")
output_geojson_path = os.path.join(
    base_dir, "output", "communes-occitanie-sales.geojson"
)
output_dir = os.path.dirname(output_geojson_path)

# Ensure output directory exists
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# Load CSV data
sales_df = pd.read_csv(csv_file_path, low_memory=False)
sales_df.dropna(
    subset=["code_commune"], inplace=True
)  # Ensure 'code_commune' is not NaN
sales_df["code_commune"] = sales_df["code_commune"].astype(str)


# Aggregate sales data by commune
# Assuming each row is a single property sale/mutation
sales_by_commune = sales_df.groupby("code_commune").size()

# Load GeoJSON data
with open(geojson_file_path, "r", encoding="utf-8") as f:
    geojson_data = json.load(f)

# Merge sales data into GeoJSON
for feature in geojson_data["features"]:
    # Use .get() to safely access 'code' and provide a default or skip if not found
    commune_code = feature["properties"].get("code")
    if commune_code and commune_code in sales_by_commune:
        feature["properties"]["properties_sold"] = int(sales_by_commune[commune_code])
    else:
        feature["properties"]["properties_sold"] = 0

# Save the updated GeoJSON
with open(output_geojson_path, "w", encoding="utf-8") as f:
    json.dump(geojson_data, f, ensure_ascii=False, indent=4)

print(f"Successfully processed data and saved to {output_geojson_path}")
