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

def send_soap_request(method, user, password, extra_xml):
    """פונקציה מרכזית לשליחת בקשות SOAP עם ה-Headers הנכונים"""
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

def check_sim_full_logic(iccid, user, password):
    """תהליך אוטומטי: מציאת MDN לפי ICCID ובדיקת חבילה"""
    
    # שלב 1: חיפוש המנוי כדי לקבל את מספר הטלפון (MDN)
    # הערה: חלק מהשרתים דורשים חיפוש ב-Header עבור SearchSubscribers, 
    # כאן נשתמש במבנה הפשוט ביותר שתואם לשרת שלך
    search_xml = f"<mdn>{iccid}</mdn>"
    raw_info = send_soap_request("GetSubscriberInformation", user, password, search_xml)
    
    mdn = None
    try:
        root = ET.fromstring(raw_info)
        for elem in root.iter():
            tag = elem.tag.split('}')[-1]
            if tag == "MDN" and elem.text and len(elem.text) >= 10:
                mdn = elem.text.strip()
                break
    except: pass

    # אם לא נמצא MDN, הסים כנראה פנוי
    if not mdn:
        if "User does not have access" in raw_info or "not found" in raw_info.lower():
            return "פנוי (Available)", "הסים טרם הופעל או שאינו משויך לחשבון", True, raw_info
        return "שגיאה בזיהוי", "השרת לא החזיר מספר טלפון עבור סים זה", False, raw_info

    # שלב 2: בדיקת חבילות פעילות לפי ה-MDN שנמצא
    pkg_xml = f"<MDN>{mdn}</MDN>"
    raw_pkg = send_soap_request("GetActivePackages", user, password, pkg_xml)
    
    found_plan = "לא מזוהה"
    try:
        root_pkg = ET.fromstring(raw_pkg)
        for elem in root_pkg.iter():
            tag = elem.tag.split('}')[-1]
            if tag in ["MasterCategory", "PlanName", "Description"]:
                if elem.text and len(elem.text) > 2:
                    found_plan = elem.text.strip()
                    break
    except: pass

    is_correct = (TARGET_PLAN.lower() in found_plan.lower())
    status = "תקין ✅" if is_correct else "תוכנית שונה ❌"
    
    return status, f"טלפון: {mdn} | תוכנית: {found_plan}", is_correct, raw_pkg

# --- ממשק האתר ---
st.set_page_config(page_title="ניהול סימים נטפרי", layout="wide")
db = load_db()

with st.sidebar:
    st.header("⚙️ הגדרות API")
    u = st.text_input("Username", db['auth'].get('user', ''))
    p = st.text_input("Password", db['auth'].get('pass', ''), type="password")
    if st.button("שמור הגדרות"):
        db['auth'] = {"user": u, "pass": p}; save_db(db)
        st.success("הגדרות נשמרו!")

st.title("📱 מערכת מעקב ובדיקת סימים אוטומטית")

tab1, tab2, tab3 = st.tabs(["🔍 בדיקה בזמן אמת", "📋 ניהול רשימה", "📊 דוחות"])

with tab1:
    iccid_input = st.text_input("הכנס ICCID לבדיקה:")
    if st.button("בדוק עכשיו 🚀"):
        with st.spinner("מחלץ מספר טלפון ובודק חבילה..."):
            status, detail, ok, raw = check_sim_full_logic(iccid_input, db['auth']['user'], db['auth']['pass'])
            if ok: st.success(f"**{status}**")
            else: st.error(f"**{status}**")
            st.info(detail)
            with st.expander("ראה נתונים גולמיים מהשרת"):
                st.code(raw, language="xml")

with tab2:
    st.subheader("הוספת סימים למעקב")
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
                res, detail, ok, _ = check_sim_full_logic(sim['iccid'], db['auth']['user'], db['auth']['pass'])
                results.append({"תאריך": datetime.now().strftime("%d/%m/%Y"), "חנות": sim['shop'], "ICCID": sim['iccid'], "תוצאה": res, "מידע": detail})
                bar.progress((i + 1) / len(db['sims']))
                time.sleep(0.5)
            
            res_df = pd.DataFrame(results)
            st.dataframe(res_df)
            st.download_button("📥 הורד דוח CSV", res_df.to_csv(index=False).encode('utf-8-sig'), "sim_report.csv")
