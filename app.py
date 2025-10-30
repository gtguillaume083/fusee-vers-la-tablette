# app.py
import streamlit as st
import json, os
from datetime import datetime

# --- CONFIG ---
# Par sécurité, on lit le token admin depuis la variable d'environnement ADMIN_TOKEN si elle existe.
# Sinon, on utilise la valeur par défaut ci-dessous (change-la avant de déployer).
DEFAULT_ADMIN_TOKEN = "mathisfusee"
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", DEFAULT_ADMIN_TOKEN)

DATA_FILE = "progress.json"

# --- Chargement / sauvegarde ---
def load_data():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return {"progress": 0, "history": []}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

data = load_data()

# --- Page config ---
st.set_page_config(page_title="Fusée vers la tablette", layout="centered")

# --- Header visuel ---
st.markdown("<h1 style='text-align:center;'>🚀 Fusée vers la tablette !</h1>", unsafe_allow_html=True)

# --- Visual : zone "ciel" et fusée positionnée selon data['progress'] ---
# On utilise HTML/CSS simple pour déplacer l'emoji fusée selon la progression (bottom %).
progress = int(data.get("progress", 0))
html = f"""
<div style="width:280px; height:420px; border-radius:12px; background:linear-gradient(#00111a, #00334d); margin:0 auto; position:relative; padding:10px;">
  <div style="position:absolute; left:50%; transform:translateX(-50%); bottom:{progress}%; transition:bottom 0.6s;">
    <div style="font-size:48px; filter: drop-shadow(0 2px 6px rgba(0,0,0,0.6));">🚀</div>
  </div>
  <div style="position:absolute; left:50%; transform:translateX(-50%); bottom:100%; margin-bottom:6px; color:#fff; font-weight:700;">
    🎯 Tablette
  </div>
</div>
"""
st.markdown(html, unsafe_allow_html=True)
st.markdown(f"**Progression actuelle : {progress} %**")

st.markdown("---")

# --- Vue grand public : historique mais sans contrôles ---
st.subheader("Historique (public)")
if not data["history"]:
    st.write("Aucune action enregistrée pour l'instant.")
else:
    for h in reversed(data["history"][-10:]):
        st.write(f"{h['date']} — **{h['action']}** de {h['valeur']} : {h['raison']}")

st.markdown("---")

# --- Admin area (cachée) ---
st.sidebar.title("Administration")
st.sidebar.write("Si tu es l'administrateur, entre ton token pour activer les contrôles.")
token_input = st.sidebar.text_input("Token admin", type="password")
is_admin = False
if token_input:
    if token_input == ADMIN_TOKEN:
        st.sidebar.success("Mode admin activé")
        is_admin = True
    else:
        st.sidebar.error("Token incorrect")

if is_admin:
    st.header("🔧 Panneau d'administration")
    col1, col2 = st.columns([1,2])
    with col1:
        action = st.radio("Action :", ["Monter", "Descendre"])
    with col2:
        value = st.slider("De combien ? (pourcent)", 1, 50, 5)
    reason = st.text_input("Pourquoi ? (ex: 'Bon comportement', 'Devoirs finis')", "")

    if st.button("Appliquer"):
        if action == "Monter":
            data["progress"] = min(100, data.get("progress", 0) + value)
        else:
            data["progress"] = max(0, data.get("progress", 0) - value)
        data["history"].append({
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "action": action,
            "valeur": value,
            "raison": reason
        })
        save_data(data)
        st.success("Mise à jour appliquée")
        st._rerun()

    st.write("⚠️ Rappel : les visiteurs peuvent voir l'historique mais ne peuvent pas modifier la progression.")
    # Optionnel : bouton "remise à zéro"
    if st.button("Réinitialiser à 0 %"):
        data["progress"] = 0
        data["history"].append({"date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                                "action": "Réinitialisation", "valeur": 0, "raison": "Reset admin"})
        save_data(data)
        st.success("Remis à zéro")
        st.rerun()

# --- footer rapide ---
st.markdown("<hr>", unsafe_allow_html=True)
st.caption("Application publique — accès libre. L'administration nécessite un token privé.")
