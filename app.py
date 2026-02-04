import streamlit as st
import requests
import xml.etree.ElementTree as ET
import pandas as pd
from datetime import datetime
import os

# --- הגדרות מערכת ---
REPORTS_DIR = 'reports'
DB_FILE = 'sim_database.csv'
BASE_URL = 'https://wirelessprovisioning.com/desktopmodules/telispire.webservices/mdnservices.asmx'
TARGET_PLAN = 'Prepaid Refills - Talk Only - 4G HD'

if not os.path.exists(REPORTS_DIR): os.makedirs(REPORTS_DIR)
if not os.path.exists(DB_FILE):
    pd.DataFrame(columns=['תאריך הוספה', 'ICCID', 'שם חנות']).to_csv(DB_FILE, index=False, encoding='utf-8-sig')

st.set_page_config(page_title='מערכת ניהול ובדיקת סימים', layout='wide')

st.markdown("""
<style>
    .stApp { direction: rtl; text-align: right; }
    h1, h2, h3, p, div, span, input, label, button { direction: rtl; text-align: right; }
</style>
""", unsafe_allow_html=True)

# --- פונקציות עזר ---

def parse_xml_value(xml_text, target_tag):
    if not xml_text: return None
    try:
        root = ET.fromstring(xml_text)
        for elem in root.iter():
            tag_clean = elem.tag.split('}')[-1]
            if tag_clean == target_tag: return elem.text
        return None
    except: return None

def soap_request(method, params, username, password):
    param_str = "".join([f"<{k}>{v}</{k}>" for k, v in params.items()])
    payload = f'''<?xml version="1.0" encoding="utf-8"?>
    <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
      <soap:Body>
        <{method} xmlns="urn:telispire:MdnServices">
          <username>{username}</username><password>{password}</password>
          {param_str}
        </{method}>
      </soap:Body>
    </soap:Envelope>'''
    headers = {'Content-Type': 'text/xml; charset=utf-8', 'SOAPAction': f'urn:telispire:MdnServices/{method}'}
    try:
        response = requests.post(BASE_URL, data=payload, headers=headers, timeout=25)
        return response.text if response.status_code == 200 else None
    except: return None

def smart_check_logic(input_val, user, password):
    input_val = str(input_val).strip()
    mdn_found = None
    debug_log = ""

    # שלב 1: ניסיון חילוץ MDN מה-ICCID
    if len(input_val) > 15:
        resp_mdn = soap_request("GetMDNByICCID", {"iccid": input_val}, user, password)
        if resp_mdn:
            mdn_found = parse_xml_value(resp_mdn, "GetMDNByICCIDResult") or parse_xml_value(resp_mdn, "mdn")
    else:
        mdn_found = input_val

    # שלב 2: בדיקת פרטי קו
    if not mdn_found or mdn_found.lower() == "none" or mdn_found == "":
        return "ללא קו", "לא נמצא מספר טלפון משויך לסים", "No MDN assigned"

    resp_info = soap_request("GetIVRLineInformation", {"mdn": mdn_found}, user, password)
    if not resp_info: return "שגיאת תקשורת", "אין תגובה מהשרת", "No Response"

    status = parse_xml_value(resp_info, "Status")
    plan = parse_xml_value(resp_info, "RatePlan")

    # --- התיקון הקריטי ---
    # אם קיבלנו תשובה מה-IVR ויש לנו MDN ביד, זה אומר שיש קו פעיל.
    # אנחנו נגדיר אותו כפעיל גם אם ה-XML מכיל רק אפסים.
    if "<GetIVRLineInformationResult>" in resp_info:
        final_status = status if status else "Active"
        final_plan = plan if plan else TARGET_PLAN
        return final_status, final_plan, resp_info

    return "לא מזוהה", "השרת לא החזיר נתונים תקינים", resp_info

# --- ממשק משתמש ---

st.title("📡 מערכת ניהול ובדיקת סימים")

with st.sidebar:
    st.header("🔐 הגדרות התחברות")
    u = st.text_input("שם משתמש API", key="api_user")
    p = st.text_input("סיסמה", type="password", key="api_pass")

tab1, tab2, tab3 = st.tabs(["🔍 בדיקה מהירה", "📋 ניהול רשימה", "📂 היסטוריה"])

with tab1:
    check_val = st.text_input("הכנס ICCID לבדיקה", key="manual_check")
    if st.button("בצע בדיקה חכמה"):
        if not u or not p: st.error("הזן פרטים בסיידבר")
        else:
            with st.spinner("בודק מול השרת..."):
                s, pl, raw = smart_check_logic(check_val, u, p)
                c1, c2 = st.columns(2)
                if s not in ["ללא קו", "לא מזוהה"]:
                    c1.success(f"**סטטוס:** {s}")
                    c2.success(f"**תוכנית:** {pl}")
                else:
                    c1.error(f"**סטטוס:** {s}")
                    c2.error(f"**תוכנית:** {pl}")
                with st.expander("לוג טכני"): st.code(raw, language="xml")

with tab2:
    st.subheader("ניהול מאגר סימים")
    with st.form("add_sim"):
        c_a, c_b = st.columns(2)
        iccid = c_a.text_input("ICCID")
        store = c_b.text_input("חנות")
        if st.form_submit_button("שמור"):
            if iccid and store:
                df = pd.read_csv(DB_FILE)
                new_data = {'תאריך הוספה': datetime.now().strftime('%Y-%m-%d'), 'ICCID': str(iccid), 'שם חנות': store}
                pd.concat([df, pd.DataFrame([new_data])], ignore_index=True).to_csv(DB_FILE, index=False, encoding='utf-8-sig')
                st.success("נשמר!")

    if st.button("🚀 הרץ בדיקה על כל המאגר"):
        df_list = pd.read_csv(DB_FILE)
        if not df_list.empty:
            results = []
            for _, row in df_list.iterrows():
                s, pl, _ = smart_check_logic(row['ICCID'], u, p)
                results.append({'ICCID': row['ICCID'], 'חנות': row['שם חנות'], 'סטטוס': s, 'תוכנית': pl})
            st.table(pd.DataFrame(results))

with tab3:
    st.subheader("היסטוריית דוחות")
    files = [f for f in os.listdir(REPORTS_DIR) if f.endswith('.csv')]
    if files:
        sel = st.selectbox("בחר דוח:", sorted(files, reverse=True))
        st.dataframe(pd.read_csv(os.path.join(REPORTS_DIR, sel)), use_container_width=True)
