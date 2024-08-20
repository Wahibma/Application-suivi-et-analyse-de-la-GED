import pandas as pd
import streamlit as st
import plotly.express as px
from datetime import datetime, timedelta
from PIL import Image
import os

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

    # Remplacer les valeurs manquantes dans 'Durée entre versions' par 0
    donnees['Durée entre versions'] = donnees['Durée entre versions'].fillna(0)

    return donnees

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

# Filtrer les données par période
def filtrer_donnees_par_periode(donnees, periode):
    date_debut = donnees['Date dépôt GED'].min()
    if periode == '6 mois':
        date_fin = date_debut + timedelta(days=180)
    elif periode == '1 an':
        date_fin = date_debut + timedelta(days=365)
    else:
        date_fin = donnees['Date dépôt GED'].max()
    
    return donnees[(donnees['Date dépôt GED'] >= date_debut) & (donnees['Date dépôt GED'] <= date_fin)]

# Fonction pour afficher les graphiques selon l'onglet sélectionné
def afficher_graphique(donnees):
    st.header("Analyse séquentielle des documents")
    
    # Sélection de la période d'analyse
    periode = st.radio('Sélectionnez la période d\'analyse', ('6 mois', '1 an', 'Toute la période'), index=0)
    
    donnees_filtrees = filtrer_donnees_par_periode(donnees, periode)
    
    lot_selectionne = st.selectbox('Sélectionnez un Lot', donnees_filtrees['LOT'].unique(), key='analyse_lot')
    donnees_lot = donnees_filtrees[donnees_filtrees['LOT'] == lot_selectionne]

    st.subheader(f"Analyse séquentielle des documents pour le Lot {lot_selectionne} sur {periode}")

    # Distribution des types de documents dans le lot sélectionné
    distribution_types = donnees_lot['TYPE DE DOCUMENT'].value_counts().reset_index()
    distribution_types.columns = ['Type de Document', 'Nombre de Documents']
    fig_distribution = px.bar(distribution_types, x='Type de Document', y='Nombre de Documents', title='Distribution des types de documents')
    st.plotly_chart(fig_distribution, use_container_width=True)

    # Définir une palette de couleurs unique pour éviter les répétitions
    unique_types = donnees_lot['TYPE DE DOCUMENT'].unique()
    palette = px.colors.qualitative.Plotly  # Utilisation d'une palette de couleurs qualitative
    color_map = {doc_type: palette[i % len(palette)] for i, doc_type in enumerate(unique_types)}

    # Séquence de diffusion des documents
    donnees_lot = donnees_lot.sort_values(by='Date dépôt GED')
    fig_sequence = px.scatter(donnees_lot, x='Date dépôt GED', y='TYPE DE DOCUMENT', 
                              color='TYPE DE DOCUMENT', color_discrete_map=color_map,
                              title='Séquence de diffusion des documents', hover_data=['Libellé du document'])
    st.plotly_chart(fig_sequence, use_container_width=True)

    # Résumé statistique
    resume = donnees_lot.groupby('TYPE DE DOCUMENT').agg({
        'Date dépôt GED': ['min', 'max'],
        'Durée entre versions': 'mean'
    }).reset_index()
    resume.columns = ['Type de Document', 'Date début', 'Date fin', 'Durée moyenne entre versions (jours)']
    st.subheader("Résumé statistique")
    st.dataframe(resume)

# Exécution principale de l'application
if __name__ == '__main__':
    afficher_logo()
    projets = gerer_telechargement()
    if projets:
        donnees, projet_selectionne = synchroniser_filtres(projets)
        donnees = pretraiter_donnees(donnees)
        afficher_graphique(donnees)
    else:
        st.write("Veuillez télécharger des fichiers CSV pour continuer.")
