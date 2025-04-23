# --------------------- IMPORTS ---------------------

import streamlit as st # Framework pour créer des applications web interactives
import pandas as pd # Bibliothèque pour manipuler des données tabulaires
import geopandas as gpd
import folium
from streamlit_folium import st_folium


# --------------------- FONCTIONS ---------------------

# Fonction pour traduire les statuts codés en libellés compréhensibles
def traduire_statut(statut):
    traductions = {
            "VU": "Vulnérable",
            "EN": "En danger",
            "CR": "En danger critique",
            "NT": "Quasi menacé",
            "LC": "Préoccupation mineure",
            "DD": "Données insuffisantes",
            "RE": "Éteint régionalement",
            "NA": "Non applicable (Non indigène ou données occasionnelles)",
            "NE": "Non évalué",
            "DH IV": "Directive Habitats, Faune, Flore - Annexe IV",
            "DH II&IV": "Directive Habitats, Faune, Flore - Annexe II & IV",
            "DO I": "Directive Oiseaux - Annexe I",
            "N.C." : "Non Concerné",
            "PRA en cours" : "Plan régional d'action en cours",
            "PNA en cours" : "Plan national d'action en cours",
            "PRA en préparation" : "Plan régional d'action en préparation",
            "PNA en préparation" : "Plan national d'action en préparation",
            "PNG en cours" : "Plan national de gestion en cours",
            "PRA en cours + PNA en préparation" : "Plan régional d'action en cours + Plan national d'action en préparation"}
                    
    return traductions.get(statut, statut) # Retourne le statut traduit ou le statut d'origine si non trouvé            


# Fonction pour obtenir une couleur en fonction de l’indice de priorité de conservation
def get_conservation_color(index):
    colors = {
        1: '#00B050',  # vert foncé
        2: '#92D050',  # vert clair
        3: '#FFFF00',  # jaune
        4: '#FF9900',  # orange
        5: '#FF0000',  # rouge
    }
    return colors.get(index, '#ffffff')  # Blanc par défaut si l’indice est inconnu


# Fonction pour obtenir une couleur en fonction de l’indice de priorité réglementaire
def get_reglementaire_color(index):
    colors = {
        0: '#00B050',  # vert foncé
        1: '#92D050',  # vert clair
        2: '#FFFF00',  # jaune
        3: '#FF9900',  # orange
        4: '#FF0000',  # rouge
    }
    return colors.get(index, '#ffffff') # Blanc par défaut si l’indice est inconnu


# --------------------- CONFIGURATION ---------------------

# Définition de la configuration de la page Streamlit
st.set_page_config(page_title="Espèces remarquables et prescriptions", page_icon="🦋", layout="wide")


# --------------------- AUTHENTIFICATION --------------

# Définir un mot de passe correct
PASSWORD = "caprimulgus"

# Initialiser une session pour suivre l'état de l'utilisateur
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# Si l'utilisateur n'est pas encore connecté
if not st.session_state.authenticated:
    with st.form("login_form"):
        st.write("### Entrez le mot de passe pour accéder à l'application")
        password_input = st.text_input("Mot de passe", type="password")
        submitted = st.form_submit_button("Se connecter")

        if submitted:
            if password_input == PASSWORD:
                st.session_state.authenticated = True
                st.rerun() # recharge la page pour cacher le formulaire
            else:
                st.error("Mot de passe incorrect.")

