import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
from logic import call_sim_api

DB_FILE = "database.json"

# טעינת נתונים
def load_data():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"sims": [], "auth": {"user": "", "pass": ""}}

def save_data(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

st.set_page_config(page_title="ניהול סימים נטפרי", layout="wide")
st.title("📱 מערכת ניהול ובדיקת סימים")

data = load_data()

# סרגל צד להגדרות
with st.sidebar:
    st.header("🔑 הגדרות API")
    data['auth']['user'] = st.text_input("שם משתמש", data['auth']['user'])
    data['auth']['pass'] = st.text_input("סיסמה", data['auth']['pass'], type="password")
    if st.button("שמור הגדרות"):
        save_data(data)
        st.success("הגדרות נשמרו!")

# הוספת סים
with st.expander("➕ הוספת סים חדש לרשימה"):
    col1, col2 = st.columns(2)
    with col1:
        new_iccid = st.text_input("מספר סים (ICCID)")
    with col2:
        new_shop = st.text_input("שם חנות")
    if st.button("הוסף לרשימה"):
        if new_iccid and new_shop:
            data['sims'].append({
                "iccid": new_iccid, 
                "shop": new_shop, 
                "date_added": datetime.now().strftime("%Y-%m-%d %H:%M")
            })
            save_data(data)
            st.rerun()

# הצגת רשימה ובדיקה מיידית
st.header("📋 רשימת סימים מעקב")
if data['sims']:
    df = pd.DataFrame(data['sims'])
    st.table(df)
    
    selected_iccid = st.selectbox("בחר סים לבדיקה מיידית", [s['iccid'] for s in data['sims']])
    if st.button("בדוק עכשיו"):
        with st.spinner("בודק..."):
            status, plan, ok = call_sim_api(selected_iccid, data['auth']['user'], data['auth']['pass'])
            color = "green" if ok else "red"
            st.markdown(f"**תוצאה:** :{color}[{status}] | **תוכנית:** {plan}")
else:
    st.info("אין סימים ברשימה כרגע.")

# דוחות
st.header("📊 דוחות היסטוריים")
report_files = [f for f in os.listdir(".") if f.startswith("report_") and f.endswith(".csv")]
if report_files:
    selected_report = st.selectbox("בחר דוח להורדה", report_files)
    with open(selected_report, "rb") as file:
        st.download_button("📥 הורד קובץ אקסל/CSV", file, file_name=selected_report)
