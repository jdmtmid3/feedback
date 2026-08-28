"""
Email configuration for feedback reply system
"""

import os
from flask_mail import Mail, Message

class EmailConfig:
    def __init__(self, app=None):
        self.mail = None
        if app:
            self.init_app(app)
    
    def init_app(self, app):
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
        """Send reply email to customer using SendGrid API (or Resend/SMTP as backup)."""
        sendgrid_api_key = os.getenv('SENDGRID_API_KEY')
        resend_api_key = os.getenv('RESEND_API_KEY')
        
        if sendgrid_api_key:
            return self._send_via_sendgrid(sendgrid_api_key, to_email, customer_name, reply_message, store_name, feedback_summary, template_type)
        elif resend_api_key:
            return self._send_via_resend(resend_api_key, to_email, customer_name, reply_message, store_name, feedback_summary, template_type)
        
        return self._send_via_smtp(to_email, customer_name, reply_message, store_name, feedback_summary, template_type, cc_emails, bcc_emails, attachments)

    def _send_via_sendgrid(self, api_key, to_email, customer_name, reply_message, store_name, feedback_summary, template_type):
        """Send email via SendGrid API (HTTPS - bypasses Railway port blocks)"""
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail as SGMail
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            html_content = self._get_email_template(template_type, customer_name, store_name, feedback_summary, reply_message)
            
            message = SGMail(
                from_email=os.getenv('MAIL_DEFAULT_SENDER', 'Feedback System <onboarding@resend.dev>'),
                to_emails=to_email,
                subject=f"Response to your feedback for {store_name}",
                html_content=html_content
            )
            
            # Explicitly set Reply-To to encourage engagement and avoid spam filters
            message.reply_to = os.getenv('MAIL_DEFAULT_SENDER')
            
            sg = SendGridAPIClient(api_key)
            response = sg.send(message)
            
            if response.status_code in [200, 201, 202]:
                logger.info(f"Email sent via SendGrid API to {to_email}")
                return True, "Email sent successfully via SendGrid API."
            else:
                logger.error(f"SendGrid API error: Status {response.status_code}")
                return False, f"SendGrid API Error: Status {response.status_code}"
                
        except Exception as e:
            logger.error(f"SendGrid API unexpected error: {str(e)}")
            return False, f"SendGrid API connection failed: {str(e)}"

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
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Response to Your Feedback</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background: #f8f9fa;
                    padding: 20px;
                    border-radius: 8px;
                    margin-bottom: 20px;
                    border-left: 4px solid #007bff;
                }}
                .content {{
                    background: white;
                    padding: 20px;
                    border-radius: 8px;
                    border: 1px solid #dee2e6;
                }}
                .footer {{
                    margin-top: 20px;
                    padding: 20px;
                    background: #f8f9fa;
                    border-radius: 8px;
                    text-align: center;
                    font-size: 14px;
                    color: #6c757d;
                }}
                .signature {{
                    margin-top: 30px;
                    border-top: 1px solid #dee2e6;
                    padding-top: 20px;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>Response to Your Feedback</h2>
                <p>Dear {customer_name},</p>
                <p>Thank you for taking the time to share your feedback about <strong>{store_name}</strong>.</p>
            </div>
            
            <div class="content">
                <h3>Your Feedback Summary:</h3>
                <p><em>"{feedback_summary}"</em></p>
                
                <h3>Our Response:</h3>
                <p>{reply_message}</p>
                
                <p>We value your input and are committed to improving our services based on customer feedback like yours.</p>
            </div>
            
            <div class="signature">
                <p>Best regards,<br>
                Customer Service Team<br>
                {store_name}</p>
            </div>
            
            <div class="footer">
                <p>This is an automated response to your feedback. If you have any questions, please don't hesitate to contact us directly.</p>
            </div>
        </body>
        </html>
        """
    
    def _get_apology_template(self, customer_name, store_name, feedback_summary, reply_message):
        """Apology email template for negative feedback"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Our Sincere Apologies</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background: #fff3cd;
                    padding: 20px;
                    border-radius: 8px;
                    margin-bottom: 20px;
                    border-left: 4px solid #ffc107;
                }}
                .content {{
                    background: white;
                    padding: 20px;
                    border-radius: 8px;
                    border: 1px solid #dee2e6;
                }}
                .footer {{
                    margin-top: 20px;
                    padding: 20px;
                    background: #f8f9fa;
                    border-radius: 8px;
                    text-align: center;
                    font-size: 14px;
                    color: #6c757d;
                }}
                .signature {{
                    margin-top: 30px;
                    border-top: 1px solid #dee2e6;
                    padding-top: 20px;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>Our Sincere Apologies</h2>
                <p>Dear {customer_name},</p>
                <p>We sincerely apologize for your experience at <strong>{store_name}</strong>.</p>
            </div>
            
            <div class="content">
                <h3>Your Feedback:</h3>
                <p><em>"{feedback_summary}"</em></p>
                
                <h3>Our Response:</h3>
                <p>{reply_message}</p>
                
                <p>We take your feedback seriously and are taking immediate steps to address the issues you've raised. Your satisfaction is our top priority.</p>
            </div>
            
            <div class="signature">
                <p>With sincere apologies,<br>
                Customer Service Team<br>
                {store_name}</p>
            </div>
            
            <div class="footer">
                <p>This is an automated response to your feedback. If you have any questions, please don't hesitate to contact us directly.</p>
            </div>
        </body>
        </html>
        """
    
    def _get_appreciation_template(self, customer_name, store_name, feedback_summary, reply_message):
        """Appreciation email template for positive feedback"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Thank You for Your Feedback!</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background: #d4edda;
                    padding: 20px;
                    border-radius: 8px;
                    margin-bottom: 20px;
                    border-left: 4px solid #28a745;
                }}
                .content {{
                    background: white;
                    padding: 20px;
                    border-radius: 8px;
                    border: 1px solid #dee2e6;
                }}
                .footer {{
                    margin-top: 20px;
                    padding: 20px;
                    background: #f8f9fa;
                    border-radius: 8px;
                    text-align: center;
                    font-size: 14px;
                    color: #6c757d;
                }}
                .signature {{
                    margin-top: 30px;
                    border-top: 1px solid #dee2e6;
                    padding-top: 20px;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>Thank You for Your Feedback!</h2>
                <p>Dear {customer_name},</p>
                <p>We're delighted to hear your positive feedback about <strong>{store_name}</strong>!</p>
            </div>
            
            <div class="content">
                <h3>Your Feedback:</h3>
                <p><em>"{feedback_summary}"</em></p>
                
                <h3>Our Response:</h3>
                <p>{reply_message}</p>
                
                <p>Your kind words mean a lot to us and motivate our team to continue providing excellent service.</p>
            </div>
            
            <div class="signature">
                <p>With gratitude,<br>
                Customer Service Team<br>
                {store_name}</p>
            </div>
            
            <div class="footer">
                <p>This is an automated response to your feedback. If you have any questions, please don't hesitate to contact us directly.</p>
            </div>
        </body>
        </html>
        """
    
    def _get_follow_up_template(self, customer_name, store_name, feedback_summary, reply_message):
        """Follow-up email template"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Follow-up to Your Feedback</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background: #e2e3e5;
                    padding: 20px;
                    border-radius: 8px;
                    margin-bottom: 20px;
                    border-left: 4px solid #6c757d;
                }}
                .content {{
                    background: white;
                    padding: 20px;
                    border-radius: 8px;
                    border: 1px solid #dee2e6;
                }}
                .footer {{
                    margin-top: 20px;
                    padding: 20px;
                    background: #f8f9fa;
                    border-radius: 8px;
                    text-align: center;
                    font-size: 14px;
                    color: #6c757d;
                }}
                .signature {{
                    margin-top: 30px;
                    border-top: 1px solid #dee2e6;
                    padding-top: 20px;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>Follow-up to Your Feedback</h2>
                <p>Dear {customer_name},</p>
                <p>We're following up on your recent feedback about <strong>{store_name}</strong>.</p>
            </div>
            
            <div class="content">
                <h3>Your Feedback:</h3>
                <p><em>"{feedback_summary}"</em></p>
                
                <h3>Our Response:</h3>
                <p>{reply_message}</p>
                
                <p>We wanted to ensure your concerns have been properly addressed and that you're satisfied with our response.</p>
            </div>
            
            <div class="signature">
                <p>Best regards,<br>
                Customer Service Team<br>
                {store_name}</p>
            </div>
            
            <div class="footer">
                <p>This is an automated response to your feedback. If you have any questions, please don't hesitate to contact us directly.</p>
            </div>
        </body>
        </html>
        """
    
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
