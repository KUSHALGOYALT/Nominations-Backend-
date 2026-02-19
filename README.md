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
