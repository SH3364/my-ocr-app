import streamlit as st
import pandas as pd
import json
import os
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import time

# --- הגדרות קבועות ---
DB_FILE = "sim_database.json"
SOAP_URL = "https://api.wirelessprovisioning.com/publish/MdnServices.asmx"
TARGET_PLAN = "Prepaid Refills - Talk Only - 4G HD"

# --- פונקציות ניהול נתונים ---
def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"sims": [], "auth": {"user": "", "pass": ""}}

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# --- לוגיקת ה-API ---
def call_api(iccid, user, password):
    soap_body = f"""<?xml version="1.0" encoding="utf-8"?>
    <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
      <soap:Header>
        <AuthenticationHeader xmlns="urn:telispire:MdnServices">
          <Username>{user}</Username>
          <Password>{password}</Password>
        </AuthenticationHeader>
      </soap:Header>
      <soap:Body>
        <SearchSubscribers xmlns="urn:telispire:MdnServices">
          <SearchValue>{iccid}</SearchValue>
          <SearchType>ICCID</SearchType>
        </SearchSubscribers>
      </soap:Body>
    </soap:Envelope>"""

    headers = {
        "Content-Type": "text/xml; charset=utf-8",
        "SOAPAction": "urn:telispire:MdnServices/SearchSubscribers"
    }

    try:
        response = requests.post(SOAP_URL, data=soap_body, headers=headers, timeout=15)
        root = ET.fromstring(response.text)
        ns = {'ns': 'urn:telispire:MdnServices'}
        
        count = root.find(".//ns:TotalCount", ns)
        if count is not None and count.text == "0":
            return "פנוי", "אין קו פעיל", True

        plan = root.find(".//ns:PlanName", ns)
        current_plan = plan.text if plan is not None else "לא ידוע"
        
        is_correct = (current_plan == TARGET_PLAN)
        status = "תקין" if is_correct else "תוכנית לא תואמת"
        return status, current_plan, is_correct
    except Exception as e:
        return "שגיאה", str(e), False

# --- ממשק המשתמש (Streamlit) ---
st.set_page_config(page_title="ניהול סימים", layout="wide")
db = load_db()

# תפריט צד להגדרות
with st.sidebar:
    st.header("⚙️ הגדרות מערכת")
    user_api = st.text_input("שם משתמש API", db['auth'].get('user', ''))
    pass_api = st.text_input("סיסמה API", db['auth'].get('pass', ''), type="password")
    if st.button("שמור הגדרות"):
        db['auth'] = {"user": user_api, "pass": pass_api}
        save_db(db)
        st.success("ההגדרות נשמרו!")

st.title("📱 מערכת מעקב סימים - Wireless Provisioning")

# טאבים לחלוקת האתר
tab1, tab2, tab3 = st.tabs(["ניהול רשימה", "בדיקה בזמן אמת", "דוחות"])

with tab1:
    st.subheader("➕ הוספת סים חדש")
    c1, c2 = st.columns(2)
    with c1:
        new_iccid = st.text_input("מספר סים (ICCID)")
    with c2:
        new_shop = st.text_input("שם חנות")
    
    if st.button("הוסף לרשימה"):
        if new_iccid and new_shop:
            db['sims'].append({
                "iccid": new_iccid,
                "shop": new_shop,
                "date_added": datetime.now().strftime("%d/%m/%Y %H:%M")
            })
            save_db(db)
            st.success(f"הסים {new_iccid} נוסף בהצלחה!")
            st.rerun()

    st.subheader("📋 רשימת הסימים הקיימת")
    if db['sims']:
        df_sims = pd.DataFrame(db['sims'])
        st.dataframe(df_sims, use_container_width=True)
        if st.button("נקה את כל הרשימה"):
            db['sims'] = []
            save_db(db)
            st.rerun()
    else:
        st.info("אין סימים ברשימה.")

with tab2:
    st.subheader("🔍 בדיקת סים ספציפי (בזמן אמת)")
    check_iccid = st.text_input("הכנס ICCID לבדיקה מיידית")
    if st.button("בדוק עכשיו"):
        if not db['auth']['user']:
            st.error("חובה להגדיר שם משתמש וסיסמה בתפריט הצד!")
        else:
            with st.spinner("מבצע בדיקה מול השרת..."):
                status, plan, ok = call_api(check_iccid, db['auth']['user'], db['auth']['pass'])
                if ok:
                    st.success(f"תוצאה: {status} | תוכנית: {plan}")
                else:
                    st.error(f"תוצאה: {status} | תוכנית: {plan}")

with tab3:
    st.subheader("📅 הרצת בדיקה יומית ידנית")
    if st.button("הפעל בדיקה לכל הרשימה"):
        results = []
        progress = st.progress(0)
        for i, sim in enumerate(db['sims']):
            status, plan, ok = call_api(sim['iccid'], db['auth']['user'], db['auth']['pass'])
            results.append({
                "תאריך": datetime.now().strftime("%d/%m/%Y"),
                "ICCID": sim['iccid'],
                "חנות": sim['shop'],
                "סטטוס": status,
                "תוכנית": plan
            })
            progress.progress((i + 1) / len(db['sims']))
            time.sleep(0.5) # מניעת עומס
        
        # שמירת דוח
        df_report = pd.DataFrame(results)
        report_name = f"report_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
        df_report.to_csv(report_name, index=False, encoding="utf-8-sig")
        st.success(f"הבדיקה הסתיימה! נוצר דוח: {report_name}")
        
        st.download_button(
            label="📥 הורד דוח עכשיו (Excel/CSV)",
            data=df_report.to_csv(index=False).encode('utf-8-sig'),
            file_name=report_name,
            mime='text/csv'
        )
