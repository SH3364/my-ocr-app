import streamlit as st
import pandas as pd
import json
import os
import requests
import xml.etree.ElementTree as ET
from datetime import datetime

# --- הגדרות לפי התיעוד ששלחת ---
DB_FILE = "sim_database.json"
TARGET_PLAN = "Prepaid Refills - Talk Only - 4G HD"
# הכתובת המדויקת מה-POST בתיעוד
API_URL = "https://wirelessprovisioning.com/desktopmodules/telispire.webservices/mdnservices.asmx"

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

def call_api_official(iccid, user, password):
    if not user or not password:
        return "חסר מידע", "נא להזין משתמש וסיסמה", False, ""

    # בניית ה-XML בדיוק לפי התמונה של התיעוד ששלחת (GetActivePackages)
    soap_body = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <GetActivePackages xmlns="urn:telispire:MdnServices">
      <username>{user}</username>
      <password>{password}</password>
      <MDN>{iccid}</MDN>
    </GetActivePackages>
  </soap:Body>
</soap:Envelope>"""

    headers = {
        "Content-Type": "text/xml; charset=utf-8",
        "SOAPAction": "urn:telispire:MdnServices/GetActivePackages"
    }

    try:
        response = requests.post(API_URL, data=soap_body, headers=headers, timeout=20)
        raw_res = response.text

        if response.status_code != 200:
            if "404" in raw_res:
                return "שגיאה 404", "הכתובת בתיעוד לא זמינה כרגע", False, raw_res
            return f"שגיאה {response.status_code}", "תגובת שרת לא תקינה", False, raw_res

        # ניתוח התשובה לפי המבנה שבתמונה
        root = ET.fromstring(raw_res)
        
        # חיפוש תגיות MasterCategory או תיאור חבילה
        found_packages = []
        for elem in root.iter():
            tag = elem.tag.split('}')[-1]
            if tag == "MasterCategory": # זה השדה שבדרך כלל מכיל את שם התוכנית
                if elem.text:
                    found_packages.append(elem.text.strip())
        
        if not found_packages:
            # אם הרשימה ריקה, כנראה אין חבילות פעילות
            return "פנוי (Available)", "לא נמצאו חבילות פעילות על הסים", True, raw_res

        # בדיקה אם התוכנית המבוקשת נמצאת ברשימה
        main_plan = found_packages[0]
        is_correct = any(TARGET_PLAN.lower() in p.lower() for p in found_packages)
        
        status = "תקין ✅" if is_correct else "תוכנית שונה ❌"
        return status, main_plan, is_correct, raw_res

    except Exception as e:
        return "שגיאה טכנית", str(e), False, ""

# --- ממשק Streamlit ---
st.set_page_config(page_title="מערכת סימים - מבוסס תיעוד", layout="wide")
db = load_db()

with st.sidebar:
    st.header("🔑 פרטי התחברות")
    st.info("הזן את המייל והסיסמה של הפאנל")
    u = st.text_input("Username", db['auth'].get('user', ''))
    p = st.text_input("Password", db['auth'].get('pass', ''), type="password")
    if st.button("שמור"):
        db['auth'] = {"user": u, "pass": p}
        save_db(db)
        st.success("נשמר!")

st.title("📱 בדיקת סטטוס סים (לפי תיעוד רשמי)")

sim_to_check = st.text_input("הכנס ICCID/MDN לבדיקה:")
if st.button("בדוק עכשיו 🚀"):
    with st.spinner("שואל את השרת..."):
        status, plan, ok, raw = call_api_official(sim_to_check, db['auth']['user'], db['auth']['pass'])
        
        if "תקין" in status:
            st.success(f"**תוצאה:** {status} | **תוכנית:** {plan}")
        elif "פנוי" in status:
            st.info(f"**תוצאה:** {status}")
        else:
            st.error(f"**תוצאה:** {status} | **נמצא:** {plan}")
        
        with st.expander("לוג טכני (XML)"):
            st.code(raw, language="xml")
