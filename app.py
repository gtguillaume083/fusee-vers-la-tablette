import streamlit as st
import json, time
import gspread
from google.oauth2.service_account import Credentials

try:
    creds_dict = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
    st.success("✅ JSON Google valide !")
except Exception as e:
    st.error(f"❌ Erreur parsing JSON : {e}")


# --- CONFIG ---
st.set_page_config(page_title="🚀 Fusée vers la tablette", layout="centered")
ADMIN_TOKEN = "monmotdepasse2025"  # <-- ton token admin ici

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
    sheet = get_sheet()
    records = sheet.get_all_records()
    if records:
        r = records[0]
        return {
            "progress": int(r.get("progress", 0)),
            "history": json.loads(r.get("history", "[]"))
        }
    else:
        return {"progress": 0, "history": []}

def save_data(data):
    sheet = get_sheet()
    sheet.clear()
    sheet.append_row(["progress", "history"])
    sheet.append_row([data["progress"], json.dumps(data["history"], ensure_ascii=False)])

# --- Chargement des données ---
data = load_data()
progress = data["progress"]
history = data["history"]

# --- Interface principale ---
st.title("🚀 Fusée vers la tablette !")

st.markdown(f"### Progression actuelle : **{progress}%**")

# Barre ou fusée visuelle
fusée_html = f"""
<div style='position:relative;width:150px;height:400px;margin:auto;background:linear-gradient(to top,#00111f,#003366);border-radius:30px;'>
  <div style='position:absolute;bottom:0;width:100%;height:{progress}%;background:linear-gradient(to top,#33ccff,#ff6699);border-radius:30px 30px 0 0;'></div>
  <div style='position:absolute;bottom:{progress}%;left:35%;font-size:48px;'>🚀</div>
  <div style='position:absolute;top:10px;left:40%;font-size:24px;'>🎯</div>
</div>
"""
st.markdown(fusée_html, unsafe_allow_html=True)

# --- Mode admin ---
st.sidebar.header("Administration")
admin_input = st.sidebar.text_input("Token admin", type="password")

if admin_input == ADMIN_TOKEN:
    st.sidebar.success("Mode admin activé ✅")
    st.header("🛠 Panneau d'administration")

    action = st.radio("Action :", ["Monter", "Descendre"], horizontal=True)
    delta = st.slider("De combien ?", 1, 20, 5)
    reason = st.text_input("Pourquoi ? (ex: 'Devoirs finis', 'Bon comportement')")

    if st.button("Appliquer"):
        if action == "Monter":
            progress = min(progress + delta, 150)  # max 150%
        else:
            progress = max(progress - delta, 0)

        history.insert(0, {
            "time": time.strftime("%Y-%m-%d %H:%M"),
            "action": action,
            "delta": delta,
            "reason": reason
        })
        data = {"progress": progress, "history": history}
        save_data(data)
        st.success("✅ Mise à jour appliquée")
        st.experimental_rerun()
else:
    st.sidebar.warning("Mode lecture seule 👀")

# --- Historique ---
st.subheader("Historique des actions")
for h in history[:10]:
    st.write(f"🕓 {h['time']} — **{h['action']} de {h['delta']}%** : {h['reason']}")
