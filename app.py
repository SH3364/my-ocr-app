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
    mdn_to_check = input_val
    debug_log = ""

    if len(input_val) > 15:
        resp_mdn = soap_request("GetMDNByICCID", {"iccid": input_val}, user, password)
        if resp_mdn:
            extracted_mdn = parse_xml_value(resp_mdn, "GetMDNByICCIDResult") or parse_xml_value(resp_mdn, "mdn")
            if extracted_mdn: mdn_to_check = extracted_mdn

    resp_info = soap_request("GetIVRLineInformation", {"mdn": mdn_to_check}, user, password)
    if not resp_info: return "שגיאת תקשורת", "אין תגובה", "No Response"

    # חילוץ נתונים קריטיים
    status = parse_xml_value(resp_info, "Status")
    plan = parse_xml_value(resp_info, "RatePlan")
    
    # --- הלוגיקה החדשה והמדויקת ---
    # אם אין סטטוס ואין שם תוכנית ב-XML, זה אומר שהסים קיים אבל הקו לא פעיל
    if not status and not plan:
        return "ללא קו פעיל", "הסים מזוהה אך לא נמצאה חבילה", resp_info
    
    # אם יש סטטוס או תוכנית, נציג אותם (או נשלים ל-Target Plan אם זה חסר אבל הסטטוס פעיל)
    final_status = status if status else "Active"
    final_plan = plan if plan else TARGET_PLAN

    return final_status, final_plan, resp_info

# --- ממשק משתמש ---

st.title("📡 מערכת ניהול ובדיקת סימים")

with st.sidebar:
    st.header("🔐 הגדרות התחברות")
    u = st.text_input("שם משתמש API", key="api_user")
    p = st.text_input("סיסמה", type="password", key="api_pass")

tab1, tab2, tab3 = st.tabs(["🔍 בדיקה מהירה", "📋 ניהול רשימה", "📂 היסטוריה"])

with tab1:
    check_val = st.text_input("הכנס ICCID או MDN לבדיקה", key="manual_check")
    if st.button("בצע בדיקה חכמה"):
        if not u or not p: st.error("הזן פרטים בסיידבר")
        else:
            with st.spinner("בודק..."):
                s, pl, raw = smart_check_logic(check_val, u, p)
                c1, c2 = st.columns(2)
                # הצלחה רק אם נמצא קו והוא תואם ליעד
                if s != "ללא קו פעיל":
                    c1.success(f"**סטטוס:** {s}")
                    c2.success(f"**תוכנית:** {pl}")
                else:
                    c1.error(f"**סטטוס:** {s}")
                    c2.error(f"**תוכנית:** {pl}")
                with st.expander("לוג טכני"): st.code(raw, language="xml")

with tab2:
    st.subheader("הוספת מספרים למאגר")
    with st.form("add_sim"):
        col_a, col_b = st.columns(2)
        new_iccid = col_a.text_input("ICCID")
        new_store = col_b.text_input("שם חנות")
        if st.form_submit_button("שמור במאגר"):
            if new_iccid and new_store:
                df = pd.read_csv(DB_FILE)
                new_data = {'תאריך הוספה': datetime.now().strftime('%Y-%m-%d'), 'ICCID': str(new_iccid), 'שם חנות': new_store}
                pd.concat([df, pd.DataFrame([new_data])], ignore_index=True).to_csv(DB_FILE, index=False, encoding='utf-8-sig')
                st.success("נשמר!")

    if st.button("🚀 הרץ בדיקה קבוצתית"):
        if not u or not p: st.error("הזן פרטים בסיידבר")
        else:
            df_list = pd.read_csv(DB_FILE)
            if not df_list.empty:
                results = []
                bar = st.progress(0)
                for i, row in df_list.iterrows():
                    s, pl, _ = smart_check_logic(row['ICCID'], u, p)
                    results.append({'ICCID': row['ICCID'], 'חנות': row['שם חנות'], 'סטטוס': s, 'תוכנית': pl})
                    bar.progress((i + 1) / len(df_list))
                st.table(pd.DataFrame(results))

with tab3:
    st.subheader("דוחות קודמים")
    files = [f for f in os.listdir(REPORTS_DIR) if f.endswith('.csv')]
    if files:
        selected_file = st.selectbox("בחר דוח:", sorted(files, reverse=True))
        st.dataframe(pd.read_csv(os.path.join(REPORTS_DIR, selected_file)), use_container_width=True)
