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
# הכתובת היציבה ביותר בשרת שלך
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

# פונקציה מרכזית לשליחת בקשות SOAP
def send_soap(method, body_content, user, password):
    soap_body = f"""<?xml version="1.0" encoding="utf-8"?>
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
        # הוספת מרכאות כפולות לערך ה-SOAPAction לפתרון שגיאת ה-Header
        "SOAPAction": f'"urn:telispire:MdnServices/{method}"'
    }
    
    try:
        response = requests.post(API_URL, data=soap_body, headers=headers, timeout=20)
        return response.text
    except Exception as e:
        return f"Error: {str(e)}"

# לוגיקת הבדיקה האוטומטית
def auto_check_flow(iccid, user, password):
    if not user or not password:
        return "שגיאה", "נא להגדיר הרשאות ב-Sidebar", False, ""

    # שלב 1: ניסיון לקבל MDN (מספר טלפון) מה-ICCID
    # נשתמש ב-SearchSubscribers או GetSubscriberInformation
    raw_info = send_soap("GetIVRLineInformation", f"<mdn>{iccid}</mdn>", user, password)
    
    # חיפוש MDN בתשובה (לפעמים ה-ICCID עצמו מזוהה כ-MDN זמני או שהשרת מחזיר את ה-MDN האמיתי)
    # ננסה לחלץ את ה-MDN מהתשובה או להשתמש בשיטה חלופית אם השרת מחזיר Fault
    
    found_mdn = None
    # אם ה-API של IVR לא נתן MDN, ננסה לחפש חבילות ישירות עם ה-ICCID (חלק מהמערכות מאפשרות זאת)
    # נבצע את השלב המכריע: בדיקת חבילות
    pkg_res = send_soap("GetActivePackages", f"<MDN>{iccid}</MDN>", user, password)
    
    if "User does not have access to MDN" in pkg_res:
        return "שגיאת גישה", "ה-ICCID לא מזוהה כ-MDN תקין בחשבון זה", False, pkg_res
    
    if "Server did not recognize" in pkg_res:
        return "שגיאת שרת", "הפקודה לא נתמכת בכתובת זו", False, pkg_res

    # ניתוח תוצאות החבילות
    found_plan = "לא נמצאה חבילה"
    try:
        root = ET.fromstring(pkg_res)
        for elem in root.iter():
            tag = elem.tag.split('}')[-1]
            if tag in ["MasterCategory", "PlanName", "Description"]:
                if elem.text and len(elem.text) > 2:
                    found_plan = elem.text.strip()
                    break
    except: pass

    is_ok = (TARGET_PLAN.lower() in found_plan.lower())
    status = "תקין ✅" if is_ok else "תוכנית שונה/לא פעיל ❌"
    
    return status, found_plan, is_ok, pkg_res

# --- ממשק האתר ---
st.set_page_config(page_title="ניהול סימים מקצועי", layout="wide")
db = load_db()

with st.sidebar:
    st.header("⚙️ הגדרות API")
    u = st.text_input("Username", db['auth'].get('user', ''))
    p = st.text_input("Password", db['auth'].get('pass', ''), type="password")
    if st.button("שמור"):
        db['auth'] = {"user": u, "pass": p}; save_db(db)
        st.success("הגדרות נשמרו")

st.title("📱 מערכת בדיקת סימים אוטומטית")

iccid = st.text_input("הכנס ICCID לבדיקה:")
if st.button("בדוק סים עכשיו 🚀"):
    with st.spinner("מבצע תהליך זיהוי אוטומטי..."):
        status, plan, ok, raw = auto_check_flow(iccid, db['auth']['user'], db['auth']['pass'])
        
        if ok: st.success(f"**{status}** | תוכנית: {plan}")
        else: st.error(f"**{status}** | מידע מהשרת: {plan}")
        
        with st.expander("ראה לוג טכני מלא"):
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
        save_db(db)
        st.rerun()

if db['sims']:
    st.table(pd.DataFrame(db['sims']))
