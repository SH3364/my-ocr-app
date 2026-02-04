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

def call_soap_api(method, user, password, extra_xml):
    """שולח בקשת SOAP עם ה-Headers המדויקים שהשרת דורש"""
    soap_body = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <{method} xmlns="urn:telispire:MdnServices">
      <username>{user}</username>
      <password>{password}</password>
      {extra_xml}
    </{method}>
  </soap:Body>
</soap:Envelope>"""

    headers = {
        "Content-Type": "text/xml; charset=utf-8",
        "SOAPAction": f'"urn:telispire:MdnServices/{method}"'
    }

    try:
        response = requests.post(API_URL, data=soap_body, headers=headers, timeout=20)
        return response.text, response.status_code
    except Exception as e:
        return f"<error>{str(e)}</error>", 500

def check_sim_full_process(iccid, user, password):
    """תהליך אוטומטי: המרת ICCID ל-MDN ואז בדיקת חבילה"""
    
    # שלב 1: חיפוש ה-MDN (מספר הטלפון) לפי ה-ICCID
    # נשתמש ב-SearchSubscribers - הדרך הכי בטוחה למצוא מנוי
    search_xml = f"<SearchValue>{iccid}</SearchValue><SearchType>ICCID</SearchType>"
    raw_search, code = call_soap_api("SearchSubscribers", user, password, search_xml)
    
    if "Server did not recognize" in raw_search:
        # אם השרת לא מכיר את SearchSubscribers, ננסה GetSubscriberInformation
        search_xml = f"<mdn>{iccid}</mdn>"
        raw_search, code = call_soap_api("GetSubscriberInformation", user, password, search_xml)

    mdn = None
    try:
        root = ET.fromstring(raw_search)
        for elem in root.iter():
            tag = elem.tag.split('}')[-1]
            if tag == "MDN" and elem.text and len(elem.text) >= 10:
                mdn = elem.text.strip()
                break
    except: pass

    # אם לא נמצא MDN בכלל - הסים פנוי (Available)
    if not mdn:
        if "User does not have access" in raw_search or "not found" in raw_search.lower():
             return "פנוי (Available)", "הסים טרם הופעל או שאינו משויך לחשבון", True, raw_search
        return "שגיאה בזיהוי", "השרת לא החזיר מספר טלפון עבור סים זה", False, raw_search

    # שלב 2: בדיקת החבילה לפי ה-MDN שמצאנו
    pkg_xml = f"<MDN>{mdn}</MDN>"
    raw_pkg, code_pkg = call_soap_api("GetActivePackages", user, password, pkg_xml)
    
    found_plan = "לא מזוהה"
    try:
        root_pkg = ET.fromstring(raw_pkg)
        for elem in root_pkg.iter():
            tag = elem.tag.split('}')[-1]
            if tag in ["MasterCategory", "Description", "PlanName"]:
                if elem.text:
                    found_plan = elem.text.strip()
                    break
    except: pass

    is_correct = (TARGET_PLAN.lower() in found_plan.lower())
    status = "תקין ✅" if is_correct else "תוכנית שונה ❌"
    
    return status, f"טלפון: {mdn} | תוכנית: {found_plan}", is_correct, raw_pkg

# --- ממשק האתר ---
st.set_page_config(page_title="ניהול סימים", layout="wide")
db = load_db()

with st.sidebar:
    st.header("⚙️ הגדרות API")
    u = st.text_input("Username", db['auth'].get('user', ''))
    p = st.text_input("Password", db['auth'].get('pass', ''), type="password")
    if st.button("שמור הגדרות"):
        db['auth'] = {"user": u, "pass": p}; save_db(db)
        st.success("נשמר!")

st.title("📱 מערכת מעקב ובדיקת סימים אוטומטית")

tab1, tab2, tab3 = st.tabs(["🔍 בדיקה בזמן אמת", "📋 רשימת מעקב", "📊 דוחות"])

with tab1:
    iccid_val = st.text_input("הכנס ICCID לבדיקה:")
    if st.button("בדוק עכשיו 🚀"):
        with st.spinner("מבצע זיהוי דו-שלבי..."):
            status, info, ok, raw = check_sim_full_process(iccid_val, db['auth']['user'], db['auth']['pass'])
            if ok: st.success(status)
            else: st.error(status)
            st.info(info)
            with st.expander("ראה נתונים גולמיים (XML Debug)"):
                st.code(raw, language="xml")

with tab2:
    st.subheader("ניהול רשימה יומית")
    c1, c2, c3 = st.columns([2,2,1])
    with c1: nid = st.text_input("ICCID להוספה")
    with c2: nshop = st.text_input("שם חנות")
    with c3:
        st.write(" ")
        if st.button("הוסף"):
            if nid:
                db['sims'].append({"iccid": nid, "shop": nshop, "date": datetime.now().strftime("%d/%m/%Y")})
                save_db(db); st.rerun()

    if db['sims']:
        df = pd.DataFrame(db['sims'])
        st.table(df)
        if st.button("מחק הכל"):
            db['sims'] = []; save_db(db); st.rerun()

with tab3:
    if st.button("הפעל בדיקה לכל הרשימה"):
        if not db['sims']: st.warning("הרשימה ריקה")
        else:
            results = []
            bar = st.progress(0)
            for i, sim in enumerate(db['sims']):
                res, info, ok, _ = check_sim_full_process(sim['iccid'], db['auth']['user'], db['auth']['pass'])
                results.append({"תאריך": datetime.now().strftime("%d/%m/%Y"), "חנות": sim['shop'], "ICCID": sim['iccid'], "תוצאה": res, "מידע": info})
                bar.progress((i + 1) / len(db['sims']))
                time.sleep(0.5)
            
            res_df = pd.DataFrame(results)
            st.dataframe(res_df)
            st.download_button("📥 הורד דוח CSV", res_df.to_csv(index=False).encode('utf-8-sig'), "sim_report.csv")
