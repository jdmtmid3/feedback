# Licensing System

Centralized license management for Tugon feedback system deployments.

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Configure environment variables in `.env`:
   ```
   SECRET_KEY=your-secret-key
   DB_HOST=localhost
   DB_PORT=3306
   DB_USER=root
   DB_PASSWORD=your-password
   DB_NAME=licensing_db
   LICENSING_API_KEY=replace-with-a-long-random-shared-key
   MAIN_APP_URL=https://your-main-app.up.railway.app
   ```

3. Run the application:
   ```bash
   python app.py
   ```

The licensing system will run on port 8081 by default.

## Portal login

The management dashboard is protected by a portal login. Configure both
credentials before starting the service:

```text
PORTAL_ADMIN_USERNAME=<your-admin-username>
PORTAL_ADMIN_PASSWORD=<a-long-unique-password>
```

The application intentionally has no built-in administrator password.

## Deployment

Deploy the main feedback app and the licensing portal as separate services from this repository:

```text
Main app: gunicorn app:app
Licensing portal: gunicorn licensing_app:app
```

Each service needs its own public URL and access to an online MySQL database. Set `LICENSING_PORTAL_URL` in the main app to the public URL of the licensing service. Set `MAIN_APP_URL` and the same `LICENSING_API_KEY` in both services when user synchronization is enabled.

## API Endpoints

### Validate License
- `POST /api/validate/<license_key>`
- Validates a license key and returns license details

### License Management
- `GET /` - License management dashboard
- `POST /add-license` - Create new license
- `POST /toggle/<license_id>` - Activate/deactivate license
- `POST /renew/<license_id>` - Renew license with new expiry date
- `POST /delete/<license_id>` - Delete license

## Database Schema

The licensing system uses a MySQL database with the following table:

**licenses**
- id (INT, PRIMARY KEY, AUTO_INCREMENT)
- license_key (VARCHAR(255), UNIQUE)
- license_key_hash (VARCHAR(255), UNIQUE)
- company_name (VARCHAR(255))
- contact_email (VARCHAR(255))
- max_stores (INT)
- max_questionnaires (INT)
- features (JSON)
- expiry_date (DATE)
- is_active (BOOLEAN)
- api_key (VARCHAR(255), UNIQUE)
- created_at (TIMESTAMP)
- updated_at (TIMESTAMP)

## Integration with Feedback System

The feedback system validates licenses by calling:
```
POST {licensing_portal_url}/api/validate/{license_key}
```

This returns license details including:
- valid (BOOLEAN)
- company_name (STRING)
- max_stores (INT)
- max_questionnaires (INT)
- features (JSON)
- expiry_date (ISO DATE STRING)
