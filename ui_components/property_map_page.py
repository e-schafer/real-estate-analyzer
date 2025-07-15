from datetime import date, datetime  # Added date and datetime

import folium
import numpy as np
import pandas as pd
import plotly.express as px  # Add plotly express
import streamlit as st
from streamlit_folium import folium_static


# Haversine function to calculate distance between two lat/lon points
def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Radius of Earth in kilometers

    lat1_rad = np.radians(lat1)
    lon1_rad = np.radians(lon1)
    lat2_rad = np.radians(lat2)
    lon2_rad = np.radians(lon2)

    dlon = lon2_rad - lon1_rad
    dlat = lat2_rad - lat1_rad

    a = (
        np.sin(dlat / 2) ** 2
        + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon / 2) ** 2
    )
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

    distance = R * c
    return distance


def display_property_map_page(data_processor, filtered_data_polars):
    st.markdown(
        '<div class="section-header">Carte Interactive des Biens Immobiliers</div>',
        unsafe_allow_html=True,
    )

    # Initialize session state for search parameters
    if "search_postal_code" not in st.session_state:
        st.session_state.search_postal_code = ""
    if "search_radius_km" not in st.session_state:
        st.session_state.search_radius_km = 0.0
    if "min_price" not in st.session_state:
        st.session_state.min_price = 0
    if "max_price" not in st.session_state:
        st.session_state.max_price = 0  # 0 will mean no upper limit
    if "min_surface" not in st.session_state:
        st.session_state.min_surface = 0
    if "max_surface" not in st.session_state:
        st.session_state.max_surface = 0  # 0 will mean no upper limit
    if "search_results_df" not in st.session_state:
        st.session_state.search_results_df = pd.DataFrame()
    if "map_display_key" not in st.session_state:  # Used to force map re-render
        st.session_state.map_display_key = 0

    # Search input fields
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        # Use a temporary variable for text_input to manage updates correctly
        current_postal_code = st.text_input(
            "Code Postal:",
            value=st.session_state.search_postal_code,
            key="postal_code_input",
        )
    with col2:
        current_radius_km = st.number_input(
            "Rayon de recherche (km):",
            min_value=0.0,
            value=st.session_state.search_radius_km,
            step=0.5,
            key="radius_input",
        )
    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        search_button = st.button("Rechercher")

    # Optional filters for price and surface area
    st.markdown("##### Filtres optionnels")
    filter_col1, filter_col2 = st.columns(2)
    with filter_col1:
        current_min_price = st.number_input(
            "Prix minimum (€):",
            min_value=0,
            value=st.session_state.min_price,
            step=10000,
            key="min_price_input",
        )
        current_max_price = st.number_input(
            "Prix maximum (€) (0 pour ignorer):",
            min_value=0,
            value=st.session_state.max_price,
            step=10000,
            key="max_price_input",
        )
    with filter_col2:
        current_min_surface = st.number_input(
            "Surface minimum (m²):",
            min_value=0,
            value=st.session_state.min_surface,
            step=5,
            key="min_surface_input",
        )
        current_max_surface = st.number_input(
            "Surface maximum (m²) (0 pour ignorer):",
            min_value=0,
            value=st.session_state.max_surface,
            step=5,
            key="max_surface_input",
        )

    map_placeholder = st.empty()

    if search_button:
        st.session_state.search_postal_code = current_postal_code
        st.session_state.search_radius_km = current_radius_km
        st.session_state.min_price = current_min_price
        st.session_state.max_price = current_max_price
        st.session_state.min_surface = current_min_surface
        st.session_state.max_surface = current_max_surface
        st.session_state.map_display_key += 1  # Increment key to help refresh map

        if not st.session_state.search_postal_code:
            st.warning("Veuillez entrer un code postal pour la recherche.")
            st.session_state.search_results_df = (
                pd.DataFrame()
            )  # Clear previous results
        else:
            all_properties_pd = data_processor.convert_to_pandas(filtered_data_polars)

            if all_properties_pd.empty:
                st.warning("Aucune donnée de base à filtrer.")
                st.session_state.search_results_df = pd.DataFrame()
                # Early exit if no base data
                # The map_placeholder logic below will handle showing the "Entrez un code postal..." message
            elif not all(
                col in all_properties_pd.columns
                for col in ["latitude", "longitude", "code_postal"]
            ):
                st.error(
                    "Les colonnes 'latitude', 'longitude', et 'code_postal' sont nécessaires dans les données."
                )
                st.session_state.search_results_df = pd.DataFrame()
            else:
                # Ensure lat/lon are numeric and no NaNs for distance calculation
                all_properties_pd["latitude"] = pd.to_numeric(
                    all_properties_pd["latitude"], errors="coerce"
                )
                all_properties_pd["longitude"] = pd.to_numeric(
                    all_properties_pd["longitude"], errors="coerce"
                )
                all_properties_pd.dropna(
                    subset=["latitude", "longitude", "code_postal"], inplace=True
                )

                # Filter by postal code
                pc_matches = all_properties_pd[
                    all_properties_pd["code_postal"]
                    == st.session_state.search_postal_code
                ].copy()

                if pc_matches.empty:
                    st.info(
                        f"Aucun bien trouvé pour le code postal {st.session_state.search_postal_code}."
                    )
                    st.session_state.search_results_df = pd.DataFrame()
                else:
                    if st.session_state.search_radius_km > 0:
                        center_lat_pc = pc_matches["latitude"].mean()
                        center_lon_pc = pc_matches["longitude"].mean()

                        if pd.isna(center_lat_pc) or pd.isna(center_lon_pc):
                            st.warning(
                                "Impossible de déterminer le centre pour la recherche par rayon. Affichage des résultats pour le code postal uniquement."
                            )
                            st.session_state.search_results_df = pc_matches
                        else:
                            # Calculate distances for all_properties_pd from this centroid
                            # This ensures we search in the broader dataset around the postal code's center
                            distances = all_properties_pd.apply(
                                lambda row: haversine(
                                    center_lat_pc,
                                    center_lon_pc,
                                    row["latitude"],
                                    row["longitude"],
                                ),
                                axis=1,
                            )
                            st.session_state.search_results_df = all_properties_pd[
                                distances <= st.session_state.search_radius_km
                            ].copy()
                            if st.session_state.search_results_df.empty:
                                st.info(
                                    f"Aucun bien trouvé dans un rayon de {st.session_state.search_radius_km} km autour des biens du code postal {st.session_state.search_postal_code}."
                                )
                            else:
                                st.success(
                                    f"{len(st.session_state.search_results_df)} biens trouvés."
                                )
                    else:  # Only postal code search
                        st.session_state.search_results_df = pc_matches
                        st.success(
                            f"{len(st.session_state.search_results_df)} biens trouvés pour le code postal {st.session_state.search_postal_code}."
                        )

            # Apply optional filters if results exist
            if not st.session_state.search_results_df.empty:
                temp_results_df = st.session_state.search_results_df.copy()

                # Price filter
                if st.session_state.min_price > 0:
                    temp_results_df = temp_results_df[
                        temp_results_df["valeur_fonciere"] >= st.session_state.min_price
                    ]
                if st.session_state.max_price > 0:  # 0 means no upper limit
                    temp_results_df = temp_results_df[
                        temp_results_df["valeur_fonciere"] <= st.session_state.max_price
                    ]

                # Surface filter
                if st.session_state.min_surface > 0:
                    temp_results_df = temp_results_df[
                        temp_results_df["surface_reelle_bati"]
                        >= st.session_state.min_surface
                    ]
                if st.session_state.max_surface > 0:  # 0 means no upper limit
                    temp_results_df = temp_results_df[
                        temp_results_df["surface_reelle_bati"]
                        <= st.session_state.max_surface
                    ]

                if (
                    len(temp_results_df) < len(st.session_state.search_results_df)
                    and len(temp_results_df) == 0
                ):
                    st.info(
                        "Aucun bien ne correspond aux filtres de prix/surface supplémentaires."
                    )
                    st.session_state.search_results_df = (
                        pd.DataFrame()
                    )  # Clear results if filters leave nothing
                elif len(temp_results_df) < len(st.session_state.search_results_df):
                    st.success(
                        f"{len(temp_results_df)} biens correspondent également aux filtres de prix/surface."
                    )
                    st.session_state.search_results_df = temp_results_df
                # If no change in length, no message needed, original results are kept or already filtered results are kept.

    # Display map if search results exist
    if not st.session_state.search_results_df.empty:
        properties_to_display_pd = st.session_state.search_results_df

        center_lat = properties_to_display_pd["latitude"].mean()
        center_lon = properties_to_display_pd["longitude"].mean()

        if pd.isna(center_lat) or pd.isna(center_lon):
            center_lat, center_lon = 46.2276, 2.2137  # Default center (France)

        # Determine appropriate zoom level
        zoom_start = 6  # Default broad zoom
        if st.session_state.search_radius_km > 0:
            if st.session_state.search_radius_km <= 1:
                zoom_start = 14
            elif st.session_state.search_radius_km <= 5:
                zoom_start = 12
            elif st.session_state.search_radius_km <= 10:
                zoom_start = 11
            elif st.session_state.search_radius_km <= 25:
                zoom_start = 10
            else:
                zoom_start = 9
        elif st.session_state.search_postal_code:  # Zoom for postal code
            zoom_start = 13

        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=zoom_start,
            tiles="cartodb positron",
            scrollWheelZoom=True,  # Enable mouse wheel zoom
        )

        type_colors = {
            "Maison": "blue",
            "Appartement": "green",
            "Dépendance": "purple",
            "Local industriel. commercial ou assimilé": "orange",
            "default": "gray",
        }

        sample_size = min(
            len(properties_to_display_pd), 1000
        )  # Limit markers for performance

        # Ensure sampling is only done if there are properties to sample
        if len(properties_to_display_pd) > 0:
            sampled_properties = (
                properties_to_display_pd.sample(n=sample_size, random_state=42)
                if len(properties_to_display_pd) > sample_size
                else properties_to_display_pd
            )
        else:
            sampled_properties = (
                properties_to_display_pd  # Should be empty, but handles edge case
            )

        for idx, row in sampled_properties.iterrows():
            property_type = row.get("type_local", "N/A")
            marker_color = type_colors.get(property_type, type_colors["default"])

            # Calculate sale opacity based on age
            sale_date_val = row.get("date_mutation")
            sale_opacity = 0.7  # Default opacity for missing/invalid date

            if pd.notna(sale_date_val) and sale_date_val != "N/A":
                try:
                    if isinstance(sale_date_val, str):
                        sale_date_obj = datetime.strptime(
                            sale_date_val, "%Y-%m-%d"
                        ).date()
                    elif hasattr(sale_date_val, "date"):  # Handles pandas Timestamp
                        sale_date_obj = sale_date_val.date()
                    elif isinstance(
                        sale_date_val, date
                    ):  # Handles datetime.date directly
                        sale_date_obj = sale_date_val
                    else:
                        # If type is unexpected, attempt to convert to string and parse
                        sale_date_obj = datetime.strptime(
                            str(sale_date_val), "%Y-%m-%d"
                        ).date()

                    # Ensure sale_date_obj is a date object after attempts
                    if not isinstance(sale_date_obj, date):
                        raise ValueError("Converted value is not a date object")

                    age_in_days = (date.today() - sale_date_obj).days
                    age_in_years = age_in_days / 365.25

                    if age_in_years >= 5:
                        sale_opacity = 0.2
                    elif age_in_years < 0:  # Current year or future date
                        sale_opacity = 1.0
                    else:  # Between 0 and 5 years
                        sale_opacity = 1.0 - (age_in_years / 5.0) * 0.8

                    sale_opacity = max(0.2, min(1.0, sale_opacity))

                except (ValueError, TypeError):
                    pass  # sale_opacity remains default

            # Construct Google Street View URL
            street_view_url = f"https://www.google.com/maps?q=&layer=c&cbll={row.get('latitude')},{row.get('longitude')}&cbp=11,0,0,0,0"

            popup_html = f"""
            <b>Type:</b> {property_type}<br>
            <b>Prix:</b> {row.get("valeur_fonciere", 0):,.0f} €<br>
            <b>Surface:</b> {row.get("surface_reelle_bati", 0):.0f} m²<br>
            <b>Prix/m²:</b> {row.get("price_per_sqm", 0):,.2f} €/m²<br>
            <b>Adresse:</b> {row.get("adresse_numero", "")} {row.get("adresse_nom_voie", "")}, {row.get("nom_commune", "")} ({row.get("code_postal", "")})<br>
            <b>Date Mutation:</b> {str(row.get("date_mutation", "N/A")).split(" ")[0]}<br>
            <a href="{street_view_url}" target="_blank">Voir sur Google Street View</a>
            """
            tooltip = f"{row.get('adresse_numero', '')} {row.get('adresse_nom_voie', '')}, {property_type} - {row.get('valeur_fonciere', 0):,.0f} €"

            folium.Marker(
                location=[row["latitude"], row["longitude"]],
                radius=7,
                icon=folium.Icon(
                    color=marker_color,
                    icon="home"
                    if property_type == "Maison"
                    else "business"
                    if property_type == "Appartement"
                    else "info-sign",
                ),
                color=marker_color,
                fill=True,
                fill_color=marker_color,
                fill_opacity=sale_opacity,
                opacity=sale_opacity,
                popup=folium.Popup(popup_html, max_width=300),
                tooltip=tooltip,
            ).add_to(m)

        legend_html = """
             <div style="position: fixed; bottom: 50px; left: 50px; width: 250px; 
                         border:2px solid grey; z-index:9999; font-size:14px;
                         background-color:white; opacity:0.9; padding: 10px;">
               &nbsp; <b>Légende des types de biens</b> <br>
        """
        for type_name, color in type_colors.items():
            if type_name != "default":
                legend_html += f'&nbsp; <i style="background:{color};opacity:0.7;">&nbsp;&nbsp;&nbsp;&nbsp;</i> {type_name}<br>'
        legend_html += "</div>"
        m.get_root().add_child(folium.Element(legend_html))

        with map_placeholder.container():
            st.markdown(
                f"Affichage de {len(sampled_properties)} biens sur {len(properties_to_display_pd)} trouvés."
            )
            folium_static(m, width=None, height=600)

            st.markdown(
                "<div class='sub-header'>Statistiques des biens affichés sur la carte</div>",
                unsafe_allow_html=True,
            )
            st.write(
                f"Nombre de biens affichés sur la carte: {len(sampled_properties)}"
            )
            if not sampled_properties.empty:
                avg_price_map = sampled_properties["valeur_fonciere"].mean()
                avg_sqm_map = sampled_properties["surface_reelle_bati"].mean()
                avg_price_per_sqm_map = sampled_properties["price_per_sqm"].mean()

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Prix moyen", f"{avg_price_map:,.0f} €")
                with col2:
                    st.metric("Surface moyenne", f"{avg_sqm_map:,.1f} m²")
                with col3:
                    st.metric("Prix moyen au m²", f"{avg_price_per_sqm_map:,.2f} €/m²")

            # Create columns for the charts
            chart_col1, chart_col2 = st.columns(2)

            with chart_col1:
                # Box plot for price per sqm over the past 12 months
                st.markdown(
                    "<div class='sub-header'>Distribution des Prix au m² (12 Derniers Mois)</div>",
                    unsafe_allow_html=True,
                )

                box_plot_source_df = properties_to_display_pd.copy()

                # Robust date parsing for 'date_mutation'
                # Assuming 'date_mutation' is mostly YYYY-MM-DD or can be coerced
                box_plot_source_df["sale_date_dt"] = pd.to_datetime(
                    box_plot_source_df["date_mutation"], errors="coerce"
                )

                # Ensure 'price_per_sqm' is numeric and drop rows with NA in critical columns for the plot
                box_plot_source_df["price_per_sqm"] = pd.to_numeric(
                    box_plot_source_df["price_per_sqm"], errors="coerce"
                )
                box_plot_source_df.dropna(
                    subset=["sale_date_dt", "price_per_sqm", "type_local"], inplace=True
                )

                if not box_plot_source_df.empty:
                    today_dt = pd.Timestamp(date.today())
                    twelve_months_ago = today_dt - pd.DateOffset(months=12)

                    last_12_months_data_for_plot = box_plot_source_df[
                        (box_plot_source_df["sale_date_dt"] >= twelve_months_ago)
                        & (box_plot_source_df["sale_date_dt"] <= today_dt)
                    ]

                    if not last_12_months_data_for_plot.empty:
                        # Sort 'type_local' for consistent order in box plot
                        type_order = sorted(
                            last_12_months_data_for_plot["type_local"].unique()
                        )

                        fig_box = px.box(
                            last_12_months_data_for_plot,
                            x="type_local",
                            y="price_per_sqm",
                            title="Prix au m² par Type de Bien (12 Derniers Mois)",
                            labels={
                                "price_per_sqm": "Prix au m² (€)",
                                "type_local": "Type de Bien",
                            },
                            points="outliers",  # Show outliers
                            color="type_local",  # Color boxes by type_local
                            category_orders={
                                "type_local": type_order
                            },  # Ensure consistent x-axis order
                        )
                        fig_box.update_layout(
                            margin=dict(
                                l=20, r=20, t=60, b=20
                            ),  # Adjusted top margin for title
                            showlegend=False,  # Legend is redundant if color is same as x-axis categories
                        )
                        st.plotly_chart(fig_box, use_container_width=True)
                    else:
                        st.info(
                            "Pas de données de ventes disponibles pour les 12 derniers mois pour le graphique box plot."
                        )
                else:
                    st.info(
                        "Pas de données valides (date, prix/m², type) pour générer le graphique box plot."
                    )

            with chart_col2:
                # Line chart for average price per sqm evolution over the past 3 years
                st.markdown(
                    "<div class='sub-header'>Évolution du Prix Moyen au m² (3 Dernières Années)</div>",
                    unsafe_allow_html=True,
                )

                line_chart_source_df = properties_to_display_pd.copy()
                line_chart_source_df["sale_date_dt"] = pd.to_datetime(
                    line_chart_source_df["date_mutation"], errors="coerce"
                )
                line_chart_source_df["price_per_sqm"] = pd.to_numeric(
                    line_chart_source_df["price_per_sqm"], errors="coerce"
                )
                line_chart_source_df.dropna(
                    subset=["sale_date_dt", "price_per_sqm", "type_local"], inplace=True
                )

                if not line_chart_source_df.empty:
                    current_year = pd.Timestamp(date.today()).year
                    three_years_ago_start_of_year = pd.Timestamp(
                        date(current_year - 3, 1, 1)
                    )

                    last_3_years_data = line_chart_source_df[
                        line_chart_source_df["sale_date_dt"]
                        >= three_years_ago_start_of_year
                    ]

                    if not last_3_years_data.empty:
                        # Resample to get monthly average price per sqm for each type_local
                        last_3_years_data["sale_month_year"] = last_3_years_data[
                            "sale_date_dt"
                        ].dt.to_period("M")

                        monthly_avg_price = (
                            last_3_years_data.groupby(
                                ["sale_month_year", "type_local"]
                            )["price_per_sqm"]
                            .mean()
                            .reset_index()
                        )
                        monthly_avg_price["sale_month_year"] = monthly_avg_price[
                            "sale_month_year"
                        ].astype(str)  # Convert period to string for plotly
                        monthly_avg_price.sort_values(
                            by=["sale_month_year", "type_local"], inplace=True
                        )

                        if not monthly_avg_price.empty:
                            fig_line = px.line(
                                monthly_avg_price,
                                x="sale_month_year",
                                y="price_per_sqm",
                                color="type_local",
                                title="Évolution du Prix Moyen au m² par Type de Bien (3 Dernières Années)",
                                labels={
                                    "price_per_sqm": "Prix Moyen au m² (€)",
                                    "sale_month_year": "Mois/Année",
                                    "type_local": "Type de Bien",
                                },
                                markers=True,  # Add markers to data points
                            )
                            fig_line.update_layout(
                                margin=dict(l=20, r=20, t=60, b=20),
                                legend_title_text="Type de Bien",
                            )
                            st.plotly_chart(fig_line, use_container_width=True)
                        else:
                            st.info(
                                "Pas assez de données agrégées pour afficher l'évolution des prix sur 3 ans."
                            )
                    else:
                        st.info(
                            "Pas de données de ventes disponibles pour les 3 dernières années pour le graphique d'évolution."
                        )
                else:
                    st.info(
                        "Pas de données valides (date, prix/m², type) pour générer le graphique d'évolution."
                    )

    elif (
        search_button and st.session_state.search_postal_code
    ):  # Searched but no results
        with map_placeholder.container():
            st.info(
                "Aucun bien à afficher sur la carte pour les critères sélectionnés."
            )
    else:  # Initial state or cleared search (no postal code entered on search)
        with map_placeholder.container():
            st.info(
                "Entrez un code postal et cliquez sur 'Rechercher' pour afficher les biens immobiliers."
            )
