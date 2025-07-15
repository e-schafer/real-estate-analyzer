import plotly.express as px
import polars as pl
import streamlit as st


def display_demographics_page(data_processor, filtered_data):
    st.markdown(
        '<div class="section-header">Données Démographiques (basées sur les transactions)</div>',
        unsafe_allow_html=True,
    )
    if filtered_data.is_empty():
        st.warning("Aucune donnée à afficher avec les filtres actuels.")
        return

    st.info(
        "Cette section analyse la distribution des types de biens et leur popularité par commune, offrant un aperçu démographique indirect."
    )

    # Distribution of property types
    st.markdown(
        '<div class="sub-header">Distribution des types de biens</div>',
        unsafe_allow_html=True,
    )
    property_type_dist_polars = (
        filtered_data.group_by("type_local")
        .agg(pl.count().alias("count"))
        .sort("count", descending=True)
    )
    property_type_dist_pd = data_processor.convert_to_pandas(property_type_dist_polars)

    if not property_type_dist_pd.empty:
        fig_type_dist = px.pie(
            property_type_dist_pd,
            names="type_local",
            values="count",
            title="Répartition des types de biens vendus",
            hole=0.3,
        )
        fig_type_dist.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(fig_type_dist, use_container_width=True)
    else:
        st.warning(
            "Pas assez de données pour afficher la distribution des types de biens."
        )

    # Most popular property types by commune
    st.markdown(
        '<div class="sub-header">Types de biens les plus populaires par commune</div>',
        unsafe_allow_html=True,
    )

    # Ensure 'nom_commune' and 'type_local' are present
    if (
        "nom_commune" not in filtered_data.columns
        or "type_local" not in filtered_data.columns
    ):
        st.warning(
            "Les colonnes 'nom_commune' ou 'type_local' sont manquantes dans les données filtrées."
        )
        return

    popular_types_by_commune_polars = (
        filtered_data.group_by(["nom_commune", "type_local"])
        .agg(pl.count().alias("transaction_count"))
        .sort(["nom_commune", "transaction_count"], descending=[False, True])
        .group_by(
            "nom_commune", maintain_order=True
        )  # maintain_order=True to keep the sort from previous step
        .head(3)  # Top 3 types per commune
    )

    popular_types_by_commune_pd = data_processor.convert_to_pandas(
        popular_types_by_commune_polars
    )

    if not popular_types_by_commune_pd.empty:
        # For better visualization, we might want to pivot or reformat this.
        # For now, let's display it as a table or a grouped bar chart if it makes sense.

        # Option 1: Display as a table
        st.write(
            "Top 3 des types de biens par commune (basé sur le nombre de transactions)"
        )
        st.dataframe(popular_types_by_commune_pd)

        # Option 2: Grouped Bar Chart (might be too cluttered if many communes)
        # Consider allowing user to select a few communes for this chart

        # For simplicity, let's show a bar chart for the overall top N types across all selected communes
        # This is already covered by the pie chart above, so let's focus on the per-commune aspect.

        # Let's try a more focused bar chart: Number of transactions for top type in each commune
        top_type_per_commune_polars = (
            filtered_data.group_by(["nom_commune", "type_local"])
            .agg(pl.count().alias("transaction_count"))
            .sort("transaction_count", descending=True)
            .group_by("nom_commune", maintain_order=True)
            .head(1)  # Top 1 type per commune
        )
        top_type_per_commune_pd = data_processor.convert_to_pandas(
            top_type_per_commune_polars
        )

        if not top_type_per_commune_pd.empty:
            fig_top_type_commune = px.bar(
                top_type_per_commune_pd.sort_values(
                    "transaction_count", ascending=False
                ).head(
                    20
                ),  # Show top 20 communes by transaction count of their top type
                x="nom_commune",
                y="transaction_count",
                color="type_local",
                title="Type de bien le plus transigé par commune (Top 20 communes)",
                labels={
                    "transaction_count": "Nombre de transactions",
                    "nom_commune": "Commune",
                    "type_local": "Type de bien",
                },
                hover_data=["type_local"],
            )
            st.plotly_chart(fig_top_type_commune, use_container_width=True)
        else:
            st.warning(
                "Pas assez de données pour afficher le type de bien le plus populaire par commune."
            )

    else:
        st.warning(
            "Pas assez de données pour afficher les types de biens populaires par commune."
        )
