import streamlit as st
import requests
import xml.etree.ElementTree as ET
import pandas as pd
from datetime import datetime
import os

# הגדרות מערכת
REPORTS_DIR = 'reports'
DB_FILE = 'sim_database.csv'
BASE_URL = 'https://wirelessprovisioning.com/desktopmodules/telispire.webservices/mdnservices.asmx'
TARGET_PLAN = 'Prepaid Refills - Talk Only - 4G HD'

if not os.path.exists(REPORTS_DIR): os.makedirs(REPORTS_DIR)
if not os.path.exists(DB_FILE):
    pd.DataFrame(columns=['תאריך הוספה', 'ICCID', 'שם חנות']).to_csv(DB_FILE, index=False, encoding='utf-8-sig')

st.set_page_config(page_title='מערכת סריקת סימים חכמה', layout='wide')

def soap_request(method, params, username, password):
    """פונקציה גנרית לביצוע פניות SOAP למערכת"""
    param_xml = "".join([f"<{k}>{v}</实质性>" for k, v in params.items()])
    # תיקון תגיות ה-XML במחרוזת
    param_xml = "".join([f"<{k}>{v}</{k}>" for k, v in params.items()])
    
    payload = f'''<?xml version="1.0" encoding="utf-8"?>
    <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
      <soap:Body>
        <{method} xmlns="urn:telispire:MdnServices">
          <username>{username.strip()}</username>
          <password>{password.strip()}</password>
          {param_xml}
        </{method}>
      </soap:Body>
    </soap:Envelope>'''
    
    headers = {
        'Content-Type': 'text/xml; charset=utf-8',
        'SOAPAction': f'urn:telispire:MdnServices/{method}'
    }
    
    try:
        response = requests.post(BASE_URL, data=payload, headers=headers, timeout=15)
        return response.text if response.status_code == 200 else None
    except:
        return None

def parse_xml_value(xml_text, target_tag):
    """חילוץ ערך מתגית ספציפית ב-XML"""
    if not xml_text: return None
    try:
        root = ET.fromstring(xml_text)
        for elem in root.iter():
            if elem.tag.split('}')[-1] == target_tag:
                return elem.text
        return None
    except:
        return None

def smart_check(iccid, user, pw):
    """לוגיקת הבדיקה האוטומטית שביקשת"""
    # 1. ניסיון למצוא MDN לפי ICCID
    mdn_xml = soap_request("GetMDNByICCID", {"iccid": iccid}, user, pw)
    found_mdn = parse_xml_value(mdn_xml, "GetMDNByICCIDResult") or iccid
    
    # 2. שליחת הבקשה למידע המלא (באמצעות ה-MDN שמצאנו או ה-ICCID כמפלט אחרון)
    info_xml = soap_request("GetIVRLineInformation", {"mdn": found_mdn}, user, pw)
    
    status = parse_xml_value(info_xml, "Status")
    plan = parse_xml_value(info_xml, "RatePlan")
    
    if not status:
        return "לא זוהה קו", "אין נתונים", info_xml or "שגיאת תקשורת"
    
    return status, plan, info_xml

# --- ממשק משתמש (UI) ---
with st.sidebar:
    st.header("🔐 הגדרות API")
    u = st.text_input("שם משתמש")
    p = st.text_input("סיסמה", type="password")
    st.divider()
    st.info("המערכת מבצעת כעת המרת ICCID ל-MDN באופן אוטומטי.")

tab1, tab2, tab3, tab4 = st.tabs(["📋 ניהול רשימה", "🔍 בדיקה מיידית", "🚀 בדיקה קבוצתית", "📜 היסטוריית דוחות"])

# טאב 1: ניהול רשימה
with tab1:
    with st.form("add_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        new_iccid = col1.text_input("מספר ICCID")
        store = col2.text_input("שם חנות")
        if st.form_submit_button("הוסף למאגר"):
            if new_iccid and store:
                df = pd.read_csv(DB_FILE)
                new_row = {'תאריך הוספה': datetime.now().strftime('%Y-%m-%d %H:%M'), 'ICCID': str(new_iccid), 'שם חנות': store}
                pd.concat([df, pd.DataFrame([new_row])], ignore_index=True).to_csv(DB_FILE, index=False, encoding='utf-8-sig')
                st.success("המספר נשמר בהצלחה")
    
    st.subheader("רשימת המספרים השמורה")
    st.dataframe(pd.read_csv(DB_FILE), use_container_width=True)

# טאב 2: בדיקה מיידית
with tab2:
    q_iccid = st.text_input("הכנס ICCID לבדיקה עכשיו")
    if st.button("בצע בדיקה חכמה"):
        if u and p:
            with st.spinner("מתבצעת המרת ICCID ובדיקת סטטוס..."):
                status, plan, raw = smart_check(q_iccid, u, p)
                
                is_ok = (status == 'Available' or plan == TARGET_PLAN)
                c1, c2 = st.columns(2)
                if is_ok:
                    c1.success(f"**סטטוס:** {status}")
                    c2.success(f"**תוכנית:** {plan}")
                else:
                    c1.error(f"**סטטוס:** {status}")
                    c2.error(f"**תוכנית:** {plan}")
                
                with st.expander("לצפייה בתשובה הטכנית (XML)"):
                    st.code(raw, language='xml')
        else:
            st.warning("נא להזין פרטי API בתפריט הצד")

# טאב 3: בדיקה קבוצתית
with tab3:
    if st.button("🚀 הרץ בדיקה על כל הרשימה"):
        df_list = pd.read_csv(DB_FILE)
        if not df_list.empty:
            results = []
            progress = st.progress(0)
            for i, row in df_list.iterrows():
                status, plan, _ = smart_check(row['ICCID'], u, p)
                results.append({
                    'תאריך בדיקה': datetime.now().strftime('%Y-%m-%d %H:%M'),
                    'ICCID': row['ICCID'],
                    'חנות': row['שם חנות'],
                    'סטטוס': status,
                    'תוכנית': plan,
                    'תוצאה': "✅ תקין" if (status == 'Available' or plan == TARGET_PLAN) else "❌ שגיאה/חסר"
                })
                progress.progress((i + 1) / len(df_list))
            
            res_df = pd.DataFrame(results)
            fname = f"report_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
            res_df.to_csv(os.path.join(REPORTS_DIR, fname), index=False, encoding='utf-8-sig')
            st.dataframe(res_df, use_container_width=True)
            st.success(f"הבדיקה הסתיימה. הדוח נשמר בשם: {fname}")

# טאב 4: היסטוריה
with tab4:
    st.subheader("צפייה בתוצאות בדיקות קודמות")
    report_files = sorted([f for f in os.listdir(REPORTS_DIR) if f.endswith('.csv')], reverse=True)
    if report_files:
        selected_file = st.selectbox("בחר דוח להצגה:", report_files)
        view_df = pd.read_csv(os.path.join(REPORTS_DIR, selected_file))
        st.dataframe(view_df, use_container_width=True)
        with open(os.path.join(REPORTS_DIR, selected_file), 'rb') as f:
            st.download_button("הורד קובץ זה", f, file_name=selected_file)
    else:
        st.info("עדיין לא בוצעו בדיקות קבוצתיות.")
