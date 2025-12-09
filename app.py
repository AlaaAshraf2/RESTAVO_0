

# اسم المشروع: Restavo
# حقوق الملكية (c) 2025 - فريق مطوري Restavo
# جميع الحقوق محفوظة.
# 
# تم تطوير هذا الكود بواسطة:
# - الاء اشرف قاسم الضوي
# - اميرة اشرف عبد النعيم
# -يوسف احمد يوسف 
# ----------------------------------------------------
# ====================================================
#        Restavo Hotel Booking System - Backend
# ====================================================

# ------------------------------
# 1. استيراد المكتبات
# ------------------------------

import sqlite3                     # للتعامل مع قاعدة بيانات SQLite
import os                          # للتعامل مع نظام التشغيل والمسارات
import json                        # لتحويل البيانات من وإلى JSON
import re                          # للتحقق من النصوص باستخدام Regular Expressions
from datetime import datetime      # للتعامل مع التاريخ والوقت الحالي
from contextlib import closing     #  (جديد) استيراد مكتبة لإغلاق الاتصال تلقائياً

from flask import Flask, jsonify, request, send_from_directory, session
# Flask: لإنشاء السيرفر
# jsonify: لإرجاع البيانات بصيغة JSON
# request: لاستقبال البيانات من المستخدم
# send_from_directory: لإرسال الملفات الثابتة
# session: لتخزين بيانات الجلسة

from flask_cors import CORS        # للسماح بالاتصال بين الفرونت والباك
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required   # نظام تسجيل الدخول

from werkzeug.security import generate_password_hash, check_password_hash
# لتشفير كلمات المرور والتحقق منها

from dotenv import load_dotenv     # لقراءة متغيرات البيئة من ملف .env

import google.generativeai as genai  # لاستخدام الذكاء الاصطناعي (Gemini)


# ----------------------------------------------------
# 2. الإعدادات والتهيئة
# ----------------------------------------------------

load_dotenv()  # تحميل متغيرات البيئة

# جلب مفتاح Gemini من متغيرات البيئة
GOOGLE_API_KEY = os.environ.get("GEMINI_API_KEY")

# التحقق من وجود مفتاح API
if not GOOGLE_API_KEY:
    print("⚠️ تحذير: لم يتم العثور على GEMINI_API_KEY")
else:
    genai.configure(api_key=GOOGLE_API_KEY)

# اسم قاعدة البيانات
DATABASE_FILE = "my_app_data.db"

# المسار الأساسي للمشروع
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# مسار ملفات الـ static
STATIC_DIR = os.path.join(BASE_DIR, 'static',)

# إنشاء تطبيق Flask
app = Flask(__name__, static_folder=STATIC_DIR, static_url_path='')

# مفتاح أمان الجلسات
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'kjgtuyf*ytdS$rtyuf/fu675e65d')

# منع الوصول للكوكيز عبر JavaScript
app.config['SESSION_COOKIE_HTTPONLY'] = True 

# السماح بالكوكيز أثناء التطوير
app.config['SESSION_COOKIE_SECURE'] = False 

# تفعيل CORS
CORS(app, supports_credentials=True)

# ----------------------------------------------------
# 3. إعداد Login Manager
# ----------------------------------------------------

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # صفحة تسجيل الدخول الافتراضية

# رسالة عند محاولة الدخول بدون تسجيل
@login_manager.unauthorized_handler
def unauthorized():
    return jsonify({"message": "عذراً، يجب عليك تسجيل الدخول."}), 401

# ----------------------------------------------------
# 4. نموذج المستخدم
# ----------------------------------------------------

class User(UserMixin):
    def __init__(self, id, username, full_name=None, phone=None):
        self.id = id
        self.username = username
        self.full_name = full_name
        self.phone = phone

# تحميل المستخدم من قاعدة البيانات
@login_manager.user_loader
def load_user(user_id):
    return db_manager.get_user_by_id(user_id)

# ----------------------------------------------------
# 5. كلاس إدارة قاعدة البيانات
# ----------------------------------------------------

