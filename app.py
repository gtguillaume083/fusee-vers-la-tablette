import streamlit as st
import json
import gspread
import pandas as pd
import datetime
import plotly.graph_objects as go
from google.oauth2.service_account import Credentials

# --- Configuration de la page ---
st.set_page_config(page_title="🚀 Fusée vers la tablette", layout="wide")

# 🌑 --- Thème sombre + version mobile portrait optimisée ---
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

    h1 {
        font-size: 1.8rem !important;
        color: #fff !important;
        text-align: center;
        margin-top: 0.3em;
        margin-bottom: 0.4em;
        line-height: 1.2;
    }

    h2, h3, h4 {
        color: #fff !important;
    }

    .stMetric {
        text-align: center !important;
        margin-top: -0.5em !important;
        margin-bottom: 0.5em !important;
    }

    [data-testid="stMetricLabel"] {
        font-size: 0.9rem !important;
        color: #ccc !important;
    }

    [data-testid="stMetricValue"] {
        font-size: 2rem !important;
        color: #00bfff !important;
        font-weight: bold;
    }

    .stPlotlyChart {
        height: 55vh !important;
        width: 100% !important;
    }

    .block-container {
        padding-top: 0.5rem !important;
        padding-bottom: 1rem !important;
        max-width: 95vw !important;
    }

    /* 📱 Version portrait : design resserré, lisible et centré */
    @media (max-width: 768px) {
        h1 {
            font-size: 1.4rem !important;
            margin-bottom: 0.2em !important;
        }
        [data-testid="stMetricValue"] {
            font-size: 1.6rem !important;
        }
        .stPlotlyChart {
            height: 60vh !important;
        }
        .block-container {
            padding-top: 0.2rem !important;
            padding-bottom: 0.5rem !important;
        }
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
        sheet.clear()
        sheet.append_row(["progress", "history"])
        sheet.append_row([
            int(data.get("progress", 0)),
            json.dumps(data.get("history", []), ensure_ascii=False)
        ])
    except Exception as e:
        st.error(f"❌ Impossible d'enregistrer sur Google Sheets : {e}")

# --- Charger les données ---
data = load_data()
progress = data.get("progress", 0)
history = data.get("history", [])

# --- Titre et altitude ---
st.markdown("<h1>🚀 Fusée vers la tablette — Progression annuelle</h1>", unsafe_allow_html=True)
st.metric(label="Altitude actuelle", value=f"{progress} %")

# --- Graphique de progression ---
try:
    if history is None:
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
        df = df.dropna(subset=["time"])
        df = df.sort_values("time")

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

        # Bande "espace"
        fig.add_shape(
            type="rect",
            xref="paper", x0=0, x1=1,
            yref="y", y0=100, y1=130,
            fillcolor="rgba(0, 0, 120, 0.25)",
            line=dict(width=0),
            layer="below"
        )

        # Ligne de progression
        fig.add_trace(go.Scatter(
            x=df_interp["date"],
            y=df_interp["altitude"],
            mode="lines",
            line=dict(color="deepskyblue", width=4),
            name="Progression"
        ))

        # Ligne de Karman
        fig.add_hline(y=100, line=dict(color="red", dash="dot"))
        fig.add_annotation(
            xref="paper", x=1.02, y=105,
            text="🌌 Ligne de Karman (100%)",
            showarrow=False,
            font=dict(size=12, color="red")
        )

        # Fusée + flamme
        fig.add_trace(go.Scatter(
            x=[df_interp["date"].iloc[-1]],
            y=[fus_alt],
            mode="text",
            text=["🚀"],
            textfont=dict(size=50),
            textposition="middle center",
            name="Fusée"
        ))
        fig.add_trace(go.Scatter(
            x=[df_interp["date"].iloc[-1]],
            y=[fus_alt - 5],
            mode="text",
            text=["🔥"],
            textfont=dict(size=28),
            textposition="top center",
            name="Flamme"
        ))

        # Design sombre + compact
        fig.update_layout(
            title="Trajectoire de la fusée",
            xaxis_title="Temps (du 1er septembre au 30 juin)",
            yaxis_title="Altitude (%)",
            yaxis=dict(range=[0, max(130, fus_alt + 10)], color="white"),
            xaxis=dict(color="white"),
            width=None,
            height=450,
            plot_bgcolor="#000",
            paper_bgcolor="#000",
            font=dict(color="white"),
            margin=dict(l=40, r=40, t=40, b=40)
        )

        st.plotly_chart(fig, use_container_width=True)

        st.markdown("### 📜 Historique des actions")
        for h in history:
            st.markdown(
                f"🕓 **{h['time']}** — *{h['action']} de {h['delta']} %* : {h['reason']}"
            )
    else:
        st.info("Aucune trajectoire à afficher 🚀")

except Exception as e:
    st.error(f"❌ Erreur lors de l'affichage du graphique : {e}")

# --- Mode administrateur ---
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

            # ✅ Rafraîchir immédiatement les données mises en cache
            st.cache_data.clear()
            st.success("Progression mise à jour ✅")

            # ✅ Relancer le script (recharge depuis la Sheet)
            st.rerun()
        else:
            st.info("Aucun changement détecté.")
