# --------------------- IMPORTS ---------------------

import streamlit as st # Framework pour créer des applications web interactives
import pandas as pd # Bibliothèque pour manipuler des données tabulaires
import geopandas as gpd
import folium #carte
from streamlit_folium import st_folium #carte
from streamlit.components.v1 import html #insertion excel online
import html as html2 
import io # export de donnees 
import os #chemin relatif des fichiers
from pathlib import Path

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
        1: '#FFFFFF',  # blanc
        2: '#FDE9EA',  # rouge très pâle
        3: '#FFB7B7',  # rose pastel
        4: '#FF797C',  # rouge moyen doux
        5: '#FF0000',  # rouge profond
    }
    return colors.get(index, '#ffffff')  # Blanc par défaut si l’indice est inconnu


# Fonction pour obtenir une couleur en fonction de l’indice de priorité réglementaire
def get_reglementaire_color(index):
    colors = {
        0: '#FFFFFF',  # blanc
        1: '#FDE9EA',  # rouge très pâle
        2: '#FFB7B7',  # rose pastel
        3: '#FF797C',  # rouge moyen doux
        4: '#FF0000',  # rouge profond
    }
    return colors.get(index, '#ffffff') # Blanc par défaut si l’indice est inconnu


# Fonction de reset global
def reset_all():
    st.session_state.selected_foret = None
    st.session_state.selected_parcelle = None
    st.session_state.view = "start"
    st.session_state.reset_requested = True

# Dictionnaire des couleurs de point de la carte par niveau de priorité conservation
couleurs = {
    1: "#00B050",   # vert foncé
    2: "#92D050",   # vert clair
    3: "#FFFF00",   # jaune
    4: "#FF9900",   # orange
    5: "#FF0000",   # rouge
    "default": "#D3D3D3"  # gris clair
}

# Détermination de la couleur du point de la carte d'après les indices
def get_couleur_personnalisee(row):
    c = row["Indice_priorité_conservation"]
    r = row["Indice_priorité_réglementaire"]

    try:
        if c == 5 or r == 4:
            return couleurs[5]
        elif c == 4 or r == 3:
            return couleurs[4]
        elif c == 3 or r == 2:
            return couleurs[3]
        elif c == 2 or r == 1:
            return couleurs[2]
        elif c == 1 or r == 0:
            return couleurs[1]
        else:
            return couleurs["default"]
    except:
        return couleurs["default"]

#Pour enlever sécuriser l'affichage des popus qui sinon peuvent faire bugger la carte
def safe_get(val):
    if pd.isna(val) or val in ["nan", "NaN", None]:
        return ""
    # Convertit en texte, échappe les caractères spéciaux HTML
    val_str = str(val)
    val_str = html2.escape(val_str)  # échappe &, <, >, ", '
    val_str = val_str.replace("\n", "<br>")  # gestion des retours à la ligne
    return val_str

