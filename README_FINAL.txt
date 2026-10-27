WORKTRACK - FINAL FULL STACK MINI PROJECT
Student: Jay Maruti Magdum
Project: Work Tracking System for Small Manufacturing Unit

1. INSTALL
Open PowerShell in backend folder:
  python -m venv venv
  .\venv\Scripts\Activate.ps1
  pip install -r requirements.txt

2. DATABASE
Open MySQL Workbench and run database/work_tracking_db.sql.
If your MySQL root account has a password, copy backend/.env.example to backend/.env and set DB_PASSWORD.

3. START
PowerShell:
  cd backend
  .\venv\Scripts\Activate.ps1
  python app.py

4. OPEN
http://127.0.0.1:5000/

LOGIN
Email: admin@worktrack.com
Password: admin123

5. PHONE
Make sure phone and PC use the same Wi-Fi. Run ipconfig and find IPv4 Address, then open:
http://YOUR-PC-IP:5000/
Windows Firewall may ask for permission; allow Python on the private network.

6. MAIN APIS
POST /api/login
POST /api/logout
GET /api/me
GET/POST/PUT/DELETE /api/employees
GET/POST /api/departments
GET/POST/PUT /api/work
GET /api/progress
GET/POST /api/attendance
GET/POST /api/production
GET /api/dashboard
GET /api/reports
GET/PUT /api/profile
GET /api/health

IMPORTANT
The default SQL file contains a pre-created administrator account for the college demo. Change the password/secret before real deployment.
