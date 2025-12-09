/**
 * @file script.js
 * @description ملف التحكم في منطق الواجهة الأمامية
 * @copyright (c) 2025 [restavo] - جميع الحقوق محفوظة
 */
const API_BASE_URL = '/api';

let currentUser = null;
let userFavorites = {}; 
let authMode = 'login';
let pendingBookingData = null;

// ----------------------------------------------------------------------
// أدوات المساعدة
// ----------------------------------------------------------------------
function showToast(message, isError = false) {
    const toast = document.getElementById('toast-message');
    if (!toast) return;
    toast.textContent = message;
    toast.className = isError 
        ? 'fixed top-5 left-1/2 transform -translate-x-1/2 bg-red-600 text-white px-6 py-3 rounded-lg shadow-xl z-[70] transition-opacity duration-300'
        : 'fixed top-5 left-1/2 transform -translate-x-1/2 bg-green-600 text-white px-6 py-3 rounded-lg shadow-xl z-[70] transition-opacity duration-300';
    toast.style.opacity = '1';
    setTimeout(() => { toast.style.opacity = '0'; }, 3000);
}

// ----------------------------------------------------------------------
// إدارة المصادقة والبروفايل
// ----------------------------------------------------------------------
const authModal = document.getElementById('auth-modal');
const sidebar = document.getElementById('profile-sidebar');
const overlay = document.getElementById('sidebar-overlay');

function openAuthModal() {
    authModal.classList.remove('hidden');
    document.getElementById('email').focus();
}

function toggleSidebar() {
    const isClosed = sidebar.classList.contains('translate-x-full');
    if (isClosed) {
        sidebar.classList.remove('translate-x-full');
        overlay.classList.remove('hidden');
        fillProfileData();
    } else {
        sidebar.classList.add('translate-x-full');
        overlay.classList.add('hidden');
    }
}

function fillProfileData() {
    if(!currentUser) return;
    document.getElementById('profile-email').value = currentUser.username;
    document.getElementById('profile-fullname').value = currentUser.full_name || '';
    document.getElementById('profile-phone').value = currentUser.phone || '';
}

async function saveProfileData(e) {
    // نوقف الافتراضي إذا تم استدعاؤه كحدث
    if(e) e.preventDefault();
    
    const btn = document.getElementById('save-profile-btn');
    const originalText = btn.innerHTML;
    btn.innerHTML = 'جاري الحفظ...';
    btn.disabled = true;

    const data = {
        username: document.getElementById('profile-email').value, // الاسم الجديد (الإيميل)
        full_name: document.getElementById('profile-fullname').value,
        phone: document.getElementById('profile-phone').value,
        new_password: document.getElementById('profile-password').value
    };

    try {
        const res = await fetch(`${API_BASE_URL}/profile/update`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data)
        });
        const result = await res.json();
        if(res.ok) {
            showToast(result.message);
            currentUser.username = data.username;
            currentUser.full_name = data.full_name;
            currentUser.phone = data.phone;
            document.getElementById('profile-password').value = ''; 
            updateUserUI();
        } else {
            showToast(result.message, true);
        }
    } catch(e) { showToast("خطأ في الاتصال", true); }
    finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

async function checkLoginStatus() {
    try {
        const response = await fetch(`${API_BASE_URL}/status`);
        const data = await response.json();
        
        if (data.is_authenticated) {
            currentUser = data.user;
            await fetchAndRenderFavorites();
        } else {
            currentUser = null;
            userFavorites = {};
        }
        updateUserUI();
    } catch (error) { console.error(error); }
}

