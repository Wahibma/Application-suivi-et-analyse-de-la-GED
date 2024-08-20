import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import timedelta
from PIL import Image
import os
from streamlit_option_menu import option_menu  # Import correct

# Configurer le thème Streamlit
st.set_page_config(layout="wide")
st.markdown("""
    <style>
    .css-18e3th9 {
        background-color: #FFFFFF;
    }
    .css-1d391kg {
        color: #343641;
    }
    .css-1v3fvcr {
        background-color: #17D0B1;
    }
    .css-12ttj6m {
        background-color: #FFFFFF;
    }
    </style>
""", unsafe_allow_html=True)

# Fonction pour afficher le logo
def afficher_logo():
    chemin_logo = os.path.join('logo1.jpeg')
    try:
        logo = Image.open(chemin_logo)
        st.image(logo, width=150)
    except FileNotFoundError:
        st.error(f"Le fichier logo n'a pas été trouvé à l'emplacement : {chemin_logo}")

# Fonction pour styliser l'en-tête
def style_entete():
    st.markdown(f"""
        <style>
        .entete {{
            background-color: #004080;
            color: white;
            font-weight: bold;
            text-align: center;
            padding: 20px;
            font-size: 24px;
        }}
        .sidebar .css-1d391kg {{
            background-color: #f8f9fa;
        }}
        .sidebar .css-1v3fvcr {{
            background-color: #f8f9fa;
        }}
        .main .block-container {{
            padding-top: 1rem;
        }}
        </style>
        <div class="entete">
            Analyse Exploratoire des Documents GED
        </div>
        """, unsafe_allow_html=True)

# Fonction pour charger les données depuis un fichier
@st.cache_data
def charger_donnees(chemin_fichier):
    spec_types = {
        'Date dépôt GED': str,
        'TYPE DE DOCUMENT': str,
        'PROJET': str,
        'EMET': str,
        'LOT': str,
        'INDICE': str,
        'Libellé du document': str
    }
    donnees = pd.read_csv(chemin_fichier, encoding='iso-8859-1', sep=';', dtype=spec_types, low_memory=False)
    donnees['Date dépôt GED'] = pd.to_datetime(donnees['Date dépôt GED'], format='%d/%m/%Y', errors='coerce')
    return donnees

# Fonction pour charger les données depuis un fichier téléchargé
@st.cache_data
def charger_donnees_uploaded(file):
    return charger_donnees(file)

# Fonction pour prétraiter les données
@st.cache_data
def pretraiter_donnees(donnees):
    donnees = donnees.sort_values(by=['TYPE DE DOCUMENT', 'Date dépôt GED'])
    group = donnees.groupby(['TYPE DE DOCUMENT', 'LOT', 'Libellé du document'])
    donnees['Date première version'] = group['Date dépôt GED'].transform('min')
    donnees['Date dernière version'] = group['Date dépôt GED'].transform('max')
    donnees['Différence en jours'] = (donnees['Date dernière version'] - donnees['Date première version']).dt.days
    donnees['Nombre d\'indices'] = group['INDICE'].transform('nunique')
    
    # Remplir les valeurs manquantes avant la transformation
    donnees['INDICE'] = donnees['INDICE'].fillna('')
    donnees['Indices utilisés'] = group['INDICE'].transform(lambda x: ', '.join(sorted(set(x))))

    # Ajouter les colonnes Date début et Date fin pour chaque LOT
    donnees['Date début'] = donnees.groupby('LOT')['Date dépôt GED'].transform('min')
    donnees['Date fin'] = donnees.groupby('LOT')['Date dépôt GED'].transform('max')
    
    # Calculer les durées entre chaque version pour chaque document
    donnees = donnees.sort_values(by=['Libellé du document', 'Date dépôt GED'])
    donnees['Durée entre versions'] = donnees.groupby('Libellé du document')['Date dépôt GED'].diff().dt.days

    return donnees

# Fonction pour afficher le menu latéral
def afficher_menu():
    with st.sidebar:
        selectionne = option_menu(
            menu_title="Menu",
            options=["Analyse Exploratoire", "Flux des documents", "Évolution des types de documents", "Analyse des documents par lot et indice", "Identification des acteurs principaux", "Analyse de la masse de documents par projet", "Nombre d'indices par type de document", "Durée entre versions de documents", "Calendrier des Projets", "Calendrier par Lot"],
            icons=["bar-chart-line", "exchange", "line-chart", "bar-chart", "users", "chart-bar", "file-text", "clock", "calendar", "calendar"],
            menu_icon="cast",
            default_index=0,
            orientation="vertical"
        )
    return selectionne

# Fonction pour gérer le téléchargement de fichiers
def gerer_telechargement():
    uploaded_files = st.file_uploader("Téléchargez vos fichiers CSV", type=["csv"], accept_multiple_files=True)
    projets = {}
    if uploaded_files:
        for uploaded_file in uploaded_files:
            projets[uploaded_file.name] = charger_donnees_uploaded(uploaded_file)
    return projets

