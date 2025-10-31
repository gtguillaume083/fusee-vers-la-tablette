# --- IMPORTS ---
import streamlit as st
import json
import gspread
import pandas as pd
import datetime as dt
from datetime import datetime
from google.oauth2.service_account import Credentials
import altair as alt

st.set_page_config(page_title="🚀 Fusée vers la tablette", layout="wide", page_icon="🚀")

# --- TITRE ---
st.title("🚀 Fusée vers la tablette — Progression annuelle")

# --- GOOGLE SHEETS CONNECT ---
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
            progress = int(r.get("progress", 0))
            history_json = r.get("history", "[]")
            try:
                history = json.loads(history_json)
            except:
                history = []
            return {"progress": progress, "history": history}
        else:
            return {"progress": 0, "history": []}
    except Exception as e:
        st.error("Erreur connexion Google Sheets : " + str(e))
        return {"progress": 0, "history": []}

def save_data(data):
    try:
        sheet = get_sheet()
        sheet.clear()
        sheet.append_row(["progress", "history"])
        sheet.append_row([int(data.get("progress", 0)), json.dumps(data.get("history", []), ensure_ascii=False)])
    except Exception as e:
        st.error("Impossible d'enregistrer sur Google Sheets : " + str(e))


# --- MODE ADMIN ---
st.sidebar.markdown("### 🔑 Mode administrateur")
admin_token = st.sidebar.text_input("Token admin", type="password")
ADMIN_SECRET = st.secrets.get("ADMIN_TOKEN", "")

is_admin = admin_token == ADMIN_SECRET
if is_admin:
    st.sidebar.success("Mode admin activé ✅")
else:
    st.sidebar.info("Mode lecture seule 👀")


# --- CHARGEMENT DES DONNÉES ---
data = load_data()
history = data.get("history", [])

# --- SI HISTORIQUE EXISTE, ON LE TRANSFORME ---
if history:
    df = pd.DataFrame(history)
else:
    df = pd.DataFrame(columns=["time", "action", "delta", "reason"])

# --- DATES ANNÉE SCOLAIRE ---
now = datetime.now()
start = dt.datetime(now.year if now.month >= 9 else now.year - 1, 9, 1)
end = dt.datetime(start.year + 1, 6, 30)

# --- FORMAT DES DATES ---
if "time" in df.columns and not df.empty:
    df["time"] = pd.to_datetime(df["time"], format="%d/%m %H:%M", errors="coerce")
    df["time"] = df["time"].apply(
        lambda d: d.replace(year=start.year if d and d.month >= 9 else start.year + 1)
        if pd.notnull(d) else pd.NaT
    )

# --- CALCUL CUMULÉ DE L’ALTITUDE ---
if not df.empty:
    altitude = 0
    cumulative = []
    for _, row in df.iterrows():
        act = row.get("action", "")
        delta = row.get("delta", 0)
        if act == "up":
            altitude += delta
        elif act == "down":
            altitude -= delta
        cumulative.append(altitude)
    df["altitude"] = cumulative

    # Interpolation sur toute la période
    all_dates = pd.date_range(start, end, freq="D")
    df_interp = pd.DataFrame({"time": all_dates})
    df_interp = df_interp.merge(df[["time", "altitude"]], on="time", how="left")
    df_interp["altitude"] = df_interp["altitude"].interpolate().fillna(method="bfill")

    # Position de la fusée à la date actuelle
    today = datetime.now()
    fus_alt = df_interp.loc[df_interp["time"] <= today, "altitude"].iloc[-1]

    # --- GRAPHIQUE ALTITUDE ---
    base = (
        alt.Chart(df_interp)
        .mark_line(color="#00c0ff", strokeWidth=3)
        .encode(
            x=alt.X("time:T", title="Temps (année scolaire)"),
            y=alt.Y("altitude:Q", title="Altitude (%)")
        )
        .properties(height=400, width="container")
    )

    karman = (
        alt.Chart(pd.DataFrame({"y": [100]}))
        .mark_rule(strokeDash=[5, 5], color="red")
        .encode(y="y:Q")
    )

    karman_label = (
        alt.Chart(pd.DataFrame({"y": [100], "label": ["Ligne de Kármán (100%)"]}))
        .mark_text(align="left", dx=5, dy=-5, color="red")
        .encode(y="y:Q", text="label:N")
    )

    rocket = (
        alt.Chart(pd.DataFrame({"time": [today], "altitude": [fus_alt]}))
        .mark_point(shape="rocket", size=200, color="pink")
        .encode(x="time:T", y="altitude:Q")
    )

    st.altair_chart(base + karman + karman_label + rocket, use_container_width=True)

else:
    st.info("Aucune trajectoire à afficher 🚀")


# --- MODE ADMIN : AJOUT / RETRAIT ---
if is_admin:
    st.sidebar.markdown("### 🧭 Mettre à jour la progression")

    action = st.sidebar.selectbox("Action", ["up", "down"])
    delta = st.sidebar.number_input("Variation (%)", min_value=1, max_value=50, step=1)
    reason = st.sidebar.text_input("Raison", placeholder="Motif du changement")

    if st.sidebar.button("Valider"):
        new_entry = {
            "time": datetime.now().strftime("%d/%m %H:%M"),
            "action": action,
            "delta": delta,
            "reason": reason if reason else "(non précisé)"
        }
        history.append(new_entry)
        total = sum([e["delta"] if e["action"] == "up" else -e["delta"] for e in history])
        data = {"progress": total, "history": history}
        save_data(data)
        st.sidebar.success("Progression mise à jour ✅")
        st.rerun()


# --- HISTORIQUE ---
st.markdown("### 📜 Historique des actions")
if history:
    for h in reversed(history):
        st.write(f"🕓 {h['time']} — **{h['action']} {h['delta']} %** : {h['reason']}")
else:
    st.write("Aucune action enregistrée.")