async function handleAuthSubmission(e) {
    e.preventDefault();
    const username = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    const age = document.getElementById('age').value;
    const endpoint = authMode === 'login' ? '/login' : '/register';
    const errorMsg = document.getElementById('auth-error-message');
    const btn = document.getElementById('auth-submit-btn');
    // 🔥 التحقق من السن قبل الإرسال 🔥
    if (authMode === 'register') {
        if (!age) {
            errorMsg.textContent = "الرجاء إدخال السن";
            errorMsg.classList.remove('hidden');
            return;
        }
        if (parseInt(age) < 18) {
            errorMsg.textContent = "عذراً، يجب أن يكون عمرك 18 عاماً أو أكثر للتسجيل.";
            errorMsg.classList.remove('hidden');
            return;
        }
    }
    btn.textContent = 'جاري المعالجة...';
    btn.disabled = true;
    errorMsg.classList.add('hidden');

    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password, age: age })
        });
        const result = await response.json();
        
        if (response.ok) {
            if (authMode === 'login') {
                currentUser = result.user;
                showToast(`مرحباً بك، ${result.user.full_name || result.user.username}`);
                authModal.classList.add('hidden');
                updateUserUI();
                await fetchAndRenderFavorites();
                if (pendingBookingData) { executeBooking(pendingBookingData); pendingBookingData = null; }
            } else {
                showToast('تم التسجيل! قم بتسجيل الدخول.');
                document.getElementById('login-tab').click();
            }
        } else {
            errorMsg.textContent = result.message;
            errorMsg.classList.remove('hidden');
        }
    } catch (error) {
        errorMsg.textContent = "خطأ في الاتصال";
        errorMsg.classList.remove('hidden');
    } finally {
        btn.textContent = authMode === 'login' ? 'تسجيل الدخول' : 'إنشاء حساب';
        btn.disabled = false;
    }
}

async function handleLogout() {
    await fetch(`${API_BASE_URL}/logout`, { method: 'POST' });
    currentUser = null;
    userFavorites = {};
    updateUserUI();
    toggleSidebar(); 
    showToast('تم تسجيل الخروج');
    document.getElementById('favorites-list').innerHTML = '';
    document.getElementById('bookings-list').innerHTML = '';
}

function updateUserUI() {
    const userBtn = document.getElementById('user-profile-btn');
    const userNameDisplay = document.getElementById('user-name-display');
    const authBtn = document.getElementById('auth-action-btn');
    
    if (currentUser) {
        userBtn.classList.remove('hidden');
        userNameDisplay.textContent = currentUser.full_name || currentUser.username.split('@')[0];
        authBtn.classList.add('hidden'); 
    } else {
        userBtn.classList.add('hidden');
        authBtn.classList.remove('hidden');
        authBtn.innerHTML = `<i data-lucide="user-plus" class="w-4 h-4"></i><span>دخول</span>`;
        authBtn.onclick = openAuthModal;
    }
    lucide.createIcons();
}

// ----------------------------------------------------------------------
// إدارة البحث (Real Search)
// ----------------------------------------------------------------------
async function handleSearch(e) {
    e.preventDefault();
    const city = document.getElementById('city').value;
    const list = document.getElementById('hotel-cards-list');
    
    list.innerHTML = '<p class="text-center p-10">جاري البحث عن الفنادق...</p>';
    
    try {
        const res = await fetch(`${API_BASE_URL}/search?city=${city}`);
        const hotels = await res.json();
        
        list.innerHTML = '';
        if (hotels.length === 0) {
            list.innerHTML = '<p class="text-center text-gray-500 py-10">لا توجد فنادق متاحة في هذه المدينة حالياً.</p>';
            return;
        }

        const checkIn = document.getElementById('check_in').value || new Date().toISOString().split('T')[0];
        const checkOut = document.getElementById('check_out').value || new Date(Date.now() + 86400000).toISOString().split('T')[0];

        hotels.forEach(h => {
           const isFav = userFavorites[h.name] ? 'text-red-500 fill-current' : 'text-gray-400';
            
            const correctImageUrl = h.image_url.replace('./static', ''); 

            const html = `
                <div class="bg-white rounded-xl shadow-lg mb-4 flex flex-col md:flex-row overflow-hidden border border-gray-100 hover:shadow-xl transition">
                    <div class="w-full md:w-56 bg-gray-200 h-56 md:h-auto relative group">
                        <img src="${correctImageUrl}" class="w-full h-full object-cover transition duration-500 group-hover:scale-110" >
                        <div class="absolute top-2 right-2 bg-white/90 px-2 py-1 rounded text-xs font-bold text-brand-color">⭐ ${h.rating}</div>
                    </div>
                    <div class="p-6 flex-grow flex flex-col justify-between">
                        <div class="flex justify-between items-start">
                            <div>
                                <h3 class="text-xl font-bold text-gray-900">${h.name}</h3>
                                <p class="text-gray-500 flex items-center gap-1"><i data-lucide="map-pin" class="w-3 h-3"></i> ${h.city}</p>
                            </div>
                            <button onclick="toggleFavorite('${h.name}', '${h.city}', this)" class="${isFav} hover:text-red-600 transition p-2 rounded-full hover:bg-red-50">
                                <i data-lucide="heart" class="w-6 h-6"></i>
                            </button>
                        </div>
                        <div class="flex justify-between items-end mt-4">
                            <div>
                                <span class="text-3xl font-bold text-green-700">$${h.price}</span>
                                <span class="text-sm text-gray-400">/ ليلة</span>
                            </div>
                          
                            <button onclick="bookHotel('${h.name}', '${h.city}', '${checkIn}', '${checkOut}', ${h.price})" class="bg-brand-color text-white px-6 py-2 rounded-lg hover:opacity-90 transition font-bold shadow-md" fdprocessedid="7ohfoi">
                                احجز الآن
                            </button>
                        </div>
                    </div>
                </div>
            `;
            list.insertAdjacentHTML('beforeend', html);
        });
        lucide.createIcons();
    } catch (e) {
        list.innerHTML = '<p class="text-center text-red-500">حدث خطأ أثناء البحث.</p>';
    }
}

