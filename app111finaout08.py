import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from streamlit_option_menu import option_menu
from datetime import timedelta
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
            Suivi et Analyse des Documents GED
        </div>
        """, unsafe_allow_html=True)

# Fonction pour afficher le logo dans la barre latérale
def afficher_logo_sidebar():
    chemin_logo = os.path.join('logo1.jpeg')
    try:
        logo = Image.open(chemin_logo)
        with st.sidebar:
            st.image(logo, width=95)
    except FileNotFoundError:
        st.sidebar.error(f"Le fichier logo n'a pas été trouvé à l'emplacement : {chemin_logo}")

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

# Fonction pour générer des couleurs dynamiques
def generate_dynamic_colors(n):
    return px.colors.qualitative.Plotly * (n // len(px.colors.qualitative.Plotly) + 1)

# Fonction pour afficher le menu latéral
def afficher_menu():
    with st.sidebar:
        selectionne = option_menu(
            menu_title="Menu",
            options=["Flux des documents", "Évolution des types de documents", "Analyse des documents par lot et indice", "Identification des acteurs principaux", "Analyse de la masse de documents par projet", "Nombre d'indices par type de document", "Durée entre versions de documents", "Calendrier des Projets", "Calendrier par Lot"],
            icons=["exchange", "line-chart", "bar-chart", "users", "chart-bar", "file-text", "clock", "calendar", "calendar"],
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

# Fonction pour afficher les graphiques selon l'onglet sélectionné
def afficher_graphique(selectionne, donnees, projets, projet_selectionne):
    # Onglet 1: Flux des documents
    if selectionne == "Flux des documents":
        st.header("Flux des documents")
        total_par_indice = donnees['INDICE'].value_counts(normalize=True) * 100
        total_par_indice = total_par_indice.reset_index()
        total_par_indice.columns = ['INDICE', 'Pourcentage']
        etiquettes_indices_avec_pourcentage = total_par_indice.apply(lambda row: f"{row['INDICE']} ({row['Pourcentage']:.2f}%)", axis=1)
        map_pourcentage_indice = dict(zip(total_par_indice['INDICE'], etiquettes_indices_avec_pourcentage))
        donnees['INDICE'] = donnees['INDICE'].map(map_pourcentage_indice)
        tous_les_noeuds = pd.concat([donnees['PROJET'], donnees['EMET'], donnees['TYPE DE DOCUMENT'], donnees['INDICE']]).unique()
        tous_les_noeuds = pd.Series(index=tous_les_noeuds, data=range(len(tous_les_noeuds)))
        source = tous_les_noeuds[donnees['PROJET']].tolist() + tous_les_noeuds[donnees['EMET']].tolist() + tous_les_noeuds[donnees['TYPE DE DOCUMENT']].tolist()
        cible = tous_les_noeuds[donnees['EMET']].tolist() + tous_les_noeuds[donnees['TYPE DE DOCUMENT']].tolist() + tous_les_noeuds[donnees['INDICE']].tolist()
        valeur = [1] * len(donnees['PROJET']) + [1] * len(donnees['EMET']) + [1] * len(donnees['TYPE DE DOCUMENT'])
        etiquettes_noeuds = tous_les_noeuds.index.tolist()
        fig = go.Figure(data=[go.Sankey(
            node=dict(pad=15, thickness=20, line=dict(color='black', width=0.5), label=etiquettes_noeuds),
            link=dict(source=source, target=cible, value=valeur)
        )])
        fig.add_annotation(x=0.1, y=1.1, text="Projet", showarrow=False, font=dict(size=12, color="blue"))
        fig.add_annotation(x=0.35, y=1.1, text="Émetteur", showarrow=False, font=dict(size=12, color="blue"))
        fig.add_annotation(x=0.6, y=1.1, text="Type de Document", showarrow=False, font=dict(size=12, color="blue"))
        fig.add_annotation(x=0.9, y=1.1, text="Indice", showarrow=False, font=dict(size=12, color="blue"))
        fig.update_layout(title_text="", font_size=10, margin=dict(l=0, r=0, t=40, b=0))
        st.plotly_chart(fig, use_container_width=True)

    # Onglet 2: Évolution des types de documents
    elif selectionne == "Évolution des types de documents":
        st.header("Évolution des types de documents")
        options_type_document = donnees['TYPE DE DOCUMENT'].unique()
        types_selectionnes = st.multiselect('Sélectionnez les types de document', options_type_document, default=options_type_document[0], key='tab1_types')
        donnees_groupees = donnees.groupby([donnees['Date dépôt GED'].dt.to_period("M"), 'TYPE DE DOCUMENT']).size().reset_index(name='Nombre de documents')
        donnees_groupees['Date dépôt GED'] = donnees_groupees['Date dépôt GED'].dt.to_timestamp()
        fig = go.Figure()
        for t in types_selectionnes:
            donnees_filtrees = donnees_groupees[donnees_groupees['TYPE DE DOCUMENT'] == t]
            fig.add_trace(go.Scatter(x=donnees_filtrees['Date dépôt GED'], y=donnees_filtrees['Nombre de documents'].cumsum(), mode='lines+markers', name=f'Cumulé - {t}'))
            fig.add_trace(go.Scatter(x=donnees_filtrees['Date dépôt GED'], y=donnees_filtrees['Nombre de documents'], mode='lines+markers', name=t, visible='legendonly'))
        fig.update_layout(
            title=f'Évolution du nombre de documents pour {projet_selectionne}',
            xaxis_title='Date de Dépôt',
            yaxis_title='Nombre de Documents',
            legend_title='Type de Documents',
            height=500, width=1200
        )
        st.plotly_chart(fig, use_container_width=True)

    # Onglet 3: Analyse des documents par lot et indice
    elif selectionne == "Analyse des documents par lot et indice":
        st.header("Analyse des documents par lot et indice")
        options_indice = donnees['INDICE'].unique()
        indices_selectionnes = st.multiselect('Sélectionnez un ou plusieurs indices', options_indice, key='tab3_indices')
        if indices_selectionnes:
            donnees = donnees[donnees['INDICE'].isin(indices_selectionnes)]
        donnees_groupees_treemap = donnees.groupby(['LOT', 'INDICE']).size().reset_index(name='Nombre de documents')
        fig_treemap = px.treemap(
            donnees_groupees_treemap,
            path=['LOT', 'INDICE'],
            values='Nombre de documents',
            title='Répartition des documents par lot et indice'
        )
        fig_treemap.update_layout(height=500, width=1200)
        donnees_groupees_type_indice2 = donnees.groupby(['TYPE DE DOCUMENT', 'INDICE']).size().reset_index(name='Nombre de documents')
        fig_type_indice2 = px.treemap(
            donnees_groupees_type_indice2,
            path=['TYPE DE DOCUMENT', 'INDICE'],
            values='Nombre de documents',
            title='Répartition des documents par type de documents et indice'
        )
        fig_type_indice2.update_layout(height=550, width=1200)
        donnees_groupees_type_indice = donnees.groupby(['LOT', 'TYPE DE DOCUMENT', 'INDICE']).size().reset_index(name='Nombre de documents')
        fig_type_indice = px.treemap(
            donnees_groupees_type_indice,
            path=['LOT', 'TYPE DE DOCUMENT', 'INDICE'],
            values='Nombre de documents',
            title='Répartition des documents par type de documents, lot et indice'
        )
        fig_type_indice.update_layout(height=800, width=1200)
        documents_par_lot = donnees.groupby('LOT').size().reset_index(name='Nombre de documents')
        fig_bar_lot = px.bar(
            documents_par_lot,
            y='LOT',
            x='Nombre de documents',
            orientation='h',
            title="Nombre de documents par lot",
            labels={"LOT": "Lot", "Nombre de documents": "Nombre de documents"},
            color='Nombre de documents',
            color_continuous_scale=px.colors.sequential.Viridis
        )
        fig_bar_lot.update_layout(yaxis={'categoryorder': 'total ascending'}, height=850, width=1000)
        documents_par_type = donnees.groupby('TYPE DE DOCUMENT').size().reset_index(name='Nombre de documents')
        fig_bar_type = px.bar(
            documents_par_type,
            y='TYPE DE DOCUMENT',
            x='Nombre de documents',
            orientation='h',
            title="Nombre de documents par type de documents",
            labels={"TYPE DE DOCUMENT": "Type de documents", "Nombre de documents": "Nombre de documents"},
            color='Nombre de documents',
            color_continuous_scale=px.colors.sequential.Viridis
        )
        fig_bar_type.update_layout(yaxis={'categoryorder': 'total ascending'}, height=850, width=1200)
        st.plotly_chart(fig_treemap, use_container_width=True)
        st.plotly_chart(fig_type_indice2, use_container_width=True)
        st.plotly_chart(fig_type_indice, use_container_width=True)
        st.plotly_chart(fig_bar_lot, use_container_width=True)
        st.plotly_chart(fig_bar_type, use_container_width=True)

    # Onglet 4: Identification des acteurs principaux
    elif selectionne == "Identification des acteurs principaux":
        st.header("Identification des acteurs principaux")
        donnees['Date dépôt GED'] = pd.to_datetime(donnees['Date dépôt GED'], format='%d/%m/%Y')
        donnees['Année'] = donnees['Date dépôt GED'].dt.year
        fig_emetteur = px.treemap(donnees, path=['EMET', 'TYPE DE DOCUMENT'], title='Répartition des types de documents par émetteur')
        fig_emetteur.update_layout(margin=dict(l=20, r=20, t=40, b=20), height=480, width=1200)
        st.plotly_chart(fig_emetteur, use_container_width=True)
        fig_ajoute_par = px.treemap(donnees, path=['Ajouté par', 'TYPE DE DOCUMENT'], title='Répartition des types de documents par acteur (Ajouté par)')
        fig_ajoute_par.update_layout(margin=dict(l=20, r=20, t=40, b=20), height=480, width=1200)
        st.plotly_chart(fig_ajoute_par, use_container_width=True)

    # Onglet 5: Analyse de la masse de documents par projet
    elif selectionne == "Analyse de la masse de documents par projet":
        st.header("Analyse de la masse de documents par projet")
        periode_selectionnee = st.radio(
            'Sélectionnez la période',
            options=['6m', '12m', 'all'],
            format_func=lambda x: '6 premiers mois' if x == '6m' else '12 premiers mois' if x == '12m' else 'Toute la période',
            horizontal=True
        )
        projets_selectionnes = st.multiselect('Sélectionnez les projets', list(projets.keys()), default=list(projets.keys()))

        def mise_a_jour_analyse_masse_documents(projets_selectionnes, periode_selectionnee):
            donnees_barre = []
            for projet in projets_selectionnes:
                df = projets[projet]
                date_debut = df['Date dépôt GED'].min()
                if periode_selectionnee == '6m':
                    date_fin = date_debut + timedelta(days=180)  # 6 mois
                elif periode_selectionnee == '12m':
                    date_fin = date_debut + timedelta(days=365)  # 12 mois
                else:
                    date_fin = df['Date dépôt GED'].max()  # Toute la période
                df_filtre = df[(df['Date dépôt GED'] >= date_debut) & (df['Date dépôt GED'] <= date_fin)]
                total_documents = df_filtre.shape[0]
                donnees_barre.append({
                    'Chantier': projet,
                    'Masse de documents': total_documents,
                    'Date début': date_debut.strftime('%d %b %Y'),
                    'Date fin': date_fin.strftime('%d %b %Y')
                })
            df_barre = pd.DataFrame(donnees_barre)
            df_barre = df_barre.sort_values(by='Masse de documents', ascending=False)
            mediane_masse = df_barre['Masse de documents'].median()
            df_barre['mediane'] = mediane_masse
            fig_barre = go.Figure()
            fig_barre.add_trace(go.Bar(
                x=df_barre['Chantier'], y=df_barre['Masse de documents'],
                text=df_barre['Masse de documents'], textposition='auto',
                name='Masse de documents',
                marker_color=generate_dynamic_colors(len(df_barre))
            ))
            fig_barre.add_trace(go.Scatter(
                x=df_barre['Chantier'], y=df_barre['mediane'],
                mode='lines', name='Médiane',
                line=dict(color='blue', dash='dash')
            ))
            for index, row in df_barre.iterrows():
                fig_barre.add_annotation(
                    x=row['Chantier'], y=row['Masse de documents'],
                    text=f"{row['Masse de documents']}",
                    showarrow=True, arrowhead=2
                )
            fig_barre.update_layout(
                title='Analyse de la masse de documents par projet',
                xaxis_title='Chantier', yaxis_title='Masse de documents',
                font=dict(size=15),
                height=450,
                width=1200,
                yaxis=dict(title='Masse de documents', showgrid=True, zeroline=True, showline=True, showticklabels=True),
                xaxis=dict(title='Chantier', showgrid=True, zeroline=True, showline=True, showticklabels=True)
            )
            return fig_barre

        fig1 = mise_a_jour_analyse_masse_documents(projets_selectionnes, periode_selectionnee)
        st.plotly_chart(fig1, use_container_width=True)

    # Onglet 6: Nombre d'indices par type de document
    elif selectionne == "Nombre d'indices par type de document":
        st.header("Nombre d'indices par type de document")
        type_calcul = st.selectbox('Sélectionnez le type de calcul', ['mean', 'max'], key='calcul_indices_type')
        representation = st.selectbox('Sélectionnez le type de représentation', ['Graphique barre', 'Tableau'], key='rep_indices_type', index=0)  # Par défaut à "Graphique barre"
        if representation == "Tableau":
            if type_calcul == 'mean':
                resultats = donnees.groupby('TYPE DE DOCUMENT')['Nombre d\'indices'].mean().reset_index()
                resultats.columns = ['TYPE DE DOCUMENT', 'Nombre moyen d\'indices']
            elif type_calcul == 'max':
                resultats = donnees.groupby('TYPE DE DOCUMENT')['Nombre d\'indices'].max().reset_index()
                resultats.columns = ['TYPE DE DOCUMENT', 'Nombre maximum d\'indices']
            st.dataframe(resultats)
        elif representation == "Graphique barre":
            if type_calcul == 'mean':
                resultats = donnees.groupby('TYPE DE DOCUMENT')['Nombre d\'indices'].mean().reset_index()
                title = 'Nombre moyen d\'indices par Type de Document'
            elif type_calcul == 'max':
                resultats = donnees.groupby('TYPE DE DOCUMENT')['Nombre d\'indices'].max().reset_index()
                title = 'Nombre maximum d\'indices par Type de Document'
            resultats = resultats.sort_values(by=resultats.columns[1], ascending=False)
            fig = px.bar(resultats, x='TYPE DE DOCUMENT', y=resultats.columns[1], title=title, color='TYPE DE DOCUMENT', color_discrete_sequence=generate_dynamic_colors(len(resultats)))
            fig.update_layout(showlegend=True, legend_title_text='Type de Document')
            fig.update_traces(texttemplate='%{y:.2f}', textposition='outside')
            st.plotly_chart(fig, use_container_width=True)

    # Onglet 7: Durée entre versions de documents
    elif selectionne == "Durée entre versions de documents":
        st.header("Durée entre versions de documents")
        type_calcul = st.selectbox('Sélectionnez le type de calcul', ['mean', 'max'], key='calcul_duree_versions_type')
        categorie = st.selectbox('Sélectionnez la catégorie', ['TYPE DE DOCUMENT','LOT'], key='categorie_duree_versions_type')  # Choix entre Lot et Type de Document
        representation = st.selectbox('Sélectionnez le type de représentation', ['Graphique barre', 'Tableau'], key='rep_duree_versions_type', index=0)  # Par défaut à "Graphique barre"
        
        if representation == "Tableau":
            if type_calcul == 'mean':
                resultats = donnees.groupby(categorie)['Durée entre versions'].mean().reset_index()
                resultats.columns = [categorie, 'Durée moyenne entre versions (jours)']
            elif type_calcul == 'max':
                resultats = donnees.groupby(categorie)['Durée entre versions'].max().reset_index()
                resultats.columns = [categorie, 'Durée maximum entre versions (jours)']
            resultats = resultats.sort_values(by=resultats.columns[1], ascending=False)
            st.dataframe(resultats)
        elif representation == "Graphique barre":
            if type_calcul == 'mean':
                resultats = donnees.groupby(categorie)['Durée entre versions'].mean().reset_index()
                title = f'Durée moyenne entre versions (jours) par {categorie}'
            elif type_calcul == 'max':
                resultats = donnees.groupby(categorie)['Durée entre versions'].max().reset_index()
                title = f'Durée maximum entre versions (jours) par {categorie}'
            resultats = resultats.sort_values(by=resultats.columns[1], ascending=False)
            fig = px.bar(resultats, x=categorie, y=resultats.columns[1], title=title, color=categorie, color_discrete_sequence=generate_dynamic_colors(len(resultats)))
            fig.update_layout(showlegend=True, legend_title_text=categorie)
            fig.update_traces(texttemplate='%{y:.2f}', textposition='outside')
            st.plotly_chart(fig, use_container_width=True)

        # Calcul des durées entre indices pour chaque type de document
        st.subheader("Durées entre indices par type de document")
        durées_indices = []
        for doc_type, group in donnees.groupby('TYPE DE DOCUMENT'):
            group = group.sort_values(by=['Libellé du document', 'INDICE'])
            group['Durée entre indices'] = group.groupby('Libellé du document')['Date dépôt GED'].diff().dt.days
            group['Passage indice'] = group.groupby('Libellé du document')['INDICE'].transform(lambda x: x.shift(1) + ' à ' + x)
            for _, row in group.iterrows():
                if pd.notna(row['Durée entre indices']):
                    durées_indices.append({
                        'Type de Document': doc_type,
                        'Document': row['Libellé du document'],
                        'Passage indice': row['Passage indice'],
                        'Durée entre indices (jours)': row['Durée entre indices']
                    })
        df_durées_indices = pd.DataFrame(durées_indices)
        if not df_durées_indices.empty:
            st.dataframe(df_durées_indices)
        else:
            st.write("Pas de données disponibles pour les durées entre indices.")

    # Onglet 8: Calendrier des Projets 
    elif selectionne == "Calendrier des Projets":
        st.header("Calendrier des Projets")
        # Ajouter le selectbox pour choisir entre "Lot" et "Type de Document"
        categorie_gantt = st.selectbox('Sélectionnez la catégorie', ['LOT', 'TYPE DE DOCUMENT'], key='categorie_gantt')  # Choix entre Lot et Type de Document

        # Préparer les données pour le diagramme de Gantt
        donnees_gantt = donnees.groupby(categorie_gantt).agg({
            'Date dépôt GED': ['min', 'max'],
            'Libellé du document': 'count'
        }).reset_index()
        donnees_gantt.columns = [categorie_gantt, 'Date début', 'Date fin', 'Nombre de documents']
        donnees_gantt['Durée en jours'] = (donnees_gantt['Date fin'] - donnees_gantt['Date début']).dt.days

        # Ajouter les types de documents utilisés pour chaque lot dans l'ordre d'apparition
        donnees_sorted = donnees.sort_values(by='Date dépôt GED')
        donnees_gantt['Types de documents'] = donnees_sorted.groupby(categorie_gantt)['TYPE DE DOCUMENT'].apply(lambda x: ', '.join(x.drop_duplicates())).reset_index(drop=True)

        # Trier les catégories par date de début
        donnees_gantt = donnees_gantt.sort_values('Date début')

        # Utiliser une palette de couleurs dynamique pour éviter les répétitions
        couleurs = generate_dynamic_colors(len(donnees_gantt))

        # S'assurer que les barres sont affichées même si la durée est nulle
        donnees_gantt['Date fin'] = donnees_gantt.apply(lambda x: x['Date fin'] if x['Durée en jours'] > 0 else x['Date début'] + pd.Timedelta(days=1), axis=1)

        fig_gantt = px.timeline(
            donnees_gantt,
            x_start='Date début',
            x_end='Date fin',
            y=categorie_gantt,
            color=categorie_gantt,
            hover_data=['Durée en jours', 'Nombre de documents', 'Types de documents'],
            color_discrete_sequence=couleurs,
            title=f'Calendrier des Projets par {categorie_gantt}'
        )
        fig_gantt.update_layout(
            xaxis_title='Date',
            yaxis_title=categorie_gantt,
            height=600,
            width=1000
        )
        fig_gantt.update_traces(
            hovertemplate=f'<b>{categorie_gantt}:</b> %{{y}}<br><b>Début:</b> %{{base|%d %b %Y}}<br><b>Fin:</b> %{{x|%d %b %Y}}<br><b>Durée:</b> %{{customdata[0]}} jours<br><b>Nombre de documents:</b> %{{customdata[1]}}<br><b>Types de documents:</b> %{{customdata[2]}}'
        )
        st.plotly_chart(fig_gantt, use_container_width=True)

        # Afficher le tableau récapitulatif
        donnees_gantt['Date début'] = donnees_gantt['Date début'].dt.strftime('%d %b %Y')
        donnees_gantt['Date fin'] = donnees_gantt['Date fin'].dt.strftime('%d %b %Y')
        st.subheader("Détails des projets")
        st.dataframe(donnees_gantt)

    # Onglet 9: Calendrier par Lot
    elif selectionne == "Calendrier par Lot":
        st.header("Calendrier par Lot")
        lot_selectionne = st.selectbox('Sélectionnez un Lot', donnees['LOT'].unique())
        donnees_filtrees = donnees[donnees['LOT'] == lot_selectionne]

        donnees_gantt = donnees_filtrees.groupby('TYPE DE DOCUMENT').agg({
            'Date dépôt GED': ['min', 'max'],
            'Libellé du document': 'count'
        }).reset_index()
        donnees_gantt.columns = ['TYPE DE DOCUMENT', 'Date début', 'Date fin', 'Nombre de documents']
        donnees_gantt['Durée en jours'] = (donnees_gantt['Date fin'] - donnees_gantt['Date début']).dt.days

        donnees_sorted = donnees_filtrees.sort_values(by='Date dépôt GED')
        donnees_gantt['Types de documents'] = donnees_sorted.groupby('TYPE DE DOCUMENT')['TYPE DE DOCUMENT'].apply(lambda x: ', '.join(x.drop_duplicates())).reset_index(drop=True)
        donnees_gantt = donnees_gantt.sort_values('Date début')
        couleurs = generate_dynamic_colors(len(donnees_gantt))

        donnees_gantt['Date fin'] = donnees_gantt.apply(lambda x: x['Date fin'] if x['Durée en jours'] > 0 else x['Date début'] + pd.Timedelta(days=1), axis=1)

        fig_gantt = px.timeline(
            donnees_gantt,
            x_start='Date début',
            x_end='Date fin',
            y='TYPE DE DOCUMENT',
            color='TYPE DE DOCUMENT',
            hover_data=['Durée en jours', 'Nombre de documents', 'Types de documents'],
            color_discrete_sequence=couleurs,
            title=f'Calendrier par Lot: {lot_selectionne}'
        )
        fig_gantt.update_layout(
            xaxis_title='Date',
            yaxis_title='TYPE DE DOCUMENT',
            height=600,
            width=1000
        )
        fig_gantt.update_traces(
            hovertemplate=f'<b>Type de Document:</b> %{{y}}<br><b>Début:</b> %{{base|%d %b %Y}}<br><b>Fin:</b> %{{x|%d %b %Y}}<br><b>Durée:</b> %{{customdata[0]}} jours<br><b>Nombre de documents:</b> %{{customdata[1]}}<br><b>Types de documents:</b> %{{customdata[2]}}'
        )
        st.plotly_chart(fig_gantt, use_container_width=True)

        donnees_gantt['Date début'] = donnees_gantt['Date début'].dt.strftime('%d %b %Y')
        donnees_gantt['Date fin'] = donnees_gantt['Date fin'].dt.strftime('%d %b %Y')
        st.subheader("Détails du Lot")
        st.dataframe(donnees_gantt)

# Exécution principale de l'application
if __name__ == '__main__':
    afficher_logo()
    style_entete()
    afficher_logo_sidebar()
    selectionne = afficher_menu()
    projets = gerer_telechargement()
    if projets:
        donnees, projet_selectionne = synchroniser_filtres(projets)
        donnees = pretraiter_donnees(donnees)
        afficher_graphique(selectionne, donnees, projets, projet_selectionne)
    else:
        st.write("Veuillez télécharger des fichiers CSV pour continuer.")
