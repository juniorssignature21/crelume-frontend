# Crelume

The Crelume event site — a Django application with secure accounts, Google/GitHub
sign-in, reCAPTCHA-protected forms, and paid multi-ticket orders via Paystack.

## What's included

- The full Crelume landing page: hero, event banner, resources, community, upcoming
  events, about, values, who it's for, filterable events and contact.
- Event detail pages and a seeded catalogue (one live event, one online series).
- Accounts via django-allauth: email/password with email verification, plus optional
  Google and GitHub sign-in.
- reCAPTCHA v2 "I'm not a robot" on signup, login, contact and checkout.
- Login-gated ticket checkout with server-side pricing and multi-ticket orders
  (1–10 per order by default).
- Paystack hosted checkout, server-side verification on return, and a signed webhook
  for out-of-band confirmation.
- Idempotent fulfilment: paid orders issue unique ticket codes exactly once and email
  the buyer one ticket email containing every code.
- A private order/ticket page per buyer and an account dashboard.
- Contact messages stored in the database and emailed to the team.
- A production setup with Supabase Postgres, Resend email, WhiteNoise static files,
  gunicorn, HTTPS/HSTS hardening and a `/healthz/` probe.

## Stack

| Layer | Development | Production |
| --- | --- | --- |
| Web | Django 5.2, Python 3.13 | gunicorn + WhiteNoise |
| Database | SQLite | Supabase Postgres (`DATABASE_URL`) |
| Email | Console backend | Resend via django-anymail |
| Static files | Django dev server | WhiteNoise manifest storage |
| Auth | django-allauth (email, Google, GitHub) | same |
| Bot protection | django-recaptcha v2 checkbox | same (real keys required) |
| Payments | Paystack Transactions API | same (live keys) |

## Quick start (development)

```bash
python3.13 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# edit .env: at minimum set DJANGO_SECRET_KEY and SITE_URL

python manage.py migrate          # also seeds the events and allauth Site
python manage.py createsuperuser  # optional, for /admin/
python manage.py runserver 8080
```

Open <http://localhost:8080>. The migration in `events/migrations/0002_seed_events.py`
adds the events shown in the design; edit or add more in `/admin/`.

Development defaults:

- `manage.py` loads `crelume.settings.dev` (SQLite, console email, no HTTPS redirect).
- Email — including ticket codes and allauth verification links — prints to the
  server log instead of being sent.
- Paystack, Google and GitHub are optional: the checkout notice and social buttons
  appear only when their keys are configured.

> This sandbox's `runserver` autoreloader can hit a proot `waitpid` failure. Use
> `python manage.py runserver --noreload 8080` here if you see it.

## Settings layout

```
crelume/settings/
├── base.py   # shared apps, templates, auth, Paystack, logging
├── dev.py    # SQLite, console email, DEBUG on
└── prod.py   # Supabase, Resend, WhiteNoise, strict HTTPS, fail-fast env checks
```

`manage.py` defaults to `crelume.settings.dev`; `wsgi.py` and `asgi.py` default to
`crelume.settings.prod`. Override with `DJANGO_SETTINGS_MODULE` when needed:

```bash
DJANGO_SETTINGS_MODULE=crelume.settings.prod python manage.py check --deploy
```

## Configuration

Everything is environment-driven; see `.env.example` for the full list.
Development reads a local `.env` file; production reads real environment variables
only, so a leftover `.env` never changes a deployed configuration.

| Variable | Purpose |
| --- | --- |
| `DJANGO_SETTINGS_MODULE` | `crelume.settings.dev` / `crelume.settings.prod` |
| `DJANGO_SECRET_KEY` | Required in production (50+ characters). |
| `DJANGO_DEBUG` | `1` in development; production forces `False`. |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated public hostnames (required in production). |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Extra trusted origins; defaults to `SITE_URL` in production. |
| `SITE_URL` | Public HTTPS base URL used in emails and the allauth Site record. |
| `DATABASE_URL` | Supabase Postgres connection string (required in production). |
| `DATABASE_SSL_REQUIRE` | Default `1`; adds `sslmode=require`. |
| `DB_CONN_MAX_AGE` | Persistent connection lifetime (default `600` seconds). |
| `DB_DISABLE_SERVER_SIDE_CURSORS` | Default `1` for Supabase's transaction pooler. |
| `RESEND_API_KEY` | Resend API key (required in production). |
| `DEFAULT_FROM_EMAIL` / `CONTACT_EMAIL` | Sender and team inbox. |
| `PAYSTACK_SECRET_KEY` / `PAYSTACK_PUBLIC_KEY` | Paystack API keys. Checkout is disabled while unset. |
| `PAYSTACK_CURRENCY` | Defaults to `NGN`. |
| `PAYSTACK_CALLBACK_URL` | Optional; defaults to `<SITE_URL>/payments/paystack/callback/`. |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | Enables Google sign-in. |
| `GITHUB_CLIENT_ID` / `GITHUB_CLIENT_SECRET` | Enables GitHub sign-in. |
| `RECAPTCHA_PUBLIC_KEY` / `RECAPTCHA_PRIVATE_KEY` | reCAPTCHA v2 keys. Real keys are required in production. |
| `TICKET_MAX_QUANTITY` | Maximum tickets per order (default 10). |
| `ACCOUNT_EMAIL_VERIFICATION` | `mandatory` by default; set `optional` to skip verification. |
| `DJANGO_SECURE_*`, `DJANGO_BEHIND_PROXY` | HTTPS/HSTS overrides (production defaults are safe). |

