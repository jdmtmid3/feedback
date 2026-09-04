"""
Email configuration for feedback reply system
"""

import os
import re
from html import escape
from flask_mail import Mail, Message

class EmailConfig:
    def __init__(self, app=None):
        self.mail = None
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        self.app = app
        # Email configuration
        # Switch to Gmail SSL (Port 465) as Port 587 is being blocked by Railway
        app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
        app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', '465'))
        app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'false').lower() == 'true'
        app.config['MAIL_USE_SSL'] = os.getenv('MAIL_USE_SSL', 'true').lower() == 'true'
        app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
        app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
        app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER', app.config.get('MAIL_USERNAME'))
        
        # Increase timeout and set it at the socket level
        import socket
        socket.setdefaulttimeout(30)
        
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Email system initialized: Server={app.config['MAIL_SERVER']}, Port={app.config['MAIL_PORT']}, SSL={app.config['MAIL_USE_SSL']}, TLS={app.config['MAIL_USE_TLS']}")
        
        if not app.config['MAIL_USERNAME'] or not app.config['MAIL_PASSWORD']:
            logger.warning("MAIL_USERNAME or MAIL_PASSWORD not set. Email sending will likely fail.")
            
        self.mail = Mail(app)
    
    def send_feedback_reply(self, to_email, customer_name, reply_message, store_name, feedback_summary, 
                          template_type='standard', cc_emails=None, bcc_emails=None, attachments=None):
        """Send through Resend only when outbound email is explicitly enabled.

        Keep email disabled until a verified sending domain is available. To
        enable later, set EMAIL_SENDING_ENABLED=true together with a Resend API
        key and a sender address on that verified domain.
        """
        email_enabled = os.getenv('EMAIL_SENDING_ENABLED', 'false').lower() == 'true'
        if not email_enabled:
            return False, "Email sending is temporarily disabled until the sending domain is verified."

        resend_api_key = os.getenv('RESEND_API_KEY')
        if resend_api_key:
            return self._send_via_resend(resend_api_key, to_email, customer_name, reply_message, store_name, feedback_summary, template_type)

        return False, "Resend is not configured. Add RESEND_API_KEY before enabling email sending."

    def _send_via_resend(self, api_key, to_email, customer_name, reply_message, store_name, feedback_summary, template_type):
        """Send email via Resend API (HTTPS - bypasses Railway port blocks)"""
        import requests
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            html_content = self._get_email_template(template_type, customer_name, store_name, feedback_summary, reply_message)
            
            response = requests.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": os.getenv('MAIL_DEFAULT_SENDER', 'Feedback System <onboarding@resend.dev>'),
                    "to": to_email,
                    "subject": f"Response to your feedback for {store_name}",
                    "html": html_content
                },
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                logger.info(f"Email sent via Resend API to {to_email}")
                return True, "Email sent successfully via API."
            else:
                error_data = response.json()
                logger.error(f"Resend API error: {error_data}")
                return False, f"API Error: {error_data.get('message', 'Unknown error')}"
                
        except Exception as e:
            logger.error(f"Resend API unexpected error: {str(e)}")
            return False, f"API connection failed: {str(e)}"

    def _send_via_smtp(self, to_email, customer_name, reply_message, store_name, feedback_summary, 
                          template_type='standard', cc_emails=None, bcc_emails=None, attachments=None):
        """Original SMTP sending logic"""
        try:
            # Create message
            msg = Message(
                subject=f"Response to your feedback about {store_name}",
                recipients=[to_email],
                sender=self.mail.default_sender,
                cc=cc_emails or [],
                bcc=bcc_emails or []
            )
            
            # Add attachments if provided
            if attachments:
                for attachment in attachments:
                    if attachment.get('filename') and attachment.get('content'):
                        msg.attach(
                            attachment['filename'],
                            attachment.get('content_type', 'application/octet-stream'),
                            attachment['content']
                        )
            
            # Get email template based on type
            html_body = self._get_email_template(
                template_type, customer_name, store_name, feedback_summary, reply_message
            )
            
            msg.html = html_body
            
            # Send email
            self.mail.send(msg)
            
            # Log the email for tracking
            self._log_email_sent(to_email, store_name, template_type, reply_message)
            
            return True, "Email sent successfully"
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            
            error_msg = str(e)
            if "Network is unreachable" in error_msg or "[Errno 101]" in error_msg:
                user_friendly_error = (
                    "Network unreachable. This often happens if the cloud provider (Railway) is blocking the email port. "
                    "Try using a different port or check if your SMTP server (smtp.gmail.com) is reachable from this environment."
                )
                logger.error(f"NETWORK ERROR sending email to {to_email}: {error_msg}")
                return False, user_friendly_error
            
            logger.error(f"Unexpected error sending email to {to_email}: {error_msg}")
            return False, f"An unexpected error occurred: {error_msg}"
    
    def _get_email_template(self, template_type, customer_name, store_name, feedback_summary, reply_message):
        """Get email template based on type"""
        templates = {
            'standard': self._get_standard_template(customer_name, store_name, feedback_summary, reply_message),
            'apology': self._get_apology_template(customer_name, store_name, feedback_summary, reply_message),
            'appreciation': self._get_appreciation_template(customer_name, store_name, feedback_summary, reply_message),
            'follow_up': self._get_follow_up_template(customer_name, store_name, feedback_summary, reply_message)
        }
        return templates.get(template_type, templates['standard'])
    
    def _get_standard_template(self, customer_name, store_name, feedback_summary, reply_message):
        """Standard email template"""
        return self._build_polished_template(
            customer_name, store_name, feedback_summary, reply_message,
            eyebrow="Feedback update", icon="💬", title="We heard you.",
            intro="Thank you for taking the time to share your experience.",
            closing="Your input helps us create a better experience for everyone.",
            signoff="Warm regards",
        )
    
    def _get_apology_template(self, customer_name, store_name, feedback_summary, reply_message):
        """Apology email template for negative feedback"""
        return self._build_polished_template(
            customer_name, store_name, feedback_summary, reply_message,
            eyebrow="A personal response", icon="🤝", title="We’re truly sorry.",
            intro="Thank you for telling us what happened. Your experience matters to us.",
            closing="We take your feedback seriously and are committed to making things right.",
            signoff="With sincere apologies",
        )
    
    def _get_appreciation_template(self, customer_name, store_name, feedback_summary, reply_message):
        """Appreciation email template for positive feedback"""
        reward_email = "Google Review Reward" in str(feedback_summary)
        return self._build_polished_template(
            customer_name, store_name, feedback_summary, reply_message,
            eyebrow="A little thank-you", icon="🎁" if reward_email else "✨",
            title="Your reward is here!" if reward_email else "You made our day!",
            intro="Your Google Review has been verified. Here are your reward details." if reward_email else "Thank you for sharing such thoughtful feedback with us.",
            closing="Please keep this email and present the code with your original receipt." if reward_email else "Your kind words inspire our team to keep delivering our best.",
            signoff="With gratitude",
            is_reward=reward_email,
        )
    
    def _get_follow_up_template(self, customer_name, store_name, feedback_summary, reply_message):
        """Follow-up email template"""
        return self._build_polished_template(
            customer_name, store_name, feedback_summary, reply_message,
            eyebrow="Following up", icon="👋", title="Checking in with you.",
            intro="We wanted to follow up on the feedback you recently shared.",
            closing="We hope our response addresses your concern and leaves you feeling heard.",
            signoff="Warm regards",
        )

    def _build_polished_template(self, customer_name, store_name, feedback_summary,
                                 reply_message, eyebrow, icon, title, intro,
                                 closing, signoff, is_reward=False):
        """Build a responsive, email-client-safe branded customer message."""
        name = escape(str(customer_name or "Valued Customer"))
        store = escape(str(store_name or "Our Store"))
        summary = escape(str(feedback_summary or "Feedback submitted"))
        raw_response = str(reply_message or "Thank you for your feedback.")
        response = escape(raw_response).replace("\n", "<br>")
        reward_label = "YOUR REWARD DETAILS" if is_reward else "OUR RESPONSE"
        if is_reward:
            code_match = re.search(r"reward code is\s+([A-Z0-9-]+)", raw_response, re.IGNORECASE)
            type_match = re.search(r"Reward:\s*(.+?)\.", raw_response, re.IGNORECASE)
            if code_match:
                code = escape(code_match.group(1).upper())
                reward_type = escape(type_match.group(1)) if type_match else "Your store reward"
                response = f"""
                  <div style="text-align:center;padding:4px 0 2px;">
                    <div style="font-size:34px;line-height:42px;margin-bottom:5px;">🎁</div>
                    <div style="font-size:11px;line-height:16px;font-weight:800;letter-spacing:1.2px;color:#d45125;">REWARD UNLOCKED</div>
                    <div style="margin:8px 0 5px;font-family:Menlo,Monaco,Consolas,monospace;font-size:27px;line-height:35px;font-weight:800;letter-spacing:2px;color:#b83e18;word-break:break-all;">{code}</div>
                    <div style="font-size:15px;line-height:23px;font-weight:700;color:#39333a;">{reward_type}</div>
                    <div style="border-top:2px dashed #ffd0bb;margin:18px -21px 15px;"></div>
                    <div style="font-size:13px;line-height:21px;color:#6b6570;">Bring your original receipt and a screenshot of this email. This code can only be redeemed once.</div>
                  </div>"""
        summary_block = "" if is_reward else f"""
            <tr><td style="padding:0 32px 18px;">
              <div style="background:#fff7f2;border:1px solid #ffe1d3;border-radius:18px;padding:18px 20px;">
                <div style="font-size:11px;line-height:16px;font-weight:800;letter-spacing:1.2px;color:#c64b20;margin-bottom:7px;">YOUR FEEDBACK</div>
                <div style="font-size:15px;line-height:24px;color:#4b5563;font-style:italic;">&ldquo;{summary}&rdquo;</div>
              </div>
            </td></tr>"""
        return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(title)}</title></head>
