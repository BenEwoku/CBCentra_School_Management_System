# services/email_service.py
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from datetime import datetime
import logging
from PySide6.QtWidgets import QMessageBox, QProgressDialog
from PySide6.QtCore import Qt

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self, db_connection=None):
        self.db_connection = db_connection
        self.smtp_config = {
            'gmail': {'server': 'smtp.gmail.com', 'port': 587},
            'outlook': {'server': 'smtp.office365.com', 'port': 587},
            'yahoo': {'server': 'smtp.mail.yahoo.com', 'port': 587}
        }
    
    def get_email_config(self):
        """Get email configuration from database"""
        try:
            cursor = self.db_connection.cursor(dictionary=True)  # Ensure dictionary format
            cursor.execute("""
                SELECT email_provider, email_address, email_password, 
                       default_sender_name, smtp_server, smtp_port
                FROM email_config 
                WHERE is_active = TRUE 
                ORDER BY created_at DESC 
                LIMIT 1
            """)
            
            config = cursor.fetchone()
            cursor.close()
            
            if config:
                # Convert to dictionary if it's a tuple (fallback)
                if isinstance(config, tuple):
                    # Map tuple positions to keys
                    config_dict = {
                        'email_provider': config[0],
                        'email_address': config[1],
                        'email_password': config[2],
                        'default_sender_name': config[3],
                        'smtp_server': config[4],
                        'smtp_port': config[5]
                    }
                    return config_dict
                return config
            
            return None
            
        except Exception as e:
            print(f"Error getting email config: {e}")
            return None
    
    # services/email_service.py - Updated send_email method
    def send_email(self, to_emails, subject, body, attachment_paths=None, is_html=True, reply_to=None, in_reply_to=None):
        """
        Send email to multiple recipients
        
        Parameters:
        - to_emails: List of email addresses or single email
        - subject: Email subject
        - body: Email content
        - attachment_paths: List of file paths to attach
        - is_html: Whether body is HTML format
        - reply_to: Reply-to email address
        - in_reply_to: Message-ID this is replying to
        """
        try:
            config = self.get_email_config()
            if not config or not config['email_address'] or not config['email_password']:
                return False, "Email configuration not set up"
            
            # Convert single email to list
            if isinstance(to_emails, str):
                to_emails = [to_emails]
            
            # Determine SMTP server
            if config['smtp_server']:
                smtp_server = config['smtp_server']
                smtp_port = config['smtp_port']
            else:
                provider = config['email_provider'].lower()
                smtp_config = self.smtp_config.get(provider, self.smtp_config['gmail'])
                smtp_server = smtp_config['server']
                smtp_port = smtp_config['port']
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = f"{config['default_sender_name']} <{config['email_address']}>"
            msg['To'] = ", ".join(to_emails)
            msg['Subject'] = subject
            msg['Date'] = datetime.now().strftime('%a, %d %b %Y %H:%M:%S %z')
            
            # Add Reply-To header if specified
            if reply_to:
                msg['Reply-To'] = reply_to
            
            # Add In-Reply-To header for threading
            if in_reply_to:
                msg['In-Reply-To'] = in_reply_to
                msg['References'] = in_reply_to
            
            # Add body
            if is_html:
                msg.attach(MIMEText(body, 'html'))
            else:
                msg.attach(MIMEText(body, 'plain'))
            
            # Add attachments
            if attachment_paths:
                for attachment_path in attachment_paths:
                    if os.path.exists(attachment_path):
                        with open(attachment_path, "rb") as f:
                            part = MIMEApplication(f.read(), Name=os.path.basename(attachment_path))
                        part['Content-Disposition'] = f'attachment; filename="{os.path.basename(attachment_path)}"'
                        msg.attach(part)
            
            # Send email
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(config['email_address'], config['email_password'])
                server.sendmail(config['email_address'], to_emails, msg.as_string())
            
            logger.info(f"Email sent successfully to {len(to_emails)} recipients")
            return True, "Email sent successfully"
            
        except Exception as e:
            error_msg = f"Failed to send email: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def get_recipient_emails(self, recipient_type, recipient_ids):
        """
        Get email addresses for students, teachers, or parents
        
        Parameters:
        - recipient_type: 'student', 'teacher', or 'parent'
        - recipient_ids: List of IDs or single ID
        """
        try:
            if not self.db_connection:
                return []
            
            # Convert single ID to list
            if isinstance(recipient_ids, (int, str)):
                recipient_ids = [recipient_ids]
            
            cursor = self.db_connection.cursor()
            
            if recipient_type == 'student':
                cursor.execute("""
                    SELECT id, full_name, email, parent_email 
                    FROM students 
                    WHERE id IN (%s) AND is_active = TRUE
                """ % ','.join(['%s'] * len(recipient_ids)), recipient_ids)
                
            elif recipient_type == 'teacher':
                cursor.execute("""
                    SELECT id, first_name, surname, email 
                    FROM teachers 
                    WHERE id IN (%s) AND is_active = TRUE
                """ % ','.join(['%s'] * len(recipient_ids)), recipient_ids)
                
            elif recipient_type == 'parent':
                cursor.execute("""
                    SELECT p.id, p.full_name, p.email, p.phone,
                           s.full_name as student_name, s.email as student_email
                    FROM parents p
                    JOIN students s ON p.student_id = s.id
                    WHERE p.id IN (%s) AND p.is_active = TRUE
                """ % ','.join(['%s'] * len(recipient_ids)), recipient_ids)
            
            results = cursor.fetchall()
            emails = []
            
            for result in results:
                if recipient_type == 'student':
                    # Student email and parent email
                    if result[2]:  # student email
                        emails.append(result[2])
                    if result[3]:  # parent email
                        emails.append(result[3])
                        
                elif recipient_type == 'teacher':
                    if result[3]:  # teacher email
                        emails.append(result[3])
                        
                elif recipient_type == 'parent':
                    if result[2]:  # parent email
                        emails.append(result[2])
            
            # Remove duplicates and empty emails
            emails = list(set(filter(None, emails)))
            return emails
            
        except Exception as e:
            logger.error(f"Error getting recipient emails: {e}")
            return []
    
    def send_bulk_email(self, parent_widget, recipient_type, recipient_ids, subject, body, 
                       attachment_paths=None, is_html=True):
        """
        Send bulk email with progress dialog
        """
        # Get emails
        emails = self.get_recipient_emails(recipient_type, recipient_ids)
        
        if not emails:
            QMessageBox.warning(parent_widget, "No Emails", "No email addresses found for selected recipients.")
            return False, "No email addresses found"
        
        # Show progress dialog
        progress = QProgressDialog(f"Sending email to {len(emails)} recipients...", 
                                 "Cancel", 0, len(emails), parent_widget)
        progress.setWindowModality(Qt.WindowModal)
        progress.setWindowTitle("Sending Emails")
        progress.show()
        
        try:
            # Send email
            success, message = self.send_email(emails, subject, body, attachment_paths, is_html)
            
            progress.close()
            
            if success:
                QMessageBox.information(parent_widget, "Success", 
                                      f"Email sent successfully to {len(emails)} recipients!")
            else:
                QMessageBox.warning(parent_widget, "Failed", message)
            
            return success, message
            
        except Exception as e:
            progress.close()
            error_msg = f"Failed to send bulk email: {str(e)}"
            QMessageBox.critical(parent_widget, "Error", error_msg)
            return False, error_msg

