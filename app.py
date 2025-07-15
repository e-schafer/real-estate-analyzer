import streamlit as st

from data_processing import RealEstateData
from ui_components.demographics_page import display_demographics_page
from ui_components.market_trends_page import display_market_trends_page
from ui_components.price_map_page import display_price_map_page
from ui_components.property_map_page import display_property_map_page
from ui_components.sidebar import (  # Corrected import names
    apply_filters,
    display_sidebar_controls,
)

# Removed unused imports like folium, numpy, pandas, plotly, etc. as they are now in specific UI components
# import folium
# import numpy as np
# import pandas as pd
# import plotly.express as px
# import plotly.graph_objects as go
# import polars as pl # polars is used by data_processor, but not directly in app.py anymore
# from streamlit_folium import folium_static # Moved to property_map_page


# Setup the page configuration
st.set_page_config(
    page_title="Analyse du Marché Immobilier",
    page_icon="🏠",
    layout="wide",
)

# Custom CSS for better styling
st.markdown(
    """
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E88E5;
        font-weight: bold;
        margin-bottom: 2rem;
    }
    .section-header {
        font-size: 1.8rem;
        color: #4CAF50;
        font-weight: bold;
        margin-top: 1.5rem;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #FF9800;
        font-weight: bold;
        margin-top: 1rem;
    }
    .info-text {
        font-size: 1rem;
        color: #616161;
    }
</style>
""",
    unsafe_allow_html=True,
)

# Title of the app
st.markdown(
    '<div class="main-header">Analyse du Marché Immobilier</div>',
    unsafe_allow_html=True,
)


# Initialize data processor
@st.cache_data(ttl=3600)
def load_data_and_processor():
    try:
        data_processor = RealEstateData()
        data = data_processor.load_data()
        if data is None or data.is_empty():
            st.error(
                "Le chargement des données a échoué ou les données sont vides. Vérifiez les logs et les fichiers CSV."
            )
            return None, None
        return data_processor, data
    except Exception as e:
        st.error(
            f"Erreur critique lors de l'initialisation ou du chargement des données: {e}"
        )
        return None, None


def main():
    data_processor, raw_data = load_data_and_processor()

    if not data_processor or raw_data is None or raw_data.is_empty():
        st.warning(
            "Les données n'ont pas pu être chargées. L'application ne peut pas continuer."
        )
        return

    st.success(
        f"Données chargées avec succès! {raw_data.height} transactions disponibles."
    )

    page, selected_departments, selected_types = display_sidebar_controls(
        raw_data
    )  # Corrected function name

    filtered_data = apply_filters(raw_data, selected_departments, selected_types)

    # Display filtered data statistics in sidebar (moved from main app body)
    st.sidebar.markdown(
        '<div class="sub-header">Statistiques (Données Filtrées)</div>',
        unsafe_allow_html=True,
    )
    st.sidebar.info(f"Nombre de transactions: {filtered_data.height:,}")
    if filtered_data.height > 0:
        # Ensure columns exist before trying to calculate mean
        if "valeur_fonciere" in filtered_data.columns:
            avg_price = filtered_data["valeur_fonciere"].mean()
            if avg_price is not None:
                st.sidebar.info(f"Prix moyen: {avg_price:,.2f} €")

        if "price_per_sqm" in filtered_data.columns:
            avg_price_sqm = filtered_data["price_per_sqm"].mean()
            if avg_price_sqm is not None:
                st.sidebar.info(f"Prix moyen au m²: {avg_price_sqm:,.2f} €/m²")
    else:
        st.sidebar.info("Aucune transaction après filtrage.")

    if page == "Prix au m²":
        display_price_map_page(
            data_processor, filtered_data, selected_departments, selected_types
        )
    elif page == "Tendances du marché":
        display_market_trends_page(data_processor, filtered_data)
    elif page == "Données démographiques":
        display_demographics_page(data_processor, filtered_data)
    elif page == "Carte des biens":
        display_property_map_page(data_processor, filtered_data)
    else:
        st.error("Page non reconnue.")


if __name__ == "__main__":
    main()