// ----------------------------------------------------------------------
// إدارة الحجوزات والمفضلة
// ----------------------------------------------------------------------
window.bookHotel = async (hotelName, city, checkIn, checkOut, price) => {
    const bookingData = { hotel_name: hotelName, city, check_in: checkIn, check_out: checkOut, price };
    if (!currentUser) {
        pendingBookingData = bookingData;
        openAuthModal();
        showToast("الرجاء تسجيل الدخول لإتمام الحجز");
        return;
    }
   // 2. فتح نموذج التأكيد بدلاً من التنفيذ المباشر
    openBookingConfirmModal(bookingData);
};
let currentBookingData = null; // متغير جديد لحفظ بيانات الحجز الحالية

function openBookingConfirmModal(data) {
    currentBookingData = data;
    const modal = document.getElementById('booking-confirm-modal');
    
    // 🔥🔥 عناصر الاسم الجديدة 🔥🔥
    const nameInputGroup = document.getElementById('name-input-group');
    const nameInput = document.getElementById('confirm-name-input');
    // 🔥🔥 نهاية عناصر الاسم 🔥🔥

    const phoneInputGroup = document.getElementById('phone-input-group');
    const phoneInput = document.getElementById('confirm-phone-input');
    
    // ملء البيانات الثابتة
    document.getElementById('confirm-hotel-name').textContent = data.hotel_name;
    document.getElementById('confirm-city').textContent = data.city;
    document.getElementById('confirm-check-in').textContent = data.check_in;
    document.getElementById('confirm-check-out').textContent = data.check_out;
    document.getElementById('confirm-price').textContent = `$${data.price}`;
    
    // 🆕🔥 منطق اشتراط اسم الحجز (الاسم) 🆕🔥
    if (currentUser && currentUser.full_name) {
        nameInputGroup.classList.add('hidden');
        nameInput.removeAttribute('required');
        nameInput.value = currentUser.full_name; // تعبئة القيمة من بيانات المستخدم
    } else {
        nameInputGroup.classList.remove('hidden');
        nameInput.setAttribute('required', 'required'); // جعل الحقل مطلوبًا
        nameInput.value = '';
    }
    // 🆕🔥 نهاية منطق الاسم 🆕🔥

    // 🔥🔥 منطق اشتراط رقم الهاتف 🔥🔥
    if (currentUser && currentUser.phone) {
        phoneInputGroup.classList.add('hidden');
        phoneInput.removeAttribute('required');
        phoneInput.value = currentUser.phone;
    } else {
        phoneInputGroup.classList.remove('hidden');
        phoneInput.setAttribute('required', 'required');
        phoneInput.value = '';
    }
    // 🔥🔥 نهاية المنطق 🔥🔥
    
    modal.classList.remove('hidden');
    lucide.createIcons();
}



