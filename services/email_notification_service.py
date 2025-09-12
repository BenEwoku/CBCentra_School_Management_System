# services/email_notification_service.py
import imaplib
import email
import time
import re
import json
import base64
import os
from threading import Thread
from datetime import datetime, timedelta
from email.header import decode_header
import quopri
from PySide6.QtCore import QObject, Signal, QTimer
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmailNotificationService(QObject):
    # Signals for UI updates
    new_notification = Signal(dict)
    notification_count_changed = Signal(int)
    new_conversation = Signal(dict)
    
    def __init__(self, db_connection, email_service):
        super().__init__()
        self.db_connection = db_connection
        self.email_service = email_service
        self.running = False
        self.thread = None
        self.check_interval = 60  # 1 minute
        
    def start(self):
        """Start the email monitoring service"""
        if self.running:
            return
            
        # Check if email is configured first
        config = self.email_service.get_email_config()
        if not config or not config.get('email_address') or not config.get('email_password'):
            print("Email not configured - monitoring service not started")
            return
            
        self.running = True
        self.thread = Thread(target=self._monitor_emails, daemon=True)
        self.thread.start()
        print("✅ Email notification service started")
        
    def stop(self):
        """Stop the email monitoring service gracefully"""
        if not self.running:
            return
            
        self.running = False
        print("Stopping email notification service...")
        
        if self.thread and self.thread.is_alive():
            # Wait for the thread to finish with timeout
            self.thread.join(timeout=5.0)  # 5 second timeout
            
            if self.thread.is_alive():
                print("Email thread did not stop gracefully - forcing termination")
            else:
                print("✅ Email notification service stopped gracefully")
            
    def _monitor_emails(self):
        """Main monitoring loop"""
        while self.running:
            try:
                self._check_incoming_emails()
                time.sleep(self.check_interval)
            except Exception as e:
                print(f"Email monitoring error: {e}")
                time.sleep(60)
                
    def _check_incoming_emails(self):
        """Check for new incoming emails with Gmail-specific handling"""
        try:
            config = self.email_service.get_email_config()
            
            # Extract credentials
            if isinstance(config, tuple):
                email_address = config[1] if len(config) > 1 else None
                email_password = config[2] if len(config) > 2 else None
            elif isinstance(config, dict):
                email_address = config.get('email_address')
                email_password = config.get('email_password')
            else:
                print("Email not configured")
                return
                
            if not email_address or not email_password:
                print("Email not configured - skipping email check")
                return
                
            print(f"🔗 Connecting to imap.gmail.com...")
            
            # Connect to Gmail IMAP
            mail = imaplib.IMAP4_SSL('imap.gmail.com', 993)
            mail.login(email_address, email_password)
            mail.select('inbox')
            
            # Search for UNSEEN emails (not UNREAD)
            # Gmail uses \Unseen flag instead of \Seen
            since_date = (datetime.now() - timedelta(hours=24)).strftime('%d-%b-%Y')
            status, messages = mail.search(None, f'(UNSEEN SINCE {since_date})')
            
            if status == 'OK' and messages[0]:
                email_ids = messages[0].split()
                print(f"📧 Found {len(email_ids)} new emails")
                
                for email_id in email_ids:
                    try:
                        # Fetch the email
                        status, msg_data = mail.fetch(email_id, '(RFC822)')
                        if status != 'OK':
                            continue
                            
                        raw_email = msg_data[0][1]
                        msg = email.message_from_bytes(raw_email)
                        
                        # Extract email details
                        email_data = self._extract_email_details(msg)
                        
                        # Check if this is a reply to our system
                        if self._is_system_related_email(email_data):
                            # Process the email
                            self._process_incoming_email(mail, email_id, email_data, {
                                'email_address': email_address,
                                'email_password': email_password
                            })
                            
                    except Exception as e:
                        print(f"❌ Error processing email {email_id}: {e}")
                        continue
                        
            mail.logout()
            print("✅ Email check completed successfully")
            
        except imaplib.IMAP4.error as e:
            print(f"IMAP authentication error: {e}")
            print("Please verify your App Password is correct")
        except Exception as e:
            print(f"IMAP error: {e}")
            
    def _process_incoming_email(self, mail, email_id, email_data, config):
        """Process an incoming email with Gmail-specific handling"""
        try:
            # Mark as read in Gmail (using \Seen flag)
            # With "Auto-Expunge off", this won't immediately delete the email
            mail.store(email_id, '+FLAGS', '\\Seen')
            
            # Save to database and notify UI
            self._save_incoming_email(email_data, config)
            
            print(f"✅ Processed email: {email_data['subject']}")
            
        except Exception as e:
            print(f"Error processing email: {e}")
            
    def _extract_email_details(self, msg):
        """Extract details from email message including attachments"""
        # Decode subject
        subject, encoding = decode_header(msg.get('Subject', ''))[0]
        if isinstance(subject, bytes):
            subject = subject.decode(encoding or 'utf-8')
            
        # Decode from address
        from_header = msg.get('From', '')
        from_name, from_email = self._parse_email_address(from_header)
        
        # Extract body
        body = self._extract_email_body(msg)
        
        # Extract message ID and references
        message_id = msg.get('Message-ID', '')
        references = msg.get('References', '')
        in_reply_to = msg.get('In-Reply-To', '')
        
        # Extract attachments
        attachments = self._extract_attachments(msg)
        
        return {
            'subject': subject,
            'from_name': from_name,
            'from_email': from_email,
            'body': body,
            'message_id': message_id,
            'references': references,
            'in_reply_to': in_reply_to,
            'date': msg.get('Date', ''),
            'raw_headers': dict(msg.items()),
            'attachments': attachments
        }
        
    def _parse_email_address(self, address_header):
        """Parse email address from header"""
        try:
            # Try to decode the header
            decoded, encoding = decode_header(address_header)[0]
            if isinstance(decoded, bytes):
                decoded = decoded.decode(encoding or 'utf-8')
            
            # Extract name and email
            match = re.search(r'(?:"?([^"]*)"?\s)?<?([^<>]+@[^<>]+)>?', decoded)
            if match:
                name = match.group(1) or ''
                email = match.group(2) or ''
                return name.strip(), email.strip()
            return '', decoded
        except:
            return '', address_header
            
    def _extract_email_body(self, msg):
        """Extract email body text"""
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))
                
                if content_type == "text/plain" and "attachment" not in content_disposition:
                    try:
                        payload = part.get_payload(decode=True)
                        charset = part.get_content_charset() or 'utf-8'
                        body = payload.decode(charset, errors='replace')
                        break
                    except:
                        continue
        else:
            try:
                payload = msg.get_payload(decode=True)
                charset = msg.get_content_charset() or 'utf-8'
                body = payload.decode(charset, errors='replace')
            except:
                body = msg.get_payload()
                
        return body
    
    def _extract_attachments(self, msg):
        """Extract attachments from email message"""
        attachments = []
        
        if msg.is_multipart():
            for part in msg.walk():
                content_disposition = str(part.get("Content-Disposition", ""))
                
                # Skip if not an attachment
                if "attachment" not in content_disposition and "filename" not in content_disposition:
                    continue
                    
                filename = part.get_filename()
                if filename:
                    # Decode filename if needed
                    if isinstance(filename, bytes):
                        filename = filename.decode()
                    
                    # Handle encoded filenames (e.g., =?utf-8?B?...?=)
                    decoded_filename = self._decode_header(filename)
                    
                    # Get content type and size
                    content_type = part.get_content_type()
                    payload = part.get_payload(decode=True)
                    file_size = len(payload) if payload else 0
                    
                    # Store attachment data
                    attachments.append({
                        'filename': decoded_filename,
                        'content_type': content_type,
                        'size': file_size,
                        'file_data': payload,  # Store binary data
                        'content_id': part.get('Content-ID', '').strip('<>')
                    })
        
        return attachments
    
    def _decode_header(self, header):
        """Decode email header with encoded words"""
        try:
            decoded_parts = decode_header(header)
            result = []
            for part, encoding in decoded_parts:
                if isinstance(part, bytes):
                    result.append(part.decode(encoding or 'utf-8'))
                else:
                    result.append(str(part))
            return ''.join(result)
        except:
            return header
    
    def _save_attachment_to_db(self, message_id, attachment_data):
        """Save attachment to database"""
        try:
            cursor = self.db_connection.cursor()
            
            cursor.execute("""
                INSERT INTO email_attachments 
                (message_id, content_id, filename, file_data, file_size, content_type)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                message_id,
                attachment_data.get('content_id'),
                attachment_data['filename'],
                attachment_data['file_data'],  # Store binary data
                attachment_data['size'],
                attachment_data['content_type']
            ))
            
            self.db_connection.commit()
            return cursor.lastrowid
            
        except Exception as e:
            print(f"Error saving attachment to database: {e}")
            self.db_connection.rollback()
            return None
    
    def _is_system_related_email(self, email_data):
        """Check if email is related to our system"""
        # Check if it's a reply to our emails
        if email_data['in_reply_to']:
            return True
            
        # Check for system keywords in subject
        system_keywords = [
            'school', 'assignment', 'student', 'teacher', 'parent',
            'class', 'grade', 'attendance', 'fee', 'payment'
        ]
        
        subject_lower = email_data['subject'].lower()
        return any(keyword in subject_lower for keyword in system_keywords)
    
    def _save_incoming_email(self, email_data, config):
        """Save incoming email to database with attachments"""
        try:
            cursor = self.db_connection.cursor(dictionary=True)
            
            # Check if this is part of an existing conversation
            conversation_id = self._find_existing_conversation(email_data)
            
            if not conversation_id:
                # Create new conversation
                cursor.execute("""
                    INSERT INTO email_conversations 
                    (thread_id, subject, participants, last_message_date, unread_count)
                    VALUES (%s, %s, %s, %s, %s)
                """, (
                    email_data['message_id'],
                    email_data['subject'],
                    json.dumps([email_data['from_email']]),
                    datetime.now(),
                    1
                ))
                conversation_id = cursor.lastrowid
            else:
                # Update existing conversation
                cursor.execute("""
                    UPDATE email_conversations 
                    SET unread_count = unread_count + 1, last_message_date = %s
                    WHERE id = %s
                """, (datetime.now(), conversation_id))
            
            # Save the message
            cursor.execute("""
                INSERT INTO email_messages 
                (conversation_id, message_id, from_email, from_name, to_email, 
                 subject, body, sent_date, is_outgoing, is_read)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                conversation_id,
                email_data['message_id'],
                email_data['from_email'],
                email_data['from_name'],
                config['email_address'],
                email_data['subject'],
                email_data['body'],
                datetime.now(),
                False,
                False
            ))
            
            message_id = cursor.lastrowid
            
            # Save attachments to database
            if email_data['attachments']:
                for attachment in email_data['attachments']:
                    self._save_attachment_to_db(message_id, attachment)
            
            self.db_connection.commit()
            
            # Emit signals for UI update
            notification_data = {
                'id': message_id,
                'from': email_data['from_name'] or email_data['from_email'],
                'subject': email_data['subject'],
                'preview': email_data['body'][:100] + '...' if len(email_data['body']) > 100 else email_data['body'],
                'time': datetime.now().strftime('%H:%M'),
                'conversation_id': conversation_id,
                'has_attachments': len(email_data['attachments']) > 0
            }
            
            self.new_notification.emit(notification_data)
            self._update_notification_count()
            
        except Exception as e:
            print(f"Error saving email: {e}")
            self.db_connection.rollback()
    
    def _find_existing_conversation(self, email_data):
        """Find existing conversation for this email"""
        try:
            cursor = self.db_connection.cursor(dictionary=True)
            
            # Check by message references
            if email_data['in_reply_to']:
                cursor.execute("""
                    SELECT conversation_id FROM email_messages 
                    WHERE message_id = %s
                """, (email_data['in_reply_to'],))
                result = cursor.fetchone()
                if result:
                    return result['conversation_id']
            
            # Check by subject and participant
            cursor.execute("""
                SELECT c.id FROM email_conversations c
                JOIN email_messages m ON c.id = m.conversation_id
                WHERE c.subject = %s AND m.from_email = %s
                ORDER BY c.last_message_date DESC LIMIT 1
            """, (email_data['subject'], email_data['from_email']))
            
            result = cursor.fetchone()
            return result['id'] if result else None
            
        except Exception as e:
            print(f"Error finding conversation: {e}")
            return None
    
    def get_unread_count(self):
        """Get total unread notifications count"""
        try:
            cursor = self.db_connection.cursor()
            cursor.execute("SELECT COUNT(*) FROM email_messages WHERE is_read = FALSE")
            return cursor.fetchone()[0] or 0
        except:
            return 0
            
    def _update_notification_count(self):
        """Update notification count signal"""
        count = self.get_unread_count()
        self.notification_count_changed.emit(count)
    
    def mark_as_read(self, message_id):
        """Mark message as read"""
        try:
            cursor = self.db_connection.cursor()
            cursor.execute("""
                UPDATE email_messages SET is_read = TRUE WHERE id = %s
            """, (message_id,))
            
            cursor.execute("""
                UPDATE email_conversations c
                SET unread_count = (
                    SELECT COUNT(*) FROM email_messages 
                    WHERE conversation_id = c.id AND is_read = FALSE
                )
                WHERE id = (SELECT conversation_id FROM email_messages WHERE id = %s)
            """, (message_id,))
            
            self.db_connection.commit()
            self._update_notification_count()
            
        except Exception as e:
            print(f"Error marking as read: {e}")
    
    def send_reply(self, conversation_id, message, subject=None, attachments=None):
        """Send reply to a conversation with optional attachments"""
        try:
            # Get conversation details
            cursor = self.db_connection.cursor(dictionary=True)
            cursor.execute("""
                SELECT c.participants, m.from_email, m.from_name, c.subject, m.message_id
                FROM email_conversations c
                JOIN email_messages m ON c.id = m.conversation_id
                WHERE c.id = %s
                ORDER BY m.sent_date DESC LIMIT 1
            """, (conversation_id,))
            
            conversation = cursor.fetchone()
            if not conversation:
                return False
                
            participants = json.loads(conversation['participants'])
            to_email = participants[0] if participants else conversation['from_email']
            
            # Send email
            subject = subject or f"Re: {conversation['subject']}"
            success, _ = self.email_service.send_email(
                to_email,
                subject,
                message,
                attachment_paths=attachments or [],
                is_html=True,
                reply_to=self.email_service.get_email_config()['email_address'],
                in_reply_to=conversation['message_id']
            )
            
            if success:
                # Save outgoing message
                cursor.execute("""
                    INSERT INTO email_messages 
                    (conversation_id, message_id, from_email, from_name, to_email, 
                     subject, body, sent_date, is_outgoing, is_read)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    conversation_id,
                    f"<outgoing-{datetime.now().timestamp()}@school-system>",
                    self.email_service.get_email_config()['email_address'],
                    self.email_service.get_email_config()['default_sender_name'],
                    to_email,
                    subject,
                    message,
                    datetime.now(),
                    True,
                    True
                ))
                
                # Update conversation
                cursor.execute("""
                    UPDATE email_conversations 
                    SET last_message_date = %s
                    WHERE id = %s
                """, (datetime.now(), conversation_id))
                
                self.db_connection.commit()
                
            return success
            
        except Exception as e:
            print(f"Error sending reply: {e}")
            return False
    
    def get_attachment(self, attachment_id):
        """Retrieve attachment from database"""
        try:
            cursor = self.db_connection.cursor(dictionary=True)
            cursor.execute("""
                SELECT filename, file_data, content_type 
                FROM email_attachments 
                WHERE id = %s
            """, (attachment_id,))
            
            result = cursor.fetchone()
            if result:
                return {
                    'filename': result['filename'],
                    'file_data': result['file_data'],
                    'content_type': result['content_type']
                }
            return None
            
        except Exception as e:
            print(f"Error retrieving attachment: {e}")
            return None
    
    def get_message_attachments(self, message_id):
        """Get all attachments for a message"""
        try:
            cursor = self.db_connection.cursor(dictionary=True)
            cursor.execute("""
                SELECT id, filename, file_size, content_type, content_id
                FROM email_attachments 
                WHERE message_id = %s
            """, (message_id,))
            
            attachments = []
            for row in cursor.fetchall():
                attachments.append({
                    'id': row['id'],
                    'filename': row['filename'],
                    'size': row['file_size'],
                    'content_type': row['content_type'],
                    'content_id': row['content_id']
                })
            
            return attachments
            
        except Exception as e:
            print(f"Error getting message attachments: {e}")
            return []