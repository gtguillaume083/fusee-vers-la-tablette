import streamlit as st
import json
import gspread
from google.oauth2.service_account import Credentials
import time
from pathlib import Path

# --- Connexion Google Sheets ---
def get_sheet():
    creds_dict = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
    creds = Credentials.from_service_account_info(creds_dict)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(st.secrets["SHEET_ID"]).sheet1
    return sheet

def load_data():
    try:
        sheet = get_sheet()
        records = sheet.get_all_records()
        if records and isinstance(records, list) and len(records) >= 1:
            r = records[0]
            progress = float(r.get("progress", 0))
            history_json = r.get("history", "[]")
            try:
                history = json.loads(history_json)
            except:
                history = []
            return {"progress": progress, "history": history}
        else:
            return {"progress": 0, "history": []}
    except Exception as e:
        st.error(f"Erreur connexion Google Sheets : {e}")
        return {"progress": 0, "history": []}

def save_data(data):
    try:
        sheet = get_sheet()
        sheet.clear()
        sheet.append_row(["progress", "history"])
        sheet.append_row([float(data.get("progress", 0)), json.dumps(data.get("history", []), ensure_ascii=False)])
    except Exception as e:
        st.error(f"Impossible d'enregistrer sur Google Sheets : {e}")

# --- Configuration interface ---
st.set_page_config(page_title="🚀 Fusée vers la tablette", layout="centered")
st.markdown(
    """
    <style>
    .rocket-container {
        position: relative;
        height: 400px;
        width: 150px;
        margin: auto;
        border-left: 2px dashed #bbb;
    }
    .rocket {
        position: absolute;
        left: 45%;
        transform: translateX(-50%);
        transition: bottom 1s ease-in-out;
        font-size: 60px;
    }
    .threshold {
        position: absolute;
        bottom: 100%;
        width: 100%;
        border-top: 2px dashed #4CAF50;
        text-align: center;
        color: #4CAF50;
        font-weight: bold;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- Données persistantes ---
data = load_data()
progress = data["progress"]

# --- Interface admin ---
st.title("🚀 Fusée vers la tablette")

col1, col2 = st.columns(2)
with col1:
    move = st.number_input("Δ montée/descente (%)", -50, 200, 10)
with col2:
    reason = st.text_input("Motif (facultatif)", "")

# --- Boutons de commande ---
colA, colB = st.columns(2)
with colA:
    if st.button("⬆️ Monter la fusée"):
        progress += move
        data["history"].append({"action": "up", "value": move, "reason": reason, "time": time.strftime("%d/%m %H:%M")})
        save_data({"progress": progress, "history": data["history"]})
        st.balloons()
        st.audio("https://actions.google.com/sounds/v1/ambiences/rocket_launch.ogg", format="audio/ogg")
with colB:
    if st.button("⬇️ Redescendre la fusée"):
        progress = max(0, progress - move)
        data["history"].append({"action": "down", "value": move, "reason": reason, "time": time.strftime("%d/%m %H:%M")})
        save_data({"progress": progress, "history": data["history"]})
        st.snow()
        st.audio("https://actions.google.com/sounds/v1/cartoon/wood_plank_flicks.ogg", format="audio/ogg")

# --- Animation visuelle ---
rocket_pos = min(progress, 200)  # affichage max 200%
st.markdown(
    f"""
    <div class="rocket-container">
        <div class="threshold">100 %</div>
        <div class="rocket" style="bottom: {rocket_pos*2}px;">🚀</div>
    </div>
    <p style="text-align:center;font-size:20px;">Progression actuelle : <b>{progress:.1f}%</b></p>
    """,
    unsafe_allow_html=True,
)

# --- Historique ---
with st.expander("📜 Historique des changements"):
    if data["history"]:
        for h in reversed(data["history"][-15:]):
            arrow = "⬆️" if h["action"] == "up" else "⬇️"
            st.markdown(f"{arrow} **{h['value']} %** — {h.get('reason','')} ({h['time']})")
    else:
        st.write("Aucune modification enregistrée.")
