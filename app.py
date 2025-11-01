import streamlit as st
import json
import gspread
import pandas as pd
import datetime
import plotly.graph_objects as go
from google.oauth2.service_account import Credentials

# --- Configuration de la page ---
st.set_page_config(page_title="🚀 Fusée vers la tablette", layout="wide")

# 🌑 --- Thème sombre global ---
st.markdown(
    """
    <style>
    body {
        background-color: #000 !important;
        color: #fff !important;
    }
    .stApp {
        background-color: #000 !important;
    }
    .stMarkdown, .stMetric, .stTextInput, .stNumberInput, .stButton, .stExpander {
        color: #fff !important;
    }
    h1 {
        font-size: 1.6rem !important;
        color: #ffffff !important;
        text-align: center;
        margin-bottom: 0.5em;
    }
    h2, h3, h4 {
        color: #ffffff !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --- Vérification des secrets ---
required_secrets = ["GOOGLE_CREDENTIALS", "SHEET_ID"]
missing = [k for k in required_secrets if k not in st.secrets]
if missing:
    st.error(f"⚠️ Secrets manquants : {', '.join(missing)}")
    st.stop()

ADMIN_TOKEN = st.secrets.get("ADMIN_TOKEN", None)

# --- Connexion Google Sheets ---
@st.cache_resource
def get_client():
    creds_dict = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
    creds = Credentials.from_service_account_info(
        creds_dict,
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
    )
    return gspread.authorize(creds)

def get_sheet():
    client = get_client()
    return client.open_by_key(st.secrets["SHEET_ID"]).sheet1

@st.cache_data(ttl=300)
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
        except json.JSONDecodeError:
            history = []
        return {"progress": progress, "history": history}
    except Exception as e:
        st.error(f"⚠️ Erreur connexion Google Sheets : {e}")
        return {"progress": 0, "history": []}

def save_data(data):
    try:
        sheet = get_sheet()
        sheet.update('A2:B2', [[
            int(data.get("progress", 0)),
            json.dumps(data.get("history", []), ensure_ascii=False)
        ]])
    except Exception as e:
        st.error(f"❌ Impossible d'enregistrer sur Google Sheets : {e}")

# --- Charger les données ---
data = load_data()
progress = data.get("progress", 0)
history = data.get("history", [])

# --- Titre ---
st.markdown("<h1>🚀 Fusée vers la tablette — Progression annuelle</h1>", unsafe_allow_html=True)

# --- Mode administrateur ---
if "admin" not in st.session_state:
    st.session_state.admin = False

with st.expander("🔐 Mode administrateur", expanded=False):
    token_input = st.text_input("Entre le code secret du pilote :", type="password")
    if st.button("Activer le mode admin"):
        if ADMIN_TOKEN and token_input == ADMIN_TOKEN:
            st.session_state.admin = True
            st.success("Mode admin activé ✅")
        elif not ADMIN_TOKEN:
            st.warning("⚙️ Aucun code admin défini — accès libre autorisé pour test.")
            st.session_state.admin = True
        else:
            st.error("Code incorrect ❌")

admin_mode = st.session_state.admin

# --- Altitude actuelle ---
st.metric(label="Altitude actuelle", value=f"{progress} %")

# --- Interface administrateur ---
if admin_mode:
    st.markdown("### ⚙️ Modifier la progression")
    delta = st.slider("Variation de progression (%)", -20, 20, 0)
    reason = st.text_input("Motif de la modification :")
    if st.button("💾 Enregistrer la modification"):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
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

# --- Graphique de progression ---
try:
    if not history:
        st.info("Aucune trajectoire à afficher 🚀")
    else:
        df = pd.DataFrame(history)
        df["delta"] = df["delta"].astype(int)
        df["time"] = pd.to_datetime(df["time"], format="%Y-%m-%d %H:%M", errors="coerce")
        df = df.dropna(subset=["time"]).sort_values("time")

        # 🧮 Calcul de l'altitude cumulée (fidèle à la version d'origine)
        altitude, total = [], 0
        for _, row in df.iterrows():
            total += row["delta"] if row["action"] == "up" else -row["delta"]
            altitude.append(max(0, total))
        df["altitude"] = altitude

        # 📅 Générer une interpolation journalière fidèle
        today = datetime.datetime.now()
        start_date = datetime.datetime(today.year if today.month >= 9 else today.year - 1, 9, 1)
        end_date = datetime.datetime(start_date.year + 1, 6, 30)
        df_full = pd.DataFrame({"date": pd.date_range(start=start_date, end=end_date, freq="D")})

        df_full = pd.merge_asof(
            df_full.sort_values("date"),
            df.sort_values("time").rename(columns={"time": "date"}),
            on="date",
            direction="forward"
        )

        df_full["altitude"].fillna(method="ffill", inplace=True)
        df_full["altitude"].fillna(0, inplace=True)

        df_interp = df_full[df_full["date"] <= today]
        fus_alt = df_interp["altitude"].iloc[-1]

        # 📈 Création du graphique
        fig = go.Figure()

        # Bande "espace"
        fig.add_shape(
            type="rect",
            xref="paper", x0=0, x1=1,
            yref="y", y0=100, y1=130,
            fillcolor="rgba(0, 0, 120, 0.25)",
            line=dict(width=0),
            layer="below"
        )

        # Courbe de progression
        fig.add_trace(go.Scatter(
            x=df_interp["date"],
            y=df_interp["altitude"],
            mode="lines",
            line=dict(color="deepskyblue", width=4),
            name="Progression"
        ))

        # Fusée
        fig.add_trace(go.Scatter(
            x=[df_interp["date"].iloc[-1]],
            y=[fus_alt],
            mode="text",
            text=["🚀"],
            textfont=dict(size=48),
            textposition="middle center",
            name="Fusée"
        ))

        # Flamme
        fig.add_trace(go.Scatter(
            x=[df_interp["date"].iloc[-1]],
            y=[fus_alt - 5],
            mode="text",
            text=["🔥"],
            textfont=dict(size=28),
            textposition="top center",
            name="Flamme"
        ))

        # Ligne de Karman
        fig.add_hline(y=100, line=dict(color="red", dash="dot"))
        fig.add_annotation(
            xref="paper", x=1.02, y=105,
            text="🌌 Ligne de Karman (100%)",
            showarrow=False,
            font=dict(size=12, color="red")
        )

        # Style
        fig.update_layout(
            title="Trajectoire de la fusée",
            xaxis_title="Temps (du 1er septembre au 30 juin)",
            yaxis_title="Altitude (%)",
            yaxis=dict(range=[0, max(130, fus_alt + 10)], color="white"),
            xaxis=dict(color="white"),
            width=950,
            height=550,
            plot_bgcolor="#000",
            paper_bgcolor="#000",
            font=dict(color="white"),
            margin=dict(l=50, r=50, t=50, b=50)
        )

        st.plotly_chart(fig, use_container_width=True)

        # --- Texte sous le graphique ---
        st.markdown("### 🧭 Altitude actuelle :")
        st.metric(label="Progression", value=f"{progress} %")

        st.markdown("## 📜 Historique des actions")
        for h in history:
            st.markdown(
                f"🕓 **{h['time']}** — *{h['action']} de {h['delta']} %* : {h['reason']}"
            )

except Exception as e:
    st.error(f"❌ Erreur lors de l'affichage du graphique : {e}")
