import streamlit as st
import json, time
import gspread
from google.oauth2.service_account import Credentials

# --- CONFIG ---
st.set_page_config(page_title="🚀 Fusée vers la tablette", layout="centered")
ADMIN_TOKEN = "monmotdepasse2025"  # mot de passe admin

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
    except Exception:
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


# --- Données ---
data = load_data()
progress = data["progress"]
history = data["history"]

# --- TITRE ---
st.title("🚀 Fusée vers la tablette")
st.markdown(f"### Progression actuelle : **{progress}%**")

# --- Animation / Affichage visuel ---
animation_html = f"""
<style>
.space-container {{
  position: relative;
  width: 800px;
  height: 300px;
  margin: 30px auto;
  background: linear-gradient(to right, #001020, #003366);
  border-radius: 20px;
  overflow: hidden;
  box-shadow: inset 0 0 20px rgba(255,255,255,0.15);
}}

.rocket {{
  position: absolute;
  bottom: 40%;
  left: calc({min(progress,150)}% * 0.7);
  transform: translateX(-50%);
  font-size: 64px;
  animation: fly 2.5s ease-out forwards;
}}

@keyframes fly {{
  from {{ left: 0%; }}
  to {{ left: calc({min(progress,150)}% * 0.7); }}
}}

.scale {{
  position: absolute;
  bottom: 10%;
  left: 5%;
  width: 90%;
  height: 6px;
  background: linear-gradient(to right, #555, #aaa);
  border-radius: 3px;
}}

.tick {{
  position: absolute;
  bottom: 5%;
  width: 2px;
  height: 15px;
  background: #fff;
}}

.label {{
  position: absolute;
  bottom: 0%;
  font-size: 12px;
  color: #fff;
  transform: translateX(-50%);
}}

.karman {{
  position: absolute;
  bottom: 10%;
  left: 70%;
  width: 2px;
  height: 80%;
  background: repeating-linear-gradient(
    to bottom,
    #ff5555,
    #ff5555 5px,
    transparent 5px,
    transparent 10px
  );
}}

.karman-label {{
  position: absolute;
  top: 5%;
  left: 70%;
  color: #ff9999;
  font-weight: bold;
  transform: translateX(-50%);
  font-size: 14px;
}}
</style>

<div class="space-container">
  <div class="rocket">🚀</div>
  <div class="karman"></div>
  <div class="karman-label">Kármán line (100%)</div>
  <div class="scale">
    {"".join([f'<div class="tick" style="left:{i}%"></div><div class="label" style="left:{i}%">{i}</div>' for i in range(0, 110, 10)])}
  </div>
</div>

<audio autoplay>
  <source src="https://actions.google.com/sounds/v1/transportation/rocket_whoosh.ogg" type="audio/ogg">
</audio>
"""
st.markdown(animation_html, unsafe_allow_html=True)

# --- Historique ---
st.subheader("Historique des actions")
if not history:
    st.info("Aucune action enregistrée 🚀")
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

