# ui/email_composer_dialog.py
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTextEdit,
    QPushButton, QComboBox, QListWidget, QListWidgetItem, QGroupBox,
    QFormLayout, QCheckBox, QFileDialog, QMessageBox, QScrollArea,
    QWidget, QSplitter, QProgressDialog
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon, QFont
import os
from services.email_service import EmailService, EmailTemplates
# In your email_composer_dialog.py
from ui.spam_checker_dialog import SpamCheckerDialog

class EmailComposerDialog(QDialog):
    # Add these constants
    MAX_ATTACHMENTS = 5  # Maximum number of attachments
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB in bytes
    ALLOWED_FILE_TYPES = ['.pdf', '.doc', '.docx', '.txt', '.jpg', '.jpeg', '.png', '.xls', '.xlsx']
    
    def __init__(self, parent=None, db_connection=None, recipient_type=None, 
                 recipient_ids=None, subject=None, body=None):
        super().__init__(parent)
        self.db_connection = db_connection
        self.recipient_type = recipient_type
        self.recipient_ids = recipient_ids
        self.preset_subject = subject
        self.preset_body = body
        self.attachments = []
        
        self.setWindowTitle("Compose Email")
        self.setMinimumSize(1000, 700)
        self.setup_ui()
        self.load_recipients()
        # Initialize attachment display
        self.update_attachment_display()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        
        # Header
        header_label = QLabel("Compose New Email")
        header_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #2c3e50;")
        layout.addWidget(header_label)
        
        # Create splitter for two-pane layout
        splitter = QSplitter(Qt.Horizontal)
        
        # Left pane - Recipient selection
        left_pane = QWidget()
        left_layout = QVBoxLayout(left_pane)
        left_layout.setContentsMargins(0, 0, 10, 0)
        
        recipient_group = QGroupBox("Recipients")
        recipient_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        recipient_layout = QVBoxLayout(recipient_group)
        
        # Recipient type selection
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Send to:"))
        
        self.recipient_type_combo = QComboBox()
        self.recipient_type_combo.addItems(["Students", "Teachers", "Parents", "Custom"])
        self.recipient_type_combo.currentTextChanged.connect(self.on_recipient_type_changed)
        type_layout.addWidget(self.recipient_type_combo)
        
        type_layout.addStretch()
        recipient_layout.addLayout(type_layout)
        
        # Recipient list
        self.recipient_list = QListWidget()
        self.recipient_list.setSelectionMode(QListWidget.MultiSelection)
        self.recipient_list.setMinimumWidth(250)
        self.recipient_list.setMinimumHeight(350)  # ← Add this line for minimum height
        self.recipient_list.setMaximumHeight(400)  # ← Optional: set maximum height too
        # ✅ ADD THIS LINE to connect selection changes
        self.recipient_list.itemSelectionChanged.connect(self.update_selection_count)
        recipient_layout.addWidget(self.recipient_list)
        
        # Selection info
        self.selection_label = QLabel("0 recipients selected")
        self.selection_label.setStyleSheet("color: #666; font-size: 11px;")
        recipient_layout.addWidget(self.selection_label)
        
        left_layout.addWidget(recipient_group)
        left_layout.addStretch()
        
        # Right pane - Email composition
        right_pane = QWidget()
        right_layout = QVBoxLayout(right_pane)
        right_layout.setContentsMargins(10, 0, 0, 0)
        
        # Email details group
        details_group = QGroupBox("Email Details")
        details_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        details_layout = QFormLayout(details_group)
        details_layout.setLabelAlignment(Qt.AlignRight)
        
        # From field (readonly)
        self.from_edit = QLineEdit()
        self.from_edit.setReadOnly(True)
        self.from_edit.setPlaceholderText("Loading sender email...")
        details_layout.addRow("From:", self.from_edit)
        
        # Subject field
        self.subject_edit = QLineEdit()
        self.subject_edit.setPlaceholderText("Enter email subject...")
        if self.preset_subject:
            self.subject_edit.setText(self.preset_subject)
        details_layout.addRow("Subject:", self.subject_edit)
        
        # Email body
        body_label = QLabel("Message:")
        body_label.setAlignment(Qt.AlignTop | Qt.AlignRight)
        
        self.body_edit = QTextEdit()
        self.body_edit.setPlaceholderText("Type your message here...")
        self.body_edit.setMinimumHeight(200)
        if self.preset_body:
            self.body_edit.setHtml(self.preset_body)
        
        details_layout.addRow(body_label, self.body_edit)
        
        # HTML checkbox
        self.html_checkbox = QCheckBox("Format as HTML")
        self.html_checkbox.setChecked(True)
        details_layout.addRow("", self.html_checkbox)
        
        right_layout.addWidget(details_group)
        
        # Attachments group
        attachments_group = QGroupBox("Attachments")
        attachments_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        attachments_layout = QVBoxLayout(attachments_group)
        
        # Attachment buttons
        attach_buttons_layout = QHBoxLayout()
        
        add_attach_btn = QPushButton("Add Attachment")
        add_attach_btn.setIcon(QIcon("static/icons/attach.png"))
        add_attach_btn.clicked.connect(self.add_attachment)
        attach_buttons_layout.addWidget(add_attach_btn)
        
        clear_attach_btn = QPushButton("Clear All")
        clear_attach_btn.setProperty("class", "warning")
        clear_attach_btn.setIcon(QIcon("static/icons/clear.png"))
        clear_attach_btn.clicked.connect(self.clear_attachments)
        attach_buttons_layout.addWidget(clear_attach_btn)
        
        attachments_layout.addLayout(attach_buttons_layout)
        
        # Attachment list
        self.attachment_list = QListWidget()
        self.attachment_list.setMaximumHeight(80)
        attachments_layout.addWidget(self.attachment_list)
        
        right_layout.addWidget(attachments_group)
        
        # Add panes to splitter
        splitter.addWidget(left_pane)
        splitter.addWidget(right_pane)
        splitter.setSizes([300, 500])
        
        layout.addWidget(splitter)
        
        # Button row
        button_layout = QHBoxLayout()
        
        # Test button
        test_btn = QPushButton("Send Test")
        test_btn.setProperty("class", "warning")
        test_btn.setIcon(QIcon("static/icons/test.png"))
        test_btn.clicked.connect(self.send_test_email)
        test_btn.setToolTip("Send test email to yourself first")
        button_layout.addWidget(test_btn)
        
        button_layout.addStretch()
        
        # Cancel button
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setProperty("class", "danger")
        cancel_btn.setIcon(QIcon("static/icons/cancel.png"))
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        # Send button
        send_btn = QPushButton("Send Email")
        send_btn.setIcon(QIcon("static/icons/send.png"))
        send_btn.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold;")
        send_btn.clicked.connect(self.send_email)
        button_layout.addWidget(send_btn)

        # Add spam check button to toolbar
        spam_check_btn = QPushButton("Check for Spam")
        spam_check_btn.setProperty("class", "warning")
        spam_check_btn.setToolTip("Check if content might be flagged as spam")
        spam_check_btn.clicked.connect(self.open_spam_checker)
        button_layout.addWidget(spam_check_btn)
        
        layout.addLayout(button_layout)
        
        # Load sender email
        self.load_sender_email()
        
    def load_sender_email(self):
        """Load the configured sender email"""
        try:
            email_service = EmailService(self.db_connection)
            config = email_service.get_email_config()
            if config and config.get('email_address'):
                sender_text = f"{config.get('default_sender_name', 'School')} <{config['email_address']}>"
                self.from_edit.setText(sender_text)
            else:
                self.from_edit.setText("Email not configured - Please set up email first")
                self.from_edit.setStyleSheet("color: #e74c3c;")
        except Exception as e:
            self.from_edit.setText(f"Error loading email config: {str(e)}")
            self.from_edit.setStyleSheet("color: #e74c3c;")
    
    def load_recipients(self):
        """Load recipients based on type"""
        try:
            email_service = EmailService(self.db_connection)
            
            # Clear existing items
            self.recipient_list.clear()
            
            recipient_type = self.recipient_type_combo.currentText().lower()
            
            if recipient_type == "students":
                self.load_students()
            elif recipient_type == "teachers":
                self.load_teachers()
            elif recipient_type == "parents":
                self.load_parents()
            elif recipient_type == "custom":
                self.load_custom_emails()
                
            # Preselect if recipient IDs were provided
            if self.recipient_ids and self.recipient_type:
                self.select_preset_recipients()
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load recipients: {str(e)}")
    
    def load_teachers(self):
        """Load teachers from database"""
        try:
            cursor = self.db_connection.cursor(dictionary=True)
            cursor.execute("""
                SELECT id, first_name, surname, email 
                FROM teachers 
                WHERE is_active = TRUE AND email IS NOT NULL
                ORDER BY first_name, surname
            """)
            
            teachers = cursor.fetchall()
            
            for teacher in teachers:
                display_text = f"{teacher['first_name']} {teacher['surname']} - {teacher['email']}"
                
                item = QListWidgetItem(display_text)
                item.setData(Qt.UserRole, {
                    'id': teacher['id'],
                    'type': 'teacher',
                    'emails': [teacher['email']] if teacher['email'] else []
                })
                self.recipient_list.addItem(item)
                
        except Exception as e:
            print(f"Error loading teachers: {e}")
            QMessageBox.warning(self, "Error", f"Failed to load teachers: {str(e)}")
    
    def load_students(self):
        """Load students from database using your existing schema"""
        try:
            cursor = self.db_connection.cursor(dictionary=True)
            cursor.execute("""
                SELECT s.id, s.full_name, s.email, 
                       COALESCE(GROUP_CONCAT(DISTINCT p.email SEPARATOR ', '), '') as parent_emails
                FROM students s
                LEFT JOIN student_parent sp ON s.id = sp.student_id
                LEFT JOIN parents p ON sp.parent_id = p.id
                WHERE s.is_active = TRUE AND (s.email IS NOT NULL OR p.email IS NOT NULL)
                GROUP BY s.id
                ORDER BY s.full_name
            """)
            
            students = cursor.fetchall()
            
            for student in students:
                # Create a more readable display
                display_text = student['full_name']
                emails = []
                
                if student['email']:
                    emails.append(f"Student: {student['email']}")
                
                # Now parent_emails will always be a string (empty if no parents)
                parent_emails = student['parent_emails']
                if parent_emails:  # This will be empty string if no parent emails
                    parent_email_list = parent_emails.split(', ')
                    for parent_email in parent_email_list:
                        if parent_email and parent_email != 'None' and parent_email != 'NULL':
                            emails.append(f"Parent: {parent_email}")
                
                if emails:
                    display_text += f" ({'; '.join(emails)})"
                
                item = QListWidgetItem(display_text)
                
                # Build email list
                email_list = []
                if student['email']:
                    email_list.append(student['email'])
                
                if parent_emails:  # Process parent emails
                    for email in parent_emails.split(', '):
                        if email and email != 'None' and email != 'NULL':
                            email_list.append(email)
                
                item.setData(Qt.UserRole, {
                    'id': student['id'],
                    'type': 'student',
                    'emails': email_list
                })
                self.recipient_list.addItem(item)
                
        except Exception as e:
            print(f"Error loading students: {e}")
            QMessageBox.warning(self, "Error", f"Failed to load students: {str(e)}")
    
    def load_parents(self):
        """Load parents from database using your existing student_parent table"""
        try:
            cursor = self.db_connection.cursor(dictionary=True)
            cursor.execute("""
                SELECT p.id, p.full_name, p.email, 
                       GROUP_CONCAT(s.full_name SEPARATOR ', ') as student_names
                FROM parents p
                LEFT JOIN student_parent sp ON p.id = sp.parent_id
                LEFT JOIN students s ON sp.student_id = s.id
                WHERE p.is_active = TRUE AND p.email IS NOT NULL
                GROUP BY p.id
                ORDER BY p.full_name
            """)
            
            parents = cursor.fetchall()
            
            for parent in parents:
                student_info = f" (Parent of {parent['student_names']})" if parent['student_names'] else ""
                display_text = f"{parent['full_name']}{student_info} - {parent['email']}"
                
                item = QListWidgetItem(display_text)
                item.setData(Qt.UserRole, {
                    'id': parent['id'],
                    'type': 'parent',
                    'emails': [parent['email']] if parent['email'] else []
                })
                self.recipient_list.addItem(item)
                
        except Exception as e:
            print(f"Error loading parents: {e}")
            QMessageBox.warning(self, "Error", f"Failed to load parents: {str(e)}")
    
    def load_custom_emails(self):
        """Load custom email entry"""
        item = QListWidgetItem("Click to add custom email addresses...")
        item.setData(Qt.UserRole, {
            'type': 'custom',
            'emails': []
        })
        self.recipient_list.addItem(item)
    
    def select_preset_recipients(self):
        """Select recipients based on preset IDs"""
        for i in range(self.recipient_list.count()):
            item = self.recipient_list.item(i)
            item_data = item.data(Qt.UserRole)
            
            if (item_data.get('type') == self.recipient_type and 
                item_data.get('id') in self.recipient_ids):
                item.setSelected(True)
        
        self.update_selection_count()
    
    def on_recipient_type_changed(self, recipient_type):
        """Handle recipient type change"""
        self.load_recipients()
    
    def update_selection_count(self):
        """Update selection count label"""
        selected_count = len(self.recipient_list.selectedItems())
        total_emails = 0
        
        for item in self.recipient_list.selectedItems():
            item_data = item.data(Qt.UserRole)
            total_emails += len(item_data.get('emails', []))
            print(f"DEBUG: Selected item {item_data}")  # Add this for debugging
        
        self.selection_label.setText(f"{selected_count} recipients selected ({total_emails} email addresses)")
    
    def add_attachment(self):
        """Add file attachment with limits"""
        # Check attachment count limit
        if len(self.attachments) >= self.MAX_ATTACHMENTS:
            QMessageBox.warning(
                self, 
                "Limit Reached", 
                f"Maximum {self.MAX_ATTACHMENTS} attachments allowed."
            )
            return
        
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, 
            "Select Files to Attach", 
            "", 
            f"Allowed Files ({' '.join(self.ALLOWED_FILE_TYPES)});;All Files (*)"
        )
        
        for file_path in file_paths:
            if len(self.attachments) >= self.MAX_ATTACHMENTS:
                QMessageBox.warning(
                    self, 
                    "Limit Reached", 
                    f"Maximum {self.MAX_ATTACHMENTS} attachments reached. Some files were not added."
                )
                break
                
            if not os.path.exists(file_path):
                continue
                
            # Check file size
            file_size = os.path.getsize(file_path)
            if file_size > self.MAX_FILE_SIZE:
                file_name = os.path.basename(file_path)
                size_mb = file_size / (1024 * 1024)
                max_mb = self.MAX_FILE_SIZE / (1024 * 1024)
                QMessageBox.warning(
                    self,
                    "File Too Large",
                    f"'{file_name}' ({size_mb:.1f}MB) exceeds the maximum size of {max_mb:.0f}MB."
                )
                continue
            
            # Check file type
            file_ext = os.path.splitext(file_path)[1].lower()
            if file_ext not in self.ALLOWED_FILE_TYPES:
                QMessageBox.warning(
                    self,
                    "File Type Not Allowed",
                    f"'{os.path.basename(file_path)}' file type is not allowed.\n"
                    f"Allowed types: {', '.join(self.ALLOWED_FILE_TYPES)}"
                )
                continue
            
            # Add valid attachment
            self.attachments.append(file_path)
            file_name = os.path.basename(file_path)
            
            # Add file size to display
            size_mb = file_size / (1024 * 1024)
            list_item = QListWidgetItem(f"{file_name} ({size_mb:.1f}MB)")
            self.attachment_list.addItem(list_item)
        
        # Update UI to show current attachment count
        self.update_attachment_display()
    
    def update_attachment_display(self):
        """Update attachment count display"""
        attachment_count = len(self.attachments)
        max_count = self.MAX_ATTACHMENTS
        
        # Update the group box title to show count
        attachments_group = self.findChild(QGroupBox, "Attachments")
        if attachments_group:
            attachments_group.setTitle(f"Attachments ({attachment_count}/{max_count})")
        
        # Disable add button if limit reached
        add_attach_btn = self.findChild(QPushButton, "Add Attachment")
        if add_attach_btn:
            add_attach_btn.setEnabled(attachment_count < max_count)
            if attachment_count >= max_count:
                add_attach_btn.setToolTip(f"Maximum {max_count} attachments reached")
            else:
                add_attach_btn.setToolTip(f"Add attachment ({max_count - attachment_count} remaining)")
    
    def clear_attachments(self):
        """Clear all attachments"""
        self.attachments.clear()
        self.attachment_list.clear()
        self.update_attachment_display()
    
    def get_selected_emails(self):
        """Get all selected email addresses"""
        all_emails = set()
        
        for item in self.recipient_list.selectedItems():
            item_data = item.data(Qt.UserRole)
            for email in item_data.get('emails', []):
                if email and email.strip():
                    all_emails.add(email.strip())
        
        return list(all_emails)
    
    def validate_form(self):
        """Validate the email form"""
        if not self.subject_edit.text().strip():
            QMessageBox.warning(self, "Validation", "Please enter a subject for the email.")
            return False
        
        if not self.body_edit.toPlainText().strip():
            QMessageBox.warning(self, "Validation", "Please enter a message for the email.")
            return False
        
        selected_emails = self.get_selected_emails()
        if not selected_emails:
            QMessageBox.warning(self, "Validation", "Please select at least one recipient.")
            return False
        
        # Validate sender email
        sender_email = self.from_edit.text()
        if "not configured" in sender_email.lower() or "error" in sender_email.lower():
            QMessageBox.warning(self, "Configuration", "Please configure email settings before sending.")
            return False
        
        # Validate attachment count
        if len(self.attachments) > self.MAX_ATTACHMENTS:
            QMessageBox.warning(
                self, 
                "Too Many Attachments", 
                f"Maximum {self.MAX_ATTACHMENTS} attachments allowed."
            )
            return False
        
        # Validate individual attachment sizes
        for attachment in self.attachments:
            if os.path.exists(attachment):
                file_size = os.path.getsize(attachment)
                if file_size > self.MAX_FILE_SIZE:
                    file_name = os.path.basename(attachment)
                    size_mb = file_size / (1024 * 1024)
                    max_mb = self.MAX_FILE_SIZE / (1024 * 1024)
                    QMessageBox.warning(
                        self,
                        "File Too Large",
                        f"'{file_name}' ({size_mb:.1f}MB) exceeds the maximum size of {max_mb:.0f}MB."
                    )
                    return False
        
        # Validate total attachment size
        total_size = 0
        for attachment in self.attachments:
            if os.path.exists(attachment):
                total_size += os.path.getsize(attachment)
        
        MAX_TOTAL_SIZE = 25 * 1024 * 1024  # 25MB total limit
        if total_size > MAX_TOTAL_SIZE:
            total_mb = total_size / (1024 * 1024)
            max_mb = MAX_TOTAL_SIZE / (1024 * 1024)
            QMessageBox.warning(
                self,
                "Attachments Too Large",
                f"Total attachment size ({total_mb:.1f}MB) exceeds maximum of {max_mb:.0f}MB.\n"
                "Please remove some attachments or use smaller files."
            )
            return False
        
        # Validate file types
        for attachment in self.attachments:
            file_ext = os.path.splitext(attachment)[1].lower()
            if file_ext not in self.ALLOWED_FILE_TYPES:
                file_name = os.path.basename(attachment)
                QMessageBox.warning(
                    self,
                    "File Type Not Allowed",
                    f"'{file_name}' file type is not allowed.\n"
                    f"Allowed types: {', '.join(self.ALLOWED_FILE_TYPES)}"
                )
                return False
        
        return True
    
    # Also update your send_test_email method similarly
    def send_test_email(self):
        """Send test email to yourself"""
        if not self.validate_form():
            return
        
        try:
            email_service = EmailService(self.db_connection)
            config = email_service.get_email_config()
            
            if not config or not config.get('email_address'):
                QMessageBox.warning(self, "Configuration", "Email not configured. Please set up email first.")
                return
            
            # FIX: Get the proper content based on HTML checkbox
            if self.html_checkbox.isChecked():
                email_body = self.body_edit.toPlainText().replace('\n', '<br>')
            else:
                email_body = self.body_edit.toPlainText()
            
            # Send test to yourself
            success, message = email_service.send_email(
                config['email_address'],
                f"TEST: {self.subject_edit.text()}",
                email_body,  # Use the properly formatted body
                self.attachments,
                self.html_checkbox.isChecked()
            )
            
            if success:
                QMessageBox.information(self, "Test Sent", "Test email sent successfully to yourself!")
            else:
                QMessageBox.warning(self, "Test Failed", f"Failed to send test email: {message}")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to send test email: {str(e)}")
    
    # Update your send_email method in EmailComposerDialog 
    def send_email(self):
        """Send the actual email"""
        if not self.validate_form():
            return
        
        selected_emails = self.get_selected_emails()
        if not selected_emails:
            return
        
        # Confirm before sending
        reply = QMessageBox.question(
            self,
            "Confirm Send",
            f"Send this email to {len(selected_emails)} recipients?\n\n"
            f"Subject: {self.subject_edit.text()}\n"
            f"Recipients: {', '.join(selected_emails[:3])}{'...' if len(selected_emails) > 3 else ''}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # Show progress dialog
        progress = QProgressDialog("Sending emails...", "Cancel", 0, len(selected_emails), self)
        progress.setWindowModality(Qt.WindowModal)
        progress.show()
        
        try:
            email_service = EmailService(self.db_connection)
            
            # FIX: Get the proper content based on HTML checkbox
            if self.html_checkbox.isChecked():
                # For HTML emails, convert plain text line breaks to HTML
                email_body = self.body_edit.toPlainText()
                # Convert line breaks to HTML breaks
                email_body = email_body.replace('\n', '<br>')
                # You could also use toHtml() if you want full HTML formatting
                # email_body = self.body_edit.toHtml()
            else:
                # For plain text emails, preserve line breaks
                email_body = self.body_edit.toPlainText()
            
            success, message = email_service.send_email(
                selected_emails,
                self.subject_edit.text(),
                email_body,  # Use the properly formatted body
                self.attachments,
                self.html_checkbox.isChecked()
            )
            
            progress.close()
            
            if success:
                QMessageBox.information(
                    self,
                    "Success", 
                    f"Email sent successfully to {len(selected_emails)} recipients!"
                )
                self.accept()
            else:
                QMessageBox.warning(self, "Failed", f"Failed to send email: {message}")
                
        except Exception as e:
            progress.close()
            QMessageBox.critical(self, "Error", f"Failed to send email: {str(e)}")

    
    def get_email_data(self):
        """Get email data for external sending"""
        return {
            'recipient_type': self.recipient_type_combo.currentText().lower(),
            'recipient_ids': [item.data(Qt.UserRole).get('id') for item in self.recipient_list.selectedItems()],
            'subject': self.subject_edit.text(),
            'body': self.body_edit.toHtml() if self.html_checkbox.isChecked() else self.body_edit.toPlainText(),
            'attachments': self.attachments,
            'is_html': self.html_checkbox.isChecked()
        }

    # Add this method to your EmailComposerDialog class in email_composer_dialog.py
    def open_spam_checker(self):
        """Open spam checker dialog with current email content"""
        try:
            # Get current email content
            subject = self.subject_edit.text()
            body = self.body_edit.toPlainText()
            
            # Combine subject and body for analysis
            full_content = f"Subject: {subject}\n\n{body}" if subject else body
            
            if not full_content.strip():
                QMessageBox.information(
                    self, 
                    "No Content", 
                    "Please enter some email content before checking for spam."
                )
                return
            
            # Create and show spam checker dialog
            spam_dialog = SpamCheckerDialog(self)
            
            # Pre-fill with current content
            spam_dialog.input_text.setPlainText(full_content)
            
            # Auto-analyze on open
            QTimer.singleShot(100, spam_dialog.analyze_text)
            
            spam_dialog.exec()
            
        except Exception as e:
            QMessageBox.critical(
                self, 
                "Error", 
                f"Failed to open spam checker: {str(e)}"
            )