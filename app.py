import streamlit as st
import pandas as pd
import json
import os
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import time

# --- הגדרות מערכת ---
DB_FILE = "sim_database.json"
TARGET_PLAN = "Prepaid Refills - Talk Only - 4G HD"
# הכתובת היציבה ביותר שהוכחה כעובדת אצלך
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

def call_soap_api(method, user, password, body_content):
    """שליחת בקשת SOAP עם טיפול במירכאות ב-Headers למניעת שגיאת 'Not Recognized'"""
    soap_payload = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <{method} xmlns="urn:telispire:MdnServices">
      <username>{user}</username>
      <password>{password}</password>
      {body_content}
    </{method}>
  </soap:Body>
</soap:Envelope>"""

    headers = {
        "Content-Type": "text/xml; charset=utf-8",
        # הוספת מירכאות כפולות סביב ה-Action היא הפתרון לשגיאה שקיבלת
        "SOAPAction": f'"urn:telispire:MdnServices/{method}"'
    }

    try:
        response = requests.post(API_URL, data=soap_payload, headers=headers, timeout=20)
        return response.text
    except Exception as e:
        return f"<error>{str(e)}</error>"

def check_sim_logic(iccid, user, password):
    """תהליך אוטומטי מלא: זיהוי MDN ובדיקת תוכנית"""
    
    # שלב 1: נסיון חיפוש מנוי לפי ICCID כדי לקבל את ה-MDN
    # אנחנו משתמשים ב-SearchSubscribers כי היא מתאימה לחיפוש לפי ICCID
    search_body = f"<SearchValue>{iccid}</SearchValue><SearchType>ICCID</SearchType>"
    # נשתמש בפורמט Header מעט שונה למתודת החיפוש
    search_res = call_soap_api("SearchSubscribers", user, password, search_body)
    
    mdn = None
    if "Server did not recognize" not in search_res:
        try:
            root = ET.fromstring(search_res)
            for elem in root.iter():
                tag = elem.tag.split('}')[-1]
                if tag == "MDN" and elem.text:
                    mdn = elem.text.strip()
                    break
        except: pass

    # אם השלב הראשון נכשל, ננסה להשתמש ב-ICCID ישירות מול בדיקת החבילות
    target_value = mdn if mdn else iccid
    
    # שלב 2: בדיקת חבילות (המתודה שהופיעה בתיעוד שלך!)
    pkg_res = call_soap_api("GetActivePackages", user, password, f"<MDN>{target_value}</MDN>")
    
    if "User does not have access to MDN" in pkg_res:
        return "פנוי / אין גישה", "הסים לא מזוהה כפעיל בחשבון זה", False, pkg_res

    # ניתוח תוצאות החבילה
    found_plan = "לא נמצאה חבילה"
    try:
        root_pkg = ET.fromstring(pkg_res)
        for elem in root_pkg.iter():
            tag = elem.tag.split('}')[-1]
            if tag in ["MasterCategory", "Description", "PlanName"]:
                if elem.text:
                    found_plan = elem.text.strip()
                    break
    except: pass

    is_correct = (TARGET_PLAN.lower() in found_plan.lower())
    status = "תקין ✅" if is_correct else "תוכנית שונה ❌"
    
    return status, f"תוכנית: {found_plan} (מזהה: {target_value})", is_correct, pkg_res

# --- ממשק Streamlit ---
st.set_page_config(page_title="ניהול סימים מקצועי", layout="wide")
db = load_db()

with st.sidebar:
    st.header("⚙️ הגדרות API")
    u = st.text_input("Username", db['auth'].get('user', ''))
    p = st.text_input("Password", db['auth'].get('pass', ''), type="password")
    if st.button("שמור הגדרות"):
        db['auth'] = {"user": u, "pass": p}; save_db(db)
        st.success("הגדרות נשמרו")

st.title("📱 מערכת בדיקת סימים אוטומטית (ICCID)")

iccid_input = st.text_input("הכנס ICCID לבדיקה:")
if st.button("בדוק סים 🚀"):
    with st.spinner("מבצע זיהוי ובדיקת חבילה..."):
        status, detail, ok, raw = check_sim_logic(iccid_input, db['auth']['user'], db['auth']['pass'])
        if ok: st.success(status)
        else: st.error(status)
        st.info(detail)
        with st.expander("לוג טכני (XML)"):
            st.code(raw, language="xml")

# ניהול רשימה
st.divider()
st.subheader("📋 רשימת מעקב")
c1, c2 = st.columns(2)
with c1: nid = st.text_input("הוסף ICCID לרשימה")
with c2: nshop = st.text_input("חנות")
if st.button("הוסף"):
    if nid:
        db['sims'].append({"iccid": nid, "shop": nshop, "date": datetime.now().strftime("%d/%m")})
        save_db(db); st.rerun()

if db['sims']:
    st.table(pd.DataFrame(db['sims']))
