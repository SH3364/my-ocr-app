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

def call_soap_api(method, user, password, mdn_value):
    """שליחת בקשת SOAP עם טיפול מדויק ב-SOAPAction"""
    soap_body = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <{method} xmlns="urn:telispire:MdnServices">
      <username>{user}</username>
      <password>{password}</password>
      <mdn>{mdn_value}</mdn>
    </{method}>
  </soap:Body>
</soap:Envelope>"""

    headers = {
        "Content-Type": "text/xml; charset=utf-8",
        # הוספת גרשיים היא קריטית לפתרון השגיאה שקיבלת
        "SOAPAction": f'"urn:telispire:MdnServices/{method}"'
    }

    try:
        response = requests.post(API_URL, data=soap_body, headers=headers, timeout=20)
        return response.text, response.status_code
    except Exception as e:
        return f"<error>{str(e)}</error>", 500

def check_sim_logic(iccid, user, password):
    """בדיקה אוטומטית: מנסה לקבל מידע על הקו והתוכנית"""
    
    # שלב 1: שימוש ב-GetIVRLineInformation (היחיד שלא נתן שגיאת 'לא מזוהה')
    raw_res, code = call_soap_api("GetIVRLineInformation", user, password, iccid)
    
    if "Server did not recognize" in raw_res:
        return "שגיאת שרת", "השרת לא מזהה את הפעולה. וודא שאתה משתמש בפרטי API תקינים.", False, raw_res

    try:
        root = ET.fromstring(raw_res)
        found_plan = "לא זוהה"
        is_active = False

        # סריקה לאיתור שם התוכנית (RatePlan או PlanName)
        for elem in root.iter():
            tag = elem.tag.split('}')[-1]
            if tag in ["RatePlan", "PlanName", "MasterCategory"]:
                if elem.text:
                    found_plan = elem.text.strip()
                    is_active = True
                    break
        
        # אם התשובה ריקה (כמו שקרה לך קודם עם 0 data) - ננסה GetActivePackages
        if found_plan == "לא זוהה":
            raw_pkg, code_pkg = call_soap_api("GetActivePackages", user, password, iccid)
            if "User does not have access" not in raw_pkg:
                # ניסיון ניתוח חבילות
                root_pkg = ET.fromstring(raw_pkg)
                for elem in root_pkg.iter():
                    tag = elem.tag.split('}')[-1]
                    if tag in ["MasterCategory", "Description"]:
                        found_plan = elem.text.strip()
                        is_active = True
                        break

        # לוגיקה סופית
        if not is_active:
            return "פנוי (Available)", "הסים טרם הופעל או שאין עליו קו", True, raw_res

        is_correct = (found_plan == TARGET_PLAN)
        status = "תקין ✅" if is_correct else "תוכנית לא תואמת ❌"
        return status, found_plan, is_correct, raw_res

    except Exception as e:
        return "שגיאת ניתוח", str(e), False, raw_res

# --- ממשק המשתמש (Streamlit) ---
st.set_page_config(page_title="ניהול סימים", layout="wide")
data = load_db()

with st.sidebar:
    st.header("⚙️ הגדרות API")
    u = st.text_input("Username", data['auth'].get('user', ''))
    p = st.text_input("Password", data['auth'].get('pass', ''), type="password")
    if st.button("שמור הגדרות"):
        data['auth'] = {"user": u, "pass": p}; save_db(data)
        st.success("נשמר!")

st.title("📱 מערכת מעקב סימים - Wireless Provisioning")

# טאבים
tab1, tab2 = st.tabs(["🔍 בדיקה מיידית", "📋 רשימת מעקב"])

with tab1:
    iccid_val = st.text_input("הכנס ICCID לבדיקה:")
    if st.button("בדוק עכשיו 🚀"):
        with st.spinner("מתחבר לשרת..."):
            status, plan, ok, raw = check_sim_logic(iccid_val, data['auth']['user'], data['auth']['pass'])
            if ok: st.success(f"**סטטוס:** {status} | **תוכנית:** {plan}")
            else: st.error(f"**סטטוס:** {status} | **מידע:** {plan}")
            with st.expander("ראה נתונים גולמיים (Debug)"):
                st.code(raw, language="xml")

with tab2:
    # ניהול רשימת סימים
    c1, c2 = st.columns(2)
    with c1: nid = st.text_input("הוסף ICCID")
    with c2: nshop = st.text_input("חנות")
    if st.button("הוסף לרשימה"):
        if nid:
            data['sims'].append({"iccid": nid, "shop": nshop, "date": datetime.now().strftime("%d/%m/%Y")})
            save_db(data); st.rerun()
    
    if data['sims']:
        st.dataframe(pd.DataFrame(data['sims']), use_container_width=True)
