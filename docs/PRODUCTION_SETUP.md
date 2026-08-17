# Production Deployment Guide

## Render.com Setup

This project includes a `render.yaml` Blueprint specification for deploying to Render.com.

### Steps to Deploy

1. Create a [Render](https://render.com) account.
2. Connect your GitHub repository to Render.
3. In the Render Dashboard, click **New** -> **Blueprint**.
4. Select your repository. Render will automatically detect the `render.yaml` file.
5. Render will provision 3 resources:
   - A PostgreSQL Database (`hr-mastered-db`)
   - A Web Service (`hr-mastered-web`)
   - A Background Worker (`hr-mastered-worker`)
6. Go to the Environment variables section of the Web Service and configure the remaining required environment variables:
   - `ZOHO_CLIENT_ID`
   - `ZOHO_CLIENT_SECRET`
   - `ZOHO_REFRESH_TOKEN`
   - `ZOHO_ORG_ID`
   - `ZOHO_OAUTH_REDIRECT_URI` (should be `https://<your-render-url>.onrender.com/api/zoho/auth/callback/`)

### Architecture

- **Django Web Server**: Serves API requests and static files (including the React SPA). Hosted via Gunicorn.
- **Worker**: A long-running Django management command (`python manage.py run_delivery_worker`) that continuously polls the database for `DeliveryJob`s, processes them idempotently with Zoho WorkDrive, and respects leases and backoffs to ensure robust background processing without duplicating uploads.
- **Postgres Database**: State management.

### Build Process

The `build.sh` script automates the build pipeline on Render:
1. Installs Python dependencies
2. Runs `npm install` and `npm run build` in the `frontend/` directory
3. Collects Django static files (which includes the built frontend bundle)
4. Runs Django database migrations
