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
    """שליחת בקשת SOAP עם טיפול מדויק ב-Headers"""
    soap_payload = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Header>
    <AuthenticationHeader xmlns="urn:telispire:MdnServices">
      <Username>{user}</Username>
      <Password>{password}</Password>
    </AuthenticationHeader>
  </soap:Header>
  <soap:Body>
    <{method} xmlns="urn:telispire:MdnServices">
      {body_content}
    </{method}>
  </soap:Body>
</soap:Envelope>"""

    headers = {
        "Content-Type": "text/xml; charset=utf-8",
        "SOAPAction": f'"urn:telispire:MdnServices/{method}"'
    }

    try:
        response = requests.post(API_URL, data=soap_payload, headers=headers, timeout=20)
        return response.text
    except Exception as e:
        return f"<error>{str(e)}</error>"

def check_sim_logic(iccid, user, password):
    """תהליך אוטומטי: חיפוש מנוי -> חילוץ טלפון -> בדיקת חבילה"""
    
    # שלב 1: חיפוש המנוי לפי ICCID כדי לקבל את מספר הטלפון (MDN)
    search_body = f"<SearchValue>{iccid}</SearchValue><SearchType>ICCID</SearchType>"
    raw_search = call_soap_api("SearchSubscribers", user, password, search_body)
    
    if "Server did not recognize" in raw_search:
        return "שגיאת הגדרה", "השרת לא מזהה את פקודת החיפוש. פנה למנהל המערכת.", False, raw_search

    mdn = None
    try:
        root_search = ET.fromstring(raw_search)
        for elem in root_search.iter():
            tag = elem.tag.split('}')[-1]
            if tag == "MDN" and elem.text:
                mdn = elem.text.strip()
                break
    except: pass

    # אם לא נמצא MDN, הסים כנראה פנוי (Available)
    if not mdn:
        return "פנוי (Available)", "לא נמצא מנוי פעיל המשויך ל-ICCID זה", True, raw_search

    # שלב 2: בדיקת חבילות פעילות לפי ה-MDN שנמצא (לפי התיעוד הרשמי)
    pkg_body = f"<MDN>{mdn}</MDN>"
    raw_pkg = call_soap_api("GetActivePackages", user, password, pkg_body)
    
    found_plan = "לא מזוהה"
    try:
        root_pkg = ET.fromstring(raw_pkg)
        for elem in root_pkg.iter():
            tag = elem.tag.split('}')[-1]
            # חיפוש ב-MasterCategory כפי שמופיע בתיעוד
            if tag in ["MasterCategory", "PlanName", "Description"]:
                if elem.text:
                    found_plan = elem.text.strip()
                    break
    except: pass

    is_correct = (TARGET_PLAN.lower() in found_plan.lower())
    status = "תקין ✅" if is_correct else "תוכנית שונה ❌"
    
    detail = f"מספר טלפון: {mdn} | תוכנית פעילה: {found_plan}"
    return status, detail, is_correct, raw_pkg

# --- ממשק המשתמש (Streamlit) ---
st.set_page_config(page_title="מערכת ניהול סימים", layout="wide")
db = load_db()

with st.sidebar:
    st.header("⚙️ הגדרות API")
    u = st.text_input("שם משתמש (User)", db['auth'].get('user', ''))
    p = st.text_input("סיסמה (Pass)", db['auth'].get('pass', ''), type="password")
    if st.button("שמור הגדרות"):
        db['auth'] = {"user": u, "pass": p}; save_db(db)
        st.success("נשמר!")

st.title("📱 מערכת מעקב ובדיקת סימים אוטומטית")

tab1, tab2, tab3 = st.tabs(["🔍 בדיקה מיידית", "📋 ניהול רשימה", "📊 דוחות"])

with tab1:
    val = st.text_input("הכנס ICCID לבדיקה:")
    if st.button("בדוק עכשיו 🚀"):
        if not db['auth']['user']:
            st.warning("נא להגדיר שם משתמש וסיסמה ב-Sidebar")
        else:
            with st.spinner("מבצע זיהוי אוטומטי..."):
                status, detail, ok, raw = check_sim_logic(val, db['auth']['user'], db['auth']['pass'])
                if ok: st.success(f"**סטטוס:** {status} | **מידע:** {detail}")
                else: st.error(f"**סטטוס:** {status} | **מידע:** {detail}")
                with st.expander("ראה נתונים גולמיים מהשרת (Debug)"):
                    st.code(raw, language="xml")

with tab2:
    st.subheader("הוספת סימים למעקב")
    c1, c2 = st.columns(2)
    with c1: nid = st.text_input("ICCID")
    with c2: nshop = st.text_input("שם חנות")
    if st.button("הוסף לרשימה"):
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
                res, detail, ok, _ = check_sim_logic(sim['iccid'], db['auth']['user'], db['auth']['pass'])
                results.append({"תאריך": datetime.now().strftime("%d/%m/%Y"), "חנות": sim['shop'], "ICCID": sim['iccid'], "תוצאה": res, "מידע": detail})
                bar.progress((i + 1) / len(db['sims']))
                time.sleep(0.5)
            
            res_df = pd.DataFrame(results)
            st.dataframe(res_df)
            st.download_button("📥 הורד דוח CSV", res_df.to_csv(index=False).encode('utf-8-sig'), "sim_report.csv")
