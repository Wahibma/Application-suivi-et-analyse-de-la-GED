import pandas as pd
import streamlit as st
import plotly.express as px
from sklearn.cluster import KMeans
from sklearn.ensemble import IsolationForest
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

# Calculer la séquence moyenne des documents par type
def calculer_sequence_moyenne(donnees):
    donnees['Date dépôt GED Ordinale'] = donnees['Date dépôt GED'].map(pd.Timestamp.toordinal)
    moyenne_dates = donnees.groupby('TYPE DE DOCUMENT')['Date dépôt GED Ordinale'].mean()
    moyenne_dates = moyenne_dates.map(lambda x: datetime.fromordinal(int(round(x))))
    moyenne_dates = moyenne_dates.reset_index()
    moyenne_dates.columns = ['Type de Document', 'Date Moyenne de Dépôt GED']
    return moyenne_dates

# Détection des anomalies dans la séquence de diffusion des documents
def detecter_anomalies(donnees):
    donnees['Timestamp'] = donnees['Date dépôt GED'].map(pd.Timestamp.timestamp)
    model = IsolationForest(contamination=0.05)
    donnees['Anomalie'] = model.fit_predict(donnees[['Timestamp']])
    return donnees

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

    # Séquence de diffusion des documents
    donnees_lot = donnees_lot.sort_values(by='Date dépôt GED')
    fig_sequence = px.scatter(donnees_lot, x='Date dépôt GED', y='TYPE DE DOCUMENT', color='TYPE DE DOCUMENT', 
                              title='Séquence de diffusion des documents', hover_data=['Libellé du document'])
    st.plotly_chart(fig_sequence, use_container_width=True)

    # Séquence moyenne de diffusion des documents
    moyenne_dates = calculer_sequence_moyenne(donnees_lot)
    fig_sequence_moyenne = px.scatter(moyenne_dates, x='Date Moyenne de Dépôt GED', y='Type de Document', 
                                      title='Séquence moyenne de diffusion des documents', labels={'Date Moyenne de Dépôt GED': 'Date Moyenne de Dépôt GED'})
    st.plotly_chart(fig_sequence_moyenne, use_container_width=True)

    # Analyse par clustering
    donnees_lot['Timestamp'] = donnees_lot['Date dépôt GED'].map(pd.Timestamp.timestamp)
    kmeans = KMeans(n_clusters=3)
    donnees_lot['Cluster'] = kmeans.fit_predict(donnees_lot[['Timestamp']])
    fig_clustering = px.scatter(donnees_lot, x='Date dépôt GED', y='TYPE DE DOCUMENT', color='Cluster', 
                                title='Clustering des documents par date de dépôt', hover_data=['Libellé du document'])
    st.plotly_chart(fig_clustering, use_container_width=True)

    # Détection des anomalies
    donnees_lot = detecter_anomalies(donnees_lot)
    fig_anomalies = px.scatter(donnees_lot, x='Date dépôt GED', y='TYPE DE DOCUMENT', color='Anomalie',
                               title='Détection des anomalies dans la séquence de diffusion des documents', hover_data=['Libellé du document'])
    st.plotly_chart(fig_anomalies, use_container_width=True)

    # Analyse de corrélation
    st.subheader("Analyse de corrélation")
    donnees_lot['Date Ordinale'] = donnees_lot['Date dépôt GED'].map(pd.Timestamp.toordinal)
    corr_matrix = donnees_lot[['Date Ordinale', 'Durée entre versions']].corr()
    fig_corr = px.imshow(corr_matrix, text_auto=True, title='Matrice de corrélation')
    st.plotly_chart(fig_corr, use_container_width=True)

    # Résumé statistique
    resume = donnees_lot.groupby('TYPE DE DOCUMENT').agg({
        'Date dépôt GED': ['min', 'max'],
        'Durée entre versions': 'mean'
    }).reset_index()
    resume.columns = ['Type de Document', 'Date début', 'Date fin', 'Durée moyenne entre versions (jours)']
    st.subheader("Résumé statistique")
    st.dataframe(resume)

    # Ajout de Synthèse et Recommandations
    st.subheader("Synthèse et Recommandations")
    st.markdown("""
    - **Tendances Générales**: La majorité des documents sont déposés au début de la période. Une stratégie pour lisser les dépôts pourrait être envisagée.
    - **Anomalies**: Quelques anomalies ont été détectées. Ces documents nécessitent une révision manuelle.
    - **Recommandations**: Optimiser le processus de dépôt des documents pour les projets à long terme afin de mieux répartir la charge de travail.
    """)

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
