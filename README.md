# CyberGuard KKU — implementation milestone 2
รุ่นไม่มี Login: React + Vite + Tailwind / Django REST Framework

## ทำงานแล้ว
- ตรวจ URL โดยไม่เชื่อมต่อปลายทาง พร้อมเหตุผล โฮสต์จริง และคะแนนกฎทดลอง
- บันทึกเฉพาะผลรวมและรหัสกฎ ไม่เก็บ URL ต้นฉบับ
- สถิติรวมจริง กรองวัน และคำนวณวันตาม Asia/Bangkok
- หน้าแรกตามภาพอ้างอิง พร้อมเมนูตรวจสอบ เรียนรู้ ประวัติ และสถิติ รองรับมือถือ
- ตรวจข้อความด้วยกฎทดลอง 4 กลุ่ม พร้อมผลลิงก์ภายใน นับการส่งข้อความเพียงครั้งเดียว
- บทเรียนสั้น 5 บท และแบบฝึกหัด 5 ข้อพร้อมเฉลย ตรวจคะแนนที่ Backend
- ประวัติ localStorage สูงสุด 50 รายการ ค้นหา ดูผล ลบ และปิดการบันทึกได้
- migration ครบ 7 ตารางตาม ERD v2; บทเรียนและแบบฝึกหัดปัจจุบันเป็นเนื้อหาคงที่ ยังไม่ใช้ตารางข้อสอบ
- unique request_key ป้องกัน retry เพิ่มยอด; ส่งซ้ำคืน 409 ไม่เปิดเผยผลเดิม

## ยังไม่ทำใน milestone นี้
คลังข้อสอบฉบับเต็มที่ผ่านการตรวจทาน การเชื่อมตารางข้อสอบและ snapshot/cleanup และ deploy ออนไลน์
คะแนน/threshold เป็นกฎทดลอง ยังไม่มีการประเมิน precision/recall และไม่ใช่ความน่าจะเป็น

## เริ่มบน Windows
ต้องมี Python 3.12+ และ Node ที่รองรับ Vite 7
```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
cd frontend
npm.cmd ci
npm.cmd run build
cd ../backend
../.venv/Scripts/python.exe manage.py migrate
../.venv/Scripts/python.exe manage.py runserver 127.0.0.1:8000
```
เปิด http://127.0.0.1:8000
ถ้าใช้ Python ที่ติดมากับ Codex และ ensurepip ใช้ไม่ได้ ให้ใช้ Python หลักรัน pip --python .venv/Scripts/python.exe install -r backend/requirements.txt
พัฒนา UI ด้วย npm run dev ที่ port 5173; Vite proxy /api ไป Django 8000

## ฐานข้อมูล
ถ้าไม่ตั้ง DATABASE_URL จะใช้ SQLite เฉพาะเครื่องพัฒนาเพื่อให้เปิดได้ทันที
มี compose.yaml สำหรับ PostgreSQL ในเครื่องที่มี Docker:
docker compose up -d db
ตั้ง DATABASE_URL ตาม backend/.env.example แล้ว migrate ใหม่
settings ไม่อ่าน .env อัตโนมัติ ต้องตั้ง environment variables เอง
Production DEBUG=0 บังคับ PostgreSQL และ SECRET_KEY
ยังไม่ได้ทดสอบ PostgreSQL ในเครื่องที่ไม่มี Docker/PostgreSQL

## ทดสอบ
Backend: cd backend แล้ว ../.venv/Scripts/python.exe manage.py test scanner
Django สร้างฐานข้อมูลทดสอบแยก ไม่ใช้ผลจริง
Browser: ใช้ฐานข้อมูลสาธิตแยก ตั้ง DATABASE_URL=sqlite:///absolute/path/e2e.sqlite3
migrate และ runserver 127.0.0.1:8001 --noreload จากนั้น frontend: npx playwright test
Playwright ใช้ port 8001 เป็นค่าเริ่มต้น; เปลี่ยนด้วย TEST_BASE_URL ได้
config ใช้ Microsoft Edge ที่ติดตั้งแล้ว; ถ้าไม่มีให้ติดตั้ง browser ของ Playwright และเอา channel ออก
Browser tests สร้างผลตรวจตัวอย่างในฐานข้อมูลเป้าหมาย ห้ามชี้ไป live

