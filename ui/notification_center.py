# ui/notification_center.py
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                              QPushButton, QListWidget, QListWidgetItem,
                              QTextEdit, QSplitter, QFrame, QSizePolicy, 
                              QApplication, QWidget, QProgressBar, QMenu,
                              QFileDialog, QMessageBox, QScrollArea, QGridLayout)
from PySide6.QtCore import Qt, Signal, QTimer, QSize, QUrl
from PySide6.QtGui import QFont, QColor, QTextOption, QIcon, QDesktopServices, QPixmap
import json
import os
import shutil
import tempfile
import base64


class AttachmentWidget(QWidget):
    """Professional linear attachment widget with enhanced hover effects"""
    open_attachment_signal = Signal(dict)
    save_attachment_signal = Signal(dict)

    def __init__(self, attachment_data, parent=None):
        super().__init__(parent)
        self.attachment_data = attachment_data
        self.is_hovered = False
        self.setup_ui()

    def setup_ui(self):
        self.setFixedHeight(60)
        self.setCursor(Qt.PointingHandCursor)
        
        # Set initial style without hover (we'll handle hover in events)
        self.setStyleSheet("""
            AttachmentWidget {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 8px;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(12)

        # Make sure to connect the signals to the parent's methods
        if self.parent():
            self.open_attachment_signal.connect(self.parent().open_attachment)
            self.save_attachment_signal.connect(self.parent().save_attachment)

        # === ICON ===
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(32, 32)
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.update_icon_style(False)  # Set initial icon style

        file_ext = self.attachment_data['filename'].split('.')[-1].lower() if '.' in self.attachment_data['filename'] else ''
        icon_path = self.get_icon_path(file_ext)
        if os.path.exists(icon_path):
            pixmap = QPixmap(icon_path).scaled(28, 28, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.icon_label.setPixmap(pixmap)
        else:
            self.icon_label.setText(self.get_text_icon(file_ext))
            self.icon_label.setStyleSheet(self.icon_label.styleSheet() + " font-size: 18px;")

        layout.addWidget(self.icon_label)

        # === FILE NAME ===
        filename = self.attachment_data['filename']
        truncated_name = filename if len(filename) <= 40 else filename[:37] + "..."
        self.name_label = QLabel(truncated_name)
        self.name_label.setToolTip(f"File: {filename}")
        self.name_label.setStyleSheet("font-size: 12px; font-weight: 500; color: #2c3e50;")
        self.name_label.setMinimumWidth(150)
        layout.addWidget(self.name_label, 1)

        # === FILE SIZE ===
        size_str = self.format_file_size(self.attachment_data['size'])
        self.size_label = QLabel(size_str)
        self.size_label.setStyleSheet("font-size: 11px; color: #6c757d;")
        self.size_label.setFixedWidth(70)
        layout.addWidget(self.size_label)

        # === ACTION BUTTON ===
        self.action_btn = QPushButton()
        self.action_btn.setFixedSize(30, 30)
        self.action_btn.setCursor(Qt.PointingHandCursor)

        more_icon = os.path.join("static", "icons", "more_vert.png")
        if os.path.exists(more_icon):
            self.action_btn.setIcon(QIcon(more_icon))
            self.action_btn.setIconSize(QSize(16, 16))
        else:
            self.action_btn.setText("⋮")

        self.update_button_style(False)  # Set initial button style
        self.setToolTip(f"{self.attachment_data['filename']} ({self.format_file_size(self.attachment_data['size'])})")
        self.action_btn.clicked.connect(self.show_action_menu)
        layout.addWidget(self.action_btn)
        layout.addStretch()

    def update_icon_style(self, hovered):
        """Update icon style based on hover state"""
        if hovered:
            self.icon_label.setStyleSheet("""
                background-color: #cce5ff;
                border: 1px solid #007bff;
                border-radius: 6px;
            """)
        else:
            self.icon_label.setStyleSheet("""
                background: white;
                border: 1px solid #ddd;
                border-radius: 6px;
            """)

    def update_button_style(self, hovered):
        """Update button style based on hover state"""
        if hovered:
            self.action_btn.setStyleSheet("""
                QPushButton {
                    border: 1px solid #007bff;
                    border-radius: 4px;
                    background-color: #007bff;
                    color: white;
                }
                QPushButton:hover {
                    background-color: #0056b3;
                    border-color: #0056b3;
                }
            """)
        else:
            self.action_btn.setStyleSheet("""
                QPushButton {
                    border: 1px solid #ced4da;
                    border-radius: 4px;
                    background-color: white;
                    color: #495057;
                }
                QPushButton:hover {
                    background-color: #007bff;
                    border-color: #007bff;
                    color: white;
                }
            """)

    def update_widget_style(self, hovered):
        """Update the main widget style based on hover state"""
        if hovered:
            self.setStyleSheet("""
                AttachmentWidget {
                    background-color: #e3f2fd;
                    border: 2px solid #2196f3;
                    border-radius: 8px;
                    padding: 8px;
                }
            """)
        else:
            self.setStyleSheet("""
                AttachmentWidget {
                    background-color: #f8f9fa;
                    border: 1px solid #dee2e6;
                    border-radius: 8px;
                    padding: 8px;
                }
            """)

    # === ICON / FILE EXT HELPERS ===
    def get_icon_path(self, file_ext):
        icon_map = {
            'pdf': 'pdf.png',
            'doc': 'word.png', 'docx': 'word.png',
            'xls': 'excel.png', 'xlsx': 'excel.png',
            'ppt': 'powerpoint.png', 'pptx': 'powerpoint.png',
            'jpg': 'image.png', 'jpeg': 'image.png', 'png': 'image.png', 'gif': 'image.png',
            'mp3': 'audio.png', 'wav': 'audio.png',
            'mp4': 'video.png', 'avi': 'video.png',
            'zip': 'archive.png', 'rar': 'archive.png', '7z': 'archive.png',
            'txt': 'text.png'
        }
        return os.path.join("static", "icons", icon_map.get(file_ext, 'file.png'))

    def get_text_icon(self, file_ext):
        icon_map = {
            'pdf': '📄',
            'doc': '📝', 'docx': '📝',
            'xls': '📊', 'xlsx': '📊',
            'ppt': '📺', 'pptx': '📺',
            'jpg': '🖼️', 'jpeg': '🖼️', 'png': '🖼️', 'gif': '🖼️',
            'mp3': '🎵', 'wav': '🎵',
            'mp4': '🎬', 'avi': '🎬',
            'zip': '🗜️', 'rar': '🗜️',
            'txt': '📄'
        }
        return icon_map.get(file_ext, '📎')

    def format_file_size(self, size_bytes):
        if size_bytes == 0: return "0B"
        size_names = ["B", "KB", "MB", "GB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names)-1:
            size_bytes /= 1024.0
            i += 1
        return f"{size_bytes:.1f}{size_names[i]}"

    # === ACTION MENU ===
    def show_action_menu(self):
        menu = QMenu(self)
        open_act = menu.addAction("Open")
        save_act = menu.addAction("Save As...")
        open_act.triggered.connect(self.emit_open)
        save_act.triggered.connect(self.emit_save)
        menu.exec(self.action_btn.mapToGlobal(self.action_btn.rect().bottomLeft()))

    def emit_open(self):
        self.open_attachment_signal.emit(self.attachment_data)

    def emit_save(self):
        self.save_attachment_signal.emit(self.attachment_data)

    # === ENHANCED HOVER EFFECTS ===
    def enterEvent(self, event):
        """Called when mouse enters the widget"""
        self.is_hovered = True
        self.update_widget_style(True)
        self.update_icon_style(True)
        self.update_button_style(True)
        self.update_text_style(True)  # Add text style update
        
        # Add subtle animation effect by updating the cursor
        self.setCursor(Qt.PointingHandCursor)
        
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Called when mouse leaves the widget"""
        self.is_hovered = False
        self.update_widget_style(False)
        self.update_icon_style(False)
        self.update_button_style(False)
        self.update_text_style(False)  # Add text style update
        
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        """Add click effect"""
        if event.button() == Qt.LeftButton:
            # Temporarily darken the widget on click
            self.setStyleSheet("""
                AttachmentWidget {
                    background-color: #bbdefb;
                    border: 2px solid #1976d2;
                    border-radius: 8px;
                    padding: 8px;
                }
            """)
            QTimer.singleShot(100, lambda: self.update_widget_style(self.is_hovered))
        
        super().mousePressEvent(event)

class NotificationCenter(QDialog):
    reply_requested = Signal(int, str, str)  # conversation_id, recipient, subject
    open_attachment_signal = Signal(dict)
    save_attachment_signal = Signal(dict)
    
    def __init__(self, parent=None, db_connection=None, email_service=None):
        super().__init__(parent)
        self.db_connection = db_connection
        self.email_service = email_service
        self.current_conversation = None
        self.is_loading = False
        
        # Connect signals
        #self.open_attachment_signal.connect(self.open_attachment)
        #self.save_attachment_signal.connect(self.save_attachment)
        
        # Set dialog properties
        self.setWindowTitle("Email Notifications")
        self.setMinimumSize(1400, 750)
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f5f5;
            }
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollArea > QWidget > QWidget {
                background-color: transparent;
            }
        """)
        
        self.setup_ui()
        self.load_notifications()
    
    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # Header with improved styling
        header_layout = QHBoxLayout()
        title_label = QLabel("Email Notifications")
        title_label.setFont(QFont("Tahoma", 22, QFont.Bold))
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #2c3e50; margin-bottom: 10px;")
        
        # Refresh Button
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setProperty("class", "success")
        try:
            self.refresh_btn.setIcon(QIcon(os.path.join("static", "icons", "refresh.png")))
            self.refresh_btn.setIconSize(QSize(16, 16))
        except:
            pass  # Icons are optional
        self.refresh_btn.setToolTip("Reload notifications")
        self.refresh_btn.clicked.connect(self.load_notifications)
        
        # Mark All Read Button
        self.mark_all_read_btn = QPushButton("Mark All Read")
        self.mark_all_read_btn.setProperty("class", "warning")
        try:
            self.mark_all_read_btn.setIcon(QIcon(os.path.join("static", "icons", "read.png")))
            self.mark_all_read_btn.setIconSize(QSize(16, 16))
        except:
            pass  # Icons are optional
        self.mark_all_read_btn.setToolTip("Mark all messages as read")
        self.mark_all_read_btn.clicked.connect(self.mark_all_read)

        # Debug Button
        self.debug_button = QPushButton("Debug")
        self.debug_button.setProperty("class", "info")
        self.debug_button.clicked.connect(self.debug_email_attachments)
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.refresh_btn)
        header_layout.addWidget(self.mark_all_read_btn)
        header_layout.addWidget(self.debug_button)
        main_layout.addLayout(header_layout)
        
        # Loading indicator (initially hidden)
        self.loading_indicator = QProgressBar()
        self.loading_indicator.setRange(0, 0)  # Indeterminate progress
        self.loading_indicator.setVisible(False)
        self.loading_indicator.setFixedHeight(6)
        main_layout.addWidget(self.loading_indicator)
        
        # Status label for feedback
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #495057; font-size: 13px; padding: 8px;")
        self.status_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.status_label)
        
        # Main content area with splitter
        content_splitter = QSplitter(Qt.Horizontal)
        content_splitter.setChildrenCollapsible(False)
        
        # Left panel - Conversations list (wider)
        left_panel = QWidget()
        left_panel.setMinimumWidth(350)
        left_panel.setMaximumWidth(500)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 10, 0)
        
        conversations_label = QLabel("Conversations")
        conversations_label.setFont(QFont("Arial", 16, QFont.Bold))
        conversations_label.setStyleSheet("padding: 10px; color: white; background-color: #0056b3; border-radius: 8px;")
        left_layout.addWidget(conversations_label)
        
        # Conversations list with scroll
        self.conversations_list = QListWidget()
        self.conversations_list.setStyleSheet("""
            QListWidget {
                background-color: white;
                border: 2px solid #dee2e6;
                border-radius: 8px; 
                padding: 8px;
                color: #2c3e50;
                font-family: Arial, sans-serif;
                font-size: 14px;
                outline: 0px;
            }
            QListWidget::item {
                padding: 0px;
                border-bottom: 1px solid #e9ecef;
                color: #2c3e50 !important;
            }
            QListWidget::item:selected {
                background-color: #e3f2fd;
                border-left: 4px solid #2196f3;
                color: #2c3e50 !important;
            }
            QListWidget::item:hover {
                background-color: #f8f9fa;
            }
        """)
        self.conversations_list.setUniformItemSizes(True)
        self.conversations_list.currentRowChanged.connect(self.show_conversation)
        left_layout.addWidget(self.conversations_list)
        content_splitter.addWidget(left_panel)
        
        # Right panel - Message view with unified scroll
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(10, 0, 0, 0)
        right_layout.setSpacing(15)
        
        # Message header
        self.message_header = QLabel("Select a conversation to view messages")
        self.message_header.setWordWrap(True)
        self.message_header.setStyleSheet("""
            padding: 20px;
            background-color: #2c3e50;
            color: white;
            border-radius: 8px;
            font-weight: 500;
            font-size: 15px;
            border: 1px solid #34495e;
        """)
        right_layout.addWidget(self.message_header)
        
        # Create a scroll area for the entire right content
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        right_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # Container for scrollable content
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 10, 0)  # Right margin for scrollbar
        scroll_layout.setSpacing(15)
        
        # Messages area
        self.messages_area = QTextEdit()
        self.messages_area.setReadOnly(True)
        self.messages_area.setWordWrapMode(QTextOption.WordWrap)
        self.messages_area.setStyleSheet("""
            QTextEdit {
                background-color: white;
                border: 2px solid #dee2e6; 
                border-radius: 8px;
                padding: 20px;
                font-family: Arial;
                font-size: 14px;
                color: #2c3e50;
                line-height: 1.6;
                min-height: 300px;
            }
        """)
        self.messages_area.setMinimumHeight(350)
        scroll_layout.addWidget(self.messages_area)
        
        # Attachments area
        attachments_frame = QFrame()
        attachments_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: 2px solid #dee2e6;
                border-radius: 8px;
                padding: 15px;
            }
        """)
        attachments_frame.setMinimumHeight(380)   # Show ~3 rows comfortably
        attachments_frame.setMaximumHeight(450)  # Optional: cap max height, force scroll if needed
        
        attachments_layout = QVBoxLayout(attachments_frame)
        
        attachments_label = QLabel("Attachments:")
        attachments_label.setStyleSheet("font-weight: bold; color: #495057; font-size: 14px; margin-bottom: 10px;")
        attachments_layout.addWidget(attachments_label)
        
        # Attachments scroll area with grid layout
        attachments_scroll = QScrollArea()
        attachments_scroll.setWidgetResizable(True)
        attachments_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        attachments_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        attachments_scroll.setStyleSheet("""
            QScrollArea {
                border: 1px solid #ced4da;
                border-radius: 6px;
                background-color: white;
            }
        """)
        
        # Container for attachment widgets
        self.attachments_container = QWidget()
        self.attachments_layout = QGridLayout(self.attachments_container)
        self.attachments_layout.setSpacing(10)
        self.attachments_layout.setContentsMargins(10, 10, 10, 10)
        
        attachments_scroll.setWidget(self.attachments_container)
        attachments_layout.addWidget(attachments_scroll)
        scroll_layout.addWidget(attachments_frame)
        
        # Reply area
        reply_frame = QFrame()
        reply_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: 2px solid #dee2e6; 
                border-radius: 8px;
                padding: 12px;
            }
        """)
        reply_layout = QVBoxLayout(reply_frame)
        
        reply_header = QLabel("Quick Reply:")
        reply_header.setStyleSheet("font-weight: bold; color: #495057; font-size: 14px; margin-bottom: 10px;")
        reply_layout.addWidget(reply_header)
        
        self.reply_text = QTextEdit()
        self.reply_text.setPlaceholderText("Type your reply here...")
        self.reply_text.setStyleSheet("""
            QTextEdit {
                background-color: white;
                border: 2px solid #ced4da; 
                border-radius: 8px; 
                padding: 25px;
                font-family: Arial;
                font-size: 14px;
                color: #2c3e50;
            }
        """)
        self.reply_text.setMinimumHeight(200)
        reply_layout.addWidget(self.reply_text)
        
        # Reply buttons
        reply_btn_layout = QHBoxLayout()
        self.send_btn = QPushButton("Send Reply")
        self.send_btn.setProperty("class", "primary")
        try:
            self.send_btn.setIcon(QIcon(os.path.join("static", "icons", "reply.png")))
            self.send_btn.setIconSize(QSize(16, 16))
        except:
            pass  # Icons are optional
        self.send_btn.clicked.connect(self.send_reply)
        
        clear_btn = QPushButton("Clear")
        clear_btn.setProperty("class", "secondary")
        try:
            clear_btn.setIcon(QIcon(os.path.join("static", "icons", "clear.png")))
            clear_btn.setIconSize(QSize(16, 16))
        except:
            pass  # Icons are optional
        clear_btn.clicked.connect(self.clear_reply)
        
        reply_btn_layout.addWidget(self.send_btn)
        reply_btn_layout.addWidget(clear_btn)
        reply_btn_layout.addStretch()
        
        self.reply_status_label = QLabel("")
        self.reply_status_label.setStyleSheet("font-size: 12px; color: #495057;")
        reply_btn_layout.addWidget(self.reply_status_label)
        
        reply_layout.addLayout(reply_btn_layout)
        scroll_layout.addWidget(reply_frame)
        
        # Add stretch to push everything to the top
        scroll_layout.addStretch()
        
        # Set the scroll content
        right_scroll.setWidget(scroll_content)
        right_layout.addWidget(right_scroll)
        
        content_splitter.addWidget(right_panel)
        
        # Set initial splitter sizes
        content_splitter.setSizes([450, 950])
        main_layout.addWidget(content_splitter, 1)
    
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
        self.status_label.setStyleSheet(f"color: {color}; font-size: 13px; padding: 8px;")
        QTimer.singleShot(duration, lambda: self.status_label.setText("Ready") or self.status_label.setStyleSheet("color: #6c757d; font-size: 13px; padding: 8px;"))
    
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
                widget = self.create_conversation_item(conv)
                item.setSizeHint(QSize(400, 120))
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
        layout.setContentsMargins(16, 12, 16, 12)
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
        subject_text = conversation['subject']
        if len(subject_text) > 60:
            subject_text = subject_text[:57] + "..."
        
        subject_label = QLabel(subject_text)
        subject_label.setWordWrap(False)
        subject_label.setObjectName("subjectLabel")
        subject_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        top_layout.addWidget(subject_label, 1)
    
        # Date
        date_label = QLabel(conversation['last_message_date'].strftime('%b %d, %H:%M'))
        date_label.setObjectName("dateLabel")
        top_layout.addWidget(date_label)
    
        layout.addLayout(top_layout)
    
        # Second row: Message preview
        preview_text = conversation.get("last_message_preview", "")
        if preview_text:
            if len(preview_text) > 80:
                preview_text = preview_text[:77] + "..."
            
            preview_label = QLabel(preview_text)
            preview_label.setObjectName("previewLabel")
            preview_label.setWordWrap(False)
            preview_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            layout.addWidget(preview_label)
    
        widget.setFixedHeight(120)
        widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    
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
                font-size: 14px;
            }
            #dateLabel {
                color: #6c757d;
                font-size: 11px;
            }
            #previewLabel {
                color: #495057;
                font-size: 12px;
                margin-top: 2px;
            }
            #unreadBadge {
                background-color: #e74c3c;
                color: white;
                font-weight: bold;
                font-size: 11px;
                padding: 3px 6px;
                border-radius: 8px;
                min-width: 18px;
                max-height: 18px;
                qproperty-alignment: 'AlignCenter';
            }
        """)
    
        widget.conversation_id = conversation['id']
        return widget

    # Add this method to your NotificationCenter class 
    def format_message_body(self, body):
        """Format message body for HTML display with proper line breaks"""
        if not body:
            return ""
        
        import html
        # Escape HTML characters first
        formatted_body = html.escape(body)
        # Convert line breaks to HTML breaks
        formatted_body = formatted_body.replace('\n', '<br>')
        return formatted_body
    
    def format_file_size(self, size_bytes):
        """Format file size in human readable format"""
        if size_bytes == 0:
            return "0 B"
        size_names = ["B", "KB", "MB", "GB"]
        import math
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return f"{s} {size_names[i]}"
    
    # Updated show_conversation method with line break fixes
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
            
            # Clear attachments first
            self.load_attachments(conversation_id)
            
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
                
                # Check if message has attachments
                attachments_html = ""
                cursor.execute("""
                    SELECT filename, file_size FROM email_attachments 
                    WHERE message_id = %s
                """, (msg['id'],))
                
                attachments = cursor.fetchall()
                if attachments:
                    attachments_html = "<div style='margin-top: 10px; font-size: 12px; color: #666;'>"
                    attachments_html += "<strong>📎 Attachments:</strong><br>"
                    for att in attachments:
                        file_size = self.format_file_size(att['file_size'])
                        attachments_html += f"• {att['filename']} ({file_size})<br>"
                    attachments_html += "</div>"
                
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
                            <div style='{message_body_style}'>{self.format_message_body(msg['body'])}</div>
                            {attachments_html}
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
                            <div style='{message_body_style}'>{self.format_message_body(msg['body'])}</div>
                            {attachments_html}
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
    
            self.message_header.setStyleSheet("""
                padding: 20px;
                background-color: #2c3e50;
                color: white;
                border-radius: 8px;
                font-weight: 500;
                font-size: 15px;
                border: 1px solid #34495e;
            """)
            self.mark_conversation_read(conversation_id)
            
        except Exception as e:
            self.show_temp_message(f"❌ Error loading conversation: {str(e)}", 5000, "#dc3545")
            print(f"Error showing conversation: {e}")
    
    def load_attachments(self, conversation_id):
        """Load attachments in a grid layout"""
        try:
            # Clear existing attachments
            for i in reversed(range(self.attachments_layout.count())):
                widget = self.attachments_layout.itemAt(i).widget()
                if widget:
                    widget.deleteLater()
            
            # First get the message IDs for this conversation
            cursor = self.db_connection.cursor(dictionary=True)
            cursor.execute("""
                SELECT id FROM email_messages 
                WHERE conversation_id = %s
            """, (conversation_id,))
            
            message_ids = [row['id'] for row in cursor.fetchall()]
            
            if not message_ids:
                no_attachments_label = QLabel("No attachments found")
                no_attachments_label.setAlignment(Qt.AlignCenter)
                no_attachments_label.setStyleSheet("color: #6c757d; font-style: italic;")
                self.attachments_layout.addWidget(no_attachments_label, 0, 0)
                return
            
            # Get all attachments for these messages
            all_attachments = []
            for message_id in message_ids:
                cursor.execute("""
                    SELECT id, filename, file_size, content_type, content_id
                    FROM email_attachments 
                    WHERE message_id = %s
                """, (message_id,))
                
                for row in cursor.fetchall():
                    all_attachments.append({
                        'id': row['id'],
                        'filename': row['filename'],
                        'size': row['file_size'],
                        'content_type': row['content_type'],
                        'content_id': row['content_id'],
                        'message_id': message_id
                    })
            
            # Display attachments in grid (3 per row)
            if all_attachments:
                row, col = 0, 0
                max_cols = 3  # 3 attachments per row
                
                for attachment in all_attachments:
                    attachment_widget = AttachmentWidget(attachment, self)
                    self.attachments_layout.addWidget(attachment_widget, row, col)
                    
                    col += 1
                    if col >= max_cols:
                        col = 0
                        row += 1
                
                self.show_temp_message(f"Loaded {len(all_attachments)} attachments", 2000)
            else:
                no_attachments_label = QLabel("No attachments found")
                no_attachments_label.setAlignment(Qt.AlignCenter)
                no_attachments_label.setStyleSheet("color: #6c757d; font-style: italic;")
                self.attachments_layout.addWidget(no_attachments_label, 0, 0)
                
        except Exception as e:
            print(f"Error loading attachments: {e}")
            error_label = QLabel(f"Error loading attachments: {str(e)}")
            error_label.setStyleSheet("color: #dc3545;")
            error_label.setAlignment(Qt.AlignCenter)
            self.attachments_layout.addWidget(error_label, 0, 0)
    
    def format_file_size(self, size_bytes):
        """Format file size in human-readable format"""
        if size_bytes == 0:
            return "0B"
        size_names = ["B", "KB", "MB", "GB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names)-1:
            size_bytes /= 1024.0
            i += 1
        return f"{size_bytes:.1f}{size_names[i]}"
    
    # Fixed methods for NotificationCenter class
    
    def open_attachment(self, attachment_data):
        """Open attachment using system default app"""
        try:
            cursor = self.db_connection.cursor(dictionary=True)
            cursor.execute("SELECT filename, file_data FROM email_attachments WHERE id = %s", (attachment_data['id'],))
            result = cursor.fetchone()
            if not result:
                QMessageBox.warning(self, "Not Found", "Attachment not found.")
                return
    
            filename = result['filename']
            raw_data = result['file_data']
    
            # Normalize to bytes
            if isinstance(raw_data, str):
                try:
                    file_data = base64.b64decode(raw_data)
                except Exception as e:
                    raise ValueError(f"Failed to decode Base64: {e}")
            elif isinstance(raw_data, (bytes, bytearray)):
                file_data = bytes(raw_data)
            else:
                raise ValueError("Unsupported binary type")
    
            # Write to temp file with proper extension
            temp_dir = tempfile.gettempdir()
            safe_filename = "".join(c for c in filename if c.isalnum() or c in "._()- ")
            
            # Ensure we have an extension
            if '.' not in safe_filename:
                safe_filename += '.tmp'
                
            temp_path = os.path.join(temp_dir, safe_filename)
    
            # Handle duplicate filenames
            counter = 1
            base_name, ext = os.path.splitext(safe_filename)
            original_path = temp_path
            while os.path.exists(temp_path):
                temp_path = os.path.join(temp_dir, f"{base_name}_{counter}{ext}")
                counter += 1
    
            # Write the file
            with open(temp_path, 'wb') as f:
                f.write(file_data)
    
            # Try to open with system default app
            import subprocess
            import platform
            
            system = platform.system()
            try:
                if system == "Windows":
                    os.startfile(temp_path)
                elif system == "Darwin":  # macOS
                    subprocess.run(["open", temp_path])
                else:  # Linux and others
                    subprocess.run(["xdg-open", temp_path])
                    
                self.show_temp_message(f"Opened: {filename}", 3000, "#28a745")
                print(f"Successfully opened attachment: {temp_path}")
                
            except Exception as open_error:
                # Fallback: show file location
                QMessageBox.information(
                    self, 
                    "File Saved", 
                    f"Could not open automatically, but file saved to:\n{temp_path}\n\nYou can open it manually."
                )
                print(f"Could not auto-open, saved to: {temp_path}")
    
        except Exception as e:
            QMessageBox.critical(self, "Open Failed", f"Cannot open attachment:\n{str(e)}")
            print(f"[ERROR] Open failed: {e}")
    
    def save_attachment(self, attachment_data):
        """Save attachment to user-selected location"""
        try:
            cursor = self.db_connection.cursor(dictionary=True)
            cursor.execute("SELECT filename, file_data FROM email_attachments WHERE id = %s", (attachment_data['id'],))
            result = cursor.fetchone()
            if not result:
                QMessageBox.warning(self, "Not Found", "Attachment not found.")
                return
    
            filename = result['filename']
            raw_data = result['file_data']
    
            # Normalize to bytes
            if isinstance(raw_data, str):
                try:
                    file_data = base64.b64decode(raw_data)
                except Exception as e:
                    raise ValueError(f"Decode error: {e}")
            elif isinstance(raw_data, (bytes, bytearray)):
                file_data = bytes(raw_data)
            else:
                raise TypeError("Invalid data format")
    
            # Get file extension for filter
            file_ext = filename.split('.')[-1].upper() if '.' in filename else 'ALL'
            file_filter = f"{file_ext} Files (*.{file_ext.lower()});;All Files (*)" if file_ext != 'ALL' else "All Files (*)"
    
            # Ask where to save
            save_path, selected_filter = QFileDialog.getSaveFileName(
                self,
                "Save Attachment",
                filename,  # Default filename
                file_filter
            )
            
            if not save_path:
                return  # User canceled
    
            # Write the file
            try:
                with open(save_path, 'wb') as f:
                    f.write(file_data)
                
                file_size = len(file_data)
                self.show_temp_message(
                    f"Saved: {os.path.basename(save_path)} ({self.format_file_size(file_size)})", 
                    4000, 
                    "#28a745"
                )
                print(f"Successfully saved attachment to: {save_path}")
                
            except IOError as io_error:
                QMessageBox.critical(self, "Save Failed", f"Could not write file:\n{str(io_error)}")
                print(f"[ERROR] IO error during save: {io_error}")
    
        except Exception as e:
            QMessageBox.critical(self, "Save Failed", f"Could not save attachment:\n{str(e)}")
            print(f"[ERROR] Save failed: {e}")
    

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
    
    def debug_email_attachments(self):
        """Debug method to check email attachments"""
        try:
            cursor = self.db_connection.cursor(dictionary=True)
            cursor.execute("SELECT COUNT(*) as count FROM email_attachments")
            result = cursor.fetchone()
            count = result['count'] if result else 0
            
            cursor.execute("""
                SELECT a.id, a.filename, a.file_size, a.content_type, m.subject 
                FROM email_attachments a
                JOIN email_messages m ON a.message_id = m.id
                ORDER BY a.created_at DESC LIMIT 5
            """)
            
            recent = cursor.fetchall()
            
            debug_msg = f"Total attachments in database: {count}\n\nRecent attachments:\n"
            for att in recent:
                debug_msg += f"• {att['filename']} ({att['file_size']} bytes) - {att['content_type']}\n"
            
            QMessageBox.information(self, "Debug Info", debug_msg)
            
        except Exception as e:
            QMessageBox.critical(self, "Debug Error", f"Error getting debug info: {str(e)}")