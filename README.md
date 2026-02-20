# Recognition API (Django)

## Create Django admin user (first time)

From the **backend** folder (where `manage.py` lives):

```bash
cd hexa-recognition/backend
python manage.py createsuperuser
```

Use that username/password to log in at: **http://127.0.0.1:8000/django-admin/**  
Then go to **Recognition → Participant emails** to add emails for the QR list.

## Run server

```bash
cd hexa-recognition/backend
python manage.py runserver
```

## Local testing (QR code)

When you test locally, the **QR code encodes the backend URL** that the phone/browser will open. The backend then redirects to your frontend vote page.

**What’s in the QR (local):**

- Frontend uses `NEXT_PUBLIC_API_URL` to build the URL. If you set it to your local API, the QR will contain:
  - **`http://localhost:8000/api/qr-join`** (or `http://127.0.0.1:8000/api/qr-join` if your backend runs on 8000).

**To test locally:**

1. **Backend** (`.env` in `backend/`):
   - `APP_URL=http://localhost:3000`  
     (so the redirect from `/api/qr-join` goes to your local Next.js app, not Vercel).

2. **Frontend** (`.env.local` in `frontend/`):
   - `NEXT_PUBLIC_API_URL=http://localhost:8000/api`  
     (so the admin page generates a QR with `http://localhost:8000/api/qr-join`).

3. Open the QR URL in the browser (or scan with phone on same network using `http://<your-machine-ip>:8000/api/qr-join` if needed). You should be redirected to `http://localhost:3000/vote` (or your `APP_URL` + `/vote`).
