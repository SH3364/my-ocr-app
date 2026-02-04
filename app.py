import streamlit as st
import pandas as pd
import json
import os
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import time

# --- הגדרות ---
DB_FILE = "sim_database.json"
# שימוש בכתובת ה-API המדויקת מהדוקומנטציה
SOAP_URL = "https://api.wirelessprovisioning.com/publish/MdnServices.asmx"
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

def call_api_robust(iccid, user, password):
    if not user or not password:
        return "שגיאת הגדרות", "חסר שם משתמש או סיסמה בתפריט הצד", False, ""

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
        raw_xml = response.text
        
        # בדיקה אם ה-API חסם את הגישה (פרטים לא נכונים)
        if "Authentication failed" in raw_xml or "Invalid username" in raw_xml:
            return "שגיאת הרשאה", "שם המשתמש או הסיסמה של ה-API לא נכונים", False, raw_xml

        root = ET.fromstring(raw_xml)
        
        # חיפוש נתונים בצורה רחבה ללא תלות ב-Namespace
        found_plan = "לא נמצא"
        is_active = False
        
        for elem in root.iter():
            tag_name = elem.tag.split('}')[-1] # הסרת ה-Namespace
            if tag_name in ["PlanName", "RatePlanName", "RatePlan"]:
                found_plan = elem.text if elem.text else "ריק"
            if tag_name == "Status" and elem.text == "Active":
                is_active = True

        # לוגיקת החלטה
        if found_plan == "לא נמצא" or found_plan == "ריק":
            return "פנוי / לא נמצא", "ה-API לא החזיר תוכנית למספר זה", True, raw_xml
        
        is_correct_plan = (found_plan.strip() == TARGET_PLAN)
        status = "תקין" if is_correct_plan else "תוכנית לא תואמת"
        
        return status, found_plan, is_correct_plan, raw_xml

    except Exception as e:
        return "שגיאת שרת", str(e), False, ""

# --- ממשק האתר ---
st.set_page_config(page_title="ניהול סימים", layout="wide")
db = load_db()

with st.sidebar:
    st.header("⚙️ הגדרות API")
    u = st.text_input("שם משתמש (בדרך כלל אימייל)", db['auth'].get('user', ''))
    p = st.text_input("סיסמה", db['auth'].get('pass', ''), type="password")
    if st.button("שמור הגדרות"):
        db['auth'] = {"user": u, "pass": p}
        save_db(db)
        st.success("ההגדרות נשמרו!")

st.title("📱 מערכת בדיקת סימים WP")

tab1, tab2 = st.tabs(["🔍 בדיקה בזמן אמת", "📋 רשימת מעקב"])

with tab1:
    check_iccid = st.text_input("הכנס ICCID לבדיקה:")
    show_debug = st.checkbox("הצג תשובת שרת גולמית (למקרה של תקלה)")
    
    if st.button("בדוק עכשיו 🚀"):
        with st.spinner("מתחבר ל-Wireless Provisioning..."):
            status, plan, ok, debug_info = call_api_robust(check_iccid, db['auth']['user'], db['auth']['pass'])
            
            if ok: st.success(f"**סטטוס:** {status} | **תוכנית:** {plan}")
            else: st.error(f"**סטטוס:** {status} | **תוכנית:** {plan}")
            
            if show_debug:
                st.code(debug_info, language="xml")

with tab2:
    # כאן תהיה רשימת הסימים שלך כפי שהגדרנו קודם...
    st.info("כאן תוכל להוסיף את רשימת החנויות הקבועה שלך.")
