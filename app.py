import streamlit as st
import requests
import xml.etree.ElementTree as ET
import pandas as pd
from datetime import datetime
import os
from io import BytesIO

# --- הגדרות מערכת ---
REPORTS_DIR = 'reports'
DB_FILE = 'sim_database.csv'
BASE_URL = 'https://wirelessprovisioning.com/desktopmodules/telispire.webservices/mdnservices.asmx'
TARGET_PLAN = 'Prepaid Refills - Talk Only - 4G HD'

if not os.path.exists(REPORTS_DIR): os.makedirs(REPORTS_DIR)
if not os.path.exists(DB_FILE):
    pd.DataFrame(columns=['תאריך הוספה', 'ICCID', 'שם חנות']).to_csv(DB_FILE, index=False, encoding='utf-8-sig')

st.set_page_config(page_title='מערכת בדיקת סימים', layout='wide')

st.markdown("""
<style>
    .stApp { direction: rtl; text-align: right; }
    h1, h2, h3, p, div, span, input, label, button { direction: rtl; text-align: right; }
</style>
""", unsafe_allow_html=True)

def parse_xml_value(xml_text, target_tag):
    if not xml_text: return None
    try:
        root = ET.fromstring(xml_text)
        for elem in root.iter():
            tag_clean = elem.tag.split('}')[-1]
            if tag_clean == target_tag:
                return elem.text
        return None
    except:
        return None

def soap_request(method, params, username, password):
    param_str = "".join([f"<{k}>{v}</{k}>" for k, v in params.items()])
    payload = f'''<?xml version="1.0" encoding="utf-8"?>
    <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
      <soap:Body>
        <{method} xmlns="urn:telispire:MdnServices">
          <username>{username}</username>
          <password>{password}</password>
          {param_str}
        </{method}>
      </soap:Body>
    </soap:Envelope>'''
    headers = {'Content-Type': 'text/xml; charset=utf-8', 'SOAPAction': f'urn:telispire:MdnServices/{method}'}
    try:
        response = requests.post(BASE_URL, data=payload, headers=headers, timeout=25)
        return response.text if response.status_code == 200 else None
    except:
        return None

def smart_check_logic(input_val, user, password):
    input_val = str(input_val).strip()
    mdn_to_check = input_val
    debug_log = ""

    if len(input_val) > 15:
        resp_mdn = soap_request("GetMDNByICCID", {"iccid": input_val}, user, password)
        if resp_mdn:
            extracted_mdn = parse_xml_value(resp_mdn, "GetMDNByICCIDResult") or parse_xml_value(resp_mdn, "mdn")
            if extracted_mdn:
                mdn_to_check = extracted_mdn
                debug_log += f"✅ נמצא MDN תואם: {mdn_to_check}\n"

    resp_info = soap_request("GetIVRLineInformation", {"mdn": mdn_to_check}, user, password)
    
    if not resp_info:
        return "שגיאת תקשורת", "لا ניתן להתחבר", debug_log + "\nNo Response"

    status = parse_xml_value(resp_info, "Status")
    plan = parse_xml_value(resp_info, "RatePlan")
    
    # --- התיקון כאן: בדיקה אם קיימים נתוני חבילה גם ללא תגית Status מפורשת ---
    megabytes = parse_xml_value(resp_info, "MegabytesRemaining")
    
    if not status and megabytes is not None:
        status = "Active (Detected)"
        plan = plan if plan else "תוכנית קיימת (מידע מוסתר)"
    
    if not status:
        if "<GetIVRLineInformationResult>" in resp_info:
             return "זוהה (ללא קו)", "הסים קיים אך השרת לא החזיר פרטי תוכנית", debug_log + "\n" + resp_info
        return "לא נמצא", "אין נתונים", debug_log + "\n" + resp_info

    return status, plan, debug_log + "\n" + resp_info

# --- UI (נשאר ללא שינוי) ---
st.title("📡 מערכת ניהול ובדיקת סימים")

with st.sidebar:
    st.header("🔐 הגדרות התחברות")
    current_user = st.text_input("שם משתמש API", key="api_user")
    current_pass = st.text_input("סיסמה", type="password", key="api_pass")
    st.info("המערכת מנסה כעת להמיר אוטומטית ICCID ל-MDN.")

tab1, tab2, tab3 = st.tabs(["🔍 בדיקה מהירה", "📋 ניהול רשימה", "📂 היסטוריה"])

with tab1:
    st.subheader("בדיקת סים בודד")
    check_val = st.text_input("הכנס ICCID או MDN לבדיקה")
    if st.button("בצע בדיקה חכמה"):
        if not current_user or not current_pass:
            st.error("❌ חובה להזין שם משתמש וסיסמה בתפריט הצד!")
        elif not check_val:
            st.warning("נא להזין מספר לבדיקה")
        else:
            with st.spinner("מבצע בדיקה..."):
                final_status, final_plan, raw_log = smart_check_logic(check_val, current_user, current_pass)
                col1, col2 = st.columns(2)
                if final_status in ['Available', 'Active', 'Active (Detected)'] or final_plan == TARGET_PLAN:
                    col1.success(f"**סטטוס:** {final_status}")
                    col2.success(f"**תוכנית:** {final_plan}")
                else:
                    col1.error(f"**סטטוס:** {final_status}")
                    col2.error(f"**תוכנית:** {final_plan}")
                with st.expander("🛠️ נתונים טכניים (לוג מלא)"):
                    st.text(raw_log)

with tab2:
    st.subheader("הוספת מספרים למאגר")
    with st.form("db_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        in_iccid = c1.text_input("ICCID")
        in_store = c2.text_input("שם חנות")
        if st.form_submit_button("שמור"):
            if in_iccid and in_store:
                df = pd.read_csv(DB_FILE)
                new_row = {'תאריך הוספה': datetime.now().strftime('%Y-%m-%d %H:%M'), 'ICCID': str(in_iccid), 'שם חנות': in_store}
                pd.concat([df, pd.DataFrame([new_row])], ignore_index=True).to_csv(DB_FILE, index=False, encoding='utf-8-sig')
                st.success("נשמר!")
    
    if st.button("🚀 הרץ בדיקה על כל הרשימה"):
        if not current_user or not current_pass: st.error("נא להתחבר")
        else:
            df = pd.read_csv(DB_FILE)
            if not df.empty:
                results = []
                my_bar = st.progress(0)
                for i, row in df.iterrows():
                    stat, plan, _ = smart_check_logic(row['ICCID'], current_user, current_pass)
                    results.append({'ICCID': row['ICCID'], 'חנות': row['שם חנות'], 'סטטוס': stat, 'תוכנית': plan, 'תאריך': datetime.now().strftime('%d/%m %H:%M')})
                    my_bar.progress((i + 1) / len(df))
                st.dataframe(pd.DataFrame(results), use_container_width=True)

with tab3:
    st.subheader("דוחות קודמים")
    files = sorted([f for f in os.listdir(REPORTS_DIR) if f.endswith('.csv')], reverse=True)
    if files:
        sel = st.selectbox("בחר דוח:", files)
        st.dataframe(pd.read_csv(os.path.join(REPORTS_DIR, sel)), use_container_width=True)