<body style="margin:0;padding:0;background:#f4f4f6;color:#202124;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;">
  <div style="display:none;max-height:0;overflow:hidden;color:transparent;">A message from {store} about your feedback.</div>
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background:#f4f4f6;">
    <tr><td align="center" style="padding:28px 12px;">
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="max-width:600px;background:#ffffff;border-radius:28px;overflow:hidden;box-shadow:0 14px 45px rgba(31,41,55,.10);">
        <tr><td style="height:7px;background:#ff6b35;font-size:0;line-height:0;">&nbsp;</td></tr>
        <tr><td align="center" style="padding:36px 32px 25px;background:#fff8f4;">
          <div style="width:64px;height:64px;line-height:64px;border-radius:20px;background:#ffffff;font-size:31px;text-align:center;box-shadow:0 8px 20px rgba(66,36,25,.10);margin-bottom:17px;">{icon}</div>
          <div style="font-size:11px;line-height:16px;font-weight:800;letter-spacing:1.5px;color:#d45125;text-transform:uppercase;">{escape(eyebrow)}</div>
          <h1 style="margin:7px 0 9px;font-size:30px;line-height:37px;letter-spacing:-.7px;color:#231f20;">{escape(title)}</h1>
          <p style="margin:0;font-size:15px;line-height:24px;color:#67616a;">{escape(intro)}</p>
        </td></tr>
        <tr><td style="padding:28px 32px 18px;font-size:16px;line-height:26px;color:#343038;">
          Hi <strong>{name}</strong>,<br><br>Thank you for connecting with <strong>{store}</strong>.
        </td></tr>
        {summary_block}
        <tr><td style="padding:0 32px 20px;">
          <div style="border:1px solid #e8e7ea;border-radius:20px;padding:21px;background:#ffffff;box-shadow:0 5px 18px rgba(31,41,55,.05);">
            <div style="font-size:11px;line-height:16px;font-weight:800;letter-spacing:1.2px;color:#d45125;margin-bottom:9px;">{reward_label}</div>
            <div style="font-size:16px;line-height:26px;color:#29252b;">{response}</div>
          </div>
        </td></tr>
        <tr><td style="padding:0 32px 30px;font-size:15px;line-height:24px;color:#625d65;">{escape(closing)}</td></tr>
        <tr><td style="padding:24px 32px;background:#242124;color:#ffffff;">
          <div style="font-size:14px;line-height:22px;color:#d7d3d7;">{escape(signoff)},</div>
          <div style="font-size:17px;line-height:25px;font-weight:800;color:#ffffff;">Customer Care · {store}</div>
        </td></tr>
      </table>
      <div style="max-width:540px;padding:18px 20px 0;text-align:center;font-size:12px;line-height:18px;color:#8a858d;">This email was sent in response to feedback you submitted to {store}. Please do not share a one-time reward code with others.</div>
    </td></tr>
  </table>
