import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import polars as pl
import streamlit as st


def display_market_trends_page(data_processor, filtered_data):
    st.markdown(
        '<div class="section-header">Tendances du Marché Immobilier</div>',
        unsafe_allow_html=True,
    )
    if filtered_data.is_empty():
        st.warning("Aucune donnée à afficher avec les filtres actuels.")
        return

    # Get market trends data using filtered_data
    trends_polars = (
        filtered_data.with_columns(
            [
                pl.col("date_mutation").dt.year().alias("year"),
                pl.col("date_mutation").dt.month().alias("month"),
            ]
        )
        .group_by(["year", "month"])
        .agg(
            [
                pl.median("price_per_sqm").alias("median_price_per_sqm"),
                pl.count().alias(
                    "transaction_count"
                ),  # Use pl.count() for transaction_count
            ]
        )
        .filter(
            pl.col("median_price_per_sqm").is_not_null()
            & (pl.col("transaction_count") > 0)
        )
        .sort(["year", "month"])
    )

    if trends_polars.is_empty():
        st.warning("Aucune donnée de tendance disponible avec les filtres actuels.")
        return

    trends_pd = data_processor.convert_to_pandas(trends_polars)
    if trends_pd.empty:
        st.warning("Conversion des données de tendance en Pandas a échoué ou est vide.")
        return

    trends_pd["date"] = pd.to_datetime(trends_pd[["year", "month"]].assign(day=1))
    trends_pd = trends_pd.sort_values("date")

    # Plot price trend over time
    st.markdown(
        '<div class="sub-header">Évolution des prix au m²</div>', unsafe_allow_html=True
    )
    fig_price = px.line(
        trends_pd,
        x="date",
        y="median_price_per_sqm",
        title="Évolution du prix médian au m² dans le temps",
        labels={"median_price_per_sqm": "Prix médian/m²", "date": "Date"},
        markers=True,
    )

    y_series_price = trends_pd["median_price_per_sqm"].dropna()
    if not y_series_price.empty:
        y_price = y_series_price.to_numpy(dtype=np.float64)
        x_price = np.arange(len(y_price))
        if (
            len(x_price) > 1
            and not np.isnan(y_price).any()
            and not np.isinf(y_price).any()
        ):
            try:
                z_price = np.polyfit(x_price, y_price, 1)
                p_price = np.poly1d(z_price)
                fig_price.add_trace(
                    go.Scatter(
                        x=trends_pd.loc[y_series_price.index, "date"],
                        y=p_price(x_price),
                        mode="lines",
                        name="Tendance (Prix)",
                        line=dict(color="red", dash="dash"),
                    )
                )
            except (np.linalg.LinAlgError, ValueError) as e:
                st.warning(f"Impossible de calculer la tendance des prix: {e}")
    st.plotly_chart(fig_price, use_container_width=True)

    # Stacked bar chart for transaction volume by property type
    st.markdown(
        '<div class="sub-header">Volume de transactions par type de bien</div>',
        unsafe_allow_html=True,
    )
    volume_by_type_polars = (
        filtered_data.with_columns(
            [
                pl.col("date_mutation").dt.year().alias("year"),
                pl.col("date_mutation").dt.month().alias("month"),
            ]
        )
        .group_by(["year", "month", "type_local"])
        .agg(
            pl.count().alias("transaction_count")  # Corrected aggregation
        )
        .filter(pl.col("transaction_count") > 0)  # Ensure there are transactions
        .sort(["year", "month", "type_local"])
    )

    if volume_by_type_polars.is_empty():
        st.warning(
            "Pas assez de données pour afficher le volume de transactions par type de bien."
        )
    else:
        volume_by_type_pd = data_processor.convert_to_pandas(volume_by_type_polars)
        if not volume_by_type_pd.empty:
            volume_by_type_pd["date"] = pd.to_datetime(
                volume_by_type_pd[["year", "month"]].assign(day=1)
            )
            fig_volume_by_type = px.bar(
                volume_by_type_pd,
                x="date",
                y="transaction_count",
                color="type_local",
                title="Volume de Transactions Mensuel par Type de Bien",
                labels={
                    "transaction_count": "Nombre de Transactions",
                    "date": "Date",
                    "type_local": "Type de Bien",
                },
                barmode="stack",
            )
            st.plotly_chart(fig_volume_by_type, use_container_width=True)
        else:
            st.warning(
                "Conversion des données de volume par type en Pandas a échoué ou est vide."
            )

    # Price evolution by property type
    st.markdown(
        '<div class="sub-header">Évolution des prix par type de bien</div>',
        unsafe_allow_html=True,
    )
    type_trends_polars = (
        filtered_data.with_columns(
            [
                pl.col("date_mutation").dt.year().alias("year"),
                pl.col("date_mutation").dt.month().alias("month"),
            ]
        )
        .group_by(["year", "month", "type_local"])
        .agg(
            [
                pl.median("price_per_sqm").alias("median_price_per_sqm"),
                pl.count().alias("transaction_count"),  # Use pl.count()
            ]
        )
        .filter(
            (pl.col("transaction_count") >= 5)  # Added parentheses here
            & pl.col("median_price_per_sqm").is_not_null()
        )
        .sort(["year", "month", "type_local"])
    )

    if type_trends_polars.is_empty():
        st.warning(
            "Pas assez de données pour afficher l'évolution des prix par type de bien avec les filtres actuels."
        )
    else:
        type_trends_pd = data_processor.convert_to_pandas(type_trends_polars)
        if not type_trends_pd.empty:
            type_trends_pd["date"] = pd.to_datetime(
                type_trends_pd[["year", "month"]].assign(day=1)
            )
            fig_type_trends = px.bar(  # Changed from px.line to px.bar
                type_trends_pd,
                x="date",
                y="median_price_per_sqm",
                color="type_local",
                title="Évolution du prix médian au m² par type de bien",
                labels={
                    "median_price_per_sqm": "Prix médian/m²",
                    "date": "Date",
                    "type_local": "Type de bien",
                },
                barmode="group",  # Add this line to group bars
            )
            st.plotly_chart(fig_type_trends, use_container_width=True)
        else:
            st.warning(
                "Conversion des données de tendance par type en Pandas a échoué ou est vide."
            )
