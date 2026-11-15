import streamlit as st
from math import log, log10
from chemicals.identifiers import search_chemical
from chemicals import Tb, Tc, Pc
from thermo.group_contribution.joback import Joback

# Configuration de la page
st.set_page_config(page_title="ChemAura - Simulateur Thermodynamique", page_icon="🧪", layout="centered")

# --- PERSONNALISATION DES COULEURS (Rose & Violet) ---
st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(135deg, #F8F5FF 0%, #FDF2F8 100%);
    }
    h1, h2, h3 {
        color: #4C1D95 !important;
        font-family: 'Outfit', sans-serif;
    }
    .stButton>button {
        background: linear-gradient(135deg, #7C3AED 0%, #EC4899 100%);
        color: white;
        border: none;
        border-radius: 12px;
        font-weight: bold;
        padding: 10px 20px;
        width: 100%;
        box-shadow: 0 4px 15px rgba(124, 58, 237, 0.3);
    }
    .stButton>button:hover {
        opacity: 0.9;
    }
    </style>
""", unsafe_allow_html=True)

# --- AUTHENTIFICATION ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown("<h2 style='text-align: center;'>🔐 ChemAura - Espace Sécurisé</h2>", unsafe_allow_html=True)
    with st.form("login_form"):
        username = st.text_input("Identifiant")
        password = st.text_input("Mot de passe", type="password")
        submit_login = st.form_submit_button("Se connecter")
        
        if submit_login:
            # Identifiants de ton amie
            if username == "hajar" and password == "chimie2026":
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Identifiant ou mot de passe incorrect.")
    st.stop()

# Barre latérale
with st.sidebar:
    st.write("Connectée : **Hajar**")
    if st.button("Se déconnecter"):
        st.session_state.logged_in = False
        st.rerun()
    st.markdown("---")
    st.markdown("### 🧪 ChemAura")
    st.markdown("Génie des Procédés - Thermodynamique")

# --- MOTEUR DE CALCUL ---
R = 8.314
P_ATM = 101325.0

def identifier(nom):
    try:
        return search_chemical(nom)
    except Exception:
        return None

def tb_normale(mol):
    try:
        valeur = Tb(mol.CAS)
        if valeur is not None:
            return valeur, "Valeur mesurée (base de données)", None
    except Exception:
        pass
    try:
        est = Joback(mol.smiles).estimate()
        return est["Tb"], "Estimation Joback", est
    except Exception:
        return None, "Impossible de calculer", None

def tb_antoine(mol, P):
    try:
        from chemicals.vapor_pressure import Psat_data_AntoinePoling as D
        ligne = D.loc[mol.CAS]
        A, B, C = float(ligne["A"]), float(ligne["B"]), float(ligne["C"])
        T = B / (A - log10(P)) - C
        return T, "Équation d'Antoine"
    except Exception:
        return None, None

def tb_clausius(mol, tb1, est, P):
    try:
        tc = Tc(mol.CAS) or (est or {}).get("Tc")
        pc = Pc(mol.CAS) or (est or {}).get("Pc")
        if tc is None or pc is None:
            est = Joback(mol.smiles).estimate()
            tc, pc = est["Tc"], est["Pc"]
        from chemicals.phase_change import Riedel
        hvap = Riedel(tb1, tc, pc)
        T2 = 1.0 / (1.0 / tb1 - R * log(P / P_ATM) / hvap)
        return T2, "Clausius-Clapeyron & Riedel"
    except Exception:
        return None, None

def calcul(nom, P=P_ATM):
    mol = identifier(nom)
    if mol is None:
        return None, "Molécule introuvable (essayez le nom en anglais)."

    tb1, source1, est = tb_normale(mol)
    resultat = {"nom": getattr(mol, 'common_name', nom), "formule": getattr(mol, 'formula', ''),
                "CAS": getattr(mol, 'CAS', ''), "tb_1atm": tb1, "source_1atm": source1}

    if abs(P - P_ATM) < 1:
        resultat["tb"], resultat["methode"] = tb1, source1
        return resultat, None

    T, methode = tb_antoine(mol, P)
    if T is None and tb1 is not None:
        T, methode = tb_clausius(mol, tb1, est, P)
    resultat["tb"], resultat["methode"] = T, methode
    return resultat, None

UNITES = {"pa": 1.0, "kpa": 1e3, "bar": 1e5, "atm": P_ATM, "mmhg": 133.322}

# --- INTERFACE UTILISATEUR ---
st.title("🧪 ChemAura - Simulateur")
st.write("Estimez les températures d'ébullition et visualisez la structure des molécules.")

with st.form("simulation_form"):
    molecule_input = st.text_input("Nom de la molécule (en anglais, ex: ethanol, acetone)", value="ethanol")
    col1, col2 = st.columns(2)
    with col1:
        pression_val = st.number_input("Valeur de la pression", value=1.0, step=0.01)
    with col2:
        unite = st.selectbox("Unité de pression", ["atm", "bar", "kPa", "Pa", "mmHg"])
    
    submit_calc = st.form_submit_button("Lancer le calcul thermodynamique")

if submit_calc:
    P = pression_val * UNITES.get(unite.lower(), P_ATM)
    res, err = calcul(molecule_input.strip(), P)
    
    if err:
        st.error(err)
    else:
        tb_final = res.get('tb') if abs(P - P_ATM) >= 1 else res.get('tb_1atm')
        tb_c = tb_final - 273.15 if tb_final else None
        methode_utilisee = res.get('methode') or res.get('source_1atm')
        
        st.success("Calcul effectué avec succès !")
        
        st.subheader(f"✨ Résultats pour : {str(res['nom']).capitalize()}")
        
        col_r1, col_r2, col_r3 = st.columns(3)
        with col_r1:
            st.metric("Formule", res['formule'])
        with col_r2:
            st.metric("CAS", res['CAS'])
        with col_r3:
            st.metric("Pression", f"{pression_val} {unite}")
            
        if tb_c is not None:
            st.metric("Température d'ébullition", f"{tb_c:.2f} °C", f"{tb_c + 273.15:.2f} K")
        else:
            st.warning("Température d'ébullition non disponible.")
            
        st.info(f"**Modèle appliqué :** {methode_utilisee}")
        
        # Affichage de la structure moléculaire
        st.subheader("Structure Chimique (PubChem)")
        image_url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{molecule_input.strip()}/PNG?image_size=large"
        st.image(image_url, caption=f"Structure moléculaire de {molecule_input}", use_container_width=True)