</body></html>"""
    
    def _log_email_sent(self, to_email, store_name, template_type, reply_message):
        """Log email sent for tracking purposes"""
        import json
        from datetime import datetime
        
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'to_email': to_email,
            'store_name': store_name,
            'template_type': template_type,
            'message_length': len(reply_message)
        }
        
        # Create logs directory if it doesn't exist
        os.makedirs('email_logs', exist_ok=True)
        
        # Append to log file with proper error handling
        log_file = 'email_logs/email_sent_log.json'
        try:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry) + '\n')
        except IOError as e:
            logger.error(f"Failed to write email log (IOError): {e}")
        except Exception as e:
            logger.error(f"Failed to log email: {e}")
    
    def send_bulk_feedback_reply(self, email_list, customer_names, reply_message, store_name, 
                               feedback_summaries, template_type='standard'):
        """Send bulk email replies to multiple customers"""
        results = []
        
        for i, to_email in enumerate(email_list):
            customer_name = customer_names[i] if i < len(customer_names) else "Valued Customer"
            feedback_summary = feedback_summaries[i] if i < len(feedback_summaries) else "No summary available"
            
            success, message = self.send_feedback_reply(
                to_email=to_email,
                customer_name=customer_name,
                reply_message=reply_message,
                store_name=store_name,
                feedback_summary=feedback_summary,
                template_type=template_type
            )
            
            results.append({
                'email': to_email,
                'success': success,
                'message': message
            })
        
        return results
    
    def get_email_statistics(self):
        """Get email sending statistics"""
        import json
        from datetime import datetime, timedelta
        from collections import defaultdict
        
        log_file = 'email_logs/email_sent_log.json'
        if not os.path.exists(log_file):
            return {'total_emails': 0, 'last_7_days': 0, 'by_template': {}, 'by_store': {}}
        
        stats = {
            'total_emails': 0,
            'last_7_days': 0,
            'by_template': defaultdict(int),
            'by_store': defaultdict(int)
        }
        
        seven_days_ago = datetime.now() - timedelta(days=7)
        
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        try:
                            log_entry = json.loads(line.strip())
                            stats['total_emails'] += 1
                            
                            # Check if within last 7 days
                            log_time = datetime.fromisoformat(log_entry['timestamp'])
                            if log_time >= seven_days_ago:
                                stats['last_7_days'] += 1
                            
                            stats['by_template'][log_entry['template_type']] += 1
                            stats['by_store'][log_entry['store_name']] += 1
                        except (json.JSONDecodeError, KeyError, ValueError) as e:
                            logger.warning(f"Skipping malformed log entry: {e}")
                            continue
        except IOError as e:
            logger.error(f"Failed to read email logs (IOError): {e}")
        except Exception as e:
            logger.error(f"Unexpected error reading email logs: {e}")
        
        # Convert defaultdicts to regular dicts for JSON serialization
        return {
            'total_emails': stats['total_emails'],
            'last_7_days': stats['last_7_days'],
            'by_template': dict(stats['by_template']),
            'by_store': dict(stats['by_store'])
        }

# Initialize email config
email_config = EmailConfig()
