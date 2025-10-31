import streamlit as st
import pandas as pd
import json
import datetime
import time
import gspread
from google.oauth2.service_account import Credentials
import plotly.graph_objects as go

st.set_page_config(page_title="🚀 Fusée vers la tablette", layout="wide")
st.title("🚀 Fusée vers la tablette — Progression annuelle")

# --- Connexion Google Sheets ---
def get_sheet():
    creds_dict = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=["https://www.googleapis.com/auth/spreadsheets"])
    client = gspread.authorize(creds)
    sheet = client.open_by_key(st.secrets["SHEET_ID"]).sheet1
    return sheet

def load_data():
    sheet = get_sheet()
    records = sheet.get_all_records()
    if records:
        r = records[0]
        progress = int(r.get("progress", 0))
        history = json.loads(r.get("history", "[]"))
    else:
        progress, history = 0, []
    return progress, history

def save_data(progress, history):
    sheet = get_sheet()
    sheet.clear()
    sheet.append_row(["progress", "history"])
    sheet.append_row([progress, json.dumps(history, ensure_ascii=False)])

# --- Chargement ---
progress, history = load_data()

# --- Interface admin ---
admin_mode = False
with st.sidebar:
    st.subheader("🔑 Mode administrateur")
    token = st.text_input("Token admin", type="password")
    if token == st.secrets["ADMIN_TOKEN"]:  # <-- ton ancien système gardé
        admin_mode = True
        st.success("Mode admin activé ✅")
    else:
        st.info("Mode lecture seule 👀")

# --- Modification de la progression ---
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
        save_data(progress, history)
        st.sidebar.success("Mise à jour enregistrée ✅")
        st.experimental_rerun()

# --- Si pas d’historique ---
if len(history) == 0:
    st.warning("Aucune trajectoire à afficher 🚀")
else:
    df = pd.DataFrame(history)
    df["date"] = pd.to_datetime(df["time"], format="%d/%m %H:%M", errors="coerce")
    df = df.sort_values("date")

    # --- Cumul des altitudes ---
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

    # --- Interpolation temporelle (année scolaire) ---
    start_date = datetime.datetime(datetime.datetime.now().year, 9, 1)
    end_date = datetime.datetime(datetime.datetime.now().year + 1, 6, 30)
    full_dates = pd.date_range(start=start_date, end=end_date, freq="D")
    df_interp = pd.DataFrame({"date": full_dates})
    df_interp = pd.merge_asof(df_interp, df[["date", "altitude"]], on="date", direction="forward")
    df_interp["altitude"].fillna(method="ffill", inplace=True)
    df_interp["altitude"].fillna(0, inplace=True)

    # --- Position de la fusée ---
    today = datetime.datetime.now()
    fus_index = df_interp["date"].searchsorted(today)
    fus_index = min(fus_index, len(df_interp) - 1)
    fus_alt = df_interp["altitude"].iloc[fus_index]
    fus_date = df_interp["date"].iloc[fus_index]

    # --- Graphique Plotly ---
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df_interp["date"], y=df_interp["altitude"],
        mode="lines",
        line=dict(color="skyblue", width=4),
        name="Progression"
    ))

    fig.add_hline(y=100, line_dash="dot", line_color="red",
                  annotation_text="Ligne de Kármán (100%)", annotation_position="right")

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
        xaxis_title="Temps (année scolaire)",
        yaxis_title="Altitude (%)",
        yaxis_range=[0, max(110, df_interp['altitude'].max() + 10)],
        template="plotly_dark",
        height=500
    )

    st.plotly_chart(fig, use_container_width=True)

# --- Historique lisible ---
st.subheader("📜 Historique des actions")
if len(history) == 0:
    st.write("Aucune action enregistrée.")
else:
    for h in reversed(history):
        st.write(f"🕓 {h['time']} — **{h['action']} {h['delta']} %** : {h['reason']}")