# Email templates
class EmailTemplates:
    @staticmethod
    def assignment_notification(student_name, assignment_details):
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                          color: white; padding: 20px; text-align: center; border-radius: 10px 10px 0 0;">
                    <h1 style="margin: 0;">📚 Class Assignment</h1>
                </div>
                
                <div style="background: #f8f9fa; padding: 20px; border-radius: 0 0 10px 10px;">
                    <p>Dear {student_name},</p>
                    
                    <p>You have been assigned to the following class:</p>
                    
                    <div style="background: white; padding: 15px; border-radius: 5px; margin: 15px 0; border-left: 4px solid #667eea;">
                        <h3 style="color: #667eea; margin-top: 0;">Assignment Details</h3>
                        <table style="width: 100%;">
                            <tr><td style="padding: 5px; font-weight: bold;">Class:</td><td style="padding: 5px;">{assignment_details.get('class_name', 'N/A')}</td></tr>
                            <tr><td style="padding: 5px; font-weight: bold;">Stream:</td><td style="padding: 5px;">{assignment_details.get('stream', 'N/A')}</td></tr>
                            <tr><td style="padding: 5px; font-weight: bold;">Level:</td><td style="padding: 5px;">{assignment_details.get('level', 'N/A')}</td></tr>
                            <tr><td style="padding: 5px; font-weight: bold;">Term:</td><td style="padding: 5px;">{assignment_details.get('term', 'N/A')}</td></tr>
                            <tr><td style="padding: 5px; font-weight: bold;">Academic Year:</td><td style="padding: 5px;">{assignment_details.get('year', 'N/A')}</td></tr>
                            <tr><td style="padding: 5px; font-weight: bold;">Status:</td><td style="padding: 5px;">{assignment_details.get('status', 'Active')}</td></tr>
                        </table>
                    </div>
                    
                    <p>If you have any questions, please contact the administration office.</p>
                    
                    <div style="margin-top: 20px; padding-top: 20px; border-top: 1px solid #ddd;">
                        <p style="color: #6c757d; font-size: 12px;">
                            This is an automated message from School Management System.<br>
                            Please do not reply to this email.
                        </p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
    
    @staticmethod
    def borrowing_notification(recipient_name, book_details):
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2>📖 Book Borrowing Notification</h2>
            <p>Dear {recipient_name},</p>
            <p>You have borrowed the following book:</p>
            <div style="background: #f0f8ff; padding: 15px; border-radius: 5px;">
                <strong>{book_details.get('title', 'N/A')}</strong><br>
                Author: {book_details.get('author', 'N/A')}<br>
                Due Date: {book_details.get('due_date', 'N/A')}
            </div>
        </body>
        </html>
        """
    
    @staticmethod
    def simple_notification(recipient_name, title, message):
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2>{title}</h2>
            <p>Dear {recipient_name},</p>
            <p>{message}</p>
        </body>
        </html>
        """