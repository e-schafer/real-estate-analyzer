import json  # For handling GeoJSON data
import os  # For checking file existence

import plotly.express as px
import polars as pl
import streamlit as st


def display_price_map_page(
    data_processor, filtered_data, selected_departments, selected_types
):
    st.markdown(
        '<div class="section-header">Carte des Prix au m² par Commune</div>',
        unsafe_allow_html=True,
    )
    if filtered_data.is_empty():
        st.warning("Aucune donnée à afficher avec les filtres actuels.")
        return

    # Ensure 'latitude', 'longitude', and 'code_commune' are present for map and aggregation
    required_cols = [
        "latitude",
        "longitude",
        "code_commune",
        "nom_commune",
        "price_per_sqm",
        "id_mutation",
    ]
    missing_cols = [col for col in required_cols if col not in filtered_data.columns]
    if missing_cols:
        st.error(
            f"Colonnes manquantes dans les données filtrées, nécessaires pour la carte des prix: {', '.join(missing_cols)}"
        )
        return

    geo_data_for_map_polars = filtered_data.filter(
        pl.col("latitude").is_not_null()
        & pl.col("longitude").is_not_null()
        & pl.col("code_commune").is_not_null()
    )

    if geo_data_for_map_polars.is_empty():
        st.warning(
            "Aucune donnée géographique ou de code commune disponible pour la carte des prix avec les filtres actuels."
        )
        return

    geo_data_pd = data_processor.convert_to_pandas(geo_data_for_map_polars)

    if not geo_data_pd.empty:
        center_lat = geo_data_pd["latitude"].mean()
        center_lon = geo_data_pd["longitude"].mean()

        # Aggregate data at commune level using 'code_commune'
        commune_level_data = (
            geo_data_pd.groupby("code_commune")
            .agg(
                nom_commune=(
                    "nom_commune",
                    "first",
                ),  # Keep for bar chart and potential tooltips
                price_per_sqm=("price_per_sqm", "median"),
                transaction_count=(
                    "id_mutation",
                    "count",
                ),
            )
            .reset_index()
        )
        commune_level_data = commune_level_data[
            commune_level_data["transaction_count"] >= 5
        ]  # Filter for communes with enough data

        if commune_level_data.empty:
            st.warning(
                "Pas assez de données agrégées par commune pour afficher la carte des prix."
            )
            return

        # Path to your GeoJSON file
        geojson_path = "resources/communes-occitanie.geojson"

        if not os.path.exists(geojson_path):
            st.error(f"Fichier GeoJSON introuvable: {geojson_path}")
            return

        try:
            with open(geojson_path, "r", encoding="utf-8") as f:
                geojson_data_dict = json.load(f)
        except Exception as e:
            st.error(f"Erreur lors du chargement du fichier GeoJSON: {e}")
            return

        # MAP DISPLAY (Full Width)
        if not commune_level_data.empty:
            min_price = commune_level_data["price_per_sqm"].min()
            max_price = commune_level_data["price_per_sqm"].max()

            fig_map = px.choropleth_mapbox(
                commune_level_data,
                geojson=geojson_data_dict,
                locations="code_commune",
                featureidkey="properties.code",
                color="price_per_sqm",
                color_continuous_scale="RdYlGn_r",  # Green (low) to Red (high)
                range_color=(min_price, max_price),
                mapbox_style="carto-positron",
                zoom=7,  # Initial zoom
                center={"lat": center_lat, "lon": center_lon},
                opacity=0.6,
                hover_name="nom_commune",
                hover_data={
                    "price_per_sqm": ":,.0f €/m²",  # Format as integer currency
                    "transaction_count": True,  # Show transaction_count
                    "code_commune": False,  # Hide commune code from hover
                },
                labels={
                    "price_per_sqm": "Prix médian/m²",
                    "transaction_count": "Nb Transactions",
                    "nom_commune": "Commune",
                },
            )
            fig_map.update_layout(
                margin={
                    "r": 0,
                    "t": 30,
                    "l": 0,
                    "b": 0,
                },  # Added top margin for title
                coloraxis_colorbar_title_text="Prix médian au m² (€/m²)",
                height=800,  # Match previous Folium height
            )
            st.plotly_chart(fig_map, use_container_width=True)
        else:
            st.info("Pas de données à afficher sur la carte.")

        # HORIZONTAL BAR CHARTS SECTION
        charts_col1, charts_col2 = st.columns(2)

        with charts_col1:
            top_communes = commune_level_data.sort_values(
                "price_per_sqm", ascending=False
            ).head(10)
            if not top_communes.empty:
                fig_top_communes = px.bar(
                    top_communes,
                    x="nom_commune",
                    y="price_per_sqm",
                    title="Top10 du prix médian au m²",
                    labels={"price_per_sqm": "Prix/m² (€)", "nom_commune": "Commune"},
                    color="price_per_sqm",
                    color_continuous_scale=px.colors.sequential.OrRd,
                )
                fig_top_communes.update_layout(height=500)
                st.plotly_chart(fig_top_communes, use_container_width=True)
            else:
                st.info("Pas de données pour le top 10 des communes.")

        with charts_col2:
            # Ensure 'type_local' and 'price_per_sqm' are present
            if not all(
                col in filtered_data.columns for col in ["type_local", "price_per_sqm"]
            ):
                st.warning(
                    "Colonnes 'type_local' ou 'price_per_sqm' manquantes pour l'analyse par type de bien."
                )
            else:
                property_types_data_polars = (
                    filtered_data.group_by("type_local")
                    .agg(
                        avg_price_per_sqm=pl.median(
                            "price_per_sqm"
                        ),  # Using median for robustness
                        count=pl.count(),
                    )
                    .filter(
                        pl.col("avg_price_per_sqm").is_not_null()
                        & (pl.col("count") > 0)
                    )
                    .sort("count", descending=True)
                )

                if property_types_data_polars.is_empty():
                    st.warning(
                        "Aucune donnée sur les types de biens disponible avec les filtres actuels."
                    )
                else:
                    property_types_pd = data_processor.convert_to_pandas(
                        property_types_data_polars
                    )
                    if not property_types_pd.empty:
                        fig_property_types = px.bar(
                            property_types_pd,
                            x="type_local",
                            y="avg_price_per_sqm",
                            title="Prix médian au m² par type de bien",
                            labels={
                                "avg_price_per_sqm": "Prix médian/m² (€)",
                                "type_local": "Type de bien",
                            },
                            color="avg_price_per_sqm",
                            text="count",
                            color_continuous_scale=px.colors.sequential.Blues,
                        )
                        fig_property_types.update_traces(
                            texttemplate="%{text:,} transactions",
                            textposition="outside",
                        )
                        st.plotly_chart(fig_property_types, use_container_width=True)
                    else:
                        st.warning(
                            "Pas assez de données pour afficher les prix par type de bien."
                        )
    else:
        st.warning(
            "Pas assez de données géolocalisées valides pour afficher la carte des prix avec les filtres actuels."
        )
