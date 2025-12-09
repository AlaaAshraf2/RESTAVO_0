# test_app.py

import pytest
import json
import os
import time
from werkzeug.security import check_password_hash

# 💡 ملاحظة: يجب أن يكون ملف app.py في نفس المجلد
# نستورد التطبيق (app)، وكلاس إدارة قاعدة البيانات (DBManager)، ووظيفة توليد الهاش
from app import app, DBManager, generate_password_hash

# 📌 اسم قاعدة بيانات الاختبار المؤقتة
TEST_DATABASE_FILE = "test_app_data.db"

# 🛠️ دالة مساعدة لحذف الملف بأمان (تحاول عدة مرات إذا كان مشغولاً)
def safe_remove_db(db_file):
    if os.path.exists(db_file):
        for _ in range(5):  # 5 attempts
            try:
                os.remove(db_file)
                break
            except PermissionError:
                time.sleep(0.1)  # Wait 100ms
        else:
            print(f"Warning: Could not remove {db_file} after retries.")

# 🛠️ Fixture: إعداد عميل الاختبار وقاعدة البيانات المؤقتة
# -----------------------------------------------------------
@pytest.fixture
def client(monkeypatch):
    """
    يقوم بإعداد تطبيق Flask لعملية الاختبار:
    1. يضبط وضع الاختبار.
    2. ينشئ قاعدة بيانات SQLite مؤقتة.
    3. يوفر عميل اختبار لإجراء الطلبات.
    4. يقوم بالتنظيف وحذف قاعدة البيانات المؤقتة بعد الانتهاء.
    """
    
    # 1. إعداد التطبيق لـ TESTING
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'kjgtuyf*ytdS$rtyuf/fu675e65d'
    # هذه السطر حيوي: يسمح للجلسات بالعمل في بيئة الاختبار بدون HTTPS
    app.config['SESSION_COOKIE_SECURE'] = False 

    # 2. إنشاء DBManager جديدة وموجهة لقاعدة بيانات الاختبار
    safe_remove_db(TEST_DATABASE_FILE)
        
    db_manager = DBManager(TEST_DATABASE_FILE)
    
    # استبدال مدير قاعدة البيانات الأصلي بالنسخة المؤقتة للاختبار
    monkeypatch.setattr('app.db_manager', db_manager)
    
    # 3. استخدام عميل الاختبار. يجب أن تكون جميع طلبات الجلسة داخل الـ `with` block
    with app.test_client() as client:
        yield client

    # 4. التنظيف بعد الاختبارات
    # نغلق الاتصال إذا كان هناك أي مرجع معلق (اختياري، لكن جيد للتأكيد)
    # في app.py قمنا بإصلاح DBManager ليغلق الاتصالات فوراً، لذا الحذف هنا يجب أن ينجح.
    safe_remove_db(TEST_DATABASE_FILE)


def register_test_user(client, username='test@example.com', password='password123'):
    """
    وظيفة مساعدة لتسجيل مستخدم، وتجنب تكرار الكود.
    """
    client.post('/api/register', json={
        'username': username,
        'password': password,
        'age': 25 # سن آمن فوق الـ 18
    })


# 🚀 اختبار المسارات العامة (Routes)
# -----------------------------------------------

def test_index_route(client):
    """اختبار مسار الصفحة الرئيسية /"""
    response = client.get('/')
    assert response.status_code == 200
    assert 'text/html' in response.content_type

def test_search_hotels_default(client):
    """اختبار مسار البحث الافتراضي (بدون تحديد مدينة)"""
    response = client.get('/api/search')
    data = json.loads(response.data)
    assert response.status_code == 200
    assert len(data) > 0 
    assert all(h['city'] == 'Dubai' for h in data) # يجب أن يكون الافتراضي هو دبي

def test_search_hotels_with_city(client):
    """اختبار مسار البحث مع تحديد مدينة معينة"""
    response = client.get('/api/search?city=Cairo')
    data = json.loads(response.data)
    assert response.status_code == 200
    # يجب أن تكون هناك نتائج من Cairo (حسب بيانات الـ seed)
    assert any(h['city'] == 'Cairo' for h in data)


