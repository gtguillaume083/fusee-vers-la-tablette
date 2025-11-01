import streamlit as st
import json
import gspread
import pandas as pd
import datetime
import plotly.graph_objects as go
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="🚀 Fusée vers la tablette", layout="wide")

# --- Connexion Google Sheets (avec cache) ---
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

st.title("🚀 Fusée vers la tablette — Progression annuelle")

# --- Mode administrateur ---
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

# --- Altitude actuelle ---
st.subheader("Altitude actuelle :")
st.metric(label="Progression", value=f"{progress} %")

# --- Interface administrateur ---
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

# --- Graphique de progression ---
try:
    if history is None:
        history = []

    if history:
        df = pd.DataFrame(history)
        df["delta"] = df["delta"].astype(int)

        # 🔧 Convertir les dates (année scolaire)
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

        # 🧮 Calcul cumulatif
        altitude, total = [], 0
        for _, row in df.iterrows():
            total += row["delta"] if row["action"] == "up" else -row["delta"]
            altitude.append(max(0, total))
        df["altitude"] = altitude

        # 📆 Année scolaire (septembre → juin)
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

        # 🌌 Bande "espace" au-dessus de 100 %
        fig.add_shape(
            type="rect",
            xref="paper", x0=0, x1=1,
            yref="y", y0=100, y1=130,
            fillcolor="rgba(0, 0, 80, 0.15)",
            line=dict(width=0),
            layer="below"
        )

        # 🌤 Ligne de progression
        fig.add_trace(go.Scatter(
            x=df_interp["date"],
            y=df_interp["altitude"],
            mode="lines",
            line=dict(color="skyblue", width=4),
            name="Progression"
        ))

        # 🌌 Ligne de Karman (100 %)
        fig.add_hline(y=100, line=dict(color="red", dash="dot"), name="Ligne de Karman")
        fig.add_annotation(
            xref="paper", x=1.02, y=105,
            text="🌌 Ligne de Karman (100%)",
            showarrow=False,
            font=dict(size=12, color="red")
        )

        # 🚀 Fusée
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
            yaxis=dict(range=[0, max(130, fus_alt + 10)]),
            width=900,
            height=500,
            template="plotly_white",
            plot_bgcolor="white"
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
    else:
        st.info("Aucune trajectoire à afficher 🚀")

except Exception as e:
    st.error(f"❌ Erreur lors de l'affichage du graphique : {e}")