# Fonction d'affichage des cartes
def afficher_carte(df, df_reference, titre="📍 Localisation des espèces "):
    if df.empty:
        st.warning("Aucune donnée à afficher pour cette sélection.")
        return

    # Fusion avec la table de référence via CD_NOM
    df = df.rename(columns={"Code taxon (cd_nom)": "CD_NOM"})
    df_popup = df.merge(
        df_reference[["CD_NOM", "Indice_priorité_conservation", "Indice_priorité_réglementaire"]],
        on="CD_NOM", how="left"
    )

    # Colonnes à afficher
    colonnes_a_afficher = ['Forêt', 'CD_NOM', 'Date début', 'Espèce', 'Commentaire du relevé', 'Commentaire de la localisation', "Commentaire de l'observation", 'Parcelle de forêt', 'Surface de la géométrie', 'Coordonnée 1', 'Coordonnée 2', 'Système de coordonnées', 'Observateur(s)', "Fiabilité de l'observation", "Statut juridique"]
    
    df_fusion = df[colonnes_a_afficher].merge(
        df_reference[["CD_NOM"]],
        on="CD_NOM", how="left"
    )

    # Fusion complète pour export
    colonnes_reference = [
        "Cat_naturaliste", "Nom_scientifique_valide", "LR_nat", "LR_reg",
        "Indice_priorité_conservation",
        "Directives_euro", "Plan_action", "Arrêté_protection_nationale", "Arrêté_protection_BN",
        "Arrêté_protection_HN", "Article_arrêté", "Type_protection", "Conseils_gestion"
    ]

    df_export = df_fusion.merge(
        df_reference[["CD_NOM"] + colonnes_reference],
        on="CD_NOM", how="left"
    )

    # Astuce CSS pour limiter la hauteur au chargement
    st.markdown("""
        <style>
            .folium-map {
                max-height: 650px;
                overflow: hidden;
            }
        </style>
    """, unsafe_allow_html=True)

    # Calcul du centre de la carte
    lat_centre = df["Coordonnée 2"].mean()
    lon_centre = df["Coordonnée 1"].mean()

    # Création de la carte Folium
    m = folium.Map(location=[lat_centre, lon_centre], zoom_start=13, control_scale=True)

    # Ajout du fond de carte cadastre (WMS IGN)
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

    # Ajout des points naturalistes
    for _, row in df_popup.iterrows():
        if pd.notna(row["Coordonnée 1"]) and pd.notna(row["Coordonnée 2"]):
            couleur = get_couleur_personnalisee(row)

            popup = f"""<b>Parcelle :</b> {safe_get(row.get('Parcelle de forêt'))}<br>
            <b>Espèce :</b> {safe_get(row.get('Espèce'))}<br>
            <b>Commentaire de la localisation :</b> {safe_get(row.get('Commentaire de la localisation'))}<br>
            <b>Commentaire de l'observation :</b> {safe_get(row.get("Commentaire de l'observation"))}<br>
            <b>Commentaire du relevé :</b> {safe_get(row.get("Commentaire du relevé"))}<br>
            <b>Date d'observation :</b> {safe_get(row.get("Date de début"))}<br>
            <b>Surface de la géométrie : </b> {row["Surface de la géométrie"]}<br>
            <b>Système de coordonnées :</b> {safe_get(row.get("Système de coordonnées"))}<br>
            """

            folium.CircleMarker(
                location=[row["Coordonnée 2"], row["Coordonnée 1"]],
                radius=6,
                color="black",
                weight=1,
                fill=True,
                fill_color=couleur,
                fill_opacity=1,
                popup=folium.Popup(popup, max_width=500)
            ).add_to(m)

    # Contrôle de couches
    folium.LayerControl().add_to(m)

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df_notice.to_excel(writer, sheet_name="Notice", index=False)
        df_export.to_excel(writer, sheet_name="Export aménagement", index=False)

    # Affichage dans Streamlit
    with st.container():
        st.markdown(f"### {titre}")
        col1, col2 = st.columns([5.5, 1.5])  # Large légende à gauche, petit bouton à droite

        with col1:
            st.markdown("""
            <div style="
                background-color: white;
                border: 1px solid black;
                border-radius: 10px;
                padding: 12px 24px;
                box-shadow: 3px 3px 6px rgba(0, 0, 0, 0.1);
                display: flex;
                flex-wrap: nowrap;
                align-items: center;
                gap: 24px;
                font-size: 14px;
                overflow-x: auto;
            ">
                <div style="display: flex; align-items: center;">
                    <span style="width:14px; height:14px; background-color:#FF0000; border-radius:50%; margin-right:6px; display:inline-block;"></span>
                    Enjeu potentiellement majeur
                </div>
                <div style="display: flex; align-items: center;">
                    <span style="width:14px; height:14px; background-color:#FF9900; border-radius:50%; margin-right:6px; display:inline-block;"></span>
                    Enjeu potentiellement fort
                </div>
                <div style="display: flex; align-items: center;">
                    <span style="width:14px; height:14px; background-color:#FFFF00; border-radius:50%; margin-right:6px; display:inline-block;"></span>
                    Enjeu potentiellement élevé
                </div>
                <div style="display: flex; align-items: center;">
                    <span style="width:14px; height:14px; background-color:#92D050; border-radius:50%; margin-right:6px; display:inline-block;"></span>
                    Enjeu modéré
                </div>
                <div style="display: flex; align-items: center;">
                    <span style="width:14px; height:14px; background-color:#00B050; border-radius:50%; margin-right:6px; display:inline-block;"></span>
                    Enjeu faible
                </div>
                <div style="display: flex; align-items: center;">
                    <span style="width:14px; height:14px; background-color:#D3D3D3; border-radius:50%; margin-right:6px; display:inline-block;"></span>
                    Enjeu inconnu
                </div>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            st.download_button(
                label="📥 Export aménagement",
                data=buffer.getvalue(),
                file_name="export_amenagement.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="download_xlsx_amenagement"
            )

        st_folium(m, height=600, returned_objects=[], use_container_width=True)


# Fonction d'affichage des statuts et prescriptions
def afficher_statuts_prescriptions(df_filtré, df_reference):
    if df_filtré.empty:
        st.warning("Aucune espèce à afficher pour cette sélection.")
        return

    # Colonnes à afficher
    colonnes_a_afficher = ['Forêt', 'Code taxon (cd_nom)', 'Date début', 'Espèce', 'Commentaire du relevé', 'Commentaire de la localisation', "Commentaire de l'observation", 'Parcelle de forêt', 'Surface de la géométrie', 'Coordonnée 1', 'Coordonnée 2', 'Système de coordonnées', 'Observateur(s)', "Fiabilité de l'observation", "Statut juridique"]

    st.dataframe(df_filtré[colonnes_a_afficher])

    # Création d’un mapping lisible : {cd_nom: "Espèce"}
    df_temp = df_filtré[['Code taxon (cd_nom)', 'Espèce']].dropna()
    df_temp['Espèce'] = df_temp['Espèce'].astype(str).str.strip()
    df_temp['Code taxon (cd_nom)'] = df_temp['Code taxon (cd_nom)'].astype(str).str.strip()

    species_dict = dict(zip(df_temp['Code taxon (cd_nom)'], df_temp['Espèce']))
    reverse_dict = {v: k for k, v in species_dict.items()}

    # Affichage des espèces comme options dans la selectbox
    selected_label = st.selectbox("🔎 Choisissez une espèce :", sorted(species_dict.values()))

    # On récupère le cd_nom correspondant au nom d’espèce sélectionné
    selected_species = reverse_dict.get(selected_label)

    # Injecter du CSS personnalisé pour modifier l'apparence des expanders
    st.markdown("""
        <style>
        /* Style de l'expander ONF compact */
        details {
            background-color: #DDEEDD;
            border: none;
        }
        </style>
    """, unsafe_allow_html=True)


    if selected_species:
        selected_species = str(selected_species).strip()
        df_reference['CD_NOM'] = df_reference['CD_NOM'].astype(str).str.strip()
        species_reference_info = df_reference[df_reference['CD_NOM'] == selected_species]
        st.markdown("")
        st.subheader(f"📘 Statuts et prescriptions : {selected_label}")

        if not species_reference_info.empty and pd.notna(species_reference_info['Rôle_TFT'].iloc[0]) and str(species_reference_info['Rôle_TFT'].iloc[0]).strip():
            nom_sci = species_reference_info['Nom_scientifique_valide'].iloc[0]

            st.markdown(f"**Nom scientifique :** {nom_sci}")
            st.markdown(f"**Nom vernaculaire :** {species_reference_info['Nom_vernaculaire'].iloc[0]}")
            st.markdown(f"**Catégorie naturaliste :** {species_reference_info['Cat_naturaliste'].iloc[0]}")

            conserv_index = species_reference_info['Indice_priorité_conservation'].iloc[0]
            color = get_conservation_color(conserv_index)
            st.markdown(f"""<div style='background-color: {color}; padding: 6px 12px; border-radius: 8px; font-size: 20px; display: inline-block;'><b>Priorité de conservation* :</b> {conserv_index}</div>""", unsafe_allow_html=True)

            reg_index = species_reference_info['Indice_priorité_réglementaire'].iloc[0]
            color_reg = get_reglementaire_color(reg_index)
            st.markdown(f"""<div style='background-color: {color_reg}; padding: 6px 12px; border-radius: 8px; font-size: 20px; display: inline-block;'><b>Priorité réglementaire* :</b> {reg_index}</div>""", unsafe_allow_html=True)

            st.markdown ("---")
            st.markdown(f"**Code unique clause :** {species_reference_info['Code_unique'].iloc[0]}")
            st.markdown(f"**Condition d'application de la clause :** {species_reference_info['Condition(s)_application_clause'].iloc[0]}")

            st.markdown(f"**Rôle du TFT :** {species_reference_info['Rôle_TFT'].iloc[0]}")

            with st.expander("📋 Libellé des clauses à inscrire"):
                st.write(f"**Fiche chantier (TECK) :** {species_reference_info['Libellé_fiche_chantier_ONF (TECK)'].iloc[0]}")
                st.write(f"**Fiche désignation (DESIGNATION MOBILE) :** {species_reference_info['Libellé_fiche_désignation_ONF (DESIGNATION MOBILE)'].iloc[0]}")
                st.write(f"**Fiche vente (PRODUCTION BOIS) :** {species_reference_info['Libellé_fiche_vente_ONF (PRODUCTION BOIS)'].iloc[0]}")


            st.markdown ("---")
            with st.expander("*Légende des indices de priorité"):
                st.markdown("""
                **Indice de priorité de conservation** :
                - `5` : Priorité de conservation cruciale
                - `4` : Priorité de conservation majeure 
                - `3` : Priorité de conservation forte
                - `2` : Priorité de conservation significative
                - `1` : Priorité de conservation modérée

                **Indice de priorité réglementaire** :
                - `4` : Risque réglementaire majeur (Espèce réglementée au niveau européen + national ou régional) si les interventions forestières impactent les spécimens OU les éléments nécessaires au bon fonctionnement de leur cycle biologique (site de reproduction, site de repos, source de nourriture etc.).
                - `3` : Risque réglementaire élevé (Espèce réglementée au niveau national ou régional) si les interventions forestières impactent les spécimens OU les éléments nécessaires au bon fonctionnement de leur cycle biologique (site de reproduction, site de repos, source de nourriture etc.).
                - `2` : Risque réglementaire uniquement si les interventions forestières impactent les spécimens.
                - `1` : La gestion forestière courante de l'ONF suffit à conserver le bon état des populations de l'espèce à l'échelle du massif.
                - `0` : Espèce non protégée.
                """)

            respo_dict = {1: "Faible", 2: "Modérée", 3: "Significative", 4: "Forte", 5: "Majeure"}
            valeur_respo = species_reference_info['Respo_reg'].iloc[0]
            texte_respo = respo_dict.get(valeur_respo, "Non Renseigné")

            with st.expander("📘 Détail des statuts"):
                st.write(f"**Liste rouge régionale :** {traduire_statut(species_reference_info['LR_reg'].iloc[0])}")
                st.write(f"**Liste rouge nationale :** {traduire_statut(species_reference_info['LR_nat'].iloc[0])}")
                st.write(f"**Responsabilité régionale :** {texte_respo}")
                st.write(f"**Directives européennes :** {traduire_statut(species_reference_info['Directives_euro'].iloc[0])}")
                st.write(f"**Plan d'action :** {traduire_statut(species_reference_info['Plan_action'].iloc[0])}")
                # Récupération des 3 colonnes concernées
                apn = species_reference_info['Arrêté_protection_nationale'].iloc[0]
                ap_bn = species_reference_info['Arrêté_protection_BN'].iloc[0]
                ap_hn = species_reference_info['Arrêté_protection_HN'].iloc[0]

                # On filtre uniquement les valeurs différentes de "N.C."
                valeurs_protection = [apn, ap_bn, ap_hn]
                valeurs_non_nc = [v for v in valeurs_protection if str(v).strip() != "N.C."]

                # Affichage
                if valeurs_non_nc:
                    st.write(f"**Arrêté de protection :** {', '.join(valeurs_non_nc)}")
                else:
                    st.write("**Arrêté de protection :** Non Concerné")
                st.write(f"**Article de l'arrêté :** {traduire_statut(species_reference_info['Article_arrêté'].iloc[0])}")
            
            with st.expander("➕ Pour aller plus loin"):
                contenu = species_reference_info['Conseils_gestion'].iloc[0]
                if pd.notna(contenu) and contenu != "":
                    st.markdown(f"{contenu}")
                else:
                    st.markdown("")

        else:
            st.info("❌ Cette espèce ne fait pas l'objet de prescription environnementale.")


# --------------------- CONFIGURATION ---------------------

# Définition de la configuration de la page Streamlit
st.set_page_config(page_title="Espèces remarquables et prescriptions", page_icon="🦋", layout="wide")


# --------------------- AUTHENTIFICATION --------------

# Définir un mot de passe correct
PASSWORD = "caprimulgus"

# Initialiser une session pour suivre l'état de l'utilisateur
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# --------------------- BANDEAU FIXE ---------------------

# Ajouter du CSS pour un bandeau fixe en haut de l'écran
st.markdown("""
    <style>
        .header-banner {
            background-color: rgba(220, 220, 220, 0.9); /* Gris clair avec transparence */
            color: black;  /* Texte noir */
            padding: 6px 10px;
            text-align: center;
            font-size: 18px;
            font-weight: 500;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            z-index: 999999;
    </style>
""", unsafe_allow_html=True)

# HTML pour le bandeau
st.markdown("""
    <div class="header-banner">
        <i>OUTIL EN COURS DE DEVELOPPEMENT --  --  --  SEAP ONF NORMANDIE</i>
    </div>
""", unsafe_allow_html=True)


# ------------------------INTERFACE--------------------------


# Si l'utilisateur n'est pas encore connecté
if not st.session_state.authenticated:
    import base64

    # Charger l'image locale et l'encoder en base64
    
    file_path = Path(__file__).parent / "logo ONF.png"

    with open(file_path, "rb") as f:
        data = f.read()
        encoded = base64.b64encode(data).decode()

    # Afficher l'image centrée via HTML
    st.markdown(
        f"""
        <div style="text-align: center;">
            <img src="data:image/png;base64,{encoded}" width="250">
            <br><br>
        </div>
        """,
        unsafe_allow_html=True
    )


    with st.form("login_form"):
        st.write("### 🦋 Espèces remarquables et prescriptions")
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
    file_path = Path(__file__).parent / "logo ONF.png"
    st.sidebar.image(file_path, width=250)
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
    page = st.sidebar.radio("Aller à :",["Accueil", "Recherche par forêt", "Recherche par espèce", "Référentiel"], label_visibility="collapsed")


    # --------------------- CHARGEMENT DES DONNÉES ---------------------

    # Chargement du fichier principal contenant les observations de la Base de données naturalistes de l'ONF
    @st.cache_data
    def load_data():
        file_path = Path(__file__).parent / "MonExportBdn.xlsx"
        return pd.read_excel(file_path)

    # Chargement de la liste des codes CD_NOM autorisés (filtrage pour avoir uniquement les espèces du tableau de métadonnées des espèces remarquables)
    @st.cache_data
    def load_codes_autorises():
        file_path = Path(__file__).parent / "Metadonnees.xlsx"
        df_codes = pd.read_excel(file_path)
        return df_codes['CD_NOM'].astype(str).str.strip().tolist()

    # Chargement du fichier de référence des espèces avec leurs métadonnées
    @st.cache_data
    def load_reference_especes():
        file_path = Path(__file__).parent / "Metadonnees.xlsx"
        df_reference = pd.read_excel(file_path)
        return df_reference

    # Chargement de la notice de l'export aménagement
    @st.cache_data
    def load_notice():
        file_path = Path(__file__).parent / "Notice_export.xlsx"
        return pd.read_excel(file_path)

    # Exécution des fonctions de chargement
    df = load_data()
    codes_autorises = load_codes_autorises()
    df_reference = load_reference_especes()
    df_notice = load_notice()

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
            <br><br>        
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
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div style="
            background-color: rgba(255, 0, 0, 0.1);
            padding: 1.5rem;
            border-radius: 10px;
            border: 1px solid rgba(255, 0, 0, 0.3);
            font-size: 22px;
            line-height: 1.6;
            ">
            <i>L'indice de <b>priorité de conservation</b> intègre la menace d'extinction au niveau régional et national, ainsi que la responsabilité de la Normandie dans la conservation de l'espèce. La méthode utilisée pour calculer cet indice se base sur les travaux de Barneix et Gigot (2013) et sur les initiatives de hiérarchisation qui ont découlé de ces travaux à l'échelle des régions françaises.</i>
            <br><br>
            <i>L'indice de <b>priorité réglementaire</b> intègre les différents types de réglementation (Directives européennes, protection par arreté) et les subtilités d'interprétation des articles d'arrêtés. En effet, certains articles protègent uniquement les spécimens et d'autres articles protègent, en plus des spécimens, les éléments nécessaires au bon fonctionnement du cycle biologique de l'espèce, incluant notamment les sites de reproduction et de repos. Enfin, cet indice prend en compte le risque que l'ONF entrave ces réglementations. En effet, pour certaines espèces très communes comme la mésange bleue, le risque réglementaire est très faible étant donné que la conservation de l'espèce à l'échelle du massif est assurée par la gestion classique de l'ONF.</i>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div style='font-size:22px'>
            <br>
            Ces deux indices permettront de hiérarchiser les enjeux et de prioriser les clauses environnementales.
            <br><br>
            ⬅️ Utilisez le menu à gauche pour consulter les espèces remarquables présentes en forêt et accéder aux statuts et prescriptions.
        </div>
        """, unsafe_allow_html=True)
        
    # --------------------- PAGE FORÊT ---------------------


    if page == "Recherche par forêt":
        st.markdown("### 🔎 Recherche par forêt")
        if 'selected_foret' not in st.session_state:
            st.session_state.selected_foret = None
        if 'selected_parcelle' not in st.session_state:
            st.session_state.selected_parcelle = None
        if "view" not in st.session_state:
            st.session_state.view = 'start'
        if st.session_state.get("first_load", True):
            st.session_state.first_load = False
            st.rerun()

        # Sélection de la forêt
        if st.session_state.selected_foret is None:
            selected_foret = st.selectbox("Sélectionnez une forêt🌲:", [""] + sorted(forets))
            if selected_foret:
                st.session_state.selected_foret = selected_foret
                st.session_state.view = "forest_view"
                st.rerun()

        # Vue forêt sélectionnée
        elif st.session_state.view == "forest_view":
            foret = st.session_state.selected_foret
            df_foret = df[df['Forêt'] == foret]
            
            with st.container ():
                if st.button("📌 Filtrer par parcelle"):
                    st.session_state.view = "parcelle_view"
                    st.rerun()
                if st.button("📘 Voir les statuts et prescriptions des espèces remarquables de la forêt"):
                    st.session_state.view = "species_forest"
                    st.rerun()
                st.button("⬅️ Retour à la liste des forêts", on_click=lambda: st.session_state.update({"view": "start","selected_foret": None}))

            afficher_carte(df_foret, df_reference, titre=f"📍 Carte des espèces remarquables de la forêt {foret}")

        # Vue filtre par parcelle
        elif st.session_state.view == "parcelle_view":
            foret = st.session_state.selected_foret
            df_foret = df[df['Forêt'] == foret]
            parcelles_dispo = sorted(df_foret["Parcelle de forêt"].unique())

            # Définir la parcelle par défaut (si connue) OU forcer à "" sinon
            if st.session_state.selected_parcelle in parcelles_dispo:
                default_index = parcelles_dispo.index(st.session_state.selected_parcelle)
                selected_parcelle = st.selectbox("📌 Choisissez une parcelle :", parcelles_dispo, index=default_index)
            else:
                selected_parcelle = st.selectbox("📌 Choisissez une parcelle :", [""] + parcelles_dispo)
                
            if selected_parcelle:
                st.session_state.selected_parcelle = selected_parcelle
                df_parcelle = df_foret[df_foret["Parcelle de forêt"] == selected_parcelle]

                if st.button("📘 Voir les statuts et prescriptions des espèces remarquables de la parcelle"):
                    st.session_state.view = "species_parcelle"
                    st.rerun()

                if st.button("⬅️ Retour à la carte de la forêt"):
                    st.session_state.update({"view": "forest_view", "selected_parcelle": None})

                afficher_carte(df_parcelle, df_reference, titre=f"📍 Espèces remarquables dans la parcelle {selected_parcelle}")
            
        # Statuts et prescriptions forêt
        elif st.session_state.view == "species_forest":
            st.button("⬅️ Retour à la carte de la forêt", on_click=lambda: st.session_state.update({"view": "forest_view"}))

            st.markdown (f" ### Détails des espèces remarquables pour la forêt : {st.session_state.selected_foret}")
            df_filtré = df[df['Forêt'] == st.session_state.selected_foret]
            afficher_statuts_prescriptions(df_filtré, df_reference)

        # Statuts et prescriptions parcelle
        elif st.session_state.view == "species_parcelle":
            st.button("⬅️ Retour à la carte de la parcelle", on_click=lambda: st.session_state.update({"view": "parcelle_view", "selected_parcelle":st.session_state.selected_parcelle}))
            
            st.button("⬅️ Retour à la carte de la forêt", on_click=lambda: st.session_state.update({"view": "forest_view"}))
            
            st.markdown (f" ### Détails des espèces remarquables pour la parcelle : {st.session_state.selected_parcelle}")
            df_filtré = df[
                (df['Forêt'] == st.session_state.selected_foret) &
                (df['Parcelle de forêt'] == st.session_state.selected_parcelle)
            ]
            afficher_statuts_prescriptions(df_filtré, df_reference)

    if st.session_state.get("reset_requested"):
        st.session_state.reset_requested = False
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

        file_path = Path(__file__).parent / "inpn_ex.png"

        st.image(file_path, use_container_width=True)

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

            # Injecter du CSS personnalisé pour modifier l'apparence des expanders
            st.markdown("""
                <style>
                /* Style de l'expander ONF compact */
                details {
                    background-color: #DDEEDD;
                    border: none;
                }
                </style>
            """, unsafe_allow_html=True)

            st.subheader(f"📘 Statuts et prescriptions : {search_cd_nom}")

            if not match.empty and str(match['Rôle_TFT'].iloc[0]).strip().upper() != "N.C.":
                with st.container():
                    st.markdown(f"**Nom scientifique :** {match['Nom_scientifique_valide'].iloc[0]}")
                    st.markdown(f"**Nom vernaculaire :** {match['Nom_vernaculaire'].iloc[0]}")
                    st.markdown(f"**Catégorie naturaliste :** {match['Cat_naturaliste'].iloc[0]}")
                    
                    conserv_index = match['Indice_priorité_conservation'].iloc[0]
                    color = get_conservation_color(conserv_index)

                    st.markdown(f"""
                        <div style='background-color: {color}; padding: 6px 12px; border-radius: 8px; font-size: 20px; display: inline-block;'>
                        <b>Priorité de conservatio*:</b> {conserv_index}
                        </div>
                        """, unsafe_allow_html=True)
                    
                    reg_index = match['Indice_priorité_réglementaire'].iloc[0]
                    color_reg = get_reglementaire_color(reg_index)

                    st.markdown(f"""
                        <div style='background-color: {color_reg};  padding: 6px 12px; border-radius: 8px; font-size: 20px; display: inline-block;'>
                        <b>Priorité réglementair*:</b> {reg_index}
                        </div>
                        """, unsafe_allow_html=True)

                    st.markdown ("---")
                    st.markdown(f"**Code unique clause :** {match['Code_unique'].iloc[0]}")
                    st.markdown(f"**Condition d'application de la clause :** {match['Condition(s)_application_clause'].iloc[0]}")

                    st.markdown(f"**Rôle du TFT :** {match['Rôle_TFT'].iloc[0]}")
                    
                    with st.expander("📋 Libellé des clauses à inscrire"):
                        st.write(f"**Libellé Fiche chantier (TECK) :** {match['Libellé_fiche_chantier_ONF (TECK)'].iloc[0]}")
                        st.write(f"**Libellé Fiche désignation (DESIGNATION MOBILE) :** {match['Libellé_fiche_désignation_ONF (DESIGNATION MOBILE)'].iloc[0]}")
                        st.write(f"**Libellé Fiche vente (PRODUCTION BOIS) :** {match['Libellé_fiche_vente_ONF (PRODUCTION BOIS)'].iloc[0]}")


                    st.markdown ("---")
                    with st.expander("*Légende des indices de priorité"):
                        st.markdown("""
                        **Indice de priorité de conservation** :
                        - `5` : Priorité de conservation cruciale
                        - `4` : Priorité de conservation majeure
                        - `3` : Priorité de conservation forte
                        - `2` : Priorité de conservation significative
                        - `1` : Priorité de conservation modérée

                        **Indice de priorité réglementaire** :
                        - `4` : Risque réglementaire majeur (Espèce réglementée au niveau européen + national ou régional) si les interventions forestières impactent les spécimens OU les éléments nécessaires au bon fonctionnement de leur cycle biologique (site de reproduction, site de repos, source de nourriture etc.).
                        - `3` : Risque réglementaire élevé (Espèce réglementée au niveau national ou régional) si les interventions forestières impactent les spécimens OU les éléments nécessaires au bon fonctionnement de leur cycle biologique (site de reproduction, site de repos, source de nourriture etc.).
                        - `2` : Risque réglementaire uniquement si les interventions forestières impactent les spécimens.
                        - `1` : La gestion forestière courante de l'ONF suffit à conserver le bon état des populations de l'espèce à l'échelle du massif.
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
                    texte_respo = respo_dict.get(valeur_respo, "Non Renseigné")

                    with st.expander("📘 Détail des statuts"):
                        st.write(f"**Liste rouge régionale :** {traduire_statut(match['LR_reg'].iloc[0])}")
                        st.write(f"**Liste rouge nationale :** {traduire_statut(match['LR_nat'].iloc[0])}")
                        st.write(f"**Responsabilité régionale :** {texte_respo}")
                        st.write(f"**Directives européennes :** {traduire_statut(match['Directives_euro'].iloc[0])}")
                        st.write(f"**Plan d'action :** {traduire_statut(match['Plan_action'].iloc[0])}")
                        
                        # Récupération des 3 colonnes concernées
                        apn = match['Arrêté_protection_nationale'].iloc[0]
                        ap_bn = match['Arrêté_protection_BN'].iloc[0]
                        ap_hn = match['Arrêté_protection_HN'].iloc[0]

                        # On filtre uniquement les valeurs différentes de "N.C."
                        valeurs_protection = [apn, ap_bn, ap_hn]
                        valeurs_non_nc = [v for v in valeurs_protection if str(v).strip() != "N.C."]

                        # Affichage
                        if valeurs_non_nc:
                            st.write(f"**Arrêté de protection :** {', '.join(valeurs_non_nc)}")
                        else:
                            st.write("**Arrêté de protection :** Non Concerné")
                        st.write(f"**Article de l'arrêté :** {traduire_statut(match['Article_arrêté'].iloc[0])}")
                    
                    with st.expander("➕ Pour aller plus loin"):
                        contenu = match['Conseils_gestion'].iloc[0]
                        if pd.notna(contenu) and contenu != "":
                            st.markdown(f"{contenu}")
                        else:
                            st.markdown("")

            else:
                st.info("❌ Il n'existe pas de prescription environnementale pour cette espèce.")
        
    
    # --------------------- PAGE REFERENTIEL ---------------------

    elif page == "Référentiel" :
        st.markdown("### Tableau référentiel des statuts des espèces remarquables pour l'ONF Normandie")
        st.markdown(
        '[➡️ Voir le tableau Excel en ligne](https://officenationaldesforets-my.sharepoint.com/personal/matteo_kressmann_onf_fr/_layouts/15/Doc.aspx?sourcedoc={719dad7b-de23-4680-8262-4083c17d5603}&action=embedview)'
        )
        iframe_code = """<iframe width="2000" height="1000" frameborder="0" scrolling="no" src="https://officenationaldesforets-my.sharepoint.com/personal/matteo_kressmann_onf_fr/_layouts/15/Doc.aspx?sourcedoc={719dad7b-de23-4680-8262-4083c17d5603}&action=embedview&wdAllowInteractivity=False&wdHideGridlines=True&wdHideHeaders=True&wdDownloadButton=True&wdInConfigurator=True&wdInConfigurator=True"></iframe>"""
        html(iframe_code, height=600)