# 🔐 اختبار تدفق تسجيل الدخول/الخروج
# ------------------------------------------------

def test_register_and_login_flow(client):
    """اختبار التسجيل، ثم الدخول، ثم التحقق من الحالة، ثم الخروج."""
    new_user = 'flow_test@app.com'
    new_password = 'flowpassword'

    # 1. التسجيل الناجح
    register_response = client.post('/api/register', json={
        'username': new_user,
        'password': new_password,
        'age': 35
    })
    assert register_response.status_code == 201
    # 🌟 تم التعديل: التحقق من رسالة النجاح بدلاً من 'token'
    assert json.loads(register_response.data)['message'] == "تم التسجيل بنجاح" 

    # 2. محاولة التسجيل بنفس المستخدم (فشل)
    fail_register_response = client.post('/api/register', json={
        'username': new_user,
        'password': new_password,
        'age': 35
    })
    assert fail_register_response.status_code == 400
    assert json.loads(fail_register_response.data)['message'] == "المستخدم موجود مسبقاً"

    # 3. تسجيل الدخول الناجح
    login_response = client.post('/api/login', json={
        'username': new_user,
        'password': new_password
    })
    assert login_response.status_code == 200
    # 🌟 تم التعديل: الآن يجب أن يحتوي على 'user' بدلاً من 'token' بناءً على كود app.py
    data = json.loads(login_response.data)
    assert 'user' in data
    assert 'username' in data['user']

    # 4. التحقق من حالة الدخول
    status_response = client.get('/api/status')
    assert status_response.status_code == 200
    assert json.loads(status_response.data)['is_authenticated'] == True

    # 5. تسجيل الخروج
    logout_response = client.post('/api/logout')
    assert logout_response.status_code == 200

    # 6. التحقق من حالة الدخول بعد الخروج
    status_after_logout = client.get('/api/status')
    assert json.loads(status_after_logout.data)['is_authenticated'] == False

def test_register_underage_failure(client):
    """اختبار فشل التسجيل إذا كان السن أقل من 18 (قيد العمل)."""
    underage_user = 'kid@app.com'
    underage_password = 'childpassword'
    
    # محاولة التسجيل بعمر 17
    register_response = client.post('/api/register', json={
        'username': underage_user,
        'password': underage_password,
        'age': 17 # أقل من 18
    })
    
    # 1. التأكد من فشل التسجيل
    assert register_response.status_code == 400
    
    # 2. التأكد من رسالة الخطأ الصحيحة (حسب app.py)
    response_data = json.loads(register_response.data)
    assert response_data['message'] == "يجب أن يكون عمرك 18 عاماً أو أكثر"
    
    # 3. التأكد من أن المستخدم لم يتم إنشاؤه في قاعدة البيانات (اختياري لكن جيد)
    # محاولة الدخول بهذا المستخدم يجب أن تفشل
    login_fail_response = client.post('/api/login', json={
        'username': underage_user,
        'password': underage_password
    })
    assert login_fail_response.status_code == 401

# 🚫 اختبار الحماية (Unauthorized Access)
# ------------------------------------------------

def test_protected_routes_unauthorized(client):
    """اختبار أن جميع المسارات المحمية تتطلب 401 بدون تسجيل دخول."""
    
    # قائمة ببعض المسارات التي تتطلب @login_required
    protected_routes = [
        ('/api/profile/update', 'POST'),
        ('/api/booking', 'POST'),
        ('/api/bookings', 'GET'),
        ('/api/favorites', 'GET')
    ]
    
    for route, method in protected_routes:
        # استخدام client.open لإجراء الطلب
        if method == 'POST':
            response = client.open(route, method=method, json={}) 
        else:
            response = client.open(route, method=method)
            
        assert response.status_code == 401, f"Route {route} did not return 401"
        assert json.loads(response.data)['message'] == "عذراً، يجب عليك تسجيل الدخول."

# 👤 اختبار الملف الشخصي والحجوزات والمفضلة
# ------------------------------------------------

