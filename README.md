# Aura ERP

Django (API) + React (screens). Quotations (auto-number, revisions, PDF), masters, funnel, dashboard,
proforma invoice, receipts (email + WhatsApp), distributors + products, purchase orders, Excel import/export.

## Windows - just double-click these files (in this order)
1_SETUP.bat               one time: creates venv, installs everything, creates database + admin login
2_CONFIGURE_COMPANY.bat   company name, GSTIN, state, bank details printed on PDFs
3_CONFIGURE_EMAIL.bat     SMTP settings (Gmail needs an App Password)
4_CONFIGURE_WHATSAPP.bat  optional WhatsApp Cloud API keys
5_TEST_EMAIL.bat          sends a test email
START_APP.bat             daily use: starts backend + React and opens the browser (keep both black windows open)

Other files
START_BACKEND.bat / START_FRONTEND.bat   start one part only
EXCEL_EXPORT.bat          one Excel file with customers, products, distributors, quotations, billing, POs  -> exports folder
EXCEL_TEMPLATE.bat        blank import sheets with correct headings
EXCEL_IMPORT.bat          import customers / products / distributors / distributor products from Excel
BACKUP_DATABASE.bat       copies the database into the backups folder
CREATE_ADMIN_USER.bat     add another admin login
BUILD_FRONTEND.bat        production build of the React screens

Requirements: Python 3.11+ (tick "Add to PATH") and Node.js LTS.
Settings you enter are stored in backend\.env (contains passwords - never share it).
After receiving a new version of this project, copy over your backend\.env and backend\db.sqlite3, then run 1_SETUP.bat again.

## Manual commands (Mac/Linux)
cd backend; python3 -m venv venv; source venv/bin/activate; pip install -r requirements.txt
python manage.py init_env; python manage.py makemigrations erp; python manage.py migrate; python manage.py createsuperuser; python manage.py runserver
(second terminal) cd frontend; npm install; npm run dev        -> http://localhost:5173
