import os
import sys
import json
import time
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException

import firebase_admin
from firebase_admin import credentials, firestore

def send_telegram_msg(text):
    token = os.environ.get("TELEGRAM_BOT_TOKEN") 
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
    if token and chat_id:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        try:
            requests.post(url, data={"chat_id": chat_id, "text": text})
            print("✅ تم إرسال التلقرام")
        except Exception as e:
            print(f"❌ خطأ تلقرام: {e}")
# ==================================================
# 1️⃣ كشف المكان (جهازك ولا السيرفر؟) 🕵️‍♂️
# ==================================================
# هذا المتغير يكون موجود فقط داخل سيرفرات قيت هوب
IS_GITHUB_ACTION = os.environ.get('GITHUB_ACTIONS') == 'true'

if IS_GITHUB_ACTION:
    print("🌍 البوت يعمل الآن على سحابة GitHub (وضع السيرفر)")
else:
    print("💻 البوت يعمل الآن على جهازك الشخصي (وضع المشاهدة)")

# ==================================================
# 2️⃣ إعدادات الاتصال (للبيئتين)
# ==================================================
if not firebase_admin._apps:
    try:
        # السيناريو 1: نحن في قيت هوب
        if IS_GITHUB_ACTION:
            key_content = os.environ.get('FIREBASE_CREDENTIALS')
            if not key_content: sys.exit("❌ Secret missing")
            cred = credentials.Certificate(json.loads(key_content))
        
        # السيناريو 2: نحن في جهازك
        else:
            if os.path.exists("serviceAccountKey.json"):
                cred = credentials.Certificate("serviceAccountKey.json")
            else:
                sys.exit("❌ ملف serviceAccountKey.json غير موجود بجانب البوت!")

        firebase_admin.initialize_app(cred)
        print("✅ تم الاتصال بـ Firebase.")
    except Exception as e:
        sys.exit(f"❌ خطأ اتصال: {e}")

db = firestore.client()

# ==================================================
# ⚠️⚠️ إعدادات الدخول (عدلها هنا للتجربة المحلية) ⚠️⚠️
# ==================================================
if IS_GITHUB_ACTION:
    # في السيرفر يجيبها من الأسرار
    SITE_EMAIL = os.environ.get('TOROD_EMAIL')
    SITE_PASS = os.environ.get('TOROD_PASSWORD')
else:
    # 🛑🛑 اكتب ايميلك وباسوردك هنا عشان تجرب في جهازك 🛑🛑
    SITE_EMAIL = "kook53281@gmail.com" 
    SITE_PASS = "Abcd_0504989381"

# ==================================================
# 🔢 العداد
# ==================================================
def get_next_sequence_code():
    doc_ref = db.collection('settings').document('counter')
    try:
        doc = doc_ref.get()
        current = doc.to_dict().get('value', 0) if doc.exists else 0
        next_val = current + 1
        doc_ref.set({'value': next_val})
        return str(next_val).zfill(6)
    except: return "999999"

