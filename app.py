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

# יצירת תיקיות וקבצים אם לא קיימים
if not os.path.exists(REPORTS_DIR): os.makedirs(REPORTS_DIR)
if not os.path.exists(DB_FILE):
    pd.DataFrame(columns=['תאריך הוספה', 'ICCID', 'שם חנות']).to_csv(DB_FILE, index=False, encoding='utf-8-sig')

# --- תיקון השגיאה כאן: הורדתי את direction='rtl' ---
st.set_page_config(page_title='מערכת בדיקת סימים', layout='wide')

# הוספת תמיכה ב-RTL (ימין לשמאל) בצורה תקנית דרך CSS
st.markdown("""
<style>
    .stApp {
        direction: rtl;
        text-align: right;
    }
    /* התאמה ספציפית לכותרות וטקסטים */
    h1, h2, h3, p, div, span, input, label {
        direction: rtl; 
        text-align: right; 
    }
</style>
""", unsafe_allow_html=True)

# --- פונקציות עזר (API) ---

def parse_xml_value(xml_text, target_tag):
    """מחלץ ערך מתוך תגית XML"""
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
    """שולח בקשת SOAP לשרת"""
    param_str = ""
    for k, v in params.items():
        param_str += f"<{k}>{v}</{k}>"

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

    headers = {
        'Content-Type': 'text/xml; charset=utf-8',
        'SOAPAction': f'urn:telispire:MdnServices/{method}'
    }

    try:
        response = requests.post(BASE_URL, data=payload, headers=headers, timeout=25)
        if response.status_code == 200:
            return response.text
        else:
            return None
    except:
        return None

def smart_check_logic(input_val, user, password):
    """
    הפונקציה החכמה:
    1. מנסה להבין אם קיבלנו ICCID.
    2. אם כן, מנסה למצוא את ה-MDN שלו.
    3. בסוף מושכת את המידע על הקו.
    """
    input_val = str(input_val).strip()
    mdn_to_check = input_val
    debug_log = ""

    # שלב 1: אם זה נראה כמו ICCID (ארוך מ-15 תווים), ננסה להמיר ל-MDN
    if len(input_val) > 15:
        resp_mdn = soap_request("GetMDNByICCID", {"iccid": input_val}, user, password)
        
        if resp_mdn:
            extracted_mdn = parse_xml_value(resp_mdn, "GetMDNByICCIDResult") or parse_xml_value(resp_mdn, "mdn")
            if extracted_mdn:
                mdn_to_check = extracted_mdn
                debug_log += f"✅ נמצא MDN תואם: {mdn_to_check}\n"
            else:
                debug_log += "⚠️ לא נמצא MDN עבור ה-ICCID הזה, מנסה לבדוק ישירות.\n"
        else:
            debug_log += "⚠️ פונקציית המרת ICCID נכשלה או לא קיימת.\n"

    # שלב 2: בדיקת פרטי הקו (IVR)
    resp_info = soap_request("GetIVRLineInformation", {"mdn": mdn_to_check}, user, password)
    
    if not resp_info:
        return "שגיאת תקשורת", "לא ניתן להתחבר", debug_log + "\nNo Response"

    status = parse_xml_value(resp_info, "Status")
    plan = parse_xml_value(resp_info, "RatePlan")

    if not status:
        error_msg = parse_xml_value(resp_info, "faultstring")
        if error_msg:
            return "שגיאת API", error_msg, debug_log + "\n" + resp_info
        
        if "<GetIVRLineInformationResult>" in resp_info and "<Wireless>" not in resp_info:
             return "זוהה (ללא קו)", "הסים קיים אך לא משויך לקו", debug_log + "\n" + resp_info

        return "לא נמצא", "אין נתונים", debug_log + "\n" + resp_info

    return status, plan, debug_log + "\n" + resp_info

# --- ממשק משתמש (UI) ---

st.title("📡 מערכת ניהול ובדיקת סימים")

with st.sidebar:
    st.header("🔐 הגדרות התחברות")
    # שימוש ב-key לשמירת הנתונים בזיכרון
    st.text_input("שם משתמש API", key="api_user")
    st.text_input("סיסמה", type="password", key="api_pass")
    st.divider()
    st.info("המערכת מנסה כעת להמיר אוטומטית ICCID ל-MDN.")

