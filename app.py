import streamlit as st
import json, time, datetime
import pandas as pd
import altair as alt
import gspread
from google.oauth2.service_account import Credentials

# --- CONFIG ---
st.set_page_config(page_title="🚀 Fusée vers la tablette", layout="centered")
ADMIN_TOKEN = "monmotdepasse2025"
DEBUG_MODE = False  # Passe à True pour afficher les données brutes

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
            progress = int(r.get("progress", 0))
            history = json.loads(r.get("history", "[]"))
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
        sheet.append_row([data["progress"], json.dumps(data["history"], ensure_ascii=False)])
    except Exception as e:
        st.error(f"Impossible d'enregistrer sur Google Sheets : {e}")


# --- Données ---
data = load_data()
progress = data["progress"]
history = data["history"]

st.title("🚀 Fusée vers la tablette — Progression annuelle")

if DEBUG_MODE:
    st.subheader("🔧 Mode debug : données brutes")
    st.json(history)

# --- Préparation du DataFrame temporel ---
if history:
    df = pd.DataFrame(history)
    df["delta"] = df.get("delta", df.get("value", 0))
    df["time"] = pd.to_datetime(df["time"], format="%d/%m %H:%M", errors="coerce")
    df["time"] = df["time"].fillna(datetime.datetime.now())

    df = df.sort_values("time")
    df["altitude"] = 0
    altitude = 0
    for i, row in df.iterrows():
        if row["action"] == "up":
            altitude += row["delta"]
        elif row["action"] == "down":
            altitude -= row["delta"]
        df.at[i, "altitude"] = max(0, altitude)

    fus_alt = df["altitude"].iloc[-1]
else:
    df = pd.DataFrame(columns=["time", "altitude"])
    fus_alt = 0

# --- Domaine temporel de l’année scolaire ---
today = datetime.date.today()
start_year = today.year if today.month >= 9 else today.year - 1
start = datetime.date(start_year, 9, 1)
end = datetime.date(start_year + 1, 6, 30)

# --- S’il n’y a qu’un seul point, on duplique pour afficher un segment ---
if len(df) == 1:
    df = pd.concat([
        pd.DataFrame([{"time": pd.Timestamp(start), "altitude": 0}]),
        df
    ])

# --- Graphique ---
if not df.empty:
    base = alt.Chart(df).mark_line(
        color="#1f77b4",
        strokeWidth=3
    ).encode(
        x=alt.X("time:T", title="Temps (année scolaire)", scale=alt.Scale(domain=[start, end])),
        y=alt.Y("altitude:Q", title="Altitude (%)", scale=alt.Scale(domain=[0, 150]))
    )

    # Ligne de Kármán
    karman_line = alt.Chart(pd.DataFrame({"y": [100]})).mark_rule(
        color="red",
        strokeDash=[6, 4],
        strokeWidth=2
    ).encode(y="y")

    # Étiquette Kármán
    karman_label = alt.Chart(pd.DataFrame({"y": [100], "x": [start]})).mark_text(
        align="left",
        dx=10,
        color="red",
        fontWeight="bold"
    ).encode(x="x", y="y", text=alt.value("Ligne de Kármán (100 %)"))

    # Fusée 🚀 (dernier point)
    rocket = alt.Chart(pd.DataFrame({
        "x": [df["time"].iloc[-1]],
        "y": [fus_alt]
    })).mark_text(
        text="🚀",
        size=25
    ).encode(x="x", y="y")

    chart = (base + karman_line + karman_label + rocket).properties(
        width=800,
        height=400
    ).configure_axis(grid=True)

    st.altair_chart(chart, width="stretch")
else:
    st.warning("Aucune trajectoire à afficher pour le moment 🚀")

# --- Historique ---
st.subheader("📜 Historique des actions")
if history:
    for h in history[:10]:
        st.write(f"🕓 {h.get('time', '?')} — **{h.get('action', '?')} {h.get('delta', 0)} %** : {h.get('reason', '')}")
else:
    st.info("Aucune action enregistrée pour le moment.")

# --- Mode admin ---
st.sidebar.header("🔑 Mode administrateur")
admin_input = st.sidebar.text_input("Token admin", type="password")

if admin_input == ADMIN_TOKEN:
    st.sidebar.success("Mode admin activé ✅")
    st.header("🛠 Contrôle")

    action = st.radio("Action :", ["Monter", "Descendre"], horizontal=True)
    delta = st.slider("De combien ?", 1, 20, 5)
    reason = st.text_input("Pourquoi ?")

    if st.button("Appliquer"):
        if action == "Monter":
            progress = min(progress + delta, 150)
            act_type = "up"
        else:
            progress = max(progress - delta, 0)
            act_type = "down"

        history.insert(0, {
            "time": time.strftime("%d/%m %H:%M"),
            "action": act_type,
            "delta": delta,
            "reason": reason or "(non précisé)"
        })
        save_data({"progress": progress, "history": history})
        st.success(f"✅ Mise à jour : {action} de {delta} %")
        st.rerun()
else:
    st.sidebar.info("Mode lecture seule 👀")
