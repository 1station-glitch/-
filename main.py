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
# 1️⃣ إعدادات الاتصال (GitHub Secrets)
# ==================================================
print("🔧 جاري تهيئة الاتصال...")

if not firebase_admin._apps:
    try:
        key_content = os.environ.get('FIREBASE_KEY')
        if not key_content:
            print("❌ لم يتم العثور على مفتاح فايربيس (Secret مفقود)")
            sys.exit(1)
            
        key_dict = json.loads(key_content)
        cred = credentials.Certificate(key_dict)
        firebase_admin.initialize_app(cred)
        print("✅ تم الاتصال بـ Firebase.")
    except Exception as e:
        print(f"❌ خطأ في الاتصال: {e}")
        sys.exit(1)

db = firestore.client()
SITE_EMAIL = os.environ.get('TOROD_EMAIL')
SITE_PASS = os.environ.get('TOROD_PASSWORD')

# ==================================================
# 🔢 دالة العداد السحابي
# ==================================================
def get_next_sequence_code():
    doc_ref = db.collection('settings').document('counter')
    try:
        doc = doc_ref.get()
        current = doc.to_dict().get('value', 1) if doc.exists else 1
        next_val = current + 1
        doc_ref.set({'value': next_val})
        return str(next_val).zfill(4)
    except:
        return "9999"

# ==================================================
# 2️⃣ وظيفة الأتمتة (تصوير + كتابة ذكية)
# ==================================================
def add_address_to_torod(order_id, data):
    print(f"\n🚀 جاري معالجة الطلب: {order_id}")
    
    chrome_options = Options()
    chrome_options.add_argument("--headless=new") 
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--lang=ar")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    wait = WebDriverWait(driver, 25)

    # 👇 الدالة الذكية للكتابة (تم استرجاعها)
    def smart_send_keys(element_id, text):
        if not text: return
        for i in range(3):
            try:
                element = wait.until(EC.presence_of_element_located((By.ID, element_id)))
                wait.until(EC.element_to_be_clickable((By.ID, element_id)))
                element.clear() # مسح القديم
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
        
        driver.save_screenshot("1_login_success.png")

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

        wait.until(EC.element_to_be_clickable((By.ID, "select2-merchant_address_form_city-container"))).click()
        search_field = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "select2-search__field")))
        search_field.send_keys(city_name)
        time.sleep(5) 
        search_field.send_keys(Keys.ENTER)
        time.sleep(5) 

        # --- البيانات (الآن نستخدم smart_send_keys ✅) ---
        print("✍️ تعبئة البيانات...")
        smart_send_keys("merchant_address_form_address_details", f"حي {data.get('district', '')} - شارع {data.get('street', '')}")
        smart_send_keys("merchant_address_form_name", "1station")
        smart_send_keys("merchant_address_form_contact_name", f"{data.get('receiver_name', '')} (غير معدل)")
        smart_send_keys("merchant_address_form_phone_number", data.get('receiver_phone', ''))
        smart_send_keys("merchant_address_form_email", data.get('email', 'customer@example.com'))

        driver.save_screenshot("2_data_filled.png") # صورة للتأكد من البيانات

        # --- العداد والحفظ ---
        save_btn = wait.until(EC.presence_of_element_located((By.ID, "address_form_btn")))
        current_code = get_next_sequence_code() 
        
        for attempt in range(5):
            print(f"   🔄 محاولة ({attempt+1}) بالرمز: {current_code}")
            try:
                tf = driver.find_element(By.ID, "merchant_address_form_title")
                tf.clear()
                tf.send_keys(current_code)
            except: time.sleep(1)
            time.sleep(1)
            
            try:
                driver.execute_script("arguments[0].scrollIntoView();", save_btn)
                driver.execute_script("arguments[0].click();", save_btn)
            except: save_btn.click()
            
            time.sleep(5) 
            
            # صورة لكل محاولة عشان نعرف وش صار
            driver.save_screenshot(f"3_try_{attempt}_result.png")
            
            error_exists = False
            try:
                if driver.find_element(By.ID, "merchant_address_form_title-error").is_displayed():
                    error_exists = True
            except NoSuchElementException:
                error_exists = False
            
            if not error_exists:
                print(f"✨ تم الحفظ! الرمز: {current_code}")
                driver.save_screenshot("4_success.png") # صورة النجاح
                
                db.collection('orders').document(order_id).update({'status': 'done'})
                print("✅ تم التحديث في فايربيس.")
                return True
            
            print("   ⚠️ الرمز مكرر...")
            current_code = get_next_sequence_code() 

        driver.save_screenshot("5_failed_final.png")
        return False

    except Exception as e:
        print(f"❌ خطأ: {e}")
        driver.save_screenshot("99_crash.png")
        return False
    finally:
        driver.quit()

# ==================================================
# 3️⃣ التشغيل
# ==================================================
if __name__ == "__main__":
    try:
        orders = list(db.collection('orders').where('status', '==', 'pending').stream())
        if len(orders) > 0:
            for doc in orders:
                add_address_to_torod(doc.id, doc.to_dict())
        else:
            print("💤 لا توجد طلبات.")
    except Exception as e:
        print(f"❌ خطأ عام: {e}")
        sys.exit(1)