def test_user_profile_update(client):
    """اختبار تحديث الملف الشخصي وتغيير كلمة المرور."""
    
    # 1. التسجيل
    register_test_user(client, username='update_test@app.com', password='oldpassword')
    
    # 2. تسجيل الدخول: يجب أن يتم في نفس الدالة للاحتفاظ بالجلسة
    client.post('/api/login', json={'username': 'update_test@app.com', 'password': 'oldpassword'})

    # 3. تحديث البيانات
    new_data = {
        'username': 'update_test_new@app.com', # يجب تحديث اسم المستخدم أيضاً إذا كان ممكناً
        'full_name': 'Test User Full Name',
        'phone': '01011112222',
        'new_password': 'newstrongpassword'
    }

    response = client.post('/api/profile/update', json=new_data)
    assert response.status_code == 200
    assert json.loads(response.data)['message'] == "تم تحديث الملف الشخصي بنجاح"
    
    # 4. تسجيل الخروج
    client.post('/api/logout')

    # 5. التأكد من أن كلمة المرور القديمة لا تعمل
    login_fail_response = client.post('/api/login', json={'username': 'update_test_new@app.com', 'password': 'oldpassword'})
    assert login_fail_response.status_code == 401

    # 6. التأكد من أن كلمة المرور الجديدة تعمل
    login_success_response = client.post('/api/login', json={'username': 'update_test_new@app.com', 'password': 'newstrongpassword'})
    assert login_success_response.status_code == 200

def test_booking_and_favorites(client):
    """اختبار تدفق الحجز والمفضلة والحذف."""
    
    # 1. التسجيل
    register_test_user(client, username='booking_test@app.com', password='pass12345')
    
    # 2. تسجيل الدخول
    client.post('/api/login', json={'username': 'booking_test@app.com', 'password': 'pass12345'})
    
    # 3. إضافة حجز
    booking_data = {
        "booking_name": "Family Trip",
        "hotel_name": "Luxury Resort",
        "city": "Dubai",
        "check_in": "2025-12-15",
        "check_out": "2025-12-20",
        "price": 300.0,
        "hotel_image_url": "dummy_url.jpg"
    }
    
    add_booking_response = client.post('/api/booking', json=booking_data)
    assert add_booking_response.status_code == 200
    booking_id = json.loads(add_booking_response.data)['id']
    assert booking_id is not None

    # 4. جلب الحجوزات والتأكد من وجود الحجز
    get_bookings_response = client.get('/api/bookings')
    assert get_bookings_response.status_code == 200 # تأكيد النجاح قبل التحميل
    bookings = json.loads(get_bookings_response.data)
    assert len(bookings) == 1
    assert bookings[0]['hotel_name'] == "Luxury Resort"

    # 5. إضافة فندق للمفضلة
    toggle_fav_response = client.post('/api/favorites/toggle', json={
        "item_name": "Luxury Resort",
        "city": "Dubai"
    })
    assert toggle_fav_response.status_code == 200
    assert json.loads(toggle_fav_response.data)['is_favorite'] == True

    # 6. جلب المفضلة والتأكد من وجودها
    get_favs_response = client.get('/api/favorites')
    assert get_favs_response.status_code == 200 # تأكيد النجاح قبل التحميل
    favorites = json.loads(get_favs_response.data)
    assert len(favorites) == 1
    assert favorites[0]['item_name'] == "Luxury Resort"

    # 7. حذف الحجز
    delete_booking_response = client.delete(f'/api/booking/{booking_id}')
    assert delete_booking_response.status_code == 200
    
    # 8. التأكد من حذف الحجز
    get_bookings_after_delete = client.get('/api/bookings')
    assert len(json.loads(get_bookings_after_delete.data)) == 0

    # 9. إزالة الفندق من المفضلة (Toggle يُعيد False)
    toggle_remove_fav_response = client.post('/api/favorites/toggle', json={
        "item_name": "Luxury Resort",
        "city": "Dubai"
    })
    assert toggle_remove_fav_response.status_code == 200
    assert json.loads(toggle_remove_fav_response.data)['is_favorite'] == False
    
    # 10. التأكد من إزالة المفضلة
    get_favs_after_remove = client.get('/api/favorites')
    assert len(json.loads(get_favs_after_remove.data)) == 0