tab1, tab2, tab3 = st.tabs(["🔍 בדיקה מהירה", "📋 ניהול רשימה", "📂 היסטוריה"])

# --- טאב 1: בדיקה מהירה ---
with tab1:
    st.subheader("בדיקת סים בודד")
    check_val = st.text_input("הכנס ICCID או MDN לבדיקה")
    
    if st.button("בצע בדיקה חכמה"):
        u = st.session_state.get("api_user", "")
        p = st.session_state.get("api_pass", "")
        
        if not u or not p:
            st.error("❌ חובה להזין שם משתמש וסיסמה בתפריט הצד!")
        elif not check_val:
            st.warning("נא להזין מספר לבדיקה")
        else:
            with st.spinner("מבצע בדיקה מול השרת..."):
                final_status, final_plan, raw_log = smart_check_logic(check_val, u, p)
                
                col1, col2 = st.columns(2)
                is_success = (final_status == 'Available' or final_plan == TARGET_PLAN)
                
                if is_success:
                    col1.success(f"**סטטוס:** {final_status}")
                    col2.success(f"**תוכנית:** {final_plan}")
                    st.balloons()
                else:
                    col1.error(f"**סטטוס:** {final_status}")
                    col2.error(f"**תוכנית:** {final_plan}")
                    if "זוהה (ללא קו)" in final_status:
                        st.warning("השרת זיהה את הסים, אך לא החזיר פרטי קו. ייתכן שהסים טרם הופעל.")

                with st.expander("🛠️ נתונים טכניים (לוג מלא)"):
                    st.text(raw_log)

# --- טאב 2: ניהול רשימה ---
with tab2:
    st.subheader("הוספת מספרים למאגר")
    with st.form("db_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        in_iccid = c1.text_input("ICCID")
        in_store = c2.text_input("שם חנות")
        if st.form_submit_button("שמור"):
            if in_iccid and in_store:
                df = pd.read_csv(DB_FILE)
                new_row = {
                    'תאריך הוספה': datetime.now().strftime('%Y-%m-%d %H:%M'),
                    'ICCID': str(in_iccid),
                    'שם חנות': in_store
                }
                pd.concat([df, pd.DataFrame([new_row])], ignore_index=True).to_csv(DB_FILE, index=False, encoding='utf-8-sig')
                st.success("נשמר!")
            else:
                st.error("נא למלא את כל השדות")
    
    st.divider()
    
    if st.button("🚀 הרץ בדיקה על כל הרשימה"):
        u = st.session_state.get("api_user", "")
        p = st.session_state.get("api_pass", "")
        
        if not u or not p:
            st.error("נא להתחבר בצד ימין")
        else:
            df = pd.read_csv(DB_FILE)
            if df.empty:
                st.warning("הרשימה ריקה")
            else:
                results = []
                my_bar = st.progress(0)
                for i, row in df.iterrows():
                    stat, plan, _ = smart_check_logic(row['ICCID'], u, p)
                    res_text = "✅ תקין" if (stat == 'Available' or plan == TARGET_PLAN) else "❌ לבדוק"
                    
                    results.append({
                        'ICCID': row['ICCID'],
                        'חנות': row['שם חנות'],
                        'סטטוס': stat,
                        'תוכנית': plan,
                        'סיכום': res_text,
                        'תאריך': datetime.now().strftime('%d/%m %H:%M')
                    })
                    my_bar.progress((i + 1) / len(df))
                
                res_df = pd.DataFrame(results)
                fname = f"report_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
                res_df.to_csv(os.path.join(REPORTS_DIR, fname), index=False, encoding='utf-8-sig')
                st.success("הבדיקה הסתיימה!")
                st.dataframe(res_df, use_container_width=True)

# --- טאב 3: היסטוריה ---
with tab3:
    st.subheader("דוחות קודמים")
    files = sorted([f for f in os.listdir(REPORTS_DIR) if f.endswith('.csv')], reverse=True)
    if files:
        sel = st.selectbox("בחר דוח:", files)
        path = os.path.join(REPORTS_DIR, sel)
        st.dataframe(pd.read_csv(path), use_container_width=True)
        with open(path, 'rb') as f:
            st.download_button("הורד CSV", f, file_name=sel)