async function executeBooking(data) {
    
    // ⚠️ الخطوة الحاسمة: استخراج القيم من حقول الإدخال
    const confirmedPhone = document.getElementById('confirm-phone-input').value.trim();
    const confirmedName = document.getElementById('confirm-name-input').value.trim(); // استخراج قيمة الاسم
    
    // 1. التحقق من صحة الاسم
    const nameInputGroupIsVisible = !document.getElementById('name-input-group').classList.contains('hidden');
    if (nameInputGroupIsVisible && !confirmedName) {
        showToast("الرجاء إدخال اسم الحجز", true);
        document.getElementById('booking-confirm-modal').classList.remove('hidden'); 
        return; 
    }

    // 2. التحقق من صحة الهاتف
    const phoneInputGroupIsVisible = !document.getElementById('phone-input-group').classList.contains('hidden');
    if (phoneInputGroupIsVisible && !confirmedPhone) {
        showToast("الرجاء إدخال رقم الهاتف", true);
        document.getElementById('booking-confirm-modal').classList.remove('hidden');
        return; 
    }

    try {
        // إغلاق النموذج بعد التأكيد إذا كان مفتوحاً
        document.getElementById('booking-confirm-modal').classList.add('hidden');
        
        // 🆕 دمج الاسم ورقم الهاتف في بيانات الحجز قبل الإرسال
        const bookingDataToSend = {
            ...data,
            // نرسل الاسم الذي أدخله المستخدم أو الذي عُبئ تلقائياً
            booking_name: confirmedName, 
            booking_phone: confirmedPhone 
        };

        const response = await fetch(`${API_BASE_URL}/booking`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(bookingDataToSend)
        });
        if (response.ok) showToast(`✅ تم حجز ${data.hotel_name} بنجاح!`);
        else showToast(`❌ فشل الحجز`, true);
    } catch (error) { showToast("❌ خطأ في الاتصال", true); }
}



async function fetchAndRenderBookings() {
    const container = document.getElementById('bookings-list');
    container.innerHTML = '<p class="text-center p-4">جاري التحميل...</p>';
    try {
        const response = await fetch(`${API_BASE_URL}/bookings`);
        if (!response.ok) throw new Error();
        const bookings = await response.json();
        container.innerHTML = '';
        if (bookings.length === 0) {
            container.innerHTML = '<p class="text-center p-4 text-gray-500">لا توجد حجوزات حالياً.</p>';
            return;
        }
        bookings.forEach(booking => {
            const html = `
                <div class="bg-white p-4 rounded-lg shadow border mb-3 flex flex-col md:flex-row gap-4 items-center">
                    <div class="flex-grow text-center md:text-right">
                        <h4 class="font-bold text-lg">${booking.hotel_name}</h4>
                        <p class="text-gray-600 text-sm">${booking.city}</p>
                        <p class="text-xs text-gray-400">${booking.check_in} إلى ${booking.check_out}</p>
                    </div>
                    <div class="text-green-600 font-bold text-xl">$${booking.price}</div>
                    <div class="flex gap-2">
                        <button onclick="analyzeBooking(${booking.id})" class="bg-blue-100 text-blue-600 px-3 py-1 rounded text-sm hover:bg-blue-200">تحليل AI</button>
                        <button onclick="deleteBooking(${booking.id})" class="bg-red-100 text-red-600 px-3 py-1 rounded text-sm hover:bg-red-200">إلغاء</button>
                    </div>
                </div>
            `;
            container.insertAdjacentHTML('beforeend', html);
        });
    } catch (error) { container.innerHTML = '<p class="text-center text-red-500">سجل دخولك أولاً</p>'; }
}

window.deleteBooking = async (id) => {
    if(!confirm("هل أنت متأكد؟")) return;
    try {
        const res = await fetch(`${API_BASE_URL}/booking/${id}`, { method: 'DELETE' });
        if(res.ok) { showToast("تم الإلغاء"); fetchAndRenderBookings(); }
    } catch(e) { showToast("خطأ", true); }
}

