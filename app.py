import streamlit as st
import json
import gspread
import pandas as pd
import datetime
import time
import plotly.graph_objects as go
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="🚀 Fusée vers la tablette", layout="wide")

# --- Connexion Google Sheets ---
def get_sheet():
    creds_dict = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
    creds = Credentials.from_service_account_info(
        creds_dict,
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
    )
    client = gspread.authorize(creds)
    sheet = client.open_by_key(st.secrets["SHEET_ID"]).sheet1
    return sheet


def load_data():
    try:
        sheet = get_sheet()
        records = sheet.get_all_records()
        if not records:
            return {"progress": 0, "history": []}
        r = records[0]
        progress = int(r.get("progress", 0))
        history_json = r.get("history", "[]")
        try:
            history = json.loads(history_json)
        except:
            history = []
        return {"progress": progress, "history": history}
    except Exception as e:
        st.error(f"Erreur connexion Google Sheets : {e}")
        return {"progress": 0, "history": []}


def save_data(data):
    try:
        sheet = get_sheet()
        sheet.clear()
        sheet.append_row(["progress", "history"])
        sheet.append_row([
            int(data.get("progress", 0)),
            json.dumps(data.get("history", []), ensure_ascii=False)
        ])
    except Exception as e:
        st.error(f"Impossible d'enregistrer sur Google Sheets : {e}")


# --- Charger les données ---
data = load_data()
progress = data["progress"]
history = data["history"]

st.title("🚀 Fusée vers la tablette — Progression annuelle")

# --- Interface Admin ---
admin_mode = False
if "admin" not in st.session_state:
    st.session_state.admin = False

with st.expander("🔐 Mode administrateur", expanded=False):
    token_input = st.text_input("Entre le token administrateur :", type="password")
    if st.button("Activer le mode admin"):
        if token_input == st.secrets["ADMIN_TOKEN"]:
            st.session_state.admin = True
            st.success("Mode admin activé ✅")
        else:
            st.error("Token invalide ❌")

admin_mode = st.session_state.admin

# --- Section principale ---
st.subheader("Altitude actuelle :")
st.metric(label="Progression", value=f"{progress} %")

# --- Actions admin ---
if admin_mode:
    st.markdown("### ⚙️ Modifier la progression")
    col1, col2 = st.columns(2)
    with col1:
        up = st.number_input("⬆️ Augmenter de :", min_value=0, max_value=100, value=0, step=1)
    with col2:
        down = st.number_input("⬇️ Diminuer de :", min_value=0, max_value=100, value=0, step=1)

    reason = st.text_input("Motif de la modification :")
    if st.button("💾 Enregistrer la modification"):
        now = datetime.datetime.now().strftime("%d/%m %H:%M")
        delta = up - down
        if delta != 0:
            progress = max(0, progress + delta)
            history.insert(0, {
                "time": now,
                "action": "up" if delta > 0 else "down",
                "delta": abs(delta),
                "reason": reason if reason else "(non précisé)"
            })
            data = {"progress": progress, "history": history}
            save_data(data)
            st.success("Progression mise à jour ✅")
            st.rerun()
        else:
            st.info("Aucun changement détecté.")

# --- Historique ---
st.markdown("## 📜 Historique des actions")
if history:
    for h in history:
        st.write(f"🕓 {h['time']} — **{h['action']} de {h['delta']}%** : {h['reason']}")
else:
    st.info("Aucune action enregistrée.")

# --- Graphique de progression dans le temps ---
if history:
    df = pd.DataFrame(history)
    df["delta"] = df["delta"].astype(int)

    # 🔧 Corriger le parsing des dates sans année
    def parse_school_date(date_str):
        try:
            # Exemple : "01/09 08:00"
            d = datetime.datetime.strptime(date_str, "%d/%m %H:%M")
            today = datetime.datetime.now()
            # Si on est avant juillet → année scolaire en cours
            school_year = today.year if d.month >= 9 else today.year - 1
            return d.replace(year=school_year)
        except Exception:
            return pd.NaT

    df["time"] = df["time"].apply(parse_school_date)
    df = df.dropna(subset=["time"])
    df = df.sort_values("time")

    # 🧮 Calcul de la progression cumulée dans le temps
    altitude = []
    total = 0
    for _, row in df.iterrows():
        total += row["delta"] if row["action"] == "up" else -row["delta"]
        altitude.append(max(0, total))
    df["altitude"] = altitude

    # 📆 Étendre la courbe sur l'année scolaire
    today = datetime.datetime.now()
    start_date = datetime.datetime(today.year if today.month >= 9 else today.year - 1, 9, 1)
    end_date = datetime.datetime(start_date.year + 1, 6, 30)

    df_interp = pd.DataFrame({"date": pd.date_range(start=start_date, end=end_date, freq="D")})
    df_interp = pd.merge_asof(
        df_interp.sort_values("date"),
        df.sort_values("time").rename(columns={"time": "date"}),
        on="date",
        direction="forward"
    )

    df_interp["altitude"].fillna(method="ffill", inplace=True)
    df_interp["altitude"].fillna(0, inplace=True)

    fus_alt = df_interp["altitude"].iloc[-1]

    # 📈 Création du graphique
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df_interp["date"],
        y=df_interp["altitude"],
        mode="lines",
        line=dict(color="skyblue", width=4),
        name="Progression"
    ))

    # 🌌 Ligne de Karman (100%)
    fig.add_hline(
        y=100,
        line=dict(color="red", dash="dot"),
        name="Ligne de Karman"
    )
    fig.add_annotation(
        xref="paper", x=1.01, y=100,
        text="🌌 Ligne de Karman (100%)",
        showarrow=False,
        font=dict(size=12, color="red")
    )

    # 🚀 Position de la fusée
    fig.add_trace(go.Scatter(
        x=[df_interp["date"].iloc[-1]],
        y=[fus_alt],
        mode="markers+text",
        marker=dict(size=30, symbol="star", color="orange"),
        text=["🚀"],
        textposition="top center",
        name="Fusée"
    ))

    # ✨ Mise en page
    fig.update_layout(
        title="Trajectoire de la fusée",
        xaxis_title="Temps (du 1er septembre au 30 juin)",
        yaxis_title="Altitude (%)",
        yaxis=dict(range=[0, max(110, fus_alt + 10)]),
        width=900,
        height=500,
        template="plotly_white"
    )

    st.plotly_chart(fig, use_container_width=True)

else:
    st.info("Aucune trajectoire à afficher 🚀")

