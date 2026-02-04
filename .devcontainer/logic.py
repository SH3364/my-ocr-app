import requests
import xml.etree.ElementTree as ET
import time

TARGET_PLAN = "Prepaid Refills - Talk Only - 4G HD"
SOAP_URL = "https://api.wirelessprovisioning.com/publish/MdnServices.asmx"

def call_sim_api(iccid, user, password):
    # שימוש ב-SearchSubscribers כדי לקבל את שם התוכנית המדויק
    soap_body = f"""<?xml version="1.0" encoding="utf-8"?>
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

    headers = {
        "Content-Type": "text/xml; charset=utf-8",
        "SOAPAction": "urn:telispire:MdnServices/SearchSubscribers"
    }

    try:
        response = requests.post(SOAP_URL, data=soap_body, headers=headers, timeout=20)
        if response.status_code != 200:
            return "Error", "Connection Problem", False

        # פרסום ה-XML
        root = ET.fromstring(response.text)
        ns = {'ns': 'urn:telispire:MdnServices'}
        
        # בדיקה אם הסים קיים במערכת
        total_count = root.find(".//ns:TotalCount", ns)
        if total_count is not None and total_count.text == "0":
            return "Available", "No Line Found", True

        # שליפת שם התוכנית
        plan_elem = root.find(".//ns:PlanName", ns)
        current_plan = plan_elem.text if plan_elem is not None else "Unknown"
        
        is_ok = (current_plan == TARGET_PLAN)
        status = "Active" if is_ok else "Wrong Plan"
        
        return status, current_plan, is_ok

    except Exception as e:
        return "Error", str(e), False