window.toggleFavorite = async (hotelName, city, btnElement) => {
    if (!currentUser) { showToast("يجب تسجيل الدخول"); openAuthModal(); return; }
    try {
        const response = await fetch(`${API_BASE_URL}/favorites/toggle`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ item_name: hotelName, city })
        });
        const result = await response.json();
        if (result.success) {
            userFavorites[hotelName] = result.is_favorite;
            const icon = btnElement.querySelector('i');
            if (result.is_favorite) {
                btnElement.classList.add('text-red-500'); btnElement.classList.remove('text-gray-400');
                if(icon) icon.classList.add('fill-current');
            } else {
                btnElement.classList.remove('text-red-500'); btnElement.classList.add('text-gray-400');
                if(icon) icon.classList.remove('fill-current');
            }
            fetchAndRenderFavorites();
        }
    } catch (error) { showToast("خطأ", true); }
};

async function fetchAndRenderFavorites() {
    if (!currentUser) return;
    try {
        const response = await fetch(`${API_BASE_URL}/favorites`);
        if (!response.ok) return;
        const data = await response.json();
        userFavorites = {};
        data.forEach(item => userFavorites[item.item_name] = true);
        const count = data.length;
        document.getElementById('favorites-count').textContent = count;
        document.getElementById('favorites-count').classList.toggle('opacity-0', count === 0);
        
        const container = document.getElementById('favorites-list');
        container.innerHTML = '';
        data.forEach(fav => {
            container.insertAdjacentHTML('beforeend', `
                <div class="flex justify-between items-center bg-gray-50 p-3 rounded mb-2">
                    <div><p class="font-bold text-gray-800">${fav.item_name}</p><p class="text-xs text-gray-500">${fav.city}</p></div>
                    <button onclick="toggleFavorite('${fav.item_name}', '${fav.city}', this)" class="text-red-500 hover:text-red-700"><i data-lucide="trash-2" class="w-4 h-4"></i></button>
                </div>
            `);
        });
        lucide.createIcons();
    } catch (error) {}
}

