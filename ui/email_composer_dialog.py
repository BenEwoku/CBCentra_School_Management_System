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

class EmailComposerDialog(QDialog):
    def __init__(self, parent=None, db_connection=None, recipient_type=None, 
                 recipient_ids=None, subject=None, body=None):
        super().__init__(parent)
        self.db_connection = db_connection
        self.recipient_type = recipient_type
        self.recipient_ids = recipient_ids
        self.preset_subject = subject
        self.preset_body = body
        self.attachments = []
        
        self.setWindowTitle("✉️ Compose Email")
        self.setMinimumSize(800, 600)
        self.setup_ui()
        self.load_recipients()
        
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
        test_btn.setIcon(QIcon("static/icons/test.png"))
        test_btn.clicked.connect(self.send_test_email)
        test_btn.setToolTip("Send test email to yourself first")
        button_layout.addWidget(test_btn)
        
        button_layout.addStretch()
        
        # Cancel button
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setIcon(QIcon("static/icons/cancel.png"))
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        # Send button
        send_btn = QPushButton("Send Email")
        send_btn.setIcon(QIcon("static/icons/send.png"))
        send_btn.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold;")
        send_btn.clicked.connect(self.send_email)
        button_layout.addWidget(send_btn)
        
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
    
    def load_students(self):
        """Load students from database"""
        try:
            cursor = self.db_connection.cursor(dictionary=True)
            cursor.execute("""
                SELECT id, full_name, email, parent_email 
                FROM students 
                WHERE is_active = TRUE AND (email IS NOT NULL OR parent_email IS NOT NULL)
                ORDER BY full_name
            """)
            
            students = cursor.fetchall()
            
            for student in students:
                item_text = f"{student['full_name']}"
                if student['email']:
                    item_text += f" 📧 {student['email']}"
                if student['parent_email']:
                    item_text += f" 👨‍👩‍👧‍👦 {student['parent_email']}"
                
                item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, {
                    'id': student['id'],
                    'type': 'student',
                    'emails': [e for e in [student['email'], student['parent_email']] if e]
                })
                self.recipient_list.addItem(item)
                
        except Exception as e:
            print(f"Error loading students: {e}")
    
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
                item_text = f"{teacher['first_name']} {teacher['surname']}"
                if teacher['email']:
                    item_text += f" 📧 {teacher['email']}"
                
                item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, {
                    'id': teacher['id'],
                    'type': 'teacher',
                    'emails': [teacher['email']] if teacher['email'] else []
                })
                self.recipient_list.addItem(item)
                
        except Exception as e:
            print(f"Error loading teachers: {e}")
    
    def load_parents(self):
        """Load parents from database"""
        try:
            cursor = self.db_connection.cursor(dictionary=True)
            cursor.execute("""
                SELECT p.id, p.full_name, p.email, s.full_name as student_name
                FROM parents p
                JOIN students s ON p.student_id = s.id
                WHERE p.is_active = TRUE AND p.email IS NOT NULL
                ORDER BY p.full_name
            """)
            
            parents = cursor.fetchall()
            
            for parent in parents:
                item_text = f"{parent['full_name']} (Parent of {parent['student_name']})"
                if parent['email']:
                    item_text += f" 📧 {parent['email']}"
                
                item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, {
                    'id': parent['id'],
                    'type': 'parent',
                    'emails': [parent['email']] if parent['email'] else []
                })
                self.recipient_list.addItem(item)
                
        except Exception as e:
            print(f"Error loading parents: {e}")
    
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
        
        self.selection_label.setText(f"{selected_count} recipients selected ({total_emails} email addresses)")
    
    def add_attachment(self):
        """Add file attachment"""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "Select Files to Attach", "", "All Files (*)"
        )
        
        for file_path in file_paths:
            if os.path.exists(file_path):
                self.attachments.append(file_path)
                file_name = os.path.basename(file_path)
                self.attachment_list.addItem(QListWidgetItem(file_name))
    
    def clear_attachments(self):
        """Clear all attachments"""
        self.attachments.clear()
        self.attachment_list.clear()
    
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
        
        return True
    
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
            
            # Send test to yourself
            success, message = email_service.send_email(
                config['email_address'],
                f"TEST: {self.subject_edit.text()}",
                self.body_edit.toPlainText(),
                self.attachments,
                self.html_checkbox.isChecked()
            )
            
            if success:
                QMessageBox.information(self, "Test Sent", "Test email sent successfully to yourself!")
            else:
                QMessageBox.warning(self, "Test Failed", f"Failed to send test email: {message}")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to send test email: {str(e)}")
    
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
            
            success, message = email_service.send_email(
                selected_emails,
                self.subject_edit.text(),
                self.body_edit.toPlainText(),
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