## Production deployment

The production module refuses to start unless `DJANGO_SECRET_KEY`,
`DJANGO_ALLOWED_HOSTS`, `SITE_URL`, `DATABASE_URL`, `RESEND_API_KEY` and real
reCAPTCHA keys are present, so a misconfigured deploy fails loudly instead of
silently falling back to development defaults.

### 1. Supabase Postgres

1. Create a project at <https://supabase.com>.
2. Open **Project Settings → Database → Connection string** and copy a **pooler**
   string (better for hosts without IPv6):
   - Transaction pooler (port `6543`) — recommended; keep
     `DB_DISABLE_SERVER_SIDE_CURSORS=1`.
   - Session pooler (port `5432`) — also fine.
3. Set `DATABASE_URL` to the string with your database password filled in and keep
   `?sslmode=require` (or leave `DATABASE_SSL_REQUIRE=1`).

Migrations run automatically on deploy via `scripts/start.sh`. For a first deploy
from your machine:

```bash
export DJANGO_SETTINGS_MODULE=crelume.settings.prod
python manage.py migrate --noinput
python manage.py createsuperuser
```

### 2. Resend email

1. Create an API key at <https://resend.com/api-keys> and set `RESEND_API_KEY`.
2. Verify your sending domain in Resend (**Domains → Add domain**) and add the
   DNS records it shows.
3. Set `DEFAULT_FROM_EMAIL` to an address on that verified domain, e.g.
   `Crelume <no-reply@yourdomain.com>`, and set `CONTACT_EMAIL`.
4. Until a domain is verified you can test with `onboarding@resend.dev`, but Resend
   only delivers that sender to the account owner's address.

All mail — ticket emails, allauth verification/reset messages and contact
notifications — goes through Anymail's Resend backend.

### 3. Environment variables

Set at least:

```dotenv
DJANGO_SETTINGS_MODULE=crelume.settings.prod
DJANGO_SECRET_KEY=<50+ random characters>
DJANGO_ALLOWED_HOSTS=crelume.com,www.crelume.com
SITE_URL=https://crelume.com
DATABASE_URL=postgresql://postgres.<ref>:<password>@<region>.pooler.supabase.com:6543/postgres?sslmode=require
RESEND_API_KEY=re_...
DEFAULT_FROM_EMAIL=Crelume <no-reply@crelume.com>
CONTACT_EMAIL=hello@crelume.com
RECAPTCHA_PUBLIC_KEY=<real v2 site key>
RECAPTCHA_PRIVATE_KEY=<real v2 secret key>
PAYSTACK_SECRET_KEY=sk_live_...
PAYSTACK_PUBLIC_KEY=pk_live_...
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GITHUB_CLIENT_ID=...
GITHUB_CLIENT_SECRET=...
```

Generate a secret key with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

`SITE_URL` is written into allauth's Site record by migration `core/0002`, so set it
before the first migrate on a new database.

### 4. Run it

**Render** — commit `render.yaml` and create a Blueprint from the repository, or make
a Web Service with:

- Build command: `pip install -r requirements.txt`
- Start command: `./scripts/start.sh`
- Health check path: `/healthz/`

Fill in the `sync: false` values in the dashboard.

**Railway / Heroku-style** — `Procfile` runs `./scripts/start.sh`; set the environment
variables and `PORT` is honoured automatically.

**Docker**:

```bash
docker build -t crelume .
docker run --env-file .env.production -p 8000:8000 crelume
```