// ----------------------------------------------------------------------
// الذكاء الاصطناعي (Chat & Analysis)
// ----------------------------------------------------------------------
async function sendMessage() {
    const input = document.getElementById('chat-input');
    const msg = input.value.trim();
    if (!msg) return;
    
    const container = document.getElementById('chat-messages');
    container.insertAdjacentHTML('beforeend', `<div class="flex justify-end mb-2"><div class="bg-blue-500 text-white p-2 rounded-lg max-w-[80%]">${msg}</div></div>`);
    input.value = '';
    
    try {
        const res = await fetch(`${API_BASE_URL}/gemini/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt: msg })
        });
        const data = await res.json();
        container.insertAdjacentHTML('beforeend', `<div class="flex justify-start mb-2"><div class="bg-gray-100 text-gray-800 p-2 rounded-lg max-w-[80%] border">${data.response}</div></div>`);
        container.scrollTop = container.scrollHeight;
    } catch (e) {}
}

window.analyzeBooking = async (id) => {
    const modal = document.getElementById('ai-analysis-modal');
    const content = document.getElementById('ai-analysis-content');
    modal.classList.remove('hidden');
    content.innerHTML = '<div class="text-center p-10"><p>جاري التحليل...</p></div>';
    // 🔥 تأكد من وجود هذا السطر ليعمل زر الإغلاق الجديد 🔥
    document.getElementById('ai-analysis-close-btn').addEventListener('click', () => {
        document.getElementById('ai-analysis-modal').classList.add('hidden');
    });
    // إغلاق النوافذ (تأكد أن هذا السطر يغطي زر الإغلاق لـ AI analysis modal)
    document.querySelectorAll('[id$="-close-btn"]').forEach(btn => btn.addEventListener('click', (e) => e.target.closest('.fixed').classList.add('hidden')));
    try {
        const res = await fetch(`${API_BASE_URL}/gemini/analyze`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ booking_id: id })
        });
        const data = await res.json();
        content.innerHTML = `
            <h3 class="text-xl font-bold text-brand-color mb-3">${data.title}</h3>
            <div class="mb-4 bg-blue-50 p-3 rounded"><p class="font-bold">💰 السعر:</p><p>${data.price_analysis}</p></div><div class="mb-4"><p class="font-bold mb-2>
            🗺️ أنشطة:<p><ul class="list-disc pr-5 text-sm space-y-1>${data.activity_suggestions.map(a => `<li><b>${a.name}:</b> ${a.reason}</li>`).join('')}</ul></div>
            <div class="bg-green-50 p-3 rounded text-sm text-green-800 border border-green-200"><b>💡 الخلاصة:</b> ${data.summary}</div>
        `;
    } catch (e) { 
        console.error("Analysis Error:", e);
        content.innerHTML = '<p class="text-red-500 text-center">فشل التحليل. تأكد منىأنك مسجل الدخول.</p>'; 
    
    }
}

// ----------------------------------------------------------------------
// تهيئة الصفحة
// ----------------------------------------------------------------------
document.addEventListener('DOMContentLoaded', () => {
    checkLoginStatus();
    
    document.getElementById('auth-form').addEventListener('submit', handleAuthSubmission);
    document.getElementById('search-form').addEventListener('submit', handleSearch);
    
    // 🔥 إصلاح الحفظ: استخدام الزر بدلاً من الفورم
    document.getElementById('save-profile-btn').addEventListener('click', saveProfileData);
    
    // أزرار التبديل
    document.getElementById('login-tab').onclick = () => {
        authMode = 'login';
        document.getElementById('login-tab').classList.add('border-brand-color', 'text-brand-text');
        document.getElementById('register-tab').classList.remove('border-brand-color', 'text-brand-text');
        document.getElementById('auth-submit-btn').textContent = 'تسجيل الدخول';
        document.getElementById('age-container').classList.add('hidden');
        document.getElementById('age').required = false;
    };
    document.getElementById('register-tab').onclick = () => {
        authMode = 'register';
        document.getElementById('register-tab').classList.add('border-brand-color', 'text-brand-text');
        document.getElementById('login-tab').classList.remove('border-brand-color', 'text-brand-text');
        document.getElementById('auth-submit-btn').textContent = 'إنشاء حساب جديد';
        document.getElementById('age-container').classList.remove('hidden');
        document.getElementById('age').required = true;
    };
    
    
    // إضافة Event Listener لزر تأكيد الحجز داخل النموذج الجديد
    document.getElementById('confirm-booking-btn').addEventListener('click', () => {
        if (currentBookingData) {
            executeBooking(currentBookingData);
            currentBookingData = null; // تفريغ بعد التنفيذ
        }
    });

    // إضافة Event Listener لزر إغلاق نموذج التأكيد
    document.getElementById('booking-confirm-close-btn').addEventListener('click', () => {
        document.getElementById('booking-confirm-modal').classList.add('hidden');
    });
    // إغلاق النوافذ
    document.querySelectorAll('[id$="-close-btn"]').forEach(btn => btn.addEventListener('click', (e) => e.target.closest('.fixed').classList.add('hidden')));
    
    // Sidebar
    document.getElementById('user-profile-btn').onclick = toggleSidebar;
    document.getElementById('profile-close-btn').onclick = toggleSidebar;
    document.getElementById('sidebar-overlay').onclick = toggleSidebar;
    document.getElementById('sidebar-logout-btn').onclick = handleLogout;

    // قوائم أخرى
    document.getElementById('bookings-toggle-btn').onclick = () => { document.getElementById('bookings-modal').classList.remove('hidden'); fetchAndRenderBookings(); };
    document.getElementById('favorites-toggle-btn').onclick = () => { document.getElementById('favorites-modal').classList.remove('hidden'); fetchAndRenderFavorites(); };
    
    // الشات
    document.getElementById('chat-toggle-btn').onclick = () => document.getElementById('chat-window').classList.toggle('hidden');
    document.getElementById('chat-send-btn').onclick = sendMessage;
    document.getElementById('chat-input').onkeypress = (e) => { if(e.key === 'Enter') sendMessage(); };
    
    // تعيين التاريخ الافتراضي
    document.getElementById('check_in').valueAsDate = new Date();
    document.getElementById('check_out').valueAsDate = new Date(Date.now() + 3 * 86400000);
    
    // بدء البحث التلقائي لدبي
    document.getElementById('search-form').dispatchEvent(new Event('submit'));
    
    lucide.createIcons();
});