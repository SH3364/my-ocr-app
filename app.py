import streamlit as st
import pandas as pd
import json
import os
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import time

# --- הגדרות קבועות ---
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

# --- פונקציית API משולבת (חיפוש מנוי + בדיקת חבילה) ---
def check_sim_process(iccid, user, password):
    if not user or not password:
        return "שגיאה", "חסר שם משתמש/סיסמה", False, ""

    # שלב 1: חיפוש מנוי לפי ICCID כדי לקבל MDN
    search_soap = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Header>
    <AuthenticationHeader xmlns="urn:telispire:MdnServices">
      <Username>{user}</Username>
      <Password>{password}</Password>
    </AuthenticationHeader>
  </soap:Header>
  <soap:Body>
    <SearchSubscribers xmlns="urn:telispire:MdnServices">
      <SearchValue>{iccid}</SearchValue>
      <SearchType>ICCID</SearchType>
    </SearchSubscribers>
  </soap:Body>
</soap:Envelope>"""

    headers_search = {
        "Content-Type": "text/xml; charset=utf-8",
        "SOAPAction": '"urn:telispire:MdnServices/SearchSubscribers"'
    }

    try:
        res_search = requests.post(API_URL, data=search_soap, headers=headers_search, timeout=20)
        root_search = ET.fromstring(res_search.text)
        
        mdn = None
        for elem in root_search.iter():
            tag = elem.tag.split('}')[-1]
            if tag == "MDN":
                mdn = elem.text
                break
        
        # אם לא נמצא MDN - הסים פנוי
        if not mdn:
            return "פנוי (Available)", "לא נמצא מנוי פעיל על הסים הזה", True, res_search.text

        # שלב 2: אם נמצא MDN, בדיקת חבילות פעילות
        pkg_soap = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <GetActivePackages xmlns="urn:telispire:MdnServices">
      <username>{user}</username>
      <password>{password}</password>
      <MDN>{mdn}</MDN>
    </GetActivePackages>
  </soap:Body>
</soap:Envelope>"""

        headers_pkg = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": '"urn:telispire:MdnServices/GetActivePackages"'
        }

        res_pkg = requests.post(API_URL, data=pkg_soap, headers=headers_pkg, timeout=20)
        root_pkg = ET.fromstring(res_pkg.text)
        
        found_plan = "לא זוהתה חבילה"
        for elem in root_pkg.iter():
            tag = elem.tag.split('}')[-1]
            if tag in ["MasterCategory", "Description"]:
                if elem.text:
                    found_plan = elem.text.strip()
                    break

        is_correct = (TARGET_PLAN.lower() in found_plan.lower())
        status = "תקין ✅" if is_correct else "תוכנית שונה ❌"
        return status, f"טלפון: {mdn} | תוכנית: {found_plan}", is_correct, res_pkg.text

    except Exception as e:
        return "שגיאה טכנית", str(e), False, ""

# --- ממשק המשתמש ---
st.set_page_config(page_title="ניהול סימים נטפרי", layout="wide")
db = load_db()

with st.sidebar:
    st.header("⚙️ הגדרות API")
    u = st.text_input("Username", db['auth'].get('user', ''))
    p = st.text_input("Password", db['auth'].get('pass', ''), type="password")
    if st.button("שמור"):
        db['auth'] = {"user": u, "pass": p}; save_db(db)
        st.success("נשמר!")

st.title("📱 מערכת בדיקת סימים אוטומטית")

tab1, tab2 = st.tabs(["🔍 בדיקה בזמן אמת", "📋 רשימת מעקב"])

with tab1:
    iccid_val = st.text_input("הכנס ICCID לבדיקה:")
    if st.button("בדוק עכשיו 🚀"):
        with st.spinner("מבצע תהליך זיהוי דו-שלבי..."):
            status, detail, ok, raw = check_sim_process(iccid_val, db['auth']['user'], db['auth']['pass'])
            if ok: st.success(status)
            else: st.error(status)
            st.info(detail)
            with st.expander("לוג טכני (XML)"):
                st.code(raw, language="xml")

with tab2:
    st.subheader("ניהול רשימה יומית")
    c1, c2 = st.columns(2)
    with c1: nid = st.text_input("ICCID")
    with c2: nshop = st.text_input("חנות")
    if st.button("הוסף"):
        if nid:
            db['sims'].append({"iccid": nid, "shop": nshop, "date": datetime.now().strftime("%d/%m/%Y")})
            save_db(db); st.rerun()

    if db['sims']:
        df = pd.DataFrame(db['sims'])
        st.table(df)
        if st.button("הורד דוח ריכוז"):
            st.download_button("הורד CSV", df.to_csv(index=False).encode('utf-8-sig'), "sims.csv")