`scripts/start.sh` runs `collectstatic`, `migrate`, then gunicorn on `$PORT`
(3 workers by default, override with `WEB_CONCURRENCY`). WhiteNoise serves the
collected, hashed static files with long-lived cache headers.

### 5. Production URLs to register

- Paystack webhook: `https://<host>/payments/paystack/webhook/`
- Paystack callback: `https://<host>/payments/paystack/callback/` (default)
- Google OAuth redirect: `https://<host>/accounts/google/login/callback/`
- GitHub OAuth callback: `https://<host>/accounts/github/login/callback/`
- reCAPTCHA v2 domains: add your production hostname.

### 6. Health and checks

`GET /healthz/` returns `{"status": "ok", "database": "ok"}` with HTTP 200 when the
app and database are reachable, and HTTP 503 otherwise. It is exempt from the HTTPS
redirect so platform probes can reach it over the internal network.

Run Django's deployment checks before going live:

```bash
DJANGO_SETTINGS_MODULE=crelume.settings.prod python manage.py check --deploy
```

The one expected warning is `security.W021` (HSTS preload is opt-in). Set
`DJANGO_SECURE_HSTS_PRELOAD=1` only once your domain is ready to be submitted to
the browser preload list; the other security checks should be clean.

## Paystack

1. Create a Paystack account and copy the **test** secret key into
   `PAYSTACK_SECRET_KEY` while developing.
2. For local webhook testing, expose the server (e.g. `ngrok http 8080`) and add
   `<public-url>/payments/paystack/webhook/` as the webhook URL in the Paystack
   dashboard.
3. The return callback verifies the transaction with Paystack before issuing tickets.
   The webhook validates `x-paystack-signature` (HMAC SHA-512) and fulfils the order
   too, so tickets are issued even if the buyer closes the tab.
4. Amounts are sent to Paystack in kobo; the amount and currency are re-checked
   server-side. Card details never touch this application.

Checkout is intentionally disabled with a clear notice when no secret key is set.
Switch to the live keys (`sk_live_…` / `pk_live_…`) for production.

## Google and GitHub sign-in

Create OAuth apps and register the redirect URIs listed above, then set the
client ID/secret variables and restart. The social buttons only render when both
values for a provider are present, and they use POST (no login-on-GET).

## Email

Development defaults to the console backend, so ticket emails (including codes)
appear in the server log. Production always uses Resend. One email per paid order
lists every ticket code and links to the buyer's order page.

## Tests

```bash
.venv/bin/python manage.py test
```

The suite covers page rendering, contact handling, health checks, signup, login
gating, quantity and capacity validation, Paystack initialization failures,
amount/currency mismatch, callback and webhook verification, webhook signatures,
idempotent fulfilment, ticket emails and order privacy. Paystack is mocked — no
network calls and no real charges.

## Project layout

```
crelume/            settings/{base,dev,prod}.py, URLs, WSGI/ASGI
core/               home/contact/health views, contact model, captcha auth forms
events/             Event model, detail page, seed migration
orders/             Order/Ticket models, Paystack client, fulfilment, emails, checkout
templates/          base + landing, event, auth, checkout, order, email templates
static/             styles.css (design), app.css (new pages), main.js, app.js, fonts
scripts/start.sh    collectstatic + migrate + gunicorn production entrypoint
Dockerfile          production image
Procfile            platform start command
render.yaml         Render blueprint
```

## Security notes

- Checkout requires an authenticated account; order pages are only visible to their
  owner (unguessable access token plus an ownership check).
- Prices and totals come from the database, never from the request.
- Webhook requests are CSRF-exempt but must carry a valid HMAC signature; the payload
  is also checked against the stored order (reference, amount, currency, success).
- Fulfilment runs in a transaction with a row lock and a status check, so duplicate
  callbacks cannot issue duplicate tickets or emails.
- Standard Django CSRF protection, HttpOnly/SameSite cookies, clickjacking protection,
  secure cookies, SSL redirect and HSTS in production.
- reCAPTCHA protects signup, login, contact and checkout; production refuses to start
  with Google's test keys.
- Production refuses to start without a strong secret key, allowed hosts, HTTPS
  `SITE_URL`, Postgres URL, Resend key and real reCAPTCHA keys.
- The contact form stores messages in the database and emails a notification; delivery
  failures never lose the stored message.
- Never commit `.env`, database dumps or the SQLite file — `.gitignore` covers them.

## Design reference

`Home_20261017_144454_0000.png` in the repository root is the original 1366px design.
