# --- Google Sheets persistence (remplacer load_data/save_data existantes) ---
import json
import gspread
from google.oauth2.service_account import Credentials

def get_sheet():
    # st.secrets["GOOGLE_CREDENTIALS"] contient ton JSON (string)
    creds_dict = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
    creds = Credentials.from_service_account_info(creds_dict)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(st.secrets["SHEET_ID"]).sheet1
    return sheet

def load_data():
    try:
        sheet = get_sheet()
        # On lit toutes les lignes sous forme de dicts si la 1ère ligne est en-tête
        records = sheet.get_all_records()
        if records and isinstance(records, list) and len(records) >= 1:
            # on suppose que la première ligne contient progress et history (history en JSON)
            r = records[0]
            progress = int(r.get("progress", 0))
            history_json = r.get("history", "[]")
            try:
                history = json.loads(history_json)
            except:
                history = []
            return {"progress": progress, "history": history}
        else:
            # si la feuille est vide, on initialise
            return {"progress": 0, "history": []}
    except Exception as e:
        # En cas d'erreur de connexion, on renvoie un fallback local
        st.error("Erreur connexion Google Sheets (voir logs si problème persiste).")
        return {"progress": 0, "history": []}

def save_data(data):
    try:
        sheet = get_sheet()
        # Réécrire proprement : en-tête puis ligne avec progress et history (JSON)
        sheet.clear()
        sheet.append_row(["progress", "history"])
        sheet.append_row([int(data.get("progress", 0)), json.dumps(data.get("history", []), ensure_ascii=False)])
    except Exception as e:
        st.error("Impossible d'enregistrer sur Google Sheets — vérifie les permissions et les secrets.")
        # on ne lève pas pour que l'app reste utilisable
