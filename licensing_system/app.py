"""
Licensing Portal - Centralized license management for multiple feedback system deployments
"""
import os
import json
import logging
import mysql.connector
from mysql.connector import MySQLConnection, Error
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from datetime import datetime, date
import secrets
import bcrypt
from functools import wraps
from contextlib import contextmanager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_app() -> Flask:
    app = Flask(__name__, template_folder='templates', static_folder='static')

    # Configuration
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "licensing-secret-key-change-me")

    # Licensing management credentials come from the hosting environment.
    portal_admin_username = os.getenv("PORTAL_ADMIN_USERNAME", "admin")
    portal_admin_password = os.getenv("PORTAL_ADMIN_PASSWORD", "change-me-now")

    # Login required decorator
    def login_required(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not session.get("portal_admin_authenticated"):
                return redirect(url_for("login", next=request.path))
            return f(*args, **kwargs)
        return decorated_function
    
    # Custom Jinja2 filter for parsing JSON
    @app.template_filter('from_json')
    def from_json_filter(s):
        try:
            return json.loads(s)
        except (json.JSONDecodeError, TypeError):
            return {}
    
    # Database configuration
    def get_db_connection() -> MySQLConnection:
        try:
            # Use MYSQL_URL or individual variables
            if os.getenv("MYSQL_URL"):
                import urllib.parse
                db_url = os.getenv("MYSQL_URL")
                parsed = urllib.parse.urlparse(db_url)
                logger.info(f"Connecting to DB via MYSQL_URL: {parsed.hostname}:{parsed.port}/{parsed.path[1:]}")
                return mysql.connector.connect(
                    host=parsed.hostname,
                    port=parsed.port,
                    user=parsed.username,
                    password=parsed.password,
                    database=parsed.path[1:],
                    connection_timeout=10
                )
            else:
                host = os.getenv("DB_HOST", "localhost")
                port = int(os.getenv("DB_PORT", 3306))
                db_name = os.getenv("DB_NAME", "licensing_db")
                logger.info(f"Connecting to DB: {host}:{port}/{db_name}")
                return mysql.connector.connect(
                    host=host,
                    port=port,
                    user=os.getenv("DB_USER", "root"),
                    password=os.getenv("DB_PASSWORD", ""),
                    database=db_name,
                    connection_timeout=10
                )
        except mysql.connector.Error as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error connecting to database: {e}")
            raise

    @contextmanager
    def get_db_connection_with_transaction():
        """Context manager for database connections with automatic rollback on error."""
        conn = get_db_connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    # Initialize database schema
    def init_schema():
        retries = 3
        while retries > 0:
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                
                # Create licenses table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS licenses (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        license_key VARCHAR(255) NOT NULL UNIQUE,
                        license_key_hash VARCHAR(255) NOT NULL UNIQUE,
                        company_name VARCHAR(255) NOT NULL,
                        contact_email VARCHAR(255),
                        max_stores INT DEFAULT 0,
                        max_questionnaires INT DEFAULT 0,
                        features JSON NULL,
                        expiry_date DATE NULL,
                        is_active BOOLEAN DEFAULT TRUE,
                        api_key VARCHAR(255) NOT NULL UNIQUE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                    )
                """)
                
                # Create support_tickets table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS support_tickets (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        license_id INT NULL,
                        license_key VARCHAR(255) NULL,
                        company_name VARCHAR(255) NOT NULL,
                        contact_email VARCHAR(255) NOT NULL,
                        subject VARCHAR(255) NOT NULL,
                        message TEXT NOT NULL,
                        ticket_type ENUM('general', 'renewal', 'bug', 'feature') DEFAULT 'general',
                        status ENUM('open', 'in_progress', 'resolved', 'closed') DEFAULT 'open',
                        priority ENUM('low', 'medium', 'high') DEFAULT 'medium',
                        admin_reply TEXT NULL,
                        replied_at TIMESTAMP NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                    )
                """)

                # Create client_conversations table for messaging system
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS client_conversations (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        client_identifier VARCHAR(255) NOT NULL UNIQUE,
                        company_name VARCHAR(255) NOT NULL,
                        license_key VARCHAR(255) NULL,
                        contact_email VARCHAR(255) NOT NULL,
                        last_message_at TIMESTAMP NULL,
                        last_message_preview TEXT NULL,
                        unread_count INT DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        INDEX idx_client_identifier (client_identifier),
                        INDEX idx_last_message_at (last_message_at)
                    )
                """)

                # Create messages table for individual messages in conversations
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS messages (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        conversation_id INT NOT NULL,
                        sender_type ENUM('client', 'admin') NOT NULL,
                        sender_name VARCHAR(255) NOT NULL,
                        message TEXT NOT NULL,
                        is_read BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (conversation_id) REFERENCES client_conversations(id) ON DELETE CASCADE,
                        INDEX idx_conversation_created (conversation_id, created_at)
                    )
                """)

                # Create system_config table for configuration values
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS system_config (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        config_key VARCHAR(255) NOT NULL UNIQUE,
                        config_value TEXT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                    )
                """)
                # Insert default main_system_url if not exists
                cursor.execute("SELECT config_value FROM system_config WHERE config_key = 'main_system_url'")
                if not cursor.fetchone():
                    cursor.execute("INSERT INTO system_config (config_key, config_value) VALUES ('main_system_url', NULL)")
                    conn.commit()
                
                conn.commit()
                logger.info("Licensing database schema initialized successfully")
                return
            except Exception as e:
                retries -= 1
                logger.error(f"Schema initialization failed: {e}. Retries left: {retries}")
                if retries == 0:
                    raise
            finally:
                if 'conn' in locals():
                    conn.close()
    
    # Helper functions
    def get_system_config(config_key):
        """Get system configuration value from database"""
        conn = get_db_connection()
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT config_value FROM system_config WHERE config_key = %s", (config_key,))
            result = cursor.fetchone()
            return result['config_value'] if result else None
        finally:
            conn.close()

    def fetch_users_from_main_app():
        """Fetch users from the main application API"""
        import requests
        main_app_url = os.getenv("MAIN_APP_URL", "http://localhost:8000")
        api_key = os.getenv("LICENSING_API_KEY", "change-me")
        
        try:
            response = requests.get(
                f"{main_app_url}/api/licensing/users",
                headers={"X-Licensing-API-Key": api_key},
                timeout=10
            )
            if response.status_code == 200:
                return response.json().get("users", [])
            else:
                logger.error(f"Failed to fetch users: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Error fetching users from main app: {e}")
            return []

    def generate_license_key() -> str:
        return secrets.token_urlsafe(32)
    
    def generate_api_key() -> str:
        return secrets.token_urlsafe(32)
    
    def hash_key(key: str) -> str:
        import hashlib
        return hashlib.sha256(key.encode()).hexdigest()
    
    def get_all_licenses():
        conn = get_db_connection()
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM licenses ORDER BY created_at DESC")
            return cursor.fetchall()
        finally:
            conn.close()
    
    def get_license_by_key(license_key: str):
        conn = get_db_connection()
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM licenses WHERE license_key = %s", (license_key,))
            return cursor.fetchone()
        finally:
            conn.close()
    
    def validate_license_key(license_key: str) -> dict:
        """Validate a license key and return its details"""
        license_data = get_license_by_key(license_key)
        if not license_data:
            return {"valid": False, "message": "License not found"}
        
        if not license_data["is_active"]:
            return {"valid": False, "message": "License is inactive"}
        
        if license_data["expiry_date"]:
            if isinstance(license_data["expiry_date"], date):
                expiry_date = license_data["expiry_date"]
            else:
                expiry_date = datetime.strptime(license_data["expiry_date"], "%Y-%m-%d").date()
            
            if datetime.now().date() > expiry_date:
                return {"valid": False, "message": "License has expired"}
        
        return {
            "valid": True,
            "company_name": license_data["company_name"],
            "max_stores": license_data["max_stores"],
            "max_questionnaires": license_data["max_questionnaires"],
            "features": json.loads(license_data["features"]) if license_data["features"] else {},
            "expiry_date": license_data["expiry_date"].isoformat() if license_data["expiry_date"] else None
        }
    
    def save_license(company_name, contact_email, max_stores, max_questionnaires, features, expiry_date):
        """Save a new license with validation."""
        # Input validation
        if not company_name or not company_name.strip():
            logger.error("Company name is required")
            return None
        if max_stores < 0 or max_questionnaires < 0:
            logger.error("max_stores and max_questionnaires must be non-negative")
            return None
        if contact_email and "@" not in contact_email:
            logger.error("Invalid email format")
            return None
        
        try:
            with get_db_connection_with_transaction() as conn:
                cursor = conn.cursor()
                
                license_key = generate_license_key()
                api_key = generate_api_key()
                license_key_hash = hash_key(license_key)
                
                cursor.execute(
                    """
                    INSERT INTO licenses (license_key, license_key_hash, company_name, contact_email, 
                                         max_stores, max_questionnaires, features, expiry_date, api_key)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (license_key, license_key_hash, company_name.strip(), contact_email, 
                     max_stores, max_questionnaires, json.dumps(features), expiry_date, api_key)
                )
                
                return {"license_key": license_key, "api_key": api_key}
        except mysql.connector.Error as e:
            logger.error(f"Database error saving license: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error saving license: {e}")
            return None
    
    def toggle_license(license_id):
        """Toggle license active status."""
        try:
            with get_db_connection_with_transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE licenses SET is_active = NOT is_active WHERE id = %s", (license_id,))
            return True
        except mysql.connector.Error as e:
            logger.error(f"Database error toggling license: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error toggling license: {e}")
            return False
    
    def delete_license(license_id):
        """Delete a license by ID."""
        try:
            with get_db_connection_with_transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM licenses WHERE id = %s", (license_id,))
            return True
        except mysql.connector.Error as e:
            logger.error(f"Database error deleting license: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error deleting license: {e}")
            return False
    
    # Routes
    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            if secrets.compare_digest(username, portal_admin_username) and secrets.compare_digest(password, portal_admin_password):
                session["portal_admin_authenticated"] = True
                next_url = request.args.get("next") or url_for("index")
                return redirect(next_url if next_url.startswith("/") else url_for("index"))
            flash("Invalid username or password", "danger")
        return render_template("licensing/login.html")

    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))

    @app.route("/")
    @login_required
    def index():
        licenses = get_all_licenses()
        users = fetch_users_from_main_app()
        return render_template("licensing/index.html", licenses=licenses, users=users)
    
    @app.route("/license/add", methods=["POST"])
    @login_required
    def add_license():
        company_name = request.form.get("company_name", "").strip()
        contact_email = request.form.get("contact_email", "").strip() or None
        max_stores = int(request.form.get("max_stores", "0"))
        max_questionnaires = int(request.form.get("max_questionnaires", "0"))
        expiry_date_str = request.form.get("expiry_date", "").strip() or None
        user_id = request.form.get("user_id", "").strip() or None

        # All features enabled by default
        features = {
            "analytics": True,
            "reports": True,
            "email_notifications": True,
            "custom_branding": True,
        }

        expiry_date = None
        if expiry_date_str:
            try:
                expiry_date = datetime.strptime(expiry_date_str, "%Y-%m-%d").date()
            except ValueError:
                flash("Invalid expiry date", "danger")
                return redirect(url_for("index"))

        result = save_license(company_name, contact_email, max_stores, max_questionnaires, features, expiry_date)

        if result:
            flash(
                f"License created for {company_name}. License Key: {result['license_key']} | API Key: {result['api_key']}",
                "success"
            )
        else:
            flash("Failed to create license", "danger")

        return redirect(url_for("index"))

    @app.route("/license/generate/<int:user_id>", methods=["POST"])
    @login_required
    def generate_license_for_user(user_id):
        """Generate a license for an existing user from the main app"""
        users = fetch_users_from_main_app()
        user = next((u for u in users if u["id"] == user_id), None)
        
        if not user:
            flash("User not found", "danger")
            return redirect(url_for("index"))
        
        company_name = user.get("username", user.get("email", "Unknown"))
        contact_email = user.get("email")
        max_stores = user.get("max_stores", 0)
        max_questionnaires = 0  # Default value
        
        features = {
            "analytics": True,
            "reports": True,
            "email_notifications": False,
            "custom_branding": False,
        }
        
        expiry_date = None
        
        result = save_license(company_name, contact_email, max_stores, max_questionnaires, features, expiry_date)
        
        if result:
            flash(f"License generated for {company_name}. Key: {result['license_key']}", "success")
        else:
            flash("Failed to generate license", "danger")
        
        return redirect(url_for("index"))
    
    @app.route("/license/<int:license_id>/toggle", methods=["POST"])
    @login_required
    def toggle_license_route(license_id):
        if toggle_license(license_id):
            flash("License status updated", "success")
        else:
            flash("Failed to update license", "danger")
        return redirect(url_for("index"))
    
    @app.route("/license/<int:license_id>/delete", methods=["POST"])
    @login_required
    def delete_license_route(license_id):
        if delete_license(license_id):
            flash("License deleted", "success")
        else:
            flash("Failed to delete license", "danger")
        return redirect(url_for("index"))
    
    @app.route("/license/<int:license_id>/renew", methods=["POST"])
    @login_required
    def renew_license_route(license_id):
        """Renew a license with a custom expiry date"""
        try:
            new_expiry_str = request.form.get("new_expiry_date", "").strip()
            
            if not new_expiry_str:
                flash("Please provide an expiry date", "danger")
                return redirect(url_for("index"))
            
            # Parse the new expiry date
            try:
                new_expiry = datetime.strptime(new_expiry_str, "%Y-%m-%d").date()
            except ValueError:
                flash("Invalid expiry date format", "danger")
                return redirect(url_for("index"))
            
            with get_db_connection_with_transaction() as conn:
                cursor = conn.cursor()
                
                # Update the license with the new expiry date
                cursor.execute(
                    "UPDATE licenses SET expiry_date = %s, is_active = TRUE WHERE id = %s",
                    (new_expiry, license_id)
                )
            
            flash(f"License renewed successfully. New expiry: {new_expiry}", "success")
        except mysql.connector.Error as e:
            logger.error(f"Database error renewing license: {e}")
            flash("Failed to renew license", "danger")
        except Exception as e:
            logger.error(f"Unexpected error renewing license: {e}")
            flash("Failed to renew license", "danger")
        
        return redirect(url_for("index"))
    
    # ── Ticket helpers ──────────────────────────────────────────────
    def get_all_tickets():
        conn = get_db_connection()
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM support_tickets ORDER BY FIELD(status,'open','in_progress','resolved','closed'), created_at DESC")
            return cursor.fetchall()
        finally:
            conn.close()

    def get_tickets_by_license(license_key):
        conn = get_db_connection()
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM support_tickets WHERE license_key = %s ORDER BY created_at DESC", (license_key,))
            return cursor.fetchall()
        finally:
            conn.close()

    def create_ticket(license_key, company_name, contact_email, subject, message, ticket_type='general'):
        try:
            license_data = get_license_by_key(license_key) if license_key else None
            license_id = license_data['id'] if license_data else None
            with get_db_connection_with_transaction() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """INSERT INTO support_tickets
                       (license_id, license_key, company_name, contact_email, subject, message, ticket_type)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (license_id, license_key, company_name, contact_email, subject, message, ticket_type)
                )
            return True
        except Exception as e:
            logger.error(f"Error creating ticket: {e}")
            return False

    # ── API routes ────────────────────────────────────────────────
    @app.route("/api/validate", methods=["POST"])
    def api_validate_json():
        """Validate a license from a JSON request."""
        data = request.get_json(silent=True) or {}
        license_key = (data.get("license_key") or "").strip()
        if not license_key:
            return jsonify({"valid": False, "message": "License key is required"}), 400
        return jsonify(validate_license_key(license_key))

    @app.route("/api/validate/<license_key>", methods=["GET", "POST"])
    def api_validate(license_key):
        """API endpoint for validating licenses"""
        result = validate_license_key(license_key)
        return jsonify(result)

    @app.route("/api/tickets/create", methods=["POST"])
    def api_create_ticket():
        """API endpoint for creating tickets from the main app"""
        data = request.get_json() or {}
        license_key = data.get("license_key", "").strip()
        contact_email = data.get("contact_email", "").strip()
        subject = data.get("subject", "").strip()
        message = data.get("message", "").strip()
        ticket_type = data.get("ticket_type", "general")

        if not subject or not message or not contact_email:
            return jsonify({"error": "subject, message, and contact_email are required"}), 400

        license_data = get_license_by_key(license_key) if license_key else None
        company_name = license_data["company_name"] if license_data else "Unknown"

        # Create ticket
        if create_ticket(license_key, company_name, contact_email, subject, message, ticket_type):
            # Also create conversation and message for messaging system
            try:
                conv = get_or_create_conversation(license_key, company_name, contact_email)
                conn = get_db_connection()
                try:
                    cursor = conn.cursor()
                    # Add client message to conversation
                    full_message = f"[{ticket_type.upper()}] {subject}\n\n{message}"
                    cursor.execute(
                        """
                        INSERT INTO messages (conversation_id, sender_type, sender_name, message)
                        VALUES (%s, 'client', %s, %s)
                        """,
                        (conv['id'], contact_email, full_message)
                    )
                    # Update conversation
                    cursor.execute(
                        """
                        UPDATE client_conversations
                        SET last_message_at = NOW(), last_message_preview = %s, unread_count = unread_count + 1, updated_at = NOW()
                        WHERE id = %s
                        """,
                        (full_message[:100] if len(full_message) > 100 else full_message, conv['id'])
                    )
                    conn.commit()
                finally:
                    conn.close()
            except Exception as e:
                logger.error(f"Error creating conversation for ticket: {e}")
                # Don't fail the ticket creation if conversation creation fails
            return jsonify({"success": True}), 201
        return jsonify({"error": "Failed to create ticket"}), 500

    @app.route("/api/tickets/<license_key>", methods=["GET"])
    def api_get_tickets(license_key):
        """API endpoint for fetching tickets by license key"""
        tickets = get_tickets_by_license(license_key)
        # Convert datetime objects for JSON serialization
        serialized = []
        for t in tickets:
            row = dict(t)
            for k, v in row.items():
                if hasattr(v, 'isoformat'):
                    row[k] = v.isoformat()
            serialized.append(row)
        return jsonify({"tickets": serialized})

    # ── Messaging system ─────────────────────────────────────────
    def get_or_create_conversation(license_key, company_name, contact_email):
        """Get or create a conversation for a client"""
        client_identifier = license_key or contact_email
        conn = get_db_connection()
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                "SELECT * FROM client_conversations WHERE client_identifier = %s",
                (client_identifier,)
            )
            conv = cursor.fetchone()
            if not conv:
                cursor.execute(
                    """
                    INSERT INTO client_conversations (client_identifier, company_name, license_key, contact_email)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (client_identifier, company_name, license_key, contact_email)
                )
                conn.commit()
                cursor.execute(
                    "SELECT * FROM client_conversations WHERE client_identifier = %s",
                    (client_identifier,)
                )
                conv = cursor.fetchone()
            return conv
        finally:
            conn.close()

    @app.route("/messages")
    @login_required
    def admin_messages():
        """Messages page with client selector and message threads"""
        conn = get_db_connection()
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                "SELECT * FROM client_conversations ORDER BY last_message_at DESC, created_at DESC"
            )
            conversations = cursor.fetchall()
            return render_template("licensing/messages.html", conversations=conversations)
        finally:
            conn.close()

    @app.route("/api/conversations")
    def api_get_conversations():
        """API endpoint to get all conversations"""
        conn = get_db_connection()
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                "SELECT * FROM client_conversations ORDER BY last_message_at DESC, created_at DESC"
            )
            conversations = cursor.fetchall()
            # Convert datetime objects for JSON serialization
            for conv in conversations:
                for k, v in conv.items():
                    if hasattr(v, 'isoformat'):
                        conv[k] = v.isoformat()
            return jsonify({"conversations": conversations})
        finally:
            conn.close()

    @app.route("/api/conversations/<int:conversation_id>/messages")
    def api_get_conversation_messages(conversation_id):
        """API endpoint to get messages for a conversation"""
        conn = get_db_connection()
        try:
            cursor = conn.cursor(dictionary=True)
            # Mark messages as read
            cursor.execute(
                "UPDATE messages SET is_read = TRUE WHERE conversation_id = %s AND sender_type = 'client'",
                (conversation_id,)
            )
            conn.commit()
            # Update unread count
            cursor.execute(
                "UPDATE client_conversations SET unread_count = 0 WHERE id = %s",
                (conversation_id,)
            )
            conn.commit()

            cursor.execute(
                "SELECT * FROM messages WHERE conversation_id = %s ORDER BY created_at ASC",
                (conversation_id,)
            )
            messages = cursor.fetchall()
            # Convert datetime objects for JSON serialization
            for msg in messages:
                for k, v in msg.items():
                    if hasattr(v, 'isoformat'):
                        msg[k] = v.isoformat()
            return jsonify({"messages": messages})
        finally:
            conn.close()

    @app.route("/api/conversations/<int:conversation_id>/send", methods=["POST"])
    def api_send_message(conversation_id):
        """API endpoint to send a message to a conversation"""
        data = request.get_json() or {}
        message = data.get("message", "").strip()
        sender_type = data.get("sender_type", "admin")
        sender_name = data.get("sender_name", "Support Team")
        if not message:
            return jsonify({"error": "Message is required"}), 400

        conn = get_db_connection()
        try:
            cursor = conn.cursor(dictionary=True)
            # Get conversation details
            cursor.execute("SELECT * FROM client_conversations WHERE id = %s", (conversation_id,))
            conv = cursor.fetchone()
            if not conv:
                return jsonify({"error": "Conversation not found"}), 404

            # Insert message
            cursor.execute(
                """
                INSERT INTO messages (conversation_id, sender_type, sender_name, message)
                VALUES (%s, %s, %s, %s)
                """,
                (conversation_id, sender_type, sender_name, message)
            )
            # Update conversation
            cursor.execute(
                """
                UPDATE client_conversations
                SET last_message_at = NOW(), last_message_preview = %s, unread_count = unread_count + 1, updated_at = NOW()
                WHERE id = %s
                """,
                (message[:100] if len(message) > 100 else message, conversation_id)
            )
            conn.commit()

            # If admin message, sync to main feedback system
            if sender_type == 'admin':
                try:
                    # Get main feedback system URL from database config or environment
                    main_system_url = get_system_config('main_system_url') or os.getenv("MAIN_SYSTEM_URL")
                    if not main_system_url:
                        logger.warning("MAIN_SYSTEM_URL not configured, skipping sync to main system")
                    else:
                        import requests as http_requests
                        logger.info(f"Syncing admin message to main system at {main_system_url}")
                        resp = http_requests.post(f"{main_system_url}/api/portal/sync/message", json={
                            "client_identifier": conv['client_identifier'],
                            "message": message,
                            "sender_type": "admin",
                            "sender_name": sender_name
                        }, timeout=5)
                        if resp.status_code in (200, 201):
                            logger.info("Successfully synced admin message to main system")
                        else:
                            logger.error(f"Failed to sync admin message: {resp.status_code} - {resp.text}")
                except Exception as e:
                    logger.error(f"Failed to sync admin message to main system: {e}")

            return jsonify({"success": True})
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return jsonify({"error": "Failed to send message"}), 500
        finally:
            conn.close()

    @app.route("/api/conversations/by-identifier/<client_identifier>", methods=["GET"])
    def api_get_conversation_by_identifier(client_identifier):
        """API endpoint to get conversation by client identifier (license_key or email)"""
        conn = get_db_connection()
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                "SELECT * FROM client_conversations WHERE client_identifier = %s",
                (client_identifier,)
            )
            conv = cursor.fetchone()
            if not conv:
                return jsonify({"error": "Conversation not found"}), 404
            # Convert datetime objects for JSON serialization
            for k, v in conv.items():
                if hasattr(v, 'isoformat'):
                    conv[k] = v.isoformat()
            return jsonify({"conversation": conv})
        finally:
            conn.close()

    @app.route("/api/conversations/create", methods=["POST"])
    def api_create_conversation():
        """API endpoint to create a conversation from external system"""
        data = request.get_json() or {}
        client_identifier = data.get("client_identifier", "").strip()
        company_name = (data.get("company_name") or "").strip()
        license_key = (data.get("license_key") or "").strip()
        contact_email = (data.get("contact_email") or "").strip()

        if not client_identifier:
            return jsonify({"error": "client_identifier is required"}), 400
        # Fallback contact_email to client_identifier if empty
        if not contact_email:
            contact_email = client_identifier
        if not company_name:
            company_name = contact_email

        conn = get_db_connection()
        try:
            cursor = conn.cursor(dictionary=True)
            # Check if conversation already exists
            cursor.execute(
                "SELECT * FROM client_conversations WHERE client_identifier = %s",
                (client_identifier,)
            )
            conv = cursor.fetchone()
            if conv:
                # Return existing conversation
                for k, v in conv.items():
                    if hasattr(v, 'isoformat'):
                        conv[k] = v.isoformat()
                return jsonify({"conversation": conv, "existing": True})

            # Create new conversation
            cursor.execute(
                """
                INSERT INTO client_conversations (client_identifier, company_name, license_key, contact_email)
                VALUES (%s, %s, %s, %s)
                """,
                (client_identifier, company_name, license_key, contact_email)
            )
            conn.commit()
            cursor.execute(
                "SELECT * FROM client_conversations WHERE client_identifier = %s",
                (client_identifier,)
            )
            conv = cursor.fetchone()
            for k, v in conv.items():
                if hasattr(v, 'isoformat'):
                    conv[k] = v.isoformat()
            return jsonify({"conversation": conv, "existing": False})
        except Exception as e:
            logger.error(f"Error creating conversation: {e}")
            return jsonify({"error": "Failed to create conversation"}), 500
        finally:
            conn.close()

    @app.route("/api/config/main_system_url", methods=["GET", "POST"])
    @login_required
    def api_config_main_system_url():
        """API endpoint to get or set main system URL configuration"""
        if request.method == "GET":
            main_system_url = get_system_config('main_system_url')
            return jsonify({"main_system_url": main_system_url})
        else:
            data = request.get_json() or {}
            main_system_url = data.get("main_system_url", "").strip()
            conn = get_db_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE system_config SET config_value = %s, updated_at = NOW() WHERE config_key = 'main_system_url'",
                    (main_system_url,)
                )
                conn.commit()
                return jsonify({"success": True, "main_system_url": main_system_url})
            finally:
                conn.close()

    # ── Admin ticket management ──────────────────────────────────
    @app.route("/tickets")
    @login_required
    def admin_tickets():
        tickets = get_all_tickets()
        return render_template("licensing/tickets.html", tickets=tickets)

    @app.route("/ticket/<int:ticket_id>/reply", methods=["POST"])
    @login_required
    def admin_reply_ticket(ticket_id):
        reply = request.form.get("admin_reply", "").strip()
        new_status = request.form.get("status", "in_progress")
        if not reply:
            flash("Reply cannot be empty.", "danger")
            return redirect(url_for("admin_tickets"))
        try:
            with get_db_connection_with_transaction() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE support_tickets SET admin_reply = %s, status = %s, replied_at = NOW() WHERE id = %s",
                    (reply, new_status, ticket_id)
                )
            flash("Reply sent successfully.", "success")
        except Exception as e:
            logger.error(f"Error replying to ticket: {e}")
            flash("Failed to send reply.", "danger")
        return redirect(url_for("admin_tickets"))

    @app.route("/ticket/<int:ticket_id>/status", methods=["POST"])
    @login_required
    def admin_update_ticket_status(ticket_id):
        new_status = request.form.get("status", "open")
        try:
            with get_db_connection_with_transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE support_tickets SET status = %s WHERE id = %s", (new_status, ticket_id))
            flash(f"Ticket status updated to {new_status}.", "success")
        except Exception as e:
            logger.error(f"Error updating ticket status: {e}")
            flash("Failed to update ticket.", "danger")
        return redirect(url_for("admin_tickets"))

    # Initialize schema on startup (non-fatal — app still starts if DB is temporarily unavailable)
    try:
        init_schema()
    except Exception as e:
        logger.error(f"Schema initialization failed, will retry on first request: {e}")

    @app.route("/health")
    def health_check():
        return jsonify({"status": "ok"}), 200

    return app

# Module-level app instance for gunicorn compatibility
try:
    app = create_app()
    logger.info("Licensing app created successfully")
except Exception as e:
    logger.error(f"FATAL: Failed to create app: {e}")
    # Create a minimal fallback app so gunicorn doesn't crash entirely
    app = Flask(__name__)
    @app.route("/health")
    def health_fallback():
        return jsonify({"status": "error", "message": "App failed to initialize"}), 503

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8081))
    app.run(host="0.0.0.0", port=port)
