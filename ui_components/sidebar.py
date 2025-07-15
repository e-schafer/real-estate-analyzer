import polars as pl
import streamlit as st


def display_sidebar_controls(raw_data):
    st.sidebar.markdown(
        '<div class="section-header">Filtres</div>', unsafe_allow_html=True
    )

    # Ensure 'code_departement' and 'type_local' columns exist
    if "code_departement" not in raw_data.columns:
        st.sidebar.error("Colonne 'code_departement' manquante dans les données.")
        # Provide default empty list or handle error as appropriate
        available_departments = []
    else:
        available_departments = sorted(raw_data["code_departement"].unique().to_list())

    selected_departments = st.sidebar.multiselect(
        "Départements", options=available_departments, default=available_departments
    )

    if "type_local" not in raw_data.columns:
        st.sidebar.error("Colonne 'type_local' manquante dans les données.")
        available_types = []
    else:
        available_types = sorted(raw_data["type_local"].unique().to_list())

    selected_types = st.sidebar.multiselect(
        "Types de biens", options=available_types, default=available_types
    )

    st.sidebar.markdown(
        '<div class="section-header">Navigation</div>', unsafe_allow_html=True
    )
    page = st.sidebar.radio(
        "Sélectionnez une visualisation",
        [
            "Prix au m²",
            "Tendances du marché",
            "Données démographiques",
            "Carte des biens",
        ],
    )
    return page, selected_departments, selected_types


def apply_filters(raw_data, selected_departments, selected_types):
    filtered_data = raw_data
    if selected_departments and "code_departement" in raw_data.columns:
        filtered_data = filtered_data.filter(
            pl.col("code_departement").is_in(selected_departments)
        )
    if selected_types and "type_local" in raw_data.columns:
        filtered_data = filtered_data.filter(pl.col("type_local").is_in(selected_types))
    return filtered_data


def create_sidebar(raw_data):
    page, selected_departments, selected_types = display_sidebar_controls(raw_data)
    filtered_data = apply_filters(raw_data, selected_departments, selected_types)

    st.sidebar.markdown(
        '<div class="sub-header">Statistiques</div>', unsafe_allow_html=True
    )
    st.sidebar.info(f"Nombre de transactions: {filtered_data.shape[0]:,}")
    if filtered_data.shape[0] > 0:
        avg_price = filtered_data["valeur_fonciere"].mean()
        st.sidebar.info(f"Prix moyen: {avg_price:,.2f} €")

        avg_price_sqm = filtered_data["price_per_sqm"].mean()
        st.sidebar.info(f"Prix moyen au m²: {avg_price_sqm:,.2f} €/m²")

    return page, filtered_data, selected_departments, selected_types
