import streamlit as st
import json, time, datetime
import pandas as pd
import altair as alt
import gspread
from google.oauth2.service_account import Credentials

# --- CONFIG ---
st.set_page_config(page_title="🚀 Fusée vers la tablette", layout="centered")
ADMIN_TOKEN = "monmotdepasse2025"

# --- GOOGLE SHEETS ---
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
        if records:
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

# --- CHARGEMENT ---
data = load_data()
progress = data["progress"]
history = data["history"]

st.title("🚀 Fusée vers la tablette — Progression annuelle")

# --- HISTORIQUE EN COURBE ---
if history:
    df = pd.DataFrame(history)
    df["delta"] = df.get("delta", df.get("value", 0))
    df["time"] = pd.to_datetime(df["time"], errors="coerce")

    # ajoute l'année actuelle si absente
    df["time"] = df["time"].apply(
        lambda t: pd.Timestamp(f"{datetime.date.today().year}-{t.strftime('%m-%d %H:%M')}")
        if pd.notna(t) and t.year == 1900 else t
    )
    df = df.dropna(subset=["time"]).sort_values("time")

    if df.empty:
        df = pd.DataFrame([{"time": pd.Timestamp(datetime.date.today()), "altitude": 0}])
        fus_alt = 0
    else:
        altitude = 0
        alts = []
        for _, row in df.iterrows():
            altitude += row["delta"] if row["action"] == "up" else -row["delta"]
            alts.append(max(0, altitude))
        df["altitude"] = alts
        fus_alt = df["altitude"].iloc[-1]
else:
    df = pd.DataFrame([{"time": pd.Timestamp(datetime.date.today()), "altitude": 0}])
    fus_alt = 0

# --- DATES ÉCOLE ---
today = datetime.date.today()
start_year = today.year if today.month >= 9 else today.year - 1
start = datetime.date(start_year, 9, 1)
end = datetime.date(start_year + 1, 6, 30)

if len(df) == 1:
    df = pd.concat([
        pd.DataFrame([{"time": pd.Timestamp(start), "altitude": 0}]),
        df
    ])

# --- FONCTION GRAPHIQUE ---
def afficher_graphique(altitude_actuelle):
    base = alt.Chart(df).mark_line(color="#00bfff", strokeWidth=3).encode(
        x=alt.X("time:T", title="Temps (année scolaire)", scale=alt.Scale(domain=[start, end])),
        y=alt.Y("altitude:Q", title="Altitude (%)", scale=alt.Scale(domain=[0, 150]))
    )

    karman_line = alt.Chart(pd.DataFrame({"y": [100]})).mark_rule(
        color="red", strokeDash=[6, 4], strokeWidth=2
    ).encode(y="y")

    karman_label = alt.Chart(pd.DataFrame({"y": [100], "x": [start]})).mark_text(
        align="left", dx=10, color="red", fontWeight="bold"
    ).encode(x="x", y="y", text=alt.value("Ligne de Kármán (100 %)"))

    rocket = alt.Chart(pd.DataFrame({
        "x": [df["time"].iloc[-1]],
        "y": [altitude_actuelle]
    })).mark_text(text="🚀", size=30).encode(x="x", y="y")

    return (base + karman_line + karman_label + rocket).properties(width=800, height=400)
import json

# --- CHARGEMENT DU JSON ---
# Lecture du contenu brut depuis Google Sheets
history_raw = data[1] if isinstance(data, list) and len(data) > 1 else "[]"

try:
    history = json.loads(history_raw)
except json.JSONDecodeError:
    history = []

# Conversion en DataFrame
if history:
    df = pd.DataFrame(history)
else:
    df = pd.DataFrame(columns=["time", "action", "delta", "reason"])

# Normalisation de la colonne "time"
if "time" in df.columns:
    df["time"] = pd.to_datetime(df["time"], format="%d/%m %H:%M", errors="coerce")
    # On ajoute l'année scolaire en fonction du mois
    df["time"] = df["time"].apply(
        lambda d: d.replace(year=start.year if d.month >= 9 else start.year + 1)
        if pd.notnull(d) else pd.NaT
    )
