# ui/notification_center.py
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                              QPushButton, QListWidget, QListWidgetItem,
                              QTextEdit, QSplitter, QFrame, QSizePolicy, QApplication, QWidget, QProgressBar)
from PySide6.QtCore import Qt, Signal, QTimer, QSize
from PySide6.QtGui import QFont, QColor, QTextOption, QIcon
import json
import os

class NotificationCenter(QDialog):
    reply_requested = Signal(int, str, str)  # conversation_id, recipient, subject
    
    def __init__(self, parent=None, db_connection=None, email_service=None):
        super().__init__(parent)
        self.db_connection = db_connection
        self.email_service = email_service
        self.current_conversation = None
        self.is_loading = False
        
        # Set dialog properties
        self.setWindowTitle("Email Notifications")
        self.setMinimumSize(1200, 750)  # Increased height
        
        # Apply base background color consistent with AuditBaseForm
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f5f5; /* Matches AuditBaseForm QWidget background */
            }
        """)
        
        self.setup_ui()
        self.load_notifications()
    
    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)
        
        # Header with improved styling
        header_layout = QHBoxLayout()
        title_label = QLabel("Email Notifications")
        title_label.setFont(QFont("Arial", 18, QFont.Bold))
        title_label.setStyleSheet("color: #2c3e50;")
        
        # Refresh Button
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setProperty("class", "secondary")  # Use AuditBaseForm 'secondary' style
        self.refresh_btn.setIcon(QIcon(os.path.join("static", "icons", "refresh.png")))
        self.refresh_btn.setIconSize(QSize(14, 14))
        self.refresh_btn.setToolTip("Reload notifications")
        self.refresh_btn.clicked.connect(self.load_notifications)
        
        # Mark All Read Button
        self.mark_all_read_btn = QPushButton("Mark All Read")
        self.mark_all_read_btn.setProperty("class", "secondary")
        self.mark_all_read_btn.setIcon(QIcon(os.path.join("static", "icons", "read.png")))
        self.mark_all_read_btn.setIconSize(QSize(14, 14))
        self.mark_all_read_btn.setToolTip("Mark all messages as read")
        self.mark_all_read_btn.clicked.connect(self.mark_all_read)
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.refresh_btn)
        header_layout.addWidget(self.mark_all_read_btn)
        main_layout.addLayout(header_layout)
        
        # Loading indicator (initially hidden)
        self.loading_indicator = QProgressBar()
        self.loading_indicator.setRange(0, 0)  # Indeterminate progress
        self.loading_indicator.setVisible(False)
        self.loading_indicator.setFixedHeight(4)
        main_layout.addWidget(self.loading_indicator)
        
        # Status label for feedback
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #6c757d; font-size: 12px; padding: 5px;")
        self.status_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.status_label)
        
        # Splitter for conversations list and message view
        splitter = QSplitter(Qt.Horizontal)
        
        # Conversations list (increased height, improved padding)
        conversations_frame = QFrame()
        conversations_layout = QVBoxLayout(conversations_frame)
        conversations_label = QLabel("Conversations")
        conversations_label.setFont(QFont("Arial", 12, QFont.Bold))
        conversations_label.setStyleSheet("padding: 5px; color: #495057;")
        conversations_layout.addWidget(conversations_label)
        
        self.conversations_list = QListWidget()
        self.conversations_list.setMinimumWidth(385)  # Wider for better visibility
        # Increased padding and height, forced text color dark to override white from base styles
        self.conversations_list.setStyleSheet("""
            QListWidget {
                background-color: white;
                border: 2px solid #dee2e6; /* Slightly thicker border */
                border-radius: 12px; 
                padding: 5px;
                color: #2c3e50; /* Force dark text */
                font-family: Arial, sans-serif;
                font-size: 14px;
            }
            QListWidget::item {
                padding: 18px 12px; /* Increased top/bottom padding for item height */
                border-bottom: 1px solid #e9ecef;
                color: #2c3e50 !important; /* Force dark text on items */
            }
            QListWidget::item:selected {
                background-color: #e3f2fd;
                border-left: 4px solid #2196f3;
                color: #2c3e50 !important;
            }
        """)
        self.conversations_list.currentRowChanged.connect(self.show_conversation)
        conversations_layout.addWidget(self.conversations_list)
        splitter.addWidget(conversations_frame)
        
        # Message view area
        message_frame = QFrame()
        message_layout = QVBoxLayout(message_frame)
        
        # Message header
        self.message_header = QLabel("Select a conversation to view messages")
        self.message_header.setWordWrap(True)
        self.message_header.setStyleSheet("""
            padding: 16px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 8px;
            font-weight: 500;
        """)
        message_layout.addWidget(self.message_header)
        
        # Messages area
        self.messages_area = QTextEdit()
        self.messages_area.setReadOnly(True)
        self.messages_area.setWordWrapMode(QTextOption.WordWrap)
        self.messages_area.setStyleSheet("""
            QTextEdit {
                background-color: white;
                border: 2px solid #dee2e6; 
                border-radius: 12px;
                padding: 15px;
                font-family: Arial;
                font-size: 13px;
                color: #2c3e50; /* Force dark text */
            }
        """)
        self.messages_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        message_layout.addWidget(self.messages_area, 1)
        
        # Reply area
        reply_frame = QFrame()
        reply_frame.setFrameStyle(QFrame.StyledPanel)
        reply_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: 2px solid #dee2e6; 
                border-radius: 12px;
                padding: 15px;
            }
        """)
        reply_layout = QVBoxLayout(reply_frame)
        reply_header = QLabel("Quick Reply:")
        reply_header.setStyleSheet("font-weight: bold; color: #495057;")
        reply_layout.addWidget(reply_header)
        
        self.reply_text = QTextEdit()
        self.reply_text.setPlaceholderText("Type your reply here...")
        self.reply_text.setMaximumHeight(120)
        self.reply_text.setStyleSheet("""
            QTextEdit {
                background-color: white;
                border: 2px solid #ced4da; 
                border-radius: 8px; 
                padding: 10px;
                font-family: Arial;
                font-size: 13px;
                color: #2c3e50; /* Dark text */
            }
        """)
        reply_layout.addWidget(self.reply_text)
        
        reply_btn_layout = QHBoxLayout()
        self.send_btn = QPushButton("Send Reply")
        self.send_btn.setProperty("class", "primary")
        self.send_btn.setIcon(QIcon(os.path.join("static", "icons", "reply.png")))
        self.send_btn.setIconSize(QSize(14, 14))
        self.send_btn.clicked.connect(self.send_reply)
        
        clear_btn = QPushButton("Clear")
        clear_btn.setProperty("class", "secondary")
        clear_btn.setIcon(QIcon(os.path.join("static", "icons", "clear.png")))
        clear_btn.setIconSize(QSize(14, 14))
        clear_btn.clicked.connect(self.clear_reply)
        
        reply_btn_layout.addWidget(self.send_btn)
        reply_btn_layout.addWidget(clear_btn)
        reply_btn_layout.addStretch()
        
        self.reply_status_label = QLabel("")
        self.reply_status_label.setStyleSheet("font-size: 11px; color: #6c757d;")
        reply_btn_layout.addWidget(self.reply_status_label)
        
        reply_layout.addLayout(reply_btn_layout)
        message_layout.addWidget(reply_frame)
        
        splitter.addWidget(message_frame)
        splitter.setSizes([400, 600])
        main_layout.addWidget(splitter)
    
    def show_loading(self, message="Loading..."):
        self.is_loading = True
        self.loading_indicator.setVisible(True)
        self.status_label.setText(message)
        self.refresh_btn.setEnabled(False)
        self.mark_all_read_btn.setEnabled(False)
        self.send_btn.setEnabled(False)
        QApplication.processEvents()
    
    def hide_loading(self, message="Ready"):
        self.is_loading = False
        self.loading_indicator.setVisible(False)
        self.status_label.setText(message)
        self.refresh_btn.setEnabled(True)
        self.mark_all_read_btn.setEnabled(True)
        self.send_btn.setEnabled(True)
    
    def show_temp_message(self, message, duration=3000, color="#28a745"):
        self.status_label.setText(message)
        self.status_label.setStyleSheet(f"color: {color}; font-size: 12px; padding: 5px;")
        QTimer.singleShot(duration, lambda: self.status_label.setText("Ready") or self.status_label.setStyleSheet("color: #6c757d; font-size: 12px; padding: 5px;"))
    
    def load_notifications(self):
        if self.is_loading:
            return
        self.show_loading("Loading conversations...")
        try:
            self.conversations_list.clear()
            cursor = self.db_connection.cursor(dictionary=True)
            cursor.execute("""
                SELECT c.*, 
                       COUNT(m.id) as message_count,
                       SUM(CASE WHEN m.is_read = FALSE THEN 1 ELSE 0 END) as unread_count,
                       (
                           SELECT body 
                           FROM email_messages 
                           WHERE conversation_id = c.id 
                           ORDER BY sent_date DESC 
                           LIMIT 1
                       ) as last_message_preview
                FROM email_conversations c
                LEFT JOIN email_messages m ON c.id = m.conversation_id
                GROUP BY c.id
                ORDER BY c.last_message_date DESC
            """)
            conversations = cursor.fetchall()
    
            if not conversations:
                self.hide_loading("No conversations found")
                item = QListWidgetItem("No email conversations yet")
                item.setTextAlignment(Qt.AlignCenter)
                item.setForeground(QColor("#2c3e50"))
                self.conversations_list.addItem(item)
                return
    
            for conv in conversations:
                item = QListWidgetItem()
                widget = self.create_conversation_item(conv)  # conv now includes last_message_preview
                item.setSizeHint(widget.sizeHint())
                self.conversations_list.addItem(item)
                self.conversations_list.setItemWidget(item, widget)
    
            self.hide_loading(f"Loaded {len(conversations)} conversations")
            self.show_temp_message(f"✓ Loaded {len(conversations)} conversations", 2000)
    
        except Exception as e:
            self.hide_loading("Error loading conversations")
            self.show_temp_message(f"❌ Error: {str(e)}", 5000, "#dc3545")
            print(f"Error loading notifications: {e}")

    
    def create_conversation_item(self, conversation):
        widget = QWidget()
        widget.setObjectName("conversationItem")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 14, 16, 14)  # padding inside card
        layout.setSpacing(4)
    
        # First row: Subject + unread badge + time
        top_layout = QHBoxLayout()
        top_layout.setSpacing(10)
    
        # Unread badge
        if conversation['unread_count'] > 0:
            badge = QLabel(str(conversation['unread_count']))
            badge.setObjectName("unreadBadge")
            top_layout.addWidget(badge)
    
        # Subject
        subject_label = QLabel(conversation['subject'])
        subject_label.setWordWrap(True)
        subject_label.setObjectName("subjectLabel")
        top_layout.addWidget(subject_label, 1)
    
        # Date
        date_label = QLabel(conversation['last_message_date'].strftime('%b %d, %H:%M'))
        date_label.setObjectName("dateLabel")
        top_layout.addWidget(date_label)
    
        layout.addLayout(top_layout)
    
        # Second row: Message preview (shortened last message body if available)
        preview_text = conversation.get("last_message_preview", "")
        if preview_text:
            preview_label = QLabel(preview_text[:80] + ("..." if len(preview_text) > 80 else ""))
            preview_label.setObjectName("previewLabel")
            preview_label.setWordWrap(True)
            layout.addWidget(preview_label)
    
        # Minimum height
        widget.setMinimumHeight(80)
    
        # Styles
        widget.setStyleSheet("""
            #conversationItem {
                background-color: white;
                border: 1px solid #dee2e6;
                border-radius: 10px;
            }
            #subjectLabel {
                font-weight: bold;
                color: #2c3e50;
                font-size: 15px;
            }
            #dateLabel {
                color: #6c757d;
                font-size: 12px;
            }
            #previewLabel {
                color: #495057;
                font-size: 13px;
            }
            #unreadBadge {
                background-color: #e74c3c;
                color: white;
                font-weight: bold;
                font-size: 12px;
                padding: 4px 8px;
                border-radius: 10px;
                min-width: 22px;
                max-height: 20px;
                qproperty-alignment: 'AlignCenter';
            }
        """)
    
        widget.conversation_id = conversation['id']
        return widget



    
    def show_conversation(self, row):
        if row < 0 or self.is_loading:
            return
        try:
            item = self.conversations_list.item(row)
            widget = self.conversations_list.itemWidget(item)
            conversation_id = getattr(widget, 'conversation_id', None)
            if not conversation_id:
                return
            self.current_conversation = conversation_id
            cursor = self.db_connection.cursor(dictionary=True)
            cursor.execute("""
                SELECT * FROM email_messages
                WHERE conversation_id = %s
                ORDER BY sent_date ASC
            """, (conversation_id,))
            messages = cursor.fetchall()
            html = """
            <div style='
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                line-height: 1.6;
                color: #2c3e50;
            '>
            """
            for msg in messages:
                timestamp = msg['sent_date'].strftime('%Y-%m-%d %H:%M')
                message_body_style = "margin-top: 8px; font-size: 14px; word-break: break-word;"
                if msg['is_outgoing']:
                    html += f"""
                    <div style='margin: 20px 0; text-align: right;'>
                        <div style='
                            background: linear-gradient(135deg, #007bff, #0056b3);
                            color: white;
                            padding: 15px;
                            border-radius: 18px 18px 4px 18px;
                            display: inline-block;
                            max-width: 75%;
                            box-shadow: 0 2px 8px rgba(0,123,255,0.3);
                        '>
                            <strong>You</strong>
                            <div style='{message_body_style}'>{msg['body']}</div>
                            <div style='font-size: 11px; margin-top: 8px; opacity: 0.8;'>
                                {timestamp}
                            </div>
                        </div>
                    </div>
                    """
                else:
                    html += f"""
                    <div style='margin: 20px 0; text-align: left;'>
                        <div style='
                            background: #f1f3f4;
                            color: #202124;
                            padding: 15px;
                            border-radius: 18px 18px 18px 4px;
                            display: inline-block;
                            max-width: 75%;
                            box-shadow: 0 1px 4px rgba(0,0,0,0.1);
                        '>
                            <strong>{msg['from_name'] or msg['from_email']}</strong>
                            <div style='{message_body_style}'>{msg['body']}</div>
                            <div style='font-size: 11px; margin-top: 8px; opacity: 0.6;'>
                                {timestamp}
                            </div>
                        </div>
                    </div>
                    """
            html += "</div>"
            self.messages_area.setHtml(html)
            
            cursor.execute("SELECT * FROM email_conversations WHERE id = %s", (conversation_id,))
            conv = cursor.fetchone()
            participants = json.loads(conv['participants'])
            self.message_header.setText(
                f"💬 Conversation with: {', '.join(participants)}<br>"
                f"📧 Subject: {conv['subject']}<br>"
                f"📅 Last message: {conv['last_message_date'].strftime('%Y-%m-%d %H:%M')}"
            )
            self.mark_conversation_read(conversation_id)
        except Exception as e:
            self.show_temp_message(f"❌ Error loading conversation: {str(e)}", 5000, "#dc3545")
            print(f"Error showing conversation: {e}")
    
    def mark_conversation_read(self, conversation_id):
        try:
            cursor = self.db_connection.cursor()
            cursor.execute("""
                UPDATE email_messages SET is_read = TRUE WHERE conversation_id = %s
            """, (conversation_id,))
            cursor.execute("""
                UPDATE email_conversations SET unread_count = 0 WHERE id = %s
            """, (conversation_id,))
            self.db_connection.commit()
            self.show_temp_message("✓ Conversation marked as read", 2000)
        except Exception as e:
            self.show_temp_message(f"❌ Error marking as read: {str(e)}", 5000, "#dc3545")
            print(f"Error marking as read: {e}")
    
    def mark_all_read(self):
        if self.is_loading:
            return
        self.show_loading("Marking all as read...")
        try:
            cursor = self.db_connection.cursor()
            cursor.execute("UPDATE email_messages SET is_read = TRUE")
            cursor.execute("UPDATE email_conversations SET unread_count = 0")
            self.db_connection.commit()
            self.load_notifications()
            self.show_temp_message("✓ All messages marked as read", 3000)
        except Exception as e:
            self.hide_loading("Error marking as read")
            self.show_temp_message(f"❌ Error: {str(e)}", 5000, "#dc3545")
            print(f"Error marking all as read: {e}")
    
    def send_reply(self):
        if not self.current_conversation:
            self.show_temp_message("❌ Please select a conversation first", 3000, "#dc3545")
            return
        if not self.reply_text.toPlainText().strip():
            self.show_temp_message("❌ Please enter a message to send", 3000, "#dc3545")
            return
        
        message = self.reply_text.toPlainText().strip()
        self.show_loading("Sending reply...")
        self.reply_status_label.setText("Sending...")
        
        if self.email_service and hasattr(self.email_service, 'send_reply'):
            success = self.email_service.send_reply(self.current_conversation, message)
            if success:
                self.reply_text.clear()
                self.reply_status_label.setText("✓ Reply sent successfully")
                self.hide_loading("Reply sent successfully")
                self.show_temp_message("✓ Reply sent successfully", 3000)
                QTimer.singleShot(1000, lambda: self.show_conversation(self.conversations_list.currentRow()))
            else:
                self.hide_loading("Failed to send reply")
                self.reply_status_label.setText("❌ Failed to send reply")
                self.show_temp_message("❌ Failed to send reply", 5000, "#dc3545")
        else:
            self.hide_loading("Email service not available")
            self.show_temp_message("❌ Email service not configured", 5000, "#dc3545")
    
    def clear_reply(self):
        self.reply_text.clear()
        self.reply_status_label.setText("")
        self.show_temp_message("Reply cleared", 2000, "#6c757d")
    
    def add_new_notification(self, notification_data):
        self.load_notifications()
        self.show_temp_message(f"📧 New message from {notification_data['from']}", 5000, "#28a745")
        QTimer.singleShot(1000, self.select_latest_conversation)
    
    def select_latest_conversation(self):
        if self.conversations_list.count() > 0:
            self.conversations_list.setCurrentRow(0)