## API
POST /api/scans/url/ JSON: {url, request_key(UUID)}
- 201 ผลตรวจและ recorded=true
- 400 ข้อมูลผิด
- 409 request_key ใช้แล้ว; ไม่รับประกันคืนผลเดิม เพราะไม่ได้เก็บเนื้อหาไว้
GET /api/statistics/?start=YYYY-MM-DD&end=YYYY-MM-DD&type=url
GET /api/health/ ตรวจ DB พร้อมใช้งาน
POST /api/scans/message/ JSON: {message, request_key(UUID)}
POST /api/practice/start/ JSON: {} คืนคำถามและ signed token อายุ 1 ชั่วโมง โดยไม่ส่งเฉลย
POST /api/practice/submit/ JSON: {token, answers:[index,...]} คืนคะแนนและเฉลย
รอบฝึกไม่เก็บในฐานข้อมูล; token ผูก fingerprint ของชุดคำถาม และใช้ส่งซ้ำได้ภายในอายุ
สถิติใช้ type=all เพื่อรวม URL และข้อความ ไม่รวมจำนวนแบบฝึกหัด
ผลเฉพาะรายการไม่มี public GET endpoint; host/reasons คืนเฉพาะคำขอที่ส่งสำเร็จ
request_key ต้องใช้กับ submission เดิมเท่านั้น; เปลี่ยน input หรือเริ่มใหม่สร้าง key ใหม่

## ก่อน deploy Render
1. เลือก root directory ของแอปนี้ใน GitHub
2. Build React, ติดตั้ง backend/requirements.txt, collectstatic, migrate
3. Start: cd backend && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
4. DEBUG=0, SECRET_KEY แบบสุ่ม, DATABASE_URL จาก PostgreSQL, ALLOWED_HOSTS เป็นโดเมนจริง
5. Health check /api/health/
6. สำรอง PostgreSQL เองก่อนปรับ schema และก่อนหมดอายุ Free
ยังไม่สร้าง Render resources และยังไม่มี public URL
ไม่ใช้ SQLite บน Render เพราะ filesystem ชั่วคราว
Rate limit ปัจจุบันเป็น DRF local-memory ต่อ process เหมาะเฉพาะต้นแบบ ต้องตรวจ proxy/IP และ shared limiter ก่อนเปิดกว้าง
Public anonymous statistics คือจำนวนคำขอตรวจ ไม่ใช่คนจริง และไม่ได้ป้องกันผู้จงใจสร้างสถิติปลอมได้ทั้งหมด

## Privacy และขอบเขต
ไม่บันทึก request body ใน application log; URL ส่งผ่าน POST เท่านั้น
เครือข่าย/ผู้ให้บริการโฮสต์อาจมี access log แยก ต้องกำหนด retention เมื่อ deploy
ห้ามใช้ผลกฎเพื่ออ้างว่าเว็บไซต์ปลอดภัย
ประวัติในเบราว์เซอร์มีข้อมูลต้นฉบับ ผู้ใช้เครื่องร่วมกันอาจเห็นได้ ล้างข้อมูลเบราว์เซอร์แล้วประวัติหาย
แบบฝึกหัดมีเฉลยหลังส่ง ไม่ใช้เป็นข้อสอบรับรองผลหรือป้องกันการทุจริต

## Source / License
backend/scanner/vendor/phishdetect: 3 ไฟล์จาก Sarthakagrwal/phishing-url-detector แบบตรึง commit
อ่าน UPSTREAM.txt และ MIT LICENSE ในโฟลเดอร์นั้น
ใช้ parser/feature extractor; engine.py validation/scoring ภาษาไทยเขียนใหม่
ไม่ใช้โมเดล ML หรือค่า accuracy ของ upstream
ชุด public suffix ต้นทางเป็น subset ไม่ใช่ PSL เต็ม; รุ่นนี้ไม่ให้คะแนน TLD/subdomain เพื่อเลี่ยงข้อจำกัดนี้