# ==================================================
# 3️⃣ البوت (النسخة الذكية)
# ==================================================
def add_address_to_torod(order_id, data):
    print(f"🚀 معالجة: {order_id}")
    opt = Options()
    
    # تحديد وضع العرض بناءً على المكان
    if IS_GITHUB_ACTION:
        opt.add_argument("--headless=new") 
        opt.add_argument("--no-sandbox")
        opt.add_argument("--disable-dev-shm-usage")
    else:
        # في جهازك: افتح الشاشة وكبرها عشان تشوف
        opt.add_argument("--start-maximized") 

    opt.add_argument("--window-size=1920,1080")
    opt.add_argument("--lang=ar")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opt)
    wait = WebDriverWait(driver, 25)

    def force_click(elem_id):
        """دالة قوية جداً للضغط على الأزرار العنيدة"""
        try:
            element = wait.until(EC.presence_of_element_located((By.ID, elem_id)))
            # 1. نجيب الزر في نص الشاشة عشان ما يغطيه شي
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
            time.sleep(1)
            # 2. نضغط عليه بالجافا سكربت (أقوى من الضغط العادي)
            driver.execute_script("arguments[0].click();", element)
            return True
        except Exception as e:
            print(f"⚠️ فشل الضغط على {elem_id}: {e}")
            return False

    try:
        # --- الدخول ---
        driver.get("https://torod.co/ar/login")
        wait.until(EC.presence_of_element_located((By.NAME, "email"))).send_keys(SITE_EMAIL)
        driver.find_element(By.NAME, "password").send_keys(SITE_PASS)
        
        # ضغط زر الدخول بالقوة
        login_btn = driver.find_element(By.XPATH, "/html/body/div[2]/div/div/form/p[4]/input[1]")
        driver.execute_script("arguments[0].click();", login_btn)
        
        wait.until(EC.url_changes("https://torod.co/ar/login"))

      # --- الذهاب لصفحة الشحنة وفتح النافذة ---
        driver.get("https://torod.co/ar/shipment-create")
        time.sleep(4) # انتظار الصفحة

        # ضغط زر "إضافة عميل"
        print("🖱️ فتح نافذة العميل...")
        wait.until(EC.element_to_be_clickable((By.ID, "addCustomerBtn"))).click()
        time.sleep(2)
        
     # --- تعبئة بيانات النافذة ---
        
        # 1. إغلاق الخريطة (زر التبديل)
        try: 
            toggle_btn = wait.until(EC.element_to_be_clickable((By.ID, "customer_form_google_map_toggle")))
            driver.execute_script("arguments[0].click();", toggle_btn)
            time.sleep(1)
        except: pass

        # دالة التعبئة
        def fill(eid, val):
            try:
                el = wait.until(EC.element_to_be_clickable((By.ID, eid)))
                el.clear()
                el.send_keys(str(val))
            except: pass

        # 2. تعبئة الخانات النصية
        fill("customer_form_name", data.get('receiver_name', ''))
        fill("customer_form_phone", data.get('receiver_phone', ''))
        fill("customer_form_address_details", f"حي {data.get('receiver_district','')} - {data.get('receiver_street','')}")

        # 3. اختيار المدينة (القائمة المنسدلة)
        try:
            # فتح القائمة
            driver.find_element(By.ID, "select2-customer_form_cities_id-container").click()
            # البحث
            search = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "select2-search__field")))
            search.send_keys(data.get('city', '').strip())
            time.sleep(2)
            search.send_keys(Keys.ENTER)
        except Exception as e: print(f"⚠️ مدينة: {e}")

      # --- الحفظ والإرسال ---
        
        # 1. ضغط زر "حفظ" داخل النافذة
        print("💾 حفظ العميل...")
        save_btn = wait.until(EC.element_to_be_clickable((By.ID, "add_customer_form_btn")))
        driver.execute_script("arguments[0].click();", save_btn)
        time.sleep(3) # انتظار إغلاق النافذة

        # 2. إرسال التلقرام
        msg = (
            f"تم اضافة عنوان مستلم!\n"
            f"الاسم {data.get('receiver_name', '')}\n"
            f"الرقم {data.get('receiver_phone', '')}\n"
            f"المدينة {data.get('city', '')}"
        )
        send_telegram_msg(msg)

        # 3. إنهاء الطلب
        db.collection('orders').document(order_id).update({'status': 'done'})
        return True

    except Exception as e:
        print(f"❌ خطأ: {e}")
        return False
    finally: driver.quit()
      
if __name__ == "__customer__":
    try:
        orders = list(db.collection('shipments').where('status', '==', 'pending').stream())
        if orders:
            for doc in shioments: add_address_to_torod(doc.id, doc.to_dict())
        else: print("💤 لا طلبات جديدة")
    except: sys.exit(1)
