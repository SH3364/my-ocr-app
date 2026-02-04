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

def call_telispire_api(value, user, password, method="GetSubscriberInformation"):
    """פונקציה מרכזית לביצוע שאילתות מול ה-API"""
    
    # בניית ה-XML בהתאם לשיטה
    if method == "GetSubscriberInformation":
        # שיטה זו מחפשת לפי ICCID או MDN ומחזירה פרטים מלאים
        body = f"""<GetSubscriberInformation xmlns="urn:telispire:MdnServices">
          <username>{user}</username>
          <password>{password}</password>
          <mdn>{value}</mdn>
        </GetSubscriberInformation>"""
    else:
        # שיטה חלופית לבדיקת חבילות
        body = f"""<GetActivePackages xmlns="urn:telispire:MdnServices">
          <username>{user}</username>
          <password>{password}</password>
          <MDN>{value}</MDN>
        </GetActivePackages>"""

    soap_payload = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    {body}
  </soap:Body>
</soap:Envelope>"""

    headers = {
        "Content-Type": "text/xml; charset=utf-8",
        "SOAPAction": f'"urn:telispire:MdnServices/{method}"'
    }

    try:
        response = requests.post(API_URL, data=soap_payload, headers=headers, timeout=20)
        return response.text, response.status_code
    except Exception as e:
        return f"Error: {str(e)}", 500

def process_sim_check(iccid, user, password):
    """תהליך בדיקה לוגי של סים"""
    raw_xml, code = call_telispire_api(iccid, user, password)
    
    if code != 200 or "<soap:Fault>" in raw_xml:
        # אם יש שגיאת שרת, לא נגיד שפנוי!
        return "שגיאת API", "השרת החזיר שגיאה (בדוק פרטי התחברות)", False, raw_xml

    # ניתוח ה-XML
    try:
        root = ET.fromstring(raw_xml)
        ns = {'ns': 'urn:telispire:MdnServices'}
        
        # חיפוש סטטוס ופרטי תוכנית
        status = "Unknown"
        plan = "N/A"
        mdn = ""

        for elem in root.iter():
            tag = elem.tag.split('}')[-1]
            if tag == "Status": status = elem.text
            if tag in ["RatePlan", "PlanName", "CurrentPlan"]: plan = elem.text
            if tag == "MDN": mdn = elem.text

        # לוגיקה לקביעת התוצאה
        if status == "Available" or (not mdn and status == "N/A"):
            return "פנוי (Available)", "הסים מוכן להפעלה", True, raw_xml
        
        if status == "Active" or mdn:
            is_correct_plan = (plan.strip() == TARGET_PLAN)
            res_status = "תקין ✅" if is_correct_plan else "תוכנית שונה ❌"
            return res_status, f"MDN: {mdn} | תוכנית: {plan}", is_correct_plan, raw_xml
            
        return "לא מזוהה", f"סטטוס: {status} | תוכנית: {plan}", False, raw_xml

    except Exception as e:
        return "שגיאת ניתוח", str(e), False, raw_xml

# --- ממשק Streamlit ---
st.set_page_config(page_title="מערכת ניהול סימים", layout="wide")
db = load_db()

with st.sidebar:
    st.header("⚙️ הגדרות API")
    u = st.text_input("Username", db['auth'].get('user', ''))
    p = st.text_input("Password", db['auth'].get('pass', ''), type="password")
    if st.button("שמור הגדרות"):
        db['auth'] = {"user": u, "pass": p}; save_db(db)
        st.success("נשמר!")

st.title("📱 ניהול ובדיקת סימים - Wireless Provisioning")

tab1, tab2, tab3 = st.tabs(["🔍 בדיקה בזמן אמת", "📋 ניהול רשימה", "📊 דוחות"])

with tab1:
    iccid_input = st.text_input("הכנס ICCID לבדיקה מיידית:")
    if st.button("בדוק עכשיו 🚀"):
        with st.spinner("מבצע שאילתה..."):
            res, detail, ok, raw = process_sim_check(iccid_input, db['auth']['user'], db['auth']['pass'])
            if ok: st.success(f"**{res}**")
            else: st.error(f"**{res}**")
            st.info(detail)
            with st.expander("לוג טכני (XML)"):
                st.code(raw, language="xml")

with tab2:
    st.subheader("ניהול רשימת מעקב")
    col1, col2 = st.columns(2)
    with col1: nid = st.text_input("ICCID להוספה")
    with col2: nshop = st.text_input("שם חנות")
    if st.button("הוסף לרשימה"):
        if nid:
            db['sims'].append({"iccid": nid, "shop": nshop, "date": datetime.now().strftime("%d/%m/%Y")})
            save_db(db); st.rerun()

    if db['sims']:
        df = pd.DataFrame(db['sims'])
        st.table(df)
        if st.button("נקה רשימה"):
            db['sims'] = []; save_db(db); st.rerun()

with tab3:
    st.subheader("בדיקה מרוכזת והורדת דוח")
    if st.button("הפעל בדיקה לכל הרשימה"):
        results = []
        bar = st.progress(0)
        for i, sim in enumerate(db['sims']):
            res, detail, ok, _ = process_sim_check(sim['iccid'], db['auth']['user'], db['auth']['pass'])
            results.append({
                "תאריך": datetime.now().strftime("%d/%m/%Y"),
                "חנות": sim['shop'],
                "ICCID": sim['iccid'],
                "תוצאה": res,
                "פירוט": detail
            })
            bar.progress((i + 1) / len(db['sims']))
            time.sleep(0.5)
        
        report_df = pd.DataFrame(results)
        st.dataframe(report_df)
        st.download_button("הורד דוח CSV", report_df.to_csv(index=False).encode('utf-8-sig'), "sim_report.csv")
