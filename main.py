import os
import sys
import json
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException, ElementNotInteractableException, NoSuchElementException

import firebase_admin
from firebase_admin import credentials, firestore

# ==================================================
# 1️⃣ إعدادات الاتصال (من GitHub Secrets)
# ==================================================
print("🔧 جاري تهيئة الاتصال بـ Firebase...")

if not firebase_admin._apps:
    try:
        # قراءة مفتاح فايربيس من متغيرات البيئة
        key_content = os.environ.get('FIREBASE_KEY')
        
        if not key_content:
            print("❌ خطأ قاتل: لم يتم العثور على Secret باسم FIREBASE_KEY")
            sys.exit(1)
            
        # تحويل النص إلى JSON
        try:
            key_dict = json.loads(key_content)
            cred = credentials.Certificate(key_dict)
            firebase_admin.initialize_app(cred)
            print("✅ تم الاتصال بـ Firebase بنجاح.")
        except json.JSONDecodeError as e:
            print(f"❌ خطأ في قراءة ملف JSON: {e}")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ خطأ غير متوقع: {e}")
        sys.exit(1)

db = firestore.client()

# استلام بيانات الدخول لطرود
SITE_EMAIL = os.environ.get('TOROD_EMAIL')
SITE_PASS = os.environ.get('TOROD_PASSWORD')

if not SITE_EMAIL or not SITE_PASS:
    print("❌ خطأ: لم يتم العثور على ايميل أو باسورد طرود في Secrets")
    sys.exit(1)

# ==================================================
# 🔢 دالة العداد (تخزين سحابي في Firestore)
# ==================================================
def get_next_sequence_code():
    # نستخدم مستند في فايربيس لتخزين الرقم بدلاً من ملف txt
    # لأن ملفات GitHub تنحذف بعد كل تشغيل
    doc_ref = db.collection('settings').document('counter')
    
    try:
        doc = doc_ref.get()
        if doc.exists:
            current = doc.to_dict().get('value', 1)
        else:
            current = 1
            
        next_val = current + 1
        # تحديث الرقم في فايربيس للمرة القادمة
        doc_ref.set({'value': next_val})
        
        return str(next_val).zfill(4)
    except Exception as e:
        print(f"⚠️ خطأ في العداد السحابي: {e}")
        return "9999" # رقم طوارئ

# ==================================================
# 2️⃣ وظيفة الأتمتة
# ==================================================
def add_address_to_torod(order_id, data):
    print(f"\n🚀 جاري معالجة الطلب: {order_id}")
    
    chrome_options = Options()
    # إعدادات خاصة بسيرفرات GitHub (مهمة جداً)
    chrome_options.add_argument("--headless=new") 
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--lang=ar")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    wait = WebDriverWait(driver, 25)

    def smart_send_keys(element_id, text):
        if not text: return
        for i in range(3):
            try:
                element = wait.until(EC.presence_of_element_located((By.ID, element_id)))
                wait.until(EC.element_to_be_clickable((By.ID, element_id)))
                element.clear()
                element.send_keys(str(text))
                return True
            except (StaleElementReferenceException, ElementNotInteractableException):
                time.sleep(2)
        return False

    try:
        # --- تسجيل الدخول ---
        driver.get("https://torod.co/ar/login")
        wait.until(EC.presence_of_element_located((By.NAME, "email"))).send_keys(SITE_EMAIL)
        driver.find_element(By.NAME, "password").send_keys(SITE_PASS)
        login_btn = driver.find_element(By.XPATH, "/html/body/div[2]/div/div/form/p[4]/input[1]")
        driver.execute_script("arguments[0].click();", login_btn)
        wait.until(EC.url_changes("https://torod.co/ar/login"))
        
        # --- الانتقال للعنوان ---
        driver.get("https://torod.co/ar/settings/address")
        wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="ga4-addressesDiv"]/div/div/div[2]/a'))).click()
        
        try:
            map_toggle = wait.until(EC.element_to_be_clickable((By.ID, "merchant_address_form_google_map_toggle")))
            driver.execute_script("arguments[0].click();", map_toggle)
        except: pass
        time.sleep(2)

        # --- المدينة ---
        city_name = data.get('city', '').strip()
        print(f"🏙️ المدينة: {city_name}")

        target_btn_id = "select2-merchant_address_form_city-container"
        city_opener = wait.until(EC.element_to_be_clickable((By.ID, target_btn_id)))
        city_opener.click()
        
        search_field = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "select2-search__field")))
        search_field.send_keys(city_name)
        
        print("   ⏳ انتظار 5 ثواني...")
        time.sleep(5) 
        search_field.send_keys(Keys.ENTER)
        time.sleep(5) 

        # --- البيانات ---
        print("✍️ تعبئة البيانات...")
        smart_send_keys("merchant_address_form_address_details", f"حي {data.get('district', '')} - شارع {data.get('street', '')}")
        smart_send_keys("merchant_address_form_name", "1station")
        smart_send_keys("merchant_address_form_contact_name", f"{data.get('receiver_name', '')} (غير معدل)")
        smart_send_keys("merchant_address_form_phone_number", data.get('receiver_phone', ''))
        smart_send_keys("merchant_address_form_email", data.get('email', 'customer@example.com'))

        # --- العداد والحفظ ---
        print("🔢 معالجة الرمز...")
        save_btn = wait.until(EC.presence_of_element_located((By.ID, "address_form_btn")))
        
        current_code = get_next_sequence_code() 
        
        for attempt in range(10):
            print(f"   🔄 محاولة ({attempt+1}) بالرمز: {current_code}")
            
            try:
                title_field = driver.find_element(By.ID, "merchant_address_form_title")
                title_field.clear()
                title_field.send_keys(current_code)
            except: time.sleep(1)
            
            time.sleep(1)
            
            try:
                driver.execute_script("arguments[0].scrollIntoView();", save_btn)
                driver.execute_script("arguments[0].click();", save_btn)
            except:
                save_btn.click()
                
            print("   ⏳ فحص النتيجة...")
            time.sleep(5) 
            
            error_exists = False
            try:
                if driver.find_element(By.ID, "merchant_address_form_title-error").is_displayed():
                    error_exists = True
            except NoSuchElementException:
                error_exists = False
            
            if not error_exists:
                print(f"✨ تم الحفظ! الرمز: {current_code}")
                db.collection('orders').document(order_id).update({'status': 'done'})
                print("✅ تم تحديث الحالة في فايربيس.")
                return True
            
            print("   ⚠️ الرمز مكرر، جاري التغيير...")
            current_code = get_next_sequence_code() 

        return False

    except Exception as e:
        print(f"❌ خطأ أثناء المعالجة: {e}")
        return False
    finally:
        driver.quit()

# ==================================================
# 3️⃣ التشغيل (مرة واحدة - GitHub Schedule)
# ==================================================
if __name__ == "__main__":
    print("🤖 بدء تشغيل البوت المجدول...")
    
    try:
        # جلب الطلبات المعلقة
        orders_ref = db.collection('orders').where('status', '==', 'pending')
        orders = list(orders_ref.stream())
        
        if len(orders) > 0:
            print(f"🔔 تم العثور على {len(orders)} طلبات جديدة.")
            for doc in orders:
                add_address_to_torod(doc.id, doc.to_dict())
        else:
            print("💤 لا توجد طلبات جديدة.")
            
    except Exception as e:
        print(f"❌ خطأ عام: {e}")
        sys.exit(1)
