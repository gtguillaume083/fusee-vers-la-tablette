import streamlit as st
import pandas as pd
import json
import datetime
import time
import gspread
from google.oauth2.service_account import Credentials
import plotly.graph_objects as go

# --- Configuration de la page ---
st.set_page_config(page_title="🚀 Fusée vers la tablette", layout="wide")
st.title("🚀 Fusée vers la tablette — Progression annuelle")

# --- Connexion à Google Sheets ---
def get_sheet():
    creds_dict = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=["https://www.googleapis.com/auth/spreadsheets"])
    client = gspread.authorize(creds)
    sheet = client.open_by_key(st.secrets["SHEET_ID"]).sheet1
    return sheet

def load_data():
    try:
        sheet = get_sheet()
        records = sheet.get_all_records()
        if records and len(records) > 0:
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
        sheet.append_row([int(data["progress"]), json.dumps(data["history"], ensure_ascii=False)])
    except Exception as e:
        st.error(f"Erreur enregistrement Google Sheets : {e}")

# --- Chargement des données ---
data = load_data()
progress = data["progress"]
history = data["history"]

# --- Interface admin / lecture seule ---
admin_mode = False
with st.sidebar:
    st.subheader("🔑 Mode administrateur")
    token = st.text_input("Token admin", type="password")
    if token == st.secrets["ADMIN_TOKEN"]:
        admin_mode = True
        st.success("Mode admin activé ✅")
    else:
        st.info("Mode lecture seule 👀")

# --- Actions admin ---
if admin_mode:
    st.sidebar.markdown("### ✏️ Modifier la progression")
    action = st.sidebar.selectbox("Action", ["up", "down"])
    delta = st.sidebar.number_input("Δ %", min_value=1, max_value=50, step=1)
    reason = st.sidebar.text_input("Motif", "")
    if st.sidebar.button("Valider"):
        now = datetime.datetime.now().strftime("%d/%m %H:%M")
        history.append({
            "time": now,
            "action": action,
            "delta": delta,
            "reason": reason if reason else "(non précisé)"
        })
        if action == "up":
            progress += delta
        else:
            progress = max(0, progress - delta)
        data = {"progress": progress, "history": history}
        save_data(data)
        st.sidebar.success("Mise à jour enregistrée ✅")
        st.experimental_rerun()

# --- Historique en DataFrame ---
if len(history) == 0:
    st.warning("Aucune trajectoire à afficher 🚀")
else:
    df = pd.DataFrame(history)
    df["date"] = pd.to_datetime(df["time"], format="%d/%m %H:%M", errors="coerce")
    df = df.sort_values("date")

    # --- Altitude cumulée ---
    altitude = 0
    altitudes = []
    for _, row in df.iterrows():
        if row["action"] == "up":
            altitude += row["delta"]
        elif row["action"] == "down":
            altitude -= row["delta"]
        altitude = max(0, altitude)
        altitudes.append(altitude)
    df["altitude"] = altitudes

    # --- Interpolation sur l'année scolaire ---
    start_date = datetime.datetime(datetime.datetime.now().year, 9, 1)
    end_date = datetime.datetime(datetime.datetime.now().year + 1, 6, 30)
    full_dates = pd.date_range(start=start_date, end=end_date, freq="D")
    df_interp = pd.DataFrame({"date": full_dates})
    df_interp = pd.merge_asof(df_interp, df[["date", "altitude"]], on="date", direction="forward")
    df_interp["altitude"].fillna(method="ffill", inplace=True)
    df_interp["altitude"].fillna(0, inplace=True)

    # --- Position actuelle de la fusée ---
    today = datetime.datetime.now()
    fus_index = df_interp["date"].searchsorted(today)
    fus_index = min(fus_index, len(df_interp) - 1)
    fus_alt = df_interp["altitude"].iloc[fus_index]
    fus_date = df_interp["date"].iloc[fus_index]

    # --- Graphique Plotly ---
    fig = go.Figure()

    # Courbe de progression
    fig.add_trace(go.Scatter(
        x=df_interp["date"], y=df_interp["altitude"],
        mode="lines",
        line=dict(color="skyblue", width=4),
        name="Progression"
    ))

    # Ligne de Kármán (100 %)
    fig.add_hline(y=100, line_dash="dot", line_color="red",
                  annotation_text="Ligne de Kármán (100%)", annotation_position="right")

    # Fusée (emoji)
    fig.add_trace(go.Scatter(
        x=[fus_date], y=[fus_alt],
        mode="markers+text",
        marker=dict(size=30, symbol="star", color="orange"),
        text=["🚀"],
        textposition="top center",
        name="Fusée"
    ))

    fig.update_layout(
        title="Trajectoire de la fusée",
        xaxis_title="Temps (du 1er septembre au 30 juin)",
        yaxis_title="Altitude (%)",
        yaxis_range=[0, max(110, df_interp["altitude"].max() + 10)],
        template="plotly_dark",
        height=500
    )

    # --- Animation fluide ---
    placeholder = st.empty()
    for i in range(1, fus_index + 1):
        temp_fig = fig
        temp_fig.data[0].x = df_interp["date"][:i]
        temp_fig.data[0].y = df_interp["altitude"][:i]
        placeholder.plotly_chart(temp_fig, use_container_width=True)
        time.sleep(0.01)

# --- Historique lisible ---
st.subheader("📜 Historique des actions")
if len(history) == 0:
    st.write("Aucune action enregistrée.")
else:
    for h in reversed(history):
        st.write(f"🕓 {h['time']} — **{h['action']} {h['delta']} %** : {h['reason']}")
