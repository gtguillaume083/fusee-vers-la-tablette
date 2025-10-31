import streamlit as st
import json, time
import gspread
from google.oauth2.service_account import Credentials

# --- CONFIG ---
st.set_page_config(page_title="🚀 Fusée vers la tablette", layout="centered")
ADMIN_TOKEN = "monmotdepasse2025"  # <-- Ton mot de passe admin ici

# --- Connexion Google Sheets ---
def get_sheet():
    creds_dict = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/drive.file"
    ]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(st.secrets["SHEET_ID"]).sheet1
    return sheet


def load_data():
    try:
        sheet = get_sheet()
        records = sheet.get_all_records()
        if records and isinstance(records, list):
            r = records[0]
            return {
                "progress": int(r.get("progress", 0)),
                "history": json.loads(r.get("history", "[]"))
            }
        else:
            return {"progress": 0, "history": []}
    except Exception as e:
        st.error("Erreur connexion Google Sheets.")
        return {"progress": 0, "history": []}


def save_data(data):
    try:
        sheet = get_sheet()
        sheet.clear()
        sheet.append_row(["progress", "history"])
        sheet.append_row([data["progress"], json.dumps(data["history"], ensure_ascii=False)])
    except Exception:
        st.error("Impossible d'enregistrer sur Google Sheets.")


# --- Données principales ---
data = load_data()
progress = data["progress"]
history = data["history"]

# --- TITRE ---
st.title("🚀 Fusée vers la tablette !")

st.markdown(f"### Progression actuelle : **{progress}%**")

# --- Animation de la fusée ---
animation_html = f"""
<style>
@keyframes rise {{
  from {{ bottom: 0; }}
  to {{ bottom: {progress * 3}px; }}
}}

@keyframes smoke {{
  0% {{ opacity: 1; transform: scale(1); }}
  100% {{ opacity: 0; transform: scale(3); }}
}}

.launchpad {{
  position: relative;
  width: 200px;
  height: 600px;
  margin: auto;
  background: linear-gradient(to top, #001020 0%, #003366 100%);
  border-radius: 30px;
  overflow: hidden;
  box-shadow: inset 0 0 15px rgba(255,255,255,0.2);
}}

.rocket {{
  position: absolute;
  bottom: 0;
  left: 35%;
  font-size: 64px;
  animation: rise 3s ease-out forwards;
}}

.smoke {{
  position: absolute;
  bottom: 0;
  left: 50%;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: rgba(255,255,255,0.4);
  animation: smoke 2s infinite;
}}

.target {{
  position: absolute;
  top: {max(550 - progress * 3, 30)}px;
  left: 45%;
  font-size: 30px;
}}
</style>

<div class="launchpad">
  <div class="smoke"></div>
  <div class="rocket">🚀</div>
  <div class="target">🎯</div>
</div>

<audio autoplay>
  <source src="https://actions.google.com/sounds/v1/transportation/rocket_whoosh.ogg" type="audio/ogg">
</audio>
"""
st.markdown(animation_html, unsafe_allow_html=True)

# --- Historique ---
st.subheader("Historique des actions")
if not history:
    st.info("Aucune action enregistrée pour l’instant 🚀")
else:
    for h in history[:10]:
        action = h.get("action", "?")
        delta = h.get("delta", h.get("value", 0))
        reason = h.get("reason", "")
        st.write(f"🕓 {h.get('time', '?')} — **{action} de {delta}%** : {reason}")


# --- Panneau admin ---
st.sidebar.header("🔑 Mode administrateur")
admin_input = st.sidebar.text_input("Token admin", type="password")

if admin_input == ADMIN_TOKEN:
    st.sidebar.success("Mode admin activé ✅")
    st.header("🛠 Panneau de contrôle")

    action = st.radio("Action :", ["Monter", "Descendre"], horizontal=True)
    delta = st.slider("De combien ?", 1, 20, 5)
    reason = st.text_input("Pourquoi ? (ex : 'Devoirs finis', 'Bon comportement')")

    if st.button("Appliquer"):
        if delta == 0:
            st.warning("⚠️ Aucun changement : choisis une valeur différente de 0.")
        else:
            if action == "Monter":
                progress = min(progress + delta, 150)
            else:
                progress = max(progress - delta, 0)

            history.insert(0, {
                "time": time.strftime("%d/%m %H:%M"),
                "action": "up" if action == "Monter" else "down",
                "delta": delta,
                "reason": reason or "(non précisé)"
            })
            save_data({"progress": progress, "history": history})
            st.success(f"✅ Mise à jour : {action} de {delta}%")
            st.rerun()

else:
    st.sidebar.warning("Mode lecture seule 👀")
