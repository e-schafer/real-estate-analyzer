# Real Estate Market Analyzer - Guide d'installation et d'utilisation

## Installation

L'application utilise Python avec un environnement virtuel. Si vous avez déjà créé l'environnement virtuel, activez-le. Sinon, créez-en un nouveau :

```bash
# Activer l'environnement virtuel existant
source venv/bin/activate  # Sur Linux/Mac
# ou
.\venv\Scripts\activate   # Sur Windows
```

### Installation des dépendances avec UV

Le projet utilise `uv` pour gérer les dépendances. Si vous n'avez pas encore installé les dépendances :

```bash
# Installation des dépendances
uv pip install -e .
```

## Exécution de l'application

Pour lancer l'application, exécutez simplement :

```bash
python main.py
```

Ou directement avec Streamlit :

```bash
streamlit run app.py
```

## Structure des données

L'application utilise les fichiers CSV du dossier `data` :

-   `dvf31.csv` : Données immobilières du département 31 (Haute-Garonne)
-   `dvf65.csv` : Données immobilières du département 65 (Hautes-Pyrénées)

Ces fichiers contiennent des informations détaillées sur les transactions immobilières, y compris :

-   Prix des biens
-   Localisation (adresse, commune, code postal)
-   Caractéristiques des biens (surface, nombre de pièces)
-   Coordonnées géographiques (latitude, longitude)

## Fonctionnalités

L'application offre plusieurs visualisations :

1. **Prix au m²** : Carte montrant les prix au mètre carré par quartier ou par ville
2. **Tendances du marché** : Évolution des prix et du volume de transactions dans le temps
3. **Données démographiques** : Informations sur la population et l'activité immobilière par commune
4. **Carte des biens** : Localisation précise des biens avec leurs caractéristiques détaillées

## Filtrage des données

Vous pouvez filtrer les visualisations par :

-   Département
-   Type de bien (Maison, Appartement, etc.)

## Notes techniques

-   Le traitement des données est réalisé avec la bibliothèque Polars pour des performances optimales
-   La visualisation utilise Streamlit, Plotly et Folium
-   Les coordonnées géographiques sont utilisées pour la création des cartes interactives