# Fonction pour synchroniser les filtres entre les onglets
def synchroniser_filtres(projets):
    if 'projet_selectionne' not in st.session_state:
        st.session_state['projet_selectionne'] = list(projets.keys())[0]
    projet_selectionne = st.selectbox('Sélectionnez un projet', list(projets.keys()), key='projet_global', index=list(projets.keys()).index(st.session_state['projet_selectionne']))
    st.session_state['projet_selectionne'] = projet_selectionne
    return projets[projet_selectionne], projet_selectionne

# Fonction pour calculer les statistiques descriptives
def calculer_statistiques_descriptives(donnees):
    st.header("Statistiques Descriptives")
    
    # Calcul du nombre de documents par type de document
    stats_nombre_documents = donnees.groupby('TYPE DE DOCUMENT')['Libellé du document'].count()
    
    # Calcul de la moyenne des indices par type de document
    moyennes_indices = donnees.groupby('TYPE DE DOCUMENT')['Nombre d\'indices'].mean()
    
    # Calcul de la durée moyenne entre les versions par type de document
    duree_moyenne_versions = donnees.groupby('TYPE DE DOCUMENT')['Durée entre versions'].mean()
    
    # Création du tableau des statistiques
    tableau_statistiques = pd.DataFrame({
        'Statistique': ['Nombre de documents par type de document', 'Moyenne des indices par type de document', 'Durée moyenne entre versions par type de document'],
        'Minimum': [stats_nombre_documents.min(), moyennes_indices.min(), duree_moyenne_versions.min()],
        'Maximum': [stats_nombre_documents.max(), moyennes_indices.max(), duree_moyenne_versions.max()],
        'Moyenne': [stats_nombre_documents.mean(), moyennes_indices.mean(), duree_moyenne_versions.mean()]
    })
    
    # Affichage du tableau des statistiques
    st.table(tableau_statistiques)

# Fonction pour visualiser les tendances de révision
def visualiser_tendances_revision(donnees):
    st.header("Visualisation des tendances de révision")
    
    # Tendances de révision par type de document
    donnees_groupees = donnees.groupby([donnees['Date dépôt GED'].dt.to_period("M"), 'TYPE DE DOCUMENT']).size().reset_index(name='Nombre de documents')
    donnees_groupees['Date dépôt GED'] = donnees_groupees['Date dépôt GED'].dt.to_timestamp()

    fig = px.line(donnees_groupees, x='Date dépôt GED', y='Nombre de documents', color='TYPE DE DOCUMENT',
                  title="Tendances de révision par Type de Document")
    st.plotly_chart(fig, use_container_width=True)

    # Tendances de révision par lot de projet
    donnees_groupees_lot = donnees.groupby([donnees['Date dépôt GED'].dt.to_period("M"), 'LOT']).size().reset_index(name='Nombre de documents')
    donnees_groupees_lot['Date dépôt GED'] = donnees_groupees_lot['Date dépôt GED'].dt.to_timestamp()

    fig2 = px.line(donnees_groupees_lot, x='Date dépôt GED', y='Nombre de documents', color='LOT',
                  title="Tendances de révision par Lot de Projet")
    st.plotly_chart(fig2, use_container_width=True)

# Fonction pour identifier les corrélations entre les variables
def identifier_correlations(donnees):
    st.header("Identification des Corrélations")

    # Calcul des statistiques nécessaires
    stats_corr = donnees.groupby('TYPE DE DOCUMENT').agg({
        'Libellé du document': 'count',
        'Nombre d\'indices': 'mean',
        'Durée entre versions': 'mean'
    }).rename(columns={'Libellé du document': 'Nombre de documents',
                       'Nombre d\'indices': 'Moyenne des indices',
                       'Durée entre versions': 'Durée moyenne entre versions'})
    
    # Calcul de la matrice de corrélation
    correlation_matrix = stats_corr.corr()

    # Affichage du tableau de corrélation
    st.write("**Matrice de corrélation :**")
    st.dataframe(correlation_matrix)

    # Affichage du heatmap
    fig = px.imshow(correlation_matrix, text_auto=True, title="Heatmap des Corrélations")
    st.plotly_chart(fig, use_container_width=True)

# Fonction pour afficher les graphiques selon l'onglet sélectionné
def afficher_graphique(selectionne, donnees, projets, projet_selectionne):
    if selectionne == "Analyse Exploratoire":
        calculer_statistiques_descriptives(donnees)
        visualiser_tendances_revision(donnees)
        identifier_correlations(donnees)
    # Les autres onglets restent inchangés et peuvent être ajoutés ici...

# Exécution principale de l'application
if __name__ == '__main__':
    afficher_logo()
    style_entete()
    selectionne = afficher_menu()
    projets = gerer_telechargement()
    if projets:
        donnees, projet_selectionne = synchroniser_filtres(projets)
        donnees = pretraiter_donnees(donnees)
        afficher_graphique(selectionne, donnees, projets, projet_selectionne)
    else:
        st.write("Veuillez télécharger des fichiers CSV pour continuer.")