else:
    st.warning("Aucune donnée d'historique trouvée dans la feuille.")

# --- CALCUL CUMULÉ DE L'ALTITUDE ---
if not df.empty:
    # On convertit les variations "delta" en altitude cumulée dans le temps
    altitude = 0
    cumulative = []
    for _, row in df.iterrows():
        if row["action"] == "up":
            altitude += row["delta"]
        elif row["action"] == "down":
            altitude -= row["delta"]
        cumulative.append(altitude)
    df["altitude"] = cumulative


# --- ANIMATION TEMPORELLE ---
graph_placeholder = st.empty()

if not df.empty:
    # Recrée un axe temporel complet (du 1er sept à aujourd’hui)
    full_time = pd.date_range(start=start, end=today, freq="D")
    df_full = pd.DataFrame({"time": full_time})
    df_interp = pd.merge_asof(
        df_full.sort_values("time"),
        df[["time", "altitude"]].sort_values("time"),
        on="time",
        direction="backward"
    )

    # Si la première altitude est NaN → on lui met la première valeur connue
    first_alt = df["altitude"].iloc[0]
    df_interp["altitude"] = df_interp["altitude"].fillna(first_alt)

    # Interpolation linéaire et bornes
    df_interp["altitude"] = df_interp["altitude"].interpolate(method="linear")
    df_interp["altitude"] = df_interp["altitude"].clip(lower=0)

    # 🔥 Ajuste la courbe pour que le dernier point atteigne bien la valeur réelle
    last_val = df_interp["altitude"].iloc[-1]
    scale = progress / last_val if last_val != 0 else 1
    df_interp["altitude"] = df_interp["altitude"] * scale

    # Animation : la fusée avance sur la courbe réelle jusqu’à aujourd’hui
    for i in range(len(df_interp)):
        alt_now = df_interp["altitude"].iloc[i]
        t_now = df_interp["time"].iloc[i]
        sub_df = df_interp.iloc[:i+1]

        base = alt.Chart(sub_df).mark_line(color="#00bfff", strokeWidth=3).encode(
            x=alt.X("time:T", title="Temps (année scolaire)", scale=alt.Scale(domain=[start, end])),
            y=alt.Y("altitude:Q", title="Altitude (%)", scale=alt.Scale(domain=[0, 150]))
        )

        karman_line = alt.Chart(pd.DataFrame({"y": [100]})).mark_rule(
            color="red", strokeDash=[6, 4], strokeWidth=2
        ).encode(y="y")

        karman_label = alt.Chart(pd.DataFrame({"y": [100], "x": [start]})).mark_text(
            align="left", dx=10, color="red", fontWeight="bold"
        ).encode(x="x", y="y", text=alt.value("Ligne de Kármán (100 %)"))

        rocket = alt.Chart(pd.DataFrame({"x": [t_now], "y": [alt_now]})).mark_text(
            text="🚀", size=30
        ).encode(x="x", y="y")

        chart = (base + karman_line + karman_label + rocket).properties(width=800, height=400)
        graph_placeholder.altair_chart(chart, use_container_width=True)
        time.sleep(0.05)
else:
    st.warning("Aucune trajectoire à afficher 🚀")




# --- HISTORIQUE ---
st.subheader("📜 Historique des actions")
if history:
    for h in history[:10]:
        st.write(f"🕓 {h.get('time', '?')} — **{h.get('action', '?')} {h.get('delta', 0)} %** : {h.get('reason', '')}")
else:
    st.info("Aucune action enregistrée.")

# --- ADMIN ---
st.sidebar.header("🔑 Mode administrateur")
admin_input = st.sidebar.text_input("Token admin", type="password")

if admin_input == ADMIN_TOKEN:
    st.sidebar.success("Mode admin activé ✅")
    st.header("🛠 Contrôle de la fusée")
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
        st.toast("🚀 Mise à jour envoyée !")
        time.sleep(1)
        st.rerun()
else:
    st.sidebar.info("Mode lecture seule 👀")
