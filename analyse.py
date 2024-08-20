import pandas as pd
import streamlit as st
import plotly.express as px
import seaborn as sns
import matplotlib.pyplot as plt

# Configurer le thème Streamlit
st.set_page_config(layout="wide")

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

    # Calculer les durées entre chaque version pour chaque document
    donnees = donnees.sort_values(by=['Libellé du document', 'Date dépôt GED'])
    donnees['Durée entre versions'] = donnees.groupby('Libellé du document')['Date dépôt GED'].diff().dt.days

    # Remplacer les valeurs manquantes dans 'Durée entre versions' par 0
    donnees['Durée entre versions'] = donnees['Durée entre versions'].fillna(0)

    return donnees

# Charger les données
chemin_fichier = st.file_uploader("Téléchargez votre fichier CSV", type=["csv"])
if chemin_fichier is not None:
    donnees = charger_donnees(chemin_fichier)
    donnees = pretraiter_donnees(donnees)

    st.header("Statistiques descriptives")
    
    # Calcul des statistiques descriptives
    nombre_documents = donnees.groupby('TYPE DE DOCUMENT').size().reset_index(name='Nombre de documents')
    moyenne_indices = donnees.groupby('TYPE DE DOCUMENT')['Nombre d\'indices'].mean().reset_index(name='Nombre moyen d\'indices')
    duree_moyenne_versions = donnees.groupby('TYPE DE DOCUMENT')['Durée entre versions'].mean().reset_index(name='Durée moyenne entre versions (jours)')
    
    stats_description = pd.merge(nombre_documents, moyenne_indices, on='TYPE DE DOCUMENT')
    stats_description = pd.merge(stats_description, duree_moyenne_versions, on='TYPE DE DOCUMENT')
    
    st.dataframe(stats_description)
    
    st.header("Visualisation des tendances")
    
    # Visualisation du nombre de documents par type de document
    fig_documents_type = px.bar(nombre_documents, x='TYPE DE DOCUMENT', y='Nombre de documents', title='Nombre de documents par Type de Document')
    st.plotly_chart(fig_documents_type, use_container_width=True)
    
    # Visualisation des tendances de révision par type de document
    fig_tendances_revision = px.line(donnees, x='Date dépôt GED', y='INDICE', color='TYPE DE DOCUMENT', title='Tendances de révision par Type de Document')
    st.plotly_chart(fig_tendances_revision, use_container_width=True)
    
    st.header("Analyse de corrélation")
    
    # Calculer la matrice de corrélation
    donnees_corr = pd.merge(nombre_documents, moyenne_indices, on='TYPE DE DOCUMENT')
    donnees_corr = pd.merge(donnees_corr, duree_moyenne_versions, on='TYPE DE DOCUMENT')
    correlation_matrix = donnees_corr.corr()
    
    st.write("Matrice de corrélation:")
    st.dataframe(correlation_matrix)
    
    # Visualisation de la matrice de corrélation (Heatmap)
    fig, ax = plt.subplots()
    sns.heatmap(correlation_matrix, annot=True, cmap='coolwarm', ax=ax)
    st.pyplot(fig)
    
    # Scatter plot pour observer les corrélations spécifiques
    fig_scatter = px.scatter(donnees_corr, x='Nombre de documents', y='Durée moyenne entre versions (jours)', title='Corrélation entre Nombre de documents et Durée moyenne entre versions')
    st.plotly_chart(fig_scatter, use_container_width=True)
    
    fig_scatter_indices = px.scatter(donnees_corr, x='Nombre moyen d\'indices', y='Durée moyenne entre versions (jours)', title='Corrélation entre Nombre moyen d\'indices et Durée moyenne entre versions')
    st.plotly_chart(fig_scatter_indices, use_container_width=True)
else:
    st.write("Veuillez télécharger un fichier CSV pour commencer l'analyse.")
