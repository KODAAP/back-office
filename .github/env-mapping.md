# Mapping des Variables d'Environnement - Sycosur Backend

## 📋 Vue d'ensemble

| Type | Nombre | Description |
|------|--------|-------------|
| 🔴 Secrets | 16 | Données sensibles à protéger |
| 🟢 Variables | 15 | Configuration non sensible |

---

## 🔴 SECRETS GITHUB

**Chemin :** `Settings → Secrets and variables → Actions → New repository secret`

| Nom du Secret | Description | Exemple de valeur |
|---------------|-------------|-------------------|
| `SECRET_DJANGO_SECRET_KEY` | Clé de signature Django | `8RqBCXvoJti9XI1fBsMViiTGFnaCq4S39UlR5JMDG9P-Tzfocqc` |
| `SECRET_DJANGO_ADMIN_URL` | URL d'administration Django | `secret/` |
| `SECRET_EMAIL_PASS` | Mot de passe serveur SMTP | `sycosurinsuco2025` |
| `SECRET_CELERY_FLOWER_USER` | Utilisateur dashboard Flower | `admin` |
| `SECRET_CELERY_FLOWER_PASSWORD` | Mot de passe dashboard Flower | `pass123456` |
| `SECRET_POSTGRES_HOST` | Hôte base de données | `db.sycosur.internal` |
| `SECRET_POSTGRES_PORT` | Port base de données | `5432` |
| `SECRET_POSTGRES_DB` | Nom de la base de données | `sycosur` |
| `SECRET_POSTGRES_USER` | Utilisateur PostgreSQL | `sycosur_user` |
| `SECRET_POSTGRES_PASSWORD` | Mot de passe PostgreSQL | `***` |
| `SECRET_SIGNING_KEY` | Clé de signature JWT | `GVcMeBUMtqsLDlcD6g-v95WTcy_756hxmUsWjCT4ul015LOU9rA` |
| `SECRET_GOOGLE_CLIENT_SECRET` | Secret OAuth Google | `GOCSPX-CSEU*****_fIrzFxTLLQoi8s` |
| `SECRET_ODK_ADMIN_EMAIL` | Email pool ODK (compte 1) | `***@insuco.com` |
| `SECRET_ODK_ADMIN_PASSWORD` | Mot de passe pool ODK (compte 1) | `***` |
| `SECRET_ODK_ADMIN_PASSWORD2` | Mot de passe pool ODK (compte 2) | `***` |
| `SECRET_ADMIN_PASSWORD` | Mot de passe superuser auto-créé | `***` |

---

## 🟢 VARIABLES D'ENVIRONNEMENT

**Chemin :** `Settings → Secrets and variables → Actions → Variables → New repository variable`

| Nom de la Variable | Description | Valeur |
|--------------------|-------------|--------|
| `VAR_SITE_NAME` | Nom du site | `Sycosur2.0` |
| `VAR_DJANGO_SETTINGS_MODULE` | Module de settings Django | `config.settings.prod` |
| `VAR_DJANGO_ALLOWED_HOST` | Hosts autorisés | `.insuco.net` |
| `VAR_GUNICORN_WORKERS` | Nombre de workers Gunicorn | `5` |
| `VAR_DEFAULT_FROM_EMAIL` | Email d'expédition par défaut | `sycosur@insuco.com` |
| `VAR_EMAIL_HOST` | Serveur SMTP | `ssl0.ovh.net` |
| `VAR_EMAIL_PORT` | Port SMTP | `465` |
| `VAR_CELERY_BROKER_URL` | URL broker Celery | `redis://redis:6379/0` |
| `VAR_CELERY_RESULT_BACKEND` | Backend résultats Celery | `redis://redis:6379/0` |
| `VAR_GOOGLE_CLIENT_ID` | Client ID OAuth Google | `***.apps.googleusercontent.com` |
| `VAR_REDIRECT_URIS` | URI de redirection OAuth | `https://sycosur.insuco.net/api/v1/auth/google` |
| `VAR_DOMAIN` | Domaine principal | `sycosur.insuco.net` |
| `VAR_ODK_CENTRAL_URL` | URL API ODK Central | `https://odk.insuco.net/v1` |
| `VAR_ODK_ADMIN_EMAIL2` | Email pool ODK (compte 2) | `admin2@insuco.com` |
| `VAR_ODK_VERIFY_SSL` | Vérification SSL ODK | `true` |
| `VAR_GOOGLE_DRIVE_FOLDER_ID` | ID dossier Google Drive | `0AESY4UyOrsGjUk9PVA` |
| `VAR_FRONTEND_URL` | URL du frontend | `https://sycosur.insuco.net` |
| `VAR_COOKIE_SECURE` | Cookies sécurisés | `false` |

---

## 📄 Fichier `.env` pour développement local

