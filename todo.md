## Task Todo

- [ ] **Phase 1: تحليل الملفات المقدمة**
  - [x] قراءة ملف PDF لفهم التعديلات المطلوبة.

- [ ] **Phase 2: استخراج وتحليل ملفات البوت**
  - [x] استخراج ملفات البوت من الأرشيف المضغوط.
  - [x] عرض محتويات مجلد البوت.

- [ ] **Phase 3: تطبيق تعديلات ربط المستخدمين للدردشة**
  - [x] تعديل `handlers/search_handlers.py` لتضمين `set_chat_partner` وبدء الدردشة.
  - [x] تعديل `core/session.py` لإضافة `set_chat_partner` و `get_chat_partner`.

- [ ] **Phase 4: تطبيق تعديلات إرسال سجل المحادثة للمشرفين**
  - [x] تعديل `user_handlers.py` لتجميع سجل الدردشة وإرساله عند انقطاع الشريك.
  - [x] تعديل `core/message_forwarder.py` لإضافة `forward_chat_log`.

- [ ] **Phase 5: تطبيق تعديلات ترقية المستخدم للبريميوم**
  - [x] تعديل `core/message_forwarder.py` لإضافة زر "ترقية هذا المستخدم" بعد إرسال إثبات الدفع.
  - [x] تعديل `handlers/admin_handlers.py` لإضافة دالة `toggle_premium_callback`.
  - [x] تعديل `core/database.py` (أو ما يعادله) لتحديث حقول `premium` و `premium_expiry`.
  - [x] تسجيل `CallbackQueryHandler` في `dispatcher`.- [x] **Phase 6: مراجعة وتحديث ملفات الترجمة**
  - [x] مراجعة وتوحيد مفاتيح الترجمة بين اللغات.
  - [x] التأكد من وجود زر "⬅️ رجوع" والتسميات في ملفات الترجمة.`user_handlers.py` وآخرين.

- [x] **Phase 7: إعداد البوت للعمل على منصة Render**
  - [x] إنشاء ملف `Procfile`.
  - [x] تحديث `requirements.txt`.
  - [x] تعديل `main.py` للحصول على التوكن من المتغير البيئي.
  - [x] التأكد من تفعيل `polling` وليس `webhook`.
  - [ ] إضافة متغير `TELEGRAM_TOKEN` في تبويب `Environment` داخل Render.

- [ ] **Phase 8: تسليم النتائج النهائية للمستخدم**
  - [ ] إرسال الملفات المعدلة والتعليمات للمستخدم.

