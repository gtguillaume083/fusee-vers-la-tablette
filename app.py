import streamlit as st
import json
import gspread
import pandas as pd
import datetime
import plotly.graph_objects as go
from google.oauth2.service_account import Credentials

# --- Configuration de la page ---
st.set_page_config(page_title="🚀 Fusée vers la tablette", layout="wide")

# 🌌 --- Thème sombre + fond dégradé Terre → Espace ---
st.markdown(
    """
    <style>
    header[data-testid="stHeader"] {display: none !important;}
    [data-testid="stToolbar"] {display: none !important;}
    #MainMenu {visibility: hidden !important;}
    .viewerBadge_container__1QSob {display: none !important;}
    .block-container {padding-top: 0rem !important;}

    .stApp {
        background: linear-gradient(to top, #00bfff 0%, #001848 60%, #000000 100%) !important;
        color: white !important;
    }

    body {color: white !important;}

    h1 {
        font-size: 1.8rem !important;
        text-align: center;
        margin-top: 0.3em;
        margin-bottom: 0.4em;
        color: #fff;
        font-weight: 700;
    }

    .stMetric {
        text-align: center !important;
        margin-top: -0.5em !important;
        margin-bottom: 0.5em !important;
    }

    [data-testid="stMetricValue"] {
        font-size: 2rem !important;
        color: #00d4ff !important;
        font-weight: bold;
    }

    .stPlotlyChart {
        height: 65vh !important;
        width: 100% !important;
    }

    @media (max-width: 768px) {
        h1 {font-size: 1.4rem !important;}
        [data-testid="stMetricValue"] {font-size: 1.6rem !important;}
        .stPlotlyChart {height: 70vh !important;}
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --- Connexion Google Sheets ---
@st.cache_resource
def get_client():
    creds_dict = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
    creds = Credentials.from_service_account_info(
        creds_dict,
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ],
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
        sheet.clear()
        sheet.append_row(["progress", "history"])
        sheet.append_row([
            int(data.get("progress", 0)),
            json.dumps(data.get("history", []), ensure_ascii=False),
        ])
    except Exception as e:
        st.error(f"❌ Impossible d'enregistrer sur Google Sheets : {e}")

# --- Charger les données ---
data = load_data()
progress = data.get("progress", 0)
history = data.get("history", [])

# --- Titre ---
st.markdown("<h1>🚀 Fusée vers la tablette — Progression annuelle</h1>", unsafe_allow_html=True)
st.metric(label="Altitude actuelle", value=f"{progress} %")

# --- Graphique de progression ---
try:
    if not history:
        history = []

    if history:
        df = pd.DataFrame(history)
        df["delta"] = df["delta"].astype(int)

        def parse_school_date(date_str):
            try:
                d = datetime.datetime.strptime(date_str, "%d/%m %H:%M")
                today = datetime.datetime.now()
                school_year = today.year if d.month >= 9 else today.year - 1
                return d.replace(year=school_year)
            except Exception:
                return pd.NaT

        df["time"] = df["time"].apply(parse_school_date)
        df = df.dropna(subset=["time"]).sort_values("time")

        altitude, total = [], 0
        for _, row in df.iterrows():
            total += row["delta"] if row["action"] == "up" else -row["delta"]
            altitude.append(max(0, total))
        df["altitude"] = altitude

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

        # --- Graphique ---
        fig = go.Figure()

        # Ligne de progression
        fig.add_trace(go.Scatter(
            x=df_interp["date"],
            y=df_interp["altitude"],
            mode="lines",
            line=dict(color="deepskyblue", width=4),
            name="",
        ))

        # Ligne de Karman
        fig.add_hline(y=100, line=dict(color="red", dash="dot"))
        fig.add_annotation(
            xref="paper", x=0.5, y=105,
            text="🌌 Ligne de Kármán (100%)",
            showarrow=False,
            font=dict(size=13, color="red"),
        )

        # Fusée (sans flamme)
        fig.add_trace(go.Scatter(
            x=[df_interp["date"].iloc[-1]],
            y=[fus_alt],
            mode="text",
            text=["🚀"],
            textfont=dict(size=50),
            textposition="middle center",
            name="",
        ))

        # Nettoyage (supprimer les traces vides)
        for trace in list(fig.data):
            if hasattr(trace, "text") and (trace.text is None or trace.text == [None] or trace.text == ["undefined"]):
                fig.data = tuple(t for t in fig.data if t is not trace)

        # Mise en page finale
        fig.update_layout(
            xaxis_title=None,
            yaxis_title=None,
            yaxis=dict(range=[0, max(130, fus_alt + 10)], color="white"),
            xaxis=dict(color="white"),
            showlegend=False,
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white"),
            margin=dict(l=60, r=30, t=40, b=50),
        )

        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        st.markdown("### 🧭 Altitude actuelle :")
        st.metric(label="Progression", value=f"{progress} %")

        st.markdown("## 📜 Historique des actions")
        for h in history:
            st.markdown(f"🕓 **{h['time']}** — *{h['action']} de {h['delta']} %* : {h['reason']}")

    else:
        st.info("Aucune trajectoire à afficher 🚀")

except Exception as e:
    st.error(f"❌ Erreur lors de l'affichage du graphique : {e}")

# --- Mode admin ---
st.markdown("---")
st.markdown("### 🔐 Panneau de commande (admin)")

if "admin" not in st.session_state:
    st.session_state.admin = False

with st.expander("🔧 Contrôle de la fusée", expanded=False):
    token_input = st.text_input("Entre le code secret :", type="password")
    if st.button("Activer le mode admin"):
        if "ADMIN_TOKEN" in st.secrets and token_input == st.secrets["ADMIN_TOKEN"]:
            st.session_state.admin = True
            st.success("Mode admin activé ✅")
        else:
            st.error("Code invalide ❌")

if st.session_state.admin:
    st.markdown("#### ⚙️ Modifier la progression")
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

            # ✅ Rafraîchir le cache et relancer
            st.cache_data.clear()
            st.success("Progression mise à jour ✅")
            st.rerun()
        else:
            st.info("Aucun changement détecté.")