```bash
# Django
SECRET_DJANGO_SECRET_KEY=8RqBCXvoJti9XI1fBsMViiTGFnaCq4S39UlR5JMDG9P-Tzfocqc
SECRET_DJANGO_ADMIN_URL=secret/
VAR_DJANGO_SETTINGS_MODULE=config.settings.prod
VAR_DJANGO_ALLOWED_HOST=.insuco.net
VAR_GUNICORN_WORKERS=5

# Email
VAR_DEFAULT_FROM_EMAIL=sycosur@insuco.com
VAR_EMAIL_HOST=ssl0.ovh.net
VAR_EMAIL_PORT=465
SECRET_EMAIL_PASS=sycosurinsuco2025

# Celery
SECRET_CELERY_FLOWER_USER=admin
SECRET_CELERY_FLOWER_PASSWORD=pass123456
VAR_CELERY_BROKER_URL=redis://redis:6379/0
VAR_CELERY_RESULT_BACKEND=redis://redis:6379/0

# PostgreSQL
SECRET_POSTGRES_HOST=*****
SECRET_POSTGRES_PORT=*****
SECRET_POSTGRES_DB=sycosur
SECRET_POSTGRES_USER=*****
SECRET_POSTGRES_PASSWORD=*****

# Sécurité
VAR_COOKIE_SECURE=false
SECRET_SIGNING_KEY=GVcMeBUMtqsLDlcD6g-v95WTcy_756hxmUsWjCT4ul015LOU9rA

# Google OAuth
VAR_GOOGLE_CLIENT_ID=*****.apps.googleusercontent.com
SECRET_GOOGLE_CLIENT_SECRET=GOCSPX-CSEU*****_fIrzFxTLLQoi8s
VAR_REDIRECT_URIS=https://sycosur.insuco.net/api/v1/auth/google
VAR_DOMAIN=sycosur.insuco.net

# ODK
VAR_ODK_CENTRAL_URL=https://odk.insuco.net/v1
SECRET_ODK_ADMIN_EMAIL=*****
SECRET_ODK_ADMIN_PASSWORD=*****
VAR_ODK_ADMIN_EMAIL2=admin2@insuco.com
SECRET_ODK_ADMIN_PASSWORD2=*****
VAR_ODK_VERIFY_SSL=true

# Admin
SECRET_ADMIN_PASSWORD=*****

# Google Drive
VAR_GOOGLE_DRIVE_FOLDER_ID=0AESY4UyOrsGjUk9PVA

# Frontend
VAR_FRONTEND_URL=https://sycosur.insuco.net
```

---

## 🔧 Utilisation dans GitHub Actions

```yaml
env:
  # Secrets
  DJANGO_SECRET_KEY: ${{ secrets.SECRET_DJANGO_SECRET_KEY }}
  DJANGO_ADMIN_URL: ${{ secrets.SECRET_DJANGO_ADMIN_URL }}
  EMAIL_PASS: ${{ secrets.SECRET_EMAIL_PASS }}
  CELERY_FLOWER_USER: ${{ secrets.SECRET_CELERY_FLOWER_USER }}
  CELERY_FLOWER_PASSWORD: ${{ secrets.SECRET_CELERY_FLOWER_PASSWORD }}
  POSTGRES_HOST: ${{ secrets.SECRET_POSTGRES_HOST }}
  POSTGRES_PORT: ${{ secrets.SECRET_POSTGRES_PORT }}
  POSTGRES_DB: ${{ secrets.SECRET_POSTGRES_DB }}
  POSTGRES_USER: ${{ secrets.SECRET_POSTGRES_USER }}
  POSTGRES_PASSWORD: ${{ secrets.SECRET_POSTGRES_PASSWORD }}
  SIGNING_KEY: ${{ secrets.SECRET_SIGNING_KEY }}
  GOOGLE_CLIENT_SECRET: ${{ secrets.SECRET_GOOGLE_CLIENT_SECRET }}
  ODK_ADMIN_EMAIL: ${{ secrets.SECRET_ODK_ADMIN_EMAIL }}
  ODK_ADMIN_PASSWORD: ${{ secrets.SECRET_ODK_ADMIN_PASSWORD }}
  ODK_ADMIN_PASSWORD2: ${{ secrets.SECRET_ODK_ADMIN_PASSWORD2 }}
  ADMIN_PASSWORD: ${{ secrets.SECRET_ADMIN_PASSWORD }}

  # Variables
  SITE_NAME: ${{ vars.VAR_SITE_NAME }}
  DJANGO_SETTINGS_MODULE: ${{ vars.VAR_DJANGO_SETTINGS_MODULE }}
  DJANGO_ALLOWED_HOST: ${{ vars.VAR_DJANGO_ALLOWED_HOST }}
  GUNICORN_WORKERS: ${{ vars.VAR_GUNICORN_WORKERS }}
  DEFAULT_FROM_EMAIL: ${{ vars.VAR_DEFAULT_FROM_EMAIL }}
  EMAIL_HOST: ${{ vars.VAR_EMAIL_HOST }}
  EMAIL_PORT: ${{ vars.VAR_EMAIL_PORT }}
  CELERY_BROKER_URL: ${{ vars.VAR_CELERY_BROKER_URL }}
  CELERY_RESULT_BACKEND: ${{ vars.VAR_CELERY_RESULT_BACKEND }}
  GOOGLE_CLIENT_ID: ${{ vars.VAR_GOOGLE_CLIENT_ID }}
  REDIRECT_URIS: ${{ vars.VAR_REDIRECT_URIS }}
  DOMAIN: ${{ vars.VAR_DOMAIN }}
  ODK_CENTRAL_URL: ${{ vars.VAR_ODK_CENTRAL_URL }}
  ODK_ADMIN_EMAIL2: ${{ vars.VAR_ODK_ADMIN_EMAIL2 }}
  ODK_VERIFY_SSL: ${{ vars.VAR_ODK_VERIFY_SSL }}
  GOOGLE_DRIVE_FOLDER_ID: ${{ vars.VAR_GOOGLE_DRIVE_FOLDER_ID }}
  FRONTEND_URL: ${{ vars.VAR_FRONTEND_URL }}
  COOKIE_SECURE: ${{ vars.VAR_COOKIE_SECURE }}
```

---

## ⚠️ Recommandations de Sécurité

1. **Ne jamais committer** les secrets dans le repo
2. **Rotation régulière** des mots de passe et clés (tous les 90 jours)
3. **Limiter les accès** aux secrets GitHub aux mainteneurs uniquement
4. **Utiliser des environnements** GitHub pour séparer dev/staging/prod
5. **Activer la protection de branche** pour `main`

---

*Document généré pour Sycosur Backend - CI/CD Setup*