class DBManager:
    def __init__(self, db_file):
        self.db_file = db_file
        self.init_db()

    # إنشاء اتصال بقاعدة البيانات
    def get_connection(self):
        conn = sqlite3.connect(self.db_file, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        # 🟢 (تعديل) إرجاع الاتصال داخل closing ليتم إغلاقه تلقائياً عند انتهاء with
        return closing(conn)

    # إنشاء الجداول في قاعدة البيانات
    def init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # جدول المستخدمين
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    full_name TEXT,
                    phone TEXT,
                    age INTEGER       
                )
            ''')

            # إضافة أعمدة في حال كانت غير موجودة (للتوافق مع الإصدارات السابقة)
            try:
                cursor.execute("ALTER TABLE users ADD COLUMN full_name TEXT")
            except sqlite3.OperationalError: pass
            try:
                cursor.execute("ALTER TABLE users ADD COLUMN phone TEXT")
            except sqlite3.OperationalError: pass
            try:
                cursor.execute("ALTER TABLE users ADD COLUMN age INTEGER")
            except sqlite3.OperationalError: pass

            # جدول الحجوزات
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS bookings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    user_name TEXT NOT NULL,
                    hotel_name TEXT NOT NULL,
                    city TEXT NOT NULL,
                    check_in TEXT NOT NULL,
                    check_out TEXT NOT NULL,
                    price REAL NOT NULL,
                    hotel_image_url TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')

            # جدول المفضلة
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS favorites (
                    user_id INTEGER NOT NULL,
                    item_name TEXT NOT NULL,
                    city TEXT NOT NULL,
                    added_at TEXT NOT NULL,
                    PRIMARY KEY (user_id, item_name),
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')

            # جدول الفنادق
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS hotels (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    city TEXT NOT NULL,
                    price REAL NOT NULL,
                    rating REAL NOT NULL,
                    image_url TEXT
                )
            ''')

            conn.commit()
            self.seed_hotels()

    # إدخال بيانات الفنادق الافتراضية
    def seed_hotels(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM hotels")
            if cursor.fetchone()[0] == 0:
                hotels = [
                    ("Grand Hotel Dubai", "Dubai", 250, 4.8, "./static/image/Hotel1.jpg"),
                    ("Dubai Marina View", "Dubai", 300, 4.9, "./static/image/Hotel2.jpg"),
                    ("Palm Resort", "Dubai", 450, 5.0, "./static/image/Hotel3.jpg"),
                    ("Cairo Nile View", "Cairo", 120, 4.5, "./static/image/Hotel4.jpg"),
                    ("Pyramids Plaza", "Cairo", 150, 4.6, "./static/image/Hotel5.jpg"),
                    ("Riyadh Business Stay", "Riyadh", 200, 4.7, "./static/image/Hotel6.jpg"),
                    ("Kingdom Tower Hotel", "Riyadh", 350, 4.8, "./static/image/Hotel7.jpg"),
                    ("London Bridge Inn", "London", 180, 4.3, "./static/image/Hotel8.jpg"),
                    ("Hyde Park Suites", "London", 220, 4.6, "./static/image/Hotel9.jpg")
                ]
                cursor.executemany(
                    "INSERT INTO hotels (name, city, price, rating, image_url) VALUES (?, ?, ?, ?, ?)",
                    hotels
                )
                conn.commit()

    # جلب الفنادق كنص للذكاء الاصطناعي
    def get_all_hotels_formatted(self):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name, city, price, rating FROM hotels")
                hotels = cursor.fetchall()
                if not hotels:
                    return "لا توجد بيانات فنادق حالياً."
                hotel_list = "\n".join([
                    f"- {h['name']} في {h['city']} (السعر: ${h['price']}, التقييم: {h['rating']}⭐)"
                    for h in hotels
                ])
                return hotel_list
        except Exception:
            return "غير قادر على جلب بيانات الفنادق."

    # تسجيل مستخدم جديد
    def register_user(self, username, password, age):
        if not age:
            return False, "السن مطلوب"
        try:
            if int(age) < 18:
                return False, "يجب أن يكون عمرك 18 عاماً أو أكثر"
        except ValueError:
            return False, "السن غير صالح"

        if len(password) < 8:
            return False, "كلمة المرور قصيرة جداً"

        if not re.match(r"[^@]+@[^@]+\.[^@]+", username):
            return False, "البريد الإلكتروني غير صالح"

        try:
            password_hash = generate_password_hash(password)
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO users (username, password_hash, age) VALUES (?, ?, ?)",
                    (username, password_hash, age)
                )
                conn.commit()
                return True, "تم التسجيل بنجاح"
        except sqlite3.IntegrityError:
            return False, "المستخدم موجود مسبقاً"

    # التحقق من بيانات المستخدم عند تسجيل الدخول
    def verify_user(self, username, password):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
            user_data = cursor.fetchone()
            if user_data and check_password_hash(user_data['password_hash'], password):
                return User(
                    user_data['id'],
                    user_data['username'],
                    user_data['full_name'],
                    user_data['phone']
                )
        return None

    # جلب مستخدم حسب ID
    def get_user_by_id(self, user_id):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            data = cursor.fetchone()
            if data:
                return User(data['id'], data['username'], data['full_name'], data['phone'])
        return None

    # تحديث بيانات الملف الشخصي
    def update_user_profile(self, user_id, new_username, full_name, phone, new_password=None):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # التحقق من أن البريد غير مستخدم من شخص آخر
                cursor.execute(
                    "SELECT id FROM users WHERE username = ? AND id != ?",
                    (new_username, user_id)
                )
                if cursor.fetchone():
                    return False, "البريد الإلكتروني مستخدم بالفعل"

                if new_password:
                    pw_hash = generate_password_hash(new_password)
                    cursor.execute(
                        "UPDATE users SET username = ?, full_name = ?, phone = ?, password_hash = ? WHERE id = ?",
                        (new_username, full_name, phone, pw_hash, user_id)
                    )
                else:
                    cursor.execute(
                        "UPDATE users SET username = ?, full_name = ?, phone = ? WHERE id = ?",
                        (new_username, full_name, phone, user_id)
                    )

                conn.commit()
                return True,"تم تحديث الملف الشخصي بنجاح"
        except Exception as e:
            print(f"Error updating profile: {e}")
            return False,"خطأ في قاعدة البيانات"

    # البحث عن فنادق حسب المدينة
    def search_hotels(self, city):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM hotels WHERE city = ? COLLATE NOCASE",
                (city,)
            )
            return [dict(row) for row in cursor.fetchall()]

    # إضافة حجز جديد
    def add_booking(self, user_id, booking_name, data):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO bookings (
                        user_id, user_name, hotel_name, city,
                        check_in, check_out, price, hotel_image_url
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    user_id, booking_name,
                    data['hotel_name'], data['city'],
                    data['check_in'], data['check_out'],
                    data['price'], data.get('hotel_image_url')
                ))
                conn.commit()
                return cursor.lastrowid
        except Exception:
            return None

    # جلب حجوزات المستخدم
    def get_user_bookings(self, user_id):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM bookings WHERE user_id = ? ORDER BY id DESC",
                (user_id,)
            )
            return [dict(row) for row in cursor.fetchall()]

    # حذف حجز
    def delete_booking(self, booking_id, user_id):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM bookings WHERE id = ? AND user_id = ?",
                    (booking_id, user_id)
                )
                conn.commit()
                return cursor.rowcount > 0
        except Exception:
            return False

    # جلب حجز واحد بالـ id
    def get_booking_by_id(self, booking_id, user_id):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM bookings WHERE id = ? AND user_id = ?",
                (booking_id, user_id)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    # إضافة أو إزالة من المفضلة
    def toggle_favorite(self, user_id, item_name, city):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT 1 FROM favorites WHERE user_id = ? AND item_name = ?",
                    (user_id, item_name)
                )

                if cursor.fetchone():
                    cursor.execute(
                        "DELETE FROM favorites WHERE user_id = ? AND item_name = ?",
                        (user_id, item_name)
                    )
                    conn.commit()
                    return False
                else:
                    cursor.execute(
                        "INSERT INTO favorites (user_id, item_name, city, added_at) VALUES (?, ?, ?, ?)",
                        (user_id, item_name, city, datetime.now().isoformat())
                    )
                    conn.commit()
                    return True
        except Exception:
            return None

    # جلب المفضلة الخاصة بالمستخدم
    def get_user_favorites(self, user_id):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT item_name, city FROM favorites WHERE user_id = ?",
                (user_id,)
            )
            return [dict(row) for row in cursor.fetchall()]

    # تحديث رقم الهاتف فقط
    def update_user_phone(self, user_id, phone):
        try:
            conn = self.get_connection()
            conn.execute(
                "UPDATE users SET phone = ? WHERE id = ?",
                (phone, user_id)
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        except Exception as e:
            print(f"Error updating phone: {e}")
            return False

# إنشاء مدير قاعدة البيانات
db_manager = DBManager(DATABASE_FILE)

# ----------------------------------------------------
# 6. المسارات (Routes)
# ----------------------------------------------------

@app.route('/')
def index():
    return send_from_directory(STATIC_DIR, 'index.html')

@app.route('/api/search', methods=['GET'])
def search_hotels():
    city = request.args.get('city', 'Dubai')
    results = db_manager.search_hotels(city)
    return jsonify(results)

@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json(silent=True) or {}
    success, msg = db_manager.register_user(
        data.get('username'),
        data.get('password'),
        data.get('age')
    )
    if success:
        return jsonify({"message": msg}), 201
    return jsonify({"message": msg}), 400

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or {}
    user = db_manager.verify_user(
        data.get('username'),
        data.get('password')
    )
    if user:
        login_user(user)
        return jsonify({
            "message": "تم الدخول", 
            "user": {
                "id": user.id,
                "username": user.username,
                "full_name": user.full_name,
                "phone": user.phone
            }
        }), 200
    return jsonify({"message": "بيانات الدخول غير صحيحة"}), 401

@app.route('/api/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({"message": "تم تسجيل الخروج"}), 200

@app.route('/api/status', methods=['GET'])
def auth_status():
    if current_user.is_authenticated:
        return jsonify({
            "is_authenticated": True, 
            "user": {
                "id": current_user.id, 
                "username": current_user.username,
                "full_name": current_user.full_name,
                "phone": current_user.phone
            }
        })
    return jsonify({"is_authenticated": False})

@app.route('/api/profile/update', methods=['POST'])
@login_required
def update_profile():
    data = request.get_json(silent=True) or {}
    # إذا لم يتم توفير اسم مستخدم جديد، استخدم الحالي
    new_username = data.get('username', current_user.username)
    full_name = data.get('full_name')
    phone = data.get('phone')
    new_password = data.get('new_password')

    if not new_username or '@' not in new_username:
         return jsonify({"message": "بريد إلكتروني غير صالح"}), 400

    success, msg = db_manager.update_user_profile(
        current_user.id,
        new_username,
        full_name,
        phone,
        new_password
    )

    if success:
        current_user.username = new_username
        current_user.full_name = full_name
        current_user.phone = phone

        return jsonify({"message": "تم تحديث الملف الشخصي بنجاح"}), 200

    return jsonify({"message": msg}), 400

@app.route('/api/booking', methods=['POST'])
@login_required
def create_booking():
    data = request.get_json(silent=True) or {}

    user_booking_name = data.get('booking_name')

    if not user_booking_name:
        return jsonify({"message": "اسم الحجز مطلوب"}), 400

    res = db_manager.add_booking(
        current_user.id,
        user_booking_name,
        data
    )

    return jsonify({"message": "تم الحجز بنجاح", "id": res}), 200 if res else (jsonify({"message": "فشل في إضافة الحجز"}), 500)

@app.route('/api/bookings', methods=['GET'])
@login_required
def get_bookings():
    return jsonify(db_manager.get_user_bookings(current_user.id))

@app.route('/api/booking/<int:booking_id>', methods=['DELETE'])
@login_required
def delete_booking(booking_id):
    if db_manager.delete_booking(booking_id, current_user.id):
        return jsonify({"message": "تم الإلغاء"})
    return jsonify({"message": "خطأ"}), 400

@app.route('/api/favorites', methods=['GET'])
@login_required
def get_favorites():
    return jsonify(db_manager.get_user_favorites(current_user.id))

@app.route('/api/favorites/toggle', methods=['POST'])
@login_required
def toggle_favorite():
    data = request.get_json(silent=True) or {}
    res = db_manager.toggle_favorite(
        current_user.id,
        data.get('item_name'),
        data.get('city')
    )
    return jsonify({"success": True, "is_favorite": res})

# ----------------------------------------------------
# 4. الذكاء الاصطناعي (حقن البيانات الديناميكية)
# ----------------------------------------------------
@app.route('/api/gemini/chat', methods=['POST'])
def gemini_chat():
    data = request.get_json(silent=True) or {}
    user_prompt = data.get('prompt')
    if not user_prompt: return jsonify({"response": "..."}), 400
    
    # جلب بيانات الفنادق الحقيقية من قاعدة البيانات
    hotels_context = db_manager.get_all_hotels_formatted()
    
    # 🌟 التعليمات مع حقن البيانات
    SYSTEM_INSTRUCTION_TEXT = f"""
    أنت المساعد الذكي لتطبيق "Restavo" المتخصص في حجز الفنادق.
    
    🛑 **قاعدة صارمة جداً:** لديك قائمة محددة من الفنادق التي يدعمها التطبيق. **يجب عليك الاقتراح والإجابة بناءً على هذه القائمة فقط.**
    لا تخترع فنادق غير موجودة، ولا تقترح فنادق خارجية (مثل Booking.com وغيرها).
    
    🏨 **قائمة الفنادق المتاحة لدينا:**
    {hotels_context}
    
    تعليمات إضافية:
    1. إذا سأل المستخدم عن فندق في مدينة موجودة في القائمة أعلاه، اقترح عليه الخيارات المتاحة مع ذكر السعر.
    2. إذا سأل عن مدينة غير موجودة (مثلاً باريس)، اعتذر بلطف وقل أننا لا نخدم هذه المدينة حالياً.
    3. تحدث باللغة العربية بأسلوب مفيد ومختصر.
    """

    # التعامل مع الذاكرة (إعادة تعيين إذا تغيرت التعليمات أو البيانات)
    # ملاحظة: بما أن بيانات الفنادق قد تتغير، قد نحتاج لتحديث الـ System Prompt دائماً
    # ولكن للتبسيط هنا، سنقوم بإعادة إنشاء المحادثة إذا كانت فارغة أو إذا أردنا تحديث السياق في كل مرة.
    # الخيار الأفضل هنا هو إرسال التاريخ كاملاً مع التعليمات الجديدة في كل طلب إذا أمكن، 
    # أو الاعتماد على أن Gemini يتذكر السياق في الجلسة الواحدة.
    
    # هنا سنقوم ببدء جلسة جديدة إذا لم توجد، وسنستخدم الـ System Prompt المحدث.
    chat_history = session.get('chat_history', [])
    
    # للتحقق مما إذا كان السياق قديماً (اختياري، لكن هنا سنفترض التجديد عند الحاجة)
    # سنقوم ببناء history جديد يبدأ دائماً بالتعليمات المحدثة لضمان دقة البيانات
    if not chat_history or chat_history[0].get('parts')[0] != SYSTEM_INSTRUCTION_TEXT:
         chat_history = [
            {"role": "user", "parts": [SYSTEM_INSTRUCTION_TEXT]},
            {"role": "model", "parts": ["فهمت. سأقترح الفنادق الموجودة في القائمة المتاحة فقط."]}
        ]
    
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        chat = model.start_chat(history=chat_history)
        response = chat.send_message(user_prompt)
        session['chat_history'] = [message_to_dict(m) for m in chat.history]
        return jsonify({"response": response.text})
    except Exception: return jsonify({"response": "خطأ في الاتصال"}), 500

@app.route('/api/gemini/analyze', methods=['POST'])
@login_required
def gemini_analyze():
    data = request.get_json(silent=True) or {}
    booking = db_manager.get_booking_by_id(data.get('booking_id'), current_user.id)
    if not booking: return jsonify({"message": "Not found"}), 404
    
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = f"حلل حجز فندق {booking['hotel_name']} في {booking['city']} بسعر {booking['price']}. JSON format: title, price_analysis, activity_suggestions (list of {{name, reason}}), summary."
        response = model.generate_content(prompt, generation_config=genai.GenerationConfig(response_mime_type="application/json"))
        return jsonify(json.loads(response.text))
    except Exception: return jsonify({"message": "Error"}), 500

def message_to_dict(message):
    return {'role': message.role, 'parts': [part.text for part in message.parts]}
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)