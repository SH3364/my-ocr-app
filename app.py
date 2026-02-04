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
# הכתובת היציבה ביותר שהוכחה כעובדת בשרת שלך
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

def soap_request(method, user, password, extra_xml):
    """פונקציה גנרית לשליחת בקשות SOAP עם ה-Headers המדויקים"""
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
        return response.text
    except Exception as e:
        return f"<error>{str(e)}</error>"

def check_sim_smart_flow(iccid, user, password):
    """תהליך אוטומטי: 1. מציאת MDN לפי ICCID | 2. בדיקת חבילות לפי ה-MDN שנמצא"""
    
    # שלב א': חיפוש פרטי המנוי כדי לחלץ את מספר הטלפון (MDN)
    # נשתמש ב-GetIVRLineInformation שראינו שאינו מחזיר שגיאת "לא מזוהה"
    search_res = soap_request("GetIVRLineInformation", user, password, f"<mdn>{iccid}</mdn>")
    
    # ניסיון לחלץ MDN מכל תגית אפשרית ב-XML שחזר
    mdn = None
    if "<soap:Fault>" not in search_res:
        try:
            root = ET.fromstring(search_res)
            for elem in root.iter():
                tag = elem.tag.split('}')[-1]
                if tag == "MDN" and elem.text and len(elem.text) >= 10:
                    mdn = elem.text.strip()
                    break
        except: pass

    # אם השלב הראשון נכשל במציאת MDN, ננסה להשתמש ב-ICCID ישירות (למקרה שהשרת מאפשר)
    target_value = mdn if mdn else iccid
    
    # שלב ב': בדיקת חבילות פעילות (GetActivePackages)
    pkg_res = soap_request("GetActivePackages", user, password, f"<MDN>{target_value}</MDN>")
    
    if "User does not have access to MDN" in pkg_res:
        if not mdn:
            return "פנוי (Available)", "הסים טרם הופעל או שלא נמצא מנוי משויך", True, pkg_res
        return "שגיאת הרשאה", "אין גישה למספר הטלפון שזוהה", False, pkg_res

    # ניתוח שם התוכנית
    found_plan = "לא מזוהה"
    try:
        root_pkg = ET.fromstring(pkg_res)
        for elem in root_pkg.iter():
            tag = elem.tag.split('}')[-1]
            if tag in ["MasterCategory", "Description", "PlanName"]:
                if elem.text:
                    found_plan = elem.text.strip()
                    break
    except: pass

    is_correct = (found_plan.lower() == TARGET_PLAN.lower())
    status = "תקין ✅" if is_correct else "תוכנית שונה ❌"
    
    info = f"מספר טלפון: {mdn if mdn else 'לא זוהה'} | תוכנית: {found_plan}"
    return status, info, is_correct, pkg_res

# --- ממשק המשתמש (Streamlit) ---
st.set_page_config(page_title="מערכת ניהול סימים", layout="wide")
db = load_db()

with st.sidebar:
    st.header("⚙️ הגדרות API")
    u = st.text_input("שם משתמש", db['auth'].get('user', ''))
    p = st.text_input("סיסמה", db['auth'].get('pass', ''), type="password")
    if st.button("שמור הגדרות"):
        db['auth'] = {"user": u, "pass": p}; save_db(db)
        st.success("הגדרות נשמרו!")

st.title("📱 מערכת מעקב סימים - Wireless Provisioning")

tab1, tab2, tab3 = st.tabs(["🔍 בדיקה מיידית", "📋 ניהול רשימה", "📊 דוחות"])

with tab1:
    st.subheader("בדיקת סים בזמן אמת (לפי ICCID)")
    val = st.text_input("הכנס ICCID לבדיקה:")
    if st.button("בדוק עכשיו 🚀"):
        with st.spinner("מחלץ מספר טלפון ובודק חבילה..."):
            status, info, ok, raw = check_sim_smart_flow(val, db['auth']['user'], db['auth']['pass'])
            if ok: st.success(f"**סטטוס:** {status}")
            else: st.error(f"**סטטוס:** {status}")
            st.info(info)
            with st.expander("ראה נתונים גולמיים (Debug)"):
                st.code(raw, language="xml")

with tab2:
    st.subheader("ניהול רשימת מעקב")
    c1, c2 = st.columns(2)
    with c1: nid = st.text_input("ICCID")
    with c2: nshop = st.text_input("חנות")
    if st.button("הוסף למאגר"):
        if nid:
            db['sims'].append({"iccid": nid, "shop": nshop, "added": datetime.now().strftime("%d/%m/%Y")})
            save_db(db); st.rerun()

    if db['sims']:
        st.dataframe(pd.DataFrame(db['sims']), use_container_width=True)
        if st.button("מחק הכל"):
            db['sims'] = []; save_db(db); st.rerun()

with tab3:
    if st.button("הפעל בדיקה לכל הרשימה"):
        if not db['sims']: st.warning("הרשימה ריקה")
        else:
            results = []
            bar = st.progress(0)
            for i, sim in enumerate(db['sims']):
                res, info, ok, _ = check_sim_smart_flow(sim['iccid'], db['auth']['user'], db['auth']['pass'])
                results.append({"תאריך": datetime.now().strftime("%d/%m/%Y"), "חנות": sim['shop'], "ICCID": sim['iccid'], "תוצאה": res, "מידע": info})
                bar.progress((i + 1) / len(db['sims']))
                time.sleep(0.5)
            
            res_df = pd.DataFrame(results)
            st.dataframe(res_df)
            st.download_button("📥 הורד דוח CSV", res_df.to_csv(index=False).encode('utf-8-sig'), "sim_report.csv")