# Si l'utilisateur est connecté
if st.session_state.authenticated:

    # Insertion du logo et configuration de la barre latérale
    st.sidebar.image("logo ONF.png", width=200)
    st.sidebar.title("Navigation")
    st.sidebar.markdown("<div style='font-size:20px;'>Aller à :</div>", unsafe_allow_html=True)

    # Application d'un style personnalisé aux composants pour agrandir les polices
    st.markdown("""
                            <style>
                    div.stMarkdown p, div.stDataFrame, div.stSelectbox, div.stExpander, div[data-testid="stVerticalBlock"] {
                        font-size: 20px !important;
                    }
                    div[data-testid="stMarkdownContainer"] {
                        font-size: 20px !important;
                    }
                </style>
            """, unsafe_allow_html=True)

    # Création d’un menu de navigation latéral
    page = st.sidebar.radio("Aller à :",["Accueil", "Recherche par forêt", "Recherche par espèce"], label_visibility="collapsed")


    # --------------------- CHARGEMENT DES DONNÉES ---------------------

    # Chargement du fichier principal contenant les observations de la Base de données naturalistes de l'ONF
    @st.cache_data
    def load_data():
        return pd.read_excel('MonExportBdn.xlsx')

    # Chargement de la liste des codes CD_NOM autorisés (filtrage pour avoir uniquement les espèces du tableau de métadonnées des espèces remarquables)
    @st.cache_data
    def load_codes_autorises():
        df_codes = pd.read_excel('Metadonnees.xlsx')
        return df_codes['CD_NOM'].astype(str).str.strip().tolist()

    # Chargement du fichier de référence des espèces avec leurs métadonnées
    @st.cache_data
    def load_reference_especes():
        df_reference = pd.read_excel('Metadonnees.xlsx')
        return df_reference

    # Exécution des fonctions de chargement
    df = load_data()
    codes_autorises = load_codes_autorises()
    df_reference = load_reference_especes()

    # Nettoyage des colonnes pour garantir l'uniformité des CD_NOM
    df_reference['CD_NOM'] = df_reference['CD_NOM'].astype(str).str.strip()
    df["Code taxon (cd_nom)"] = df["Code taxon (cd_nom)"].astype(str).str.split(',')
    df = df.explode("Code taxon (cd_nom)").copy() # Une ligne par taxon si plusieurs dans une même cellule
    df["Code taxon (cd_nom)"] = df["Code taxon (cd_nom)"].str.strip()
    df = df[df["Code taxon (cd_nom)"].isin(codes_autorises)] # Filtrage uniquement sur les espèces autorisées
    forets = df['Forêt'].dropna().unique() # Liste des forêts sans doublons ni NaN


    # --------------------- PAGE ACCUEIL ---------------------


    if page == "Accueil":
        st.title("🦋 Espèces remarquables et prescriptions") # Affichage d’un titre en haut de la page d'accueil
        
        # Texte de présentation
        st.markdown("""
        <div style='font-size:22px'>
            Bienvenue dans l'outil de consultation des données d'espèces remarquables par forêt avec les prescriptions environnementales associées.
            <br><br>
            Une espèce est considérée remarquable si elle possède au moins un des statuts suivants :
            <ul>
                <li>Espèce protégée par arrêté national ou régional ;</li>
                <li>Espèce réglementée au niveau européen par les directives Oiseaux (Annexe I) ou Habitats, Faune, Flore (Annexe II & IV) ;</li>
                <li>Espèce menacée sur la liste rouge régionale normande ou sur la liste rouge nationale (Statut "Vulnérable = VU", "En danger = EN" ou "En danger critique = CR") ;</li>
                <li>Espèce faisant l'objet d'un plan national d'action en faveur des espèces menacées ;</li>
                <li>Espèce faisant l'objet d'une clause environnementale de l'ONF (9200-15-GUI-SAM-052).</li>
            </ul>
            <br>
            Les espèces ont été hiérarchisées selon deux indices, un indice de priorité de conservation et un indice de priorité réglementaire. 
            <br><br>
            L'indice de <b>priorité de conservation</b> intègre la menace d'extinction au niveau régional et national, ainsi que la responsabilité de la Normandie dans la conservation de l'espèce. La méthode utilisée pour calculer cet indice se base sur les travaux de Barneix et Gigot (2013) et sur les initiatives de hiérarchisation qui ont découlé de ces travaux à l'échelle des régions françaises. 
            <br><br>
            L'indice de <b>priorité réglementaire</b> intègre les différents types de réglementation (Directives européennes, protection par arreté) et les subtilités d'interprétation des articles d'arrêtés. En effet, certains articles protègent uniquement les spécimens et d'autres articles protègent, en plus des spécimens, les éléments nécessaires au bon fonctionnement du cycle biologique de l'espèce, incluant notamment les sites de reproduction et de repos. Enfin, cet indice prend en compte le risque que l'ONF entrave ces réglementations. En effet, pour certaines espèces très communes comme la mésange bleue, le risque réglementaire est très faible étant donné que la conservation de l'espèce à l'échelle du massif est assurée par la gestion classique de l'ONF.
            <br><br>
            Ces deux indices permettront de hiérarchiser les enjeux et de prioriser les clauses environnementales.
            <br><br>
            ⬅️ Utilisez le menu à gauche pour consulter les espèces remarquables présentes en forêt et accéder aux statuts et prescriptions.
        </div>
        """, unsafe_allow_html=True)


    # --------------------- PAGE FORÊT ---------------------


    if page == "Recherche par forêt":

        if 'selected_foret' not in st.session_state:
            st.session_state.selected_foret = None
        if 'selected_parcelle' not in st.session_state:
            st.session_state.selected_parcelle = None

        # Aucune forêt sélectionnée : afficher la liste
        if st.session_state.selected_foret is None:
            selected_foret = st.selectbox("🌲 Sélectionnez une forêt :", [""] + sorted(forets))
            if st.button("🔍Voir les espèces remarquables par parcelle"):
                st.session_state.selected_foret = selected_foret
                st.rerun()

        # Forêt sélectionnée mais pas encore de parcelle
        elif st.session_state.selected_parcelle is None:
            foret = st.session_state.selected_foret
            df_foret = df[df['Forêt'] == foret]
            parcelles_disponibles = df_foret["Parcelle de forêt"].dropna().unique()
            selected_parcelle = st.selectbox("📌 Sélectionnez une parcelle :", [""] + sorted(parcelles_disponibles))

            # Gestion des coordonnées et du sous-ensemble de données à afficher
            if selected_parcelle and selected_parcelle != "":
                df_affichage = df_foret[df_foret["Parcelle de forêt"] == selected_parcelle]
            else:
                df_affichage = df_foret

            lat_centre = df_affichage["Coordonnée 2"].mean()
            lon_centre = df_affichage["Coordonnée 1"].mean()

            # Créer la carte
            m = folium.Map(location=[lat_centre, lon_centre], zoom_start=13)

            # Ajouter le cadastre avec le service WMS de l'IGN
            folium.raster_layers.WmsTileLayer(
                url="https://data.geopf.fr/wms-r/wms",
                layers="CADASTRALPARCELS.PARCELLAIRE_EXPRESS",
                name="Cadastre",
                fmt="image/png",
                transparent=True,
                version="1.3.0",
                overlay=True,
                control=True
            ).add_to(m)

            # Ajouter les points naturalistes avec popup enrichi
            for _, row in df_affichage.iterrows():
                if pd.notna(row["Coordonnée 1"]) and pd.notna(row["Coordonnée 2"]):
                    popup = f""" <b>Espèce :</b> {row['Espèce']}<br>
                    <b>Commentaire de la localisation : </b> {row["Commentaire de la localisation"]}<br>
                    <b>Commentaire de l'observation : </b> {row["Commentaire de l'observation"]}"""
        
                    folium.Marker(
                        location=[row["Coordonnée 2"], row["Coordonnée 1"]],
                        popup=folium.Popup(popup, max_width=500),
                        icon=folium.Icon(color="green", icon="leaf", prefix="fa")
                    ).add_to(m)

            # Ajouter le contrôle de couche (permet d'activer/désactiver la couche cadastre)
            folium.LayerControl().add_to(m)

            # Afficher la carte
            st.markdown("### 📍 Localisation des espèces remarquables")
            st_folium(m, width=900, height=600)  

            if selected_parcelle and selected_parcelle != "":
                if st.button("🔍 Voir la liste des espèces par parcelle"):
                    st.session_state.selected_parcelle = selected_parcelle
                    st.rerun()
            if st.button("⬅️ Retour à la liste des forêts"):
                st.session_state.selected_foret = None
                st.session_state.selected_parcelle = None
                st.rerun()

        # Forêt + parcelle sélectionnées : afficher les espèces
        else:
            foret = st.session_state.selected_foret
            parcelle = st.session_state.selected_parcelle
            df_filtré = df[(df['Forêt'] == foret) & (df['Parcelle de forêt'] == parcelle)]

            st.subheader(f"📍 Données pour la forêt : {foret}, parcelle {parcelle}")
            st.dataframe(df_filtré)


            species_list = df_filtré['Code taxon (cd_nom)'].unique()
            selected_species = st.selectbox("🔎 Choisissez une espèce :", species_list)

            if selected_species:
                df_reference['CD_NOM'] = df_reference['CD_NOM'].astype(str).str.strip()
                selected_species = str(selected_species).strip()
                species_reference_info = df_reference[df_reference['CD_NOM'] == selected_species]

                st.subheader(f"📘 Statuts et prescriptions : {selected_species}")

                if not species_reference_info.empty and pd.notna(species_reference_info['Rôle_TFT'].iloc[0]) and str(species_reference_info['Rôle_TFT'].iloc[0]).strip() != "":
                    with st.container():
                        nom_sci_brut = species_reference_info['Nom_scientifique_valide'].iloc[0]

                        # Supprime les balises HTML <i> et </i>
                        nom_sci_sans_balise = nom_sci_brut.replace('<i>', '').replace('</i>', '')

                        # Mets juste le nom scientifique en italique, pas l’auteur
                        nom_en_italique = nom_sci_sans_balise.split(' (')[0]  # Prend juste "Sympetrum danae"
                        auteur = nom_sci_sans_balise[len(nom_en_italique):]   # Récupère " (Sulzer, 1776)"

                        # Combine le tout en Markdown
                        nom_final = f"*{nom_en_italique}*{auteur}"
                        st.markdown(f"**Nom scientifique :** {nom_final}")
                        st.markdown(f"**Nom vernaculaire :** {species_reference_info['Nom_vernaculaire'].iloc[0]}")
                        st.markdown(f"**Catégorie naturaliste :** {species_reference_info['Cat_naturaliste'].iloc[0]}")
                        
                        # Affichage des informations sur l'espèce
                        conserv_index = species_reference_info['Indice_priorité_conservation'].iloc[0]
                        color = get_conservation_color(conserv_index)

                        st.markdown(f"""
                            <div style='background-color: {color}; padding: 6px 12px; border-radius: 8px; font-size: 20px; display: inline-block;'>
                            <b>Priorité de conservation ℹ️ :</b> {conserv_index}
                            </div>
                            """, unsafe_allow_html=True)
                        
                        reg_index = species_reference_info['Indice_priorité_réglementaire'].iloc[0]
                        color_reg = get_reglementaire_color(reg_index)

                        st.markdown(f"""
                            <div style='background-color: {color_reg};  padding: 6px 12px; border-radius: 8px; font-size: 20px; display: inline-block;'>
                            <b>Priorité réglementaire ℹ️ :</b> {reg_index}
                            </div>
                            """, unsafe_allow_html=True)

                        st.markdown ("---")
                        st.markdown(f"**Code unique clause :** {species_reference_info['Code_unique'].iloc[0]}")
                        st.markdown(f"**Condition d'application de la clause :** {species_reference_info['Condition(s)_application_clause'].iloc[0]}")
                        
                        with st.expander("📋 Libellés des clauses à inscrire"):
                            st.write(f"**Libellé Fiche chantier (TECK) :** {species_reference_info['Libellé_fiche_chantier_ONF (TECK)'].iloc[0]}")
                            st.write(f"**Libellé Fiche désignation (DESIGNATION MOBILE) :** {species_reference_info['Libellé_fiche_désignation_ONF (DESIGNATION MOBILE)'].iloc[0]}")
                            st.write(f"**Libellé Fiche vente (PRODUCTION BOIS) :** {species_reference_info['Libellé_fiche_vente_ONF (PRODUCTION BOIS)'].iloc[0]}")

                        st.markdown(f"**Rôle du TFT :** {species_reference_info['Rôle_TFT'].iloc[0]}")


                        st.markdown ("---")
                        with st.expander("ℹ️ Légende des indices de priorité"):
                            st.markdown("""
                            **Indice de priorité de conservation** :
                            - `5` : Priorité de conservation majeure
                            - `4` : Priorité de conservation très élevée 
                            - `3` : Priorité de conservation élevée
                            - `2` : Priorité de conservation modérée
                            - `1` : Priorité de conservation faible

                            **Indice de priorité réglementaire** :
                            - `4` : Risque réglementaire majeur (Espèce réglementée au niveau européen + national ou régional) si les interventions forestières impactent les spécimens OU les éléments nécessaires au bon fonctionnement de leur cycle biologique (site de reproduction, site de repos, source de nourriture etc.).
                            - `3` : Risque réglementaire élevé (Espèce réglementée au niveau national ou régional) si les interventions forestières impactent les spécimens OU les éléments nécessaires au bon fonctionnement de leur cycle biologique (site de reproduction, site de repos, source de nourriture etc.).
                            - `2` : Risque réglementaire uniquement si les interventions forestières impactent les spécimens.
                            - `1` : La gestion forestière courante de l'ONF suffit à respecter la réglementation associée à l'espèce, que ce soit sur les spécimens ou sur les éléments nécessaires au bon fonctionnement de leur cycle biologique.
                            - `0` : Espèce non protégée.
                            """)

                        # Dictionnaire de correspondance
                        respo_dict = {
                            1: "Faible",
                            2: "Modérée",
                            3: "Significative",
                            4: "Forte",
                            5: "Majeure"
                        }

                        # Récupérer la valeur brute dans le tableau
                        valeur_respo = species_reference_info['Respo_reg'].iloc[0]

                        # Traduire en texte si possible
                        texte_respo = respo_dict.get(valeur_respo, "Non renseignée")

                        with st.expander("🟢Détail des statuts"):
                            st.write(f"**Liste rouge régionale :** {traduire_statut(species_reference_info['LR_reg'].iloc[0])}")
                            st.write(f"**Liste rouge nationale :** {traduire_statut(species_reference_info['LR_nat'].iloc[0])}")
                            st.write(f"**Responsabilité régionale :** {texte_respo}")
                            st.write(f"**Directives européennes :** {traduire_statut(species_reference_info['Directives_euro'].iloc[0])}")
                            st.write(f"**Plan d'action :** {traduire_statut(species_reference_info['Plan_action'].iloc[0])}")
                            st.write(f"**Arrêté de protection :** {traduire_statut(species_reference_info['Arrêté_protection'].iloc[0])}")
                            st.write(f"**Article de l'arrêté :** {traduire_statut(species_reference_info['Article_arrêté'].iloc[0])}")
                else:
                    st.info("❌ Cette espèce ne fait pas l'objet de prescription environnementale.")

            if st.button("⬅️ Retour à la liste des parcelles"):
                st.session_state.selected_parcelle = None
                st.rerun()
            if st.button("⬅️ Retour à la liste des forêts"):
                st.session_state.selected_foret = None
                st.session_state.selected_parcelle = None
                st.rerun()


    # --------------------- PAGE ESPECES ---------------------


    elif page == "Recherche par espèce" :
        st.markdown("### 🔎 Recherche par espèce")
        st.markdown(
        "<div style='font-size:20px;'>"
        "Entrez un code CD_NOM :"
        "</div>",
        unsafe_allow_html=True
        )
        search_cd_nom = st.text_input(label=" ", label_visibility="collapsed")
        
        st.markdown("""
        <div style='font-size:20px'>
        Si vous connaissez uniquement le nom de l'espèce, tapez-le dans la barre de recherche du site de l'INPN pour obtenir le CD_NOM : <a href='https://inpn.mnhn.fr/accueil/index' target='_blank'>inpn.mnhn.fr</a>
        </div>
        """, unsafe_allow_html=True)

        st.image("inpn_ex.png", use_container_width=True)

        if search_cd_nom:
            search_cd_nom = search_cd_nom.strip()
            st.markdown("""
                <style>
                    div.stMarkdown p, div.stDataFrame, div.stSelectbox, div.stExpander, div[data-testid="stVerticalBlock"] {
                        font-size: 20px !important;
                    }
                    div[data-testid="stMarkdownContainer"] {
                        font-size: 20px !important;
                    }
                </style>
            """, unsafe_allow_html=True)
            match = df_reference[df_reference['CD_NOM'] == search_cd_nom]

            st.subheader(f"📘 Statuts et prescriptions : {search_cd_nom}")

            if not match.empty and str(match['Rôle_TFT'].iloc[0]).strip().upper() != "N.C.":
                with st.container():
                    nom_sci_brut = match['Nom_scientifique_valide'].iloc[0]

                    # Supprime les balises HTML <i> et </i>
                    nom_sci_sans_balise = nom_sci_brut.replace('<i>', '').replace('</i>', '')

                    # Mets juste le nom scientifique en italique, pas l’auteur
                    nom_en_italique = nom_sci_sans_balise.split(' (')[0]  # Prend juste "Sympetrum danae"
                    auteur = nom_sci_sans_balise[len(nom_en_italique):]   # Récupère " (Sulzer, 1776)"

                    # Combine le tout en Markdown
                    nom_final = f"*{nom_en_italique}*{auteur}"
                    st.markdown(f"**Nom scientifique :** {nom_final}")
                    st.markdown(f"**Nom vernaculaire :** {match['Nom_vernaculaire'].iloc[0]}")
                    st.markdown(f"**Catégorie naturaliste :** {match['Cat_naturaliste'].iloc[0]}")
                    
                    conserv_index = match['Indice_priorité_conservation'].iloc[0]
                    color = get_conservation_color(conserv_index)

                    st.markdown(f"""
                        <div style='background-color: {color}; padding: 6px 12px; border-radius: 8px; font-size: 20px; display: inline-block;'>
                        <b>Priorité de conservation ℹ️ :</b> {conserv_index}
                        </div>
                        """, unsafe_allow_html=True)
                    
                    reg_index = match['Indice_priorité_réglementaire'].iloc[0]
                    color_reg = get_reglementaire_color(reg_index)

                    st.markdown(f"""
                        <div style='background-color: {color_reg};  padding: 6px 12px; border-radius: 8px; font-size: 20px; display: inline-block;'>
                        <b>Priorité réglementaire ℹ️ :</b> {reg_index}
                        </div>
                        """, unsafe_allow_html=True)

                    st.markdown ("---")
                    st.markdown(f"**Code unique clause :** {match['Code_unique'].iloc[0]}")
                    st.markdown(f"**Condition d'application de la clause :** {match['Condition(s)_application_clause'].iloc[0]}")
                    
                    with st.expander("📋 Libellés des clauses à inscrire"):
                        st.write(f"**Libellé Fiche chantier (TECK) :** {match['Libellé_fiche_chantier_ONF (TECK)'].iloc[0]}")
                        st.write(f"**Libellé Fiche désignation (DESIGNATION MOBILE) :** {match['Libellé_fiche_désignation_ONF (DESIGNATION MOBILE)'].iloc[0]}")
                        st.write(f"**Libellé Fiche vente (PRODUCTION BOIS) :** {match['Libellé_fiche_vente_ONF (PRODUCTION BOIS)'].iloc[0]}")

                    st.markdown(f"**Rôle du TFT :** {match['Rôle_TFT'].iloc[0]}")


                    st.markdown ("---")
                    with st.expander("ℹ️ Légende des indices de priorité"):
                        st.markdown("""
                        **Indice de priorité de conservation** :
                        - `5` : Priorité de conservation majeure
                        - `4` : Priorité de conservation très élevée 
                        - `3` : Priorité de conservation élevée
                        - `2` : Priorité de conservation modérée
                        - `1` : Priorité de conservation faible

                        **Indice de priorité réglementaire** :
                        - `4` : Risque réglementaire majeur (Espèce réglementée au niveau européen + national ou régional) si les interventions forestières impactent les spécimens OU les éléments nécessaires au bon fonctionnement de leur cycle biologique (site de reproduction, site de repos, source de nourriture etc.).
                        - `3` : Risque réglementaire élevé (Espèce réglementée au niveau national ou régional) si les interventions forestières impactent les spécimens OU les éléments nécessaires au bon fonctionnement de leur cycle biologique (site de reproduction, site de repos, source de nourriture etc.).
                        - `2` : Risque réglementaire uniquement si les interventions forestières impactent les spécimens.
                        - `1` : La gestion forestière courante de l'ONF suffit à respecter la réglementation associée à l'espèce, que ce soit sur les spécimens ou sur les éléments nécessaires au bon fonctionnement de leur cycle biologique.
                        - `0` : Espèce non protégée.
                        """)

                    # Dictionnaire de correspondance
                    respo_dict = {
                            1: "Faible",
                            2: "Modérée",
                            3: "Significative",
                            4: "Forte",
                            5: "Majeure"
                        }

                    # Récupérer la valeur brute dans le tableau
                    valeur_respo = match['Respo_reg'].iloc[0]

                    # Traduire en texte si possible
                    texte_respo = respo_dict.get(valeur_respo, "Non renseignée")

                    with st.expander("🟢Détail des statuts"):
                        st.write(f"**Liste rouge régionale :** {traduire_statut(match['LR_reg'].iloc[0])}")
                        st.write(f"**Liste rouge nationale :** {traduire_statut(match['LR_nat'].iloc[0])}")
                        st.write(f"**Responsabilité régionale :** {texte_respo}")
                        st.write(f"**Directives européennes :** {traduire_statut(match['Directives_euro'].iloc[0])}")
                        st.write(f"**Plan d'action :** {traduire_statut(match['Plan_action'].iloc[0])}")
                        st.write(f"**Arrêté de protection :** {traduire_statut(match['Arrêté_protection'].iloc[0])}")
                        st.write(f"**Article de l'arrêté :** {traduire_statut(match['Article_arrêté'].iloc[0])}")
            else:
                st.info("❌ Il n'existe pas de prescription environnementale pour cette espèce.")