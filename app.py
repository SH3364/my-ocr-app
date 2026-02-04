import streamlit as st
import pandas as pd
import json
import os
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import time

# --- הגדרות ליבה ---
DB_FILE = "sim_database.json"
TARGET_PLAN = "Prepaid Refills - Talk Only - 4G HD"
# כתובת ה-API הרשמית לחיפוש מנויים
SOAP_URL = "https://api.wirelessprovisioning.com/publish/MdnServices.asmx"

# --- ניהול נתונים ---
def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: pass
    return {"sims": [], "auth": {"user": "", "pass": ""}}

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# --- פונקציית בדיקת API (SearchSubscribers) ---
def check_sim_api(iccid, user, password):
    if not user or not password:
        return "שגיאת הגדרות", "חסר שם משתמש/סיסמה בתפריט הצד", False, ""

    # בניית גוף ה-XML עבור SearchSubscribers
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
        response = requests.post(SOAP_URL, data=soap_body, headers=headers, timeout=25)
        
        if response.status_code != 200:
            return f"שגיאת שרת ({response.status_code})", "השרת לא הגיב כמצופה", False, response.text

        # ניתוח ה-XML
        root = ET.fromstring(response.text)
        
        # בדיקה אם נמצאו תוצאות (TotalCount)
        total_count = "0"
        for elem in root.iter():
            if "TotalCount" in elem.tag:
                total_count = elem.text
                break
        
        if total_count == "0":
            return "פנוי (Available)", "הסים טרם הופעל במערכת", True, response.text

        # שליפת שם התוכנית
        found_plan = "לא זוהתה תוכנית"
        for elem in root.iter():
            tag_name = elem.tag.split('}')[-1]
            if tag_name in ["PlanName", "RatePlanName", "RatePlan"]:
                if elem.text:
                    found_plan = elem.text.strip()
                    break

        is_correct = (found_plan == TARGET_PLAN)
        status = "תקין ✅" if is_correct else "תוכנית לא תואמת ❌"
        
        return status, found_plan, is_correct, response.text

    except Exception as e:
        return "שגיאת תקשורת", str(e), False, ""

# --- עיצוב האתר ---
st.set_page_config(page_title="ניהול סימים - WP", layout="wide")
data = load_db()

# תפריט צד
with st.sidebar:
    st.header("🔑 הגדרות התחברות")
    st.markdown("הזן את פרטי ה-API שקיבלת מ-Wireless Provisioning:")
    api_user = st.text_input("שם משתמש (User)", data['auth'].get('user', ''))
    api_pass = st.text_input("סיסמה (Password)", data['auth'].get('pass', ''), type="password")
    
    if st.button("שמור הגדרות"):
        data['auth'] = {"user": api_user, "pass": api_pass}
        save_db(data)
        st.success("ההגדרות נשמרו בהצלחה!")

# תוכן מרכזי
st.title("📱 מערכת מעקב ובדיקת סימים")

tab1, tab2, tab3 = st.tabs(["🔍 בדיקה בזמן אמת", "📋 ניהול רשימה", "📊 דוחות ובדיקה יומית"])

# טאב 1: בדיקה מיידית
with tab1:
    st.subheader("בדיקת סים בודד")
    single_iccid = st.text_input("הכנס מספר ICCID לבדיקה:")
    debug = st.checkbox("הצג תשובה גולמית מהשרת (לפתרון תקלות)")
    
    if st.button("בדוק עכשיו 🚀"):
        with st.spinner("מתחבר לשרת..."):
            status, plan, ok, raw = check_sim_api(single_iccid, data['auth']['user'], data['auth']['pass'])
            if "פנוי" in status:
                st.info(f"💡 **תוצאה:** {status} | ה-API לא מצא מנוי פעיל על המספר הזה.")
            elif ok:
                st.success(f"✅ **תוצאה:** {status} | **תוכנית:** {plan}")
            else:
                st.error(f"⚠️ **תוצאה:** {status} | **תוכנית קיימת:** {plan}")
            
            if debug:
                st.divider()
                st.code(raw, language="xml")

# טאב 2: ניהול רשימה
with tab2:
    st.subheader("הוספת סימים למעקב")
    c1, c2 = st.columns(2)
    with c1:
        new_iccid = st.text_input("ICCID להוספה")
    with c2:
        new_shop = st.text_input("שם חנות")
    
    if st.button("הוסף לרשימה"):
        if new_iccid:
            data['sims'].append({
                "iccid": new_iccid,
                "shop": new_shop,
                "date": datetime.now().strftime("%d/%m/%Y")
            })
            save_db(data)
            st.rerun()

    if data['sims']:
        st.write("---")
        df = pd.DataFrame(data['sims'])
        st.dataframe(df, use_container_width=True)
        if st.button("מחק את כל הרשימה"):
            data['sims'] = []
            save_db(data)
            st.rerun()

# טאב 3: בדיקה מרוכזת
with tab3:
    st.subheader("בדיקה יומית של כל המאגר")
    if st.button("הפעל בדיקה לכל הרשימה"):
        if not data['sims']:
            st.warning("הרשימה ריקה!")
        else:
            results = []
            progress = st.progress(0)
            for i, sim in enumerate(data['sims']):
                status, plan, ok, _ = check_sim_api(sim['iccid'], data['auth']['user'], data['auth']['pass'])
                results.append({
                    "תאריך": datetime.now().strftime("%d/%m/%Y"),
                    "ICCID": sim['iccid'],
                    "חנות": sim['shop'],
                    "סטטוס": status,
                    "תוכנית": plan
                })
                progress.progress((i + 1) / len(data['sims']))
                time.sleep(0.3)
            
            res_df = pd.DataFrame(results)
            st.table(res_df)
            st.download_button("📥 הורד דוח CSV", res_df.to_csv(index=False).encode('utf-8-sig'), "report.csv")
