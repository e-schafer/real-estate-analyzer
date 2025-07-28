import os
import traceback

import pandas as pd
import polars as pl


class RealEstateData:
    def __init__(self, files=None):
        """Initialize the data processing object with file paths."""
        if files is None:
            data_dir = "data"
            if not os.path.exists(data_dir) or not os.path.isdir(data_dir):
                print(f"Error: Data directory '{data_dir}' not found.")
                self.files = []
            else:
                self.files = [
                    os.path.join(data_dir, f)
                    for f in os.listdir(data_dir)
                    if f.endswith(".parquet")
                ]
                if not self.files:
                    print(f"No CSV files found in directory '{data_dir}'.")
        else:
            self.files = files

        self.data = pl.DataFrame()
        self.processed_data = {}

    def load_data(self):
        """Load all CSV files, concatenate, clean, and transform them."""
        dataframes = []
        print("Attempting to load data...")

        if not self.files:
            print("No files specified or found for loading.")
            return self.data

        try:
            for file_idx, file_path in enumerate(self.files):
                print(
                    f"Loading data from {file_path} (File {file_idx + 1}/{len(self.files)})..."
                )
                if not os.path.exists(file_path):
                    print(f"Warning: File {file_path} does not exist. Skipping.")
                    continue
                try:
                    df = pl.read_parquet(
                        file_path,
                    )
                    print(f"Successfully read {file_path}, shape: {df.shape}")

                    if df.is_empty():
                        print(
                            f"Warning: File {file_path} is empty or resulted in an empty DataFrame after read."
                        )
                        continue

                    department = (
                        os.path.basename(file_path)
                        .replace("dvf", "")
                        .replace(".csv", "")
                    )
                    df = df.with_columns(pl.lit(department).alias("source_department"))
                    dataframes.append(df)
                except Exception as e_file:
                    print(f"Error reading or processing file {file_path}: {e_file}")
                    traceback.print_exc()

            if not dataframes:
                print("No data successfully loaded from any files.")
                return self.data

            self.data = pl.concat(dataframes)
            print(f"Concatenated data, shape: {self.data.shape}")
            if self.data.is_empty():
                print("Concatenated data is empty. No further processing.")
                return self.data

        except Exception as e_concat:
            print(f"Error during data loading or concatenation phase: {e_concat}")
            traceback.print_exc()
            self.data = pl.DataFrame()
            return self.data

        print("Starting data cleaning and transformation...")

        required_columns = [
            "valeur_fonciere",
            "surface_reelle_bati",
            "type_local",
            "date_mutation",
            "latitude",
            "longitude",
            "nombre_pieces_principales",
        ]

        missing_cols = [col for col in required_columns if col not in self.data.columns]
        if missing_cols:
            print(
                f"Error: Missing critical columns in the loaded data: {missing_cols}. Aborting processing."
            )
            self.data = pl.DataFrame()
            return self.data

        self.data = self.data.filter(pl.col("type_local").is_not_null())
        print(f"Shape after filtering null 'type_local': {self.data.shape}")
        if self.data.is_empty():
            print("Data empty after filtering null 'type_local'.")
            return self.data

        column_expressions = [
            pl.col("date_mutation").str.strptime(
                pl.Date, format="%Y-%m-%d", strict=False, exact=True
            ),
            pl.col("valeur_fonciere")
            .str.replace_all(",", "")
            .cast(pl.Float64, strict=False),
            pl.col("surface_reelle_bati")
            .str.replace_all(",", "")
            .cast(pl.Float64, strict=False),
            pl.col("nombre_pieces_principales").cast(pl.Int64, strict=False),
            pl.col("latitude").cast(pl.Float64, strict=False),
            pl.col("longitude").cast(pl.Float64, strict=False),
        ]
        self.data = self.data.with_columns(column_expressions)
        print(f"Shape after type casting attempts: {self.data.shape}")

        critical_cols_post_cast = [
            "date_mutation",
            "valeur_fonciere",
            "surface_reelle_bati",
        ]
        for col_name in critical_cols_post_cast:
            self.data = self.data.filter(pl.col(col_name).is_not_null())
        print(
            f"Shape after post-cast null filter for {critical_cols_post_cast}: {self.data.shape}"
        )
        if self.data.is_empty():
            print(
                f"Data empty after post-cast null filter for {critical_cols_post_cast}."
            )
            return self.data

        self.data = self.data.filter(pl.col("surface_reelle_bati") > 0)
        print(f"Shape after 'surface_reelle_bati > 0' filter: {self.data.shape}")
        if self.data.is_empty():
            print("Data empty after 'surface_reelle_bati > 0' filter.")
            return self.data

        self.data = self.data.with_columns(
            (pl.col("valeur_fonciere") / pl.col("surface_reelle_bati")).alias(
                "price_per_sqm"
            )
        )
        print(f"Shape after calculating 'price_per_sqm': {self.data.shape}")

        # Filter out properties with price_per_sqm > 9000
        self.data = self.data.filter(pl.col("price_per_sqm") <= 9000)
        print(
            f"Shape after filtering out properties with price_per_sqm > 9000: {self.data.shape}"
        )

        self.data = self.data.filter(
            pl.col("price_per_sqm").is_not_null() & pl.col("price_per_sqm").is_finite()
        )
        print(f"Shape after 'price_per_sqm' null/inf filter: {self.data.shape}")
        if self.data.is_empty():
            print("Data empty after 'price_per_sqm' null/inf filter.")
            return self.data

        if self.data.is_empty():
            print("Data is empty after all processing steps in load_data.")
        else:
            print(
                f"Successfully loaded and processed data. Final shape: {self.data.shape}"
            )

        return self.data

    def get_property_price_data(self):
        """Extract property price data."""
        if self.data is None or self.data.is_empty():
            print(
                "Data not loaded or empty in get_property_price_data. Attempting load."
            )
            self.load_data()
            if self.data is None or self.data.is_empty():
                print(
                    "Failed to load data or data is empty in get_property_price_data."
                )
                return pl.DataFrame()

        try:
            price_data = self.data.filter(pl.col("nature_mutation") == "Vente")
            commune_prices = price_data.group_by(["nom_commune", "code_postal"]).agg(
                [
                    pl.mean("price_per_sqm").alias("avg_price_per_sqm"),
                    pl.median("price_per_sqm").alias("median_price_per_sqm"),
                    pl.count("id_mutation").alias("transaction_count"),
                    pl.mean("valeur_fonciere").alias("avg_total_price"),
                    pl.median("valeur_fonciere").alias("median_total_price"),
                ]
            )

            self.processed_data["price_data"] = commune_prices
            return commune_prices
        except Exception as e:
            print(f"Error in get_property_price_data: {e}")
            return pl.DataFrame()

    def get_property_types_data(self):
        """Extract data on property types."""
        if self.data is None or self.data.is_empty():
            print(
                "Data not loaded or empty in get_property_types_data. Attempting load."
            )
            self.load_data()
            if self.data is None or self.data.is_empty():
                print(
                    "Failed to load data or data is empty in get_property_types_data."
                )
                return pl.DataFrame()

        try:
            property_types = self.data.group_by(["type_local"]).agg(
                [
                    pl.count("id_mutation").alias("count"),
                    pl.mean("surface_reelle_bati").alias("avg_surface"),
                    pl.mean("price_per_sqm").alias("avg_price_per_sqm"),
                    pl.median("valeur_fonciere").alias("median_price"),
                    pl.mean("nombre_pieces_principales").alias("avg_rooms"),
                ]
            )

            self.processed_data["property_types"] = property_types
            return property_types
        except Exception as e:
            print(f"Error in get_property_types_data: {e}")
            return pl.DataFrame()

    def get_market_trends(self):
        """Extract market trends over time."""
        if self.data is None or self.data.is_empty():
            print("Data not loaded or empty in get_market_trends. Attempting load.")
            self.load_data()
            if self.data is None or self.data.is_empty():
                print("Failed to load data or data is empty in get_market_trends.")
                return pl.DataFrame()

        try:
            data_with_dates = self.data.with_columns(
                [
                    pl.col("date_mutation").dt.year().alias("year"),
                    pl.col("date_mutation").dt.month().alias("month"),
                ]
            )

            trends = (
                data_with_dates.group_by(["year", "month"])
                .agg(
                    [
                        pl.count("id_mutation").alias("transaction_count"),
                        pl.mean("price_per_sqm").alias("avg_price_per_sqm"),
                        pl.median("price_per_sqm").alias("median_price_per_sqm"),
                        pl.mean("valeur_fonciere").alias("avg_price"),
                    ]
                )
                .sort(["year", "month"])
            )

            self.processed_data["market_trends"] = trends
            return trends
        except Exception as e:
            print(f"Error in get_market_trends: {e}")
            return pl.DataFrame()

    def get_demographic_features(self):
        """
        Extract demographic features.
        Note: This uses the transaction data as a proxy for demographic data.
        For a real application, you would integrate with demographic data sources.
        """
        if self.data is None or self.data.is_empty():
            print(
                "Data not loaded or empty in get_demographic_features. Attempting load."
            )
            self.load_data()
            if self.data is None or self.data.is_empty():
                print(
                    "Failed to load data or data is empty in get_demographic_features."
                )
                return pl.DataFrame()

        try:
            demographics = (
                self.data.group_by(["nom_commune", "code_postal"])
                .agg(
                    [
                        pl.count("id_mutation").alias("transaction_count"),
                        pl.n_unique("adresse_nom_voie").alias("unique_streets"),
                    ]
                )
                .sort("transaction_count", descending=True)
            )

            self.processed_data["demographics"] = demographics
            return demographics
        except Exception as e:
            print(f"Error in get_demographic_features: {e}")
            return pl.DataFrame()

    def get_property_features(self):
        """Extract property features data."""
        if self.data is None or self.data.is_empty():
            print("Data not loaded or empty in get_property_features. Attempting load.")
            self.load_data()
            if self.data is None or self.data.is_empty():
                print("Failed to load data or data is empty in get_property_features.")
                return pl.DataFrame()

        try:
            features = (
                self.data.group_by("type_local")
                .agg(
                    [
                        pl.mean("nombre_pieces_principales")
                        .fill_null(0)
                        .round(1)
                        .alias("avg_rooms"),
                        pl.median("nombre_pieces_principales")
                        .fill_null(0)
                        .alias("median_rooms"),
                        pl.mean("surface_reelle_bati")
                        .fill_null(0)
                        .round(1)
                        .alias("avg_surface"),
                        pl.median("surface_reelle_bati")
                        .fill_null(0)
                        .alias("median_surface"),
                        pl.count().alias("transaction_count"),
                    ]
                )
                .sort("transaction_count", descending=True)
            )
            return features
        except Exception as e:
            print(f"Error in get_property_features: {e}")
            return pl.DataFrame()

    def get_all_properties_geo_data(self):
        """Get geolocation data for all properties with coordinates."""
        if self.data is None or self.data.is_empty():
            print(
                "Data not loaded or empty in get_all_properties_geo_data. Attempting load."
            )
            self.load_data()
            if self.data is None or self.data.is_empty():
                print(
                    "Failed to load data or data is empty in get_all_properties_geo_data."
                )
                return pl.DataFrame()

        try:
            geo_data = self.data.filter(
                (pl.col("latitude").is_not_null()) & (pl.col("longitude").is_not_null())
            ).select(
                [
                    "id_mutation",
                    "type_local",
                    "valeur_fonciere",
                    "surface_reelle_bati",
                    "nombre_pieces_principales",
                    "nom_commune",
                    "code_postal",
                    "adresse_nom_voie",
                    "adresse_numero",
                    "latitude",
                    "longitude",
                    "price_per_sqm",
                ]
            )

            self.processed_data["geo_data"] = geo_data
            return geo_data
        except Exception as e:
            print(f"Error in get_all_properties_geo_data: {e}")
            return pl.DataFrame()

    def convert_to_pandas(self, data):
        """Convert Polars DataFrame to Pandas DataFrame."""
        if data is None or data.is_empty():
            return pd.DataFrame()
        try:
            return data.to_pandas()
        except Exception as e:
            print(f"Error converting Polars DataFrame to Pandas: {e}")
            traceback.print_exc()
            return pd.DataFrame()
