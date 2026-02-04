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

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"sims": [], "auth": {"user": "", "pass": ""}}

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def call_api(iccid, user, password):
    if not user or not password:
        return "שגיאה", "חסר שם משתמש/סיסמה בהגדרות", False

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
        response = requests.post(SOAP_URL, data=soap_body, headers=headers, timeout=20)
        # הסרת ה-Namespace כדי להקל על החיפוש ב-XML
        xml_content = response.text
        root = ET.fromstring(xml_content)
        
        # חיפוש TotalCount (כדי לדעת אם הסים פנוי)
        total_count = "0"
        for elem in root.iter():
            if "TotalCount" in elem.tag:
                total_count = elem.text
                break
        
        if total_count == "0":
            return "פנוי (Available)", "הסים טרם הופעל", True

        # חיפוש שם התוכנית בתוך התוצאות
        current_plan = "לא ידוע"
        possible_tags = ["PlanName", "RatePlanName", "RatePlan"]
        
        for elem in root.iter():
            if any(tag in elem.tag for tag in possible_tags):
                if elem.text and len(elem.text) > 2:
                    current_plan = elem.text
                    break

        is_correct = (current_plan.strip() == TARGET_PLAN)
        status = "תקין - תוכנית נכונה" if is_correct else "תוכנית לא תואמת"
        return status, current_plan, is_correct

    except Exception as e:
        return "שגיאת תקשורת", str(e), False

# --- ממשק Streamlit ---
st.set_page_config(page_title="בדיקת סימים WP", layout="wide")
db = load_db()

with st.sidebar:
    st.header("⚙️ הגדרות API")
    u = st.text_input("שם משתמש API", db['auth'].get('user', ''))
    p = st.text_input("סיסמה API", db['auth'].get('pass', ''), type="password")
    if st.button("שמור הגדרות"):
        db['auth'] = {"user": u, "pass": p}
        save_db(db)
        st.success("נשמר!")

st.title("📱 מערכת מעקב סימים Wireless Provisioning")

tab1, tab2, tab3 = st.tabs(["🔍 בדיקה בזמן אמת", "📋 ניהול רשימה", "📂 דוחות"])

with tab1:
    st.subheader("בדיקת סים מיידית")
    quick_iccid = st.text_input("הכנס ICCID לבדיקה:")
    if st.button("בדוק עכשיו 🚀"):
        with st.spinner("מתחבר לשרת..."):
            status, plan, ok = call_api(quick_iccid, db['auth']['user'], db['auth']['pass'])
            if "פנוי" in status:
                st.info(f"**סטטוס:** {status} | **מידע:** {plan}")
            elif ok:
                st.success(f"**סטטוס:** {status} | **תוכנית:** {plan}")
            else:
                st.error(f"**סטטוס:** {status} | **תוכנית קיימת:** {plan}")

with tab2:
    st.subheader("הוספת סימים למעקב קבוע")
    col1, col2 = st.columns(2)
    with col1:
        new_iccid = st.text_input("ICCID")
    with col2:
        new_shop = st.text_input("חנות")
    
    if st.button("הוסף למאגר"):
        if new_iccid:
            db['sims'].append({"iccid": new_iccid, "shop": new_shop, "added": datetime.now().strftime("%d/%m/%Y")})
            save_db(db)
            st.rerun()

    if db['sims']:
        st.write("---")
        df = pd.DataFrame(db['sims'])
        st.table(df)
        if st.button("מחק הכל"):
            db['sims'] = []
            save_db(db)
            st.rerun()

with tab3:
    st.subheader("בדיקה יומית ודוחות")
    if st.button("הרץ בדיקה על כל הרשימה"):
        if not db['sims']:
            st.warning("הרשימה ריקה!")
        else:
            all_res = []
            bar = st.progress(0)
            for i, sim in enumerate(db['sims']):
                status, plan, ok = call_api(sim['iccid'], db['auth']['user'], db['auth']['pass'])
                all_res.append({
                    "תאריך": datetime.now().strftime("%d/%m/%Y"),
                    "חנות": sim['shop'],
                    "ICCID": sim['iccid'],
                    "תוצאה": status,
                    "תוכנית": plan
                })
                bar.progress((i + 1) / len(db['sims']))
                time.sleep(0.3)
            
            final_df = pd.DataFrame(all_res)
            st.dataframe(final_df)
            st.download_button("הורד דוח CSV", final_df.to_csv(index=False).encode('utf-8-sig'), "report.csv", "text/csv")
