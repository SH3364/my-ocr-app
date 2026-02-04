import streamlit as st
import pandas as pd
import json
import os
import requests
import xml.etree.ElementTree as ET
from datetime import datetime

# --- הגדרות קבועות ---
DB_FILE = "sim_database.json"
# הכתובת המדויקת מהסקריפט המקורי שלך
SOAP_URL = "https://wirelessprovisioning.com/desktopmodules/telispire.webservices/mdnservices.asmx"
TARGET_PLAN = "Prepaid Refills - Talk Only - 4G HD"

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

def call_api(iccid, user, password):
    if not user or not password:
        return "שגיאה", "נא להזין שם משתמש וסיסמה תקינים בצד", False, ""

    # מבנה ה-XML המדויק
    soap_body = f"""<?xml version="1.0" encoding="utf-8"?>
    <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
      <soap:Body>
        <GetIVRLineInformation xmlns="urn:telispire:MdnServices">
          <username>{user}</username>
          <password>{password}</password>
          <mdn>{iccid}</mdn>
        </GetIVRLineInformation>
      </soap:Body>
    </soap:Envelope>"""

    headers = {
        "Content-Type": "text/xml; charset=utf-8",
        "SOAPAction": "urn:telispire:MdnServices/GetIVRLineInformation"
    }

    try:
        response = requests.post(SOAP_URL, data=soap_body, headers=headers, timeout=20)
        
        # אם השרת מחזיר 404 (כמו ששלחת בתמונה)
        if response.status_code == 404:
            return "שגיאת כתובת (404)", "השרת לא מצא את דף ה-API. וודא שהכתובת נכונה.", False, response.text
        
        if response.status_code != 200:
            return f"שגיאת שרת ({response.status_code})", "השרת החזיר שגיאה טכנית.", False, response.text

        # ניתוח התשובה
        xml_res = response.text
        root = ET.fromstring(xml_res)
        
        # חיפוש תוכנית וסטטוס (ללא תלות ב-Namespace)
        found_plan = "לא נמצא"
        found_status = "לא נמצא"
        
        for elem in root.iter():
            tag = elem.tag.split('}')[-1]
            if tag == "RatePlan": found_plan = elem.text
            if tag == "Status": found_status = elem.text

        if found_status == "Available":
            return "פנוי (Available)", "הסים טרם הופעל", True, xml_res
        
        if found_plan == "לא נמצא" or not found_plan:
            return "לא מזוהה", "השרת לא החזיר נתוני תוכנית (בדוק פרטי התחברות)", False, xml_res

        is_correct = (found_plan.strip() == TARGET_PLAN)
        status = "תקין ✅" if is_correct else "תוכנית לא תואמת ❌"
        return status, found_plan, is_correct, xml_res

    except Exception as e:
        return "שגיאה בחיבור", str(e), False, ""

# --- ממשק האתר ---
st.set_page_config(page_title="בדיקת סימים", layout="wide")
db = load_db()

with st.sidebar:
    st.header("🔑 פרטי התחברות API")
    st.info("שים לב: שם המשתמש הוא המייל שלך למערכת, לא שם התוכנית!")
    u = st.text_input("שם משתמש API", db['auth'].get('user', ''))
    p = st.text_input("סיסמה API", db['auth'].get('pass', ''), type="password")
    if st.button("שמור הגדרות"):
        db['auth'] = {"user": u, "pass": p}
        save_db(db)
        st.success("נשמר!")

st.title("📱 מערכת מעקב סימים")

check_iccid = st.text_input("הכנס מספר סים לבדיקה (ICCID/MDN):")
debug_mode = st.checkbox("הצג תשובה גולמית מהשרת (למקרה של תקלה)")

if st.button("בדוק סים עכשיו"):
    with st.spinner("בודק מול השרת..."):
        res_status, res_plan, is_ok, raw = call_api(check_iccid, db['auth']['user'], db['auth']['pass'])
        
        if is_ok: st.success(f"**תוצאה:** {res_status} | **תוכנית:** {res_plan}")
        else: st.error(f"**תוצאה:** {res_status} | **תוכנית:** {res_plan}")
        
        if debug_mode:
            st.divider()
            st.write("תשובת השרת (XML/HTML):")
            st.code(raw, language="xml")
