# ui/email_config_dialog.py
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                              QLineEdit, QComboBox, QPushButton, QFormLayout,
                              QGroupBox, QMessageBox, QCheckBox)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QIcon

class EmailConfigDialog(QDialog):
    # Signal emitted when configuration is saved
    config_saved = Signal()
    
    def __init__(self, parent=None, db_connection=None):
        super().__init__(parent)
        self.db_connection = db_connection
        self.setWindowTitle("⚙️ Email Configuration")
        self.setMinimumSize(500, 400)
        
        self.setup_ui()
        self.load_config()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Header
        header_label = QLabel("Email Server Configuration")
        header_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #2c3e50;")
        layout.addWidget(header_label)
        
        # Email provider group
        provider_group = QGroupBox("Email Provider Settings")
        provider_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        provider_layout = QFormLayout(provider_group)
        provider_layout.setLabelAlignment(Qt.AlignRight)
        
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["Gmail", "Outlook", "Yahoo", "Custom"])
        provider_layout.addRow("Email Provider:", self.provider_combo)
        
        self.email_edit = QLineEdit()
        self.email_edit.setPlaceholderText("your.school@gmail.com")
        provider_layout.addRow("Email Address:", self.email_edit)
        
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setPlaceholderText("App Password (not your regular password)")
        provider_layout.addRow("Password:", self.password_edit)
        
        self.sender_edit = QLineEdit()
        self.sender_edit.setPlaceholderText("School Management System")
        provider_layout.addRow("Sender Name:", self.sender_edit)
        
        layout.addWidget(provider_group)
        
        # Custom SMTP group (hidden by default)
        self.smtp_group = QGroupBox("Custom SMTP Settings")
        self.smtp_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        smtp_layout = QFormLayout(self.smtp_group)
        smtp_layout.setLabelAlignment(Qt.AlignRight)
        
        self.smtp_server_edit = QLineEdit()
        self.smtp_server_edit.setPlaceholderText("smtp.yourserver.com")
        smtp_layout.addRow("SMTP Server:", self.smtp_server_edit)
        
        self.smtp_port_edit = QLineEdit()
        self.smtp_port_edit.setPlaceholderText("587")
        smtp_layout.addRow("SMTP Port:", self.smtp_port_edit)
        
        # ADD THESE NEW IMAP FIELDS FOR CUSTOM PROVIDERS:
        self.imap_server_edit = QLineEdit()
        self.imap_server_edit.setPlaceholderText("imap.yourserver.com")
        smtp_layout.addRow("IMAP Server:", self.imap_server_edit)
        
        self.imap_port_edit = QLineEdit()
        self.imap_port_edit.setPlaceholderText("993")
        smtp_layout.addRow("IMAP Port:", self.imap_port_edit)
        
        self.ssl_checkbox = QCheckBox("Use SSL/TLS")
        self.ssl_checkbox.setChecked(True)
        smtp_layout.addRow("Security:", self.ssl_checkbox)
        
        layout.addWidget(self.smtp_group)
        self.smtp_group.setVisible(False)
        
        # Show/hide custom SMTP based on provider selection
        self.provider_combo.currentTextChanged.connect(self.toggle_smtp_settings)
        
        # Help text
        help_label = QLabel(
            "💡 For Gmail/Outlook: Enable 2-factor authentication and generate an App Password. "
            "Do not use your regular password!"
        )
        help_label.setWordWrap(True)
        help_label.setStyleSheet("color: #7f8c8d; font-size: 11px; padding: 10px; background: #f8f9fa; border-radius: 5px;")
        layout.addWidget(help_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        test_btn = QPushButton("🔧 Test Connection")
        test_btn.setIcon(QIcon("static/icons/test.png"))
        test_btn.clicked.connect(self.test_connection)
        button_layout.addWidget(test_btn)
        
        button_layout.addStretch()
        
        cancel_btn = QPushButton("❌ Cancel")
        cancel_btn.setIcon(QIcon("static/icons/cancel.png"))
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        save_btn = QPushButton("💾 Save Configuration")
        save_btn.setIcon(QIcon("static/icons/save.png"))
        save_btn.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold;")
        save_btn.clicked.connect(self.save_config)
        button_layout.addWidget(save_btn)
        
        layout.addLayout(button_layout)
        
    def toggle_smtp_settings(self, provider):
        """Show/hide custom SMTP settings"""
        self.smtp_group.setVisible(provider == "Custom")
        
    def load_config(self):
        """Load existing email configuration"""
        try:
            if self.db_connection:
                cursor = self.db_connection.cursor(dictionary=True)
                cursor.execute("SELECT * FROM email_config WHERE is_active = TRUE LIMIT 1")
                config = cursor.fetchone()
                
                if config:
                    # Set provider (handle case sensitivity)
                    provider = config['email_provider'].capitalize()
                    if provider in ["Gmail", "Outlook", "Yahoo", "Custom"]:
                        self.provider_combo.setCurrentText(provider)
                    else:
                        self.provider_combo.setCurrentText("Custom")
                    
                    self.email_edit.setText(config['email_address'])
                    self.password_edit.setText(config['email_password'])
                    self.sender_edit.setText(config.get('default_sender_name', ''))
                    self.smtp_server_edit.setText(config.get('smtp_server', ''))
                    self.smtp_port_edit.setText(str(config.get('smtp_port', '')))
                    
                    # Show SMTP settings if using custom provider
                    if config['email_provider'].lower() == 'custom':
                        self.smtp_group.setVisible(True)
                    
        except Exception as e:
            print(f"Error loading email config: {e}")
            QMessageBox.warning(self, "Warning", "Could not load existing email configuration.")
            
    def validate_form(self):
        """Validate the configuration form"""
        if not self.email_edit.text().strip():
            QMessageBox.warning(self, "Validation", "Email address is required!")
            return False
            
        if not self.password_edit.text().strip():
            QMessageBox.warning(self, "Validation", "Password is required!")
            return False
            
        if self.provider_combo.currentText() == "Custom":
            if not self.smtp_server_edit.text().strip():
                QMessageBox.warning(self, "Validation", "SMTP server is required for custom configuration!")
                return False
            if not self.smtp_port_edit.text().strip():
                QMessageBox.warning(self, "Validation", "SMTP port is required!")
                return False
                
        return True
            
    # ui/email_config_dialog.py - Fixed save_config method
    def save_config(self):
        """Save email configuration to database"""
        if not self.validate_form():
            return
            
        try:
            provider = self.provider_combo.currentText().lower()
            email = self.email_edit.text().strip()
            password = self.password_edit.text().strip()
            sender = self.sender_edit.text().strip() or "School Management System"
            
            if self.db_connection:
                cursor = self.db_connection.cursor()
                
                # Deactivate any existing config
                cursor.execute("UPDATE email_config SET is_active = FALSE")
    
                # Get IMAP settings based on provider
                if provider == 'gmail':
                    imap_server = 'imap.gmail.com'
                    imap_port = 993
                    smtp_server = 'smtp.gmail.com'
                    smtp_port = 587
                elif provider == 'outlook':
                    imap_server = 'imap-mail.outlook.com'
                    imap_port = 993
                    smtp_server = 'smtp.office365.com'
                    smtp_port = 587
                elif provider == 'yahoo':
                    imap_server = 'imap.mail.yahoo.com'
                    imap_port = 993
                    smtp_server = 'smtp.mail.yahoo.com'
                    smtp_port = 587
                else:  # Custom
                    imap_server = self.smtp_server_edit.text().strip().replace('smtp', 'imap')
                    imap_port = 993
                    smtp_server = self.smtp_server_edit.text().strip()
                    smtp_port = int(self.smtp_port_edit.text() or 587)
                    
                # Insert new config - always store the actual server values
                cursor.execute("""
                    INSERT INTO email_config 
                    (email_provider, email_address, email_password, default_sender_name,
                     smtp_server, smtp_port, imap_server, imap_port, is_active)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    provider, email, password, sender,
                    smtp_server,  # Always store the server, don't set to None
                    smtp_port,
                    imap_server,
                    imap_port,
                    True
                ))
                
                self.db_connection.commit()
                
                # Emit signal that config was saved
                self.config_saved.emit()
                
                QMessageBox.information(self, "Success", 
                    "Email configuration saved successfully!\n\n"
                    "You can now send emails from the system."
                )
                self.accept()
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save configuration:\n{str(e)}")
            print(f"Database error: {e}")  # Debug info
            
    def test_connection(self):
        """Test email connection"""
        if not self.validate_form():
            return
            
        from services.email_service import EmailService
        
        try:
            # Create temporary config for testing
            test_config = {
                'email_provider': self.provider_combo.currentText().lower(),
                'email_address': self.email_edit.text().strip(),
                'email_password': self.password_edit.text().strip(),
                'default_sender_name': self.sender_edit.text().strip() or "Test Sender",
                'smtp_server': self.smtp_server_edit.text().strip(),
                'smtp_port': int(self.smtp_port_edit.text() or 587)
            }
            
            # Create test email service
            test_service = EmailService(self.db_connection)
            
            # Test with a simple email
            success, message = test_service.send_email(
                self.email_edit.text().strip(),  # Send test to yourself
                "✅ Test Email - School Management System",
                "This is a test email to verify your email configuration is working correctly.\n\n"
                "If you received this email, your configuration is working properly!\n\n"
                "You can now send emails to students, teachers, and parents from the system.",
                is_html=False
            )
            
            if success:
                QMessageBox.information(self, "Success", 
                    "Test email sent successfully!\n\n"
                    "Please check your inbox (and spam folder) for the test message."
                )
            else:
                QMessageBox.warning(self, "Test Failed", 
                    f"Failed to send test email:\n\n{message}\n\n"
                    "Please check your configuration:\n"
                    "• Email and password are correct\n"
                    "• App password is used (not regular password)\n"
                    "• 2-factor authentication is enabled\n"
                    "• SMTP settings are correct for custom providers"
                )
                
        except Exception as e:
            QMessageBox.critical(self, "Error", 
                f"Test failed unexpectedly:\n\n{str(e)}\n\n"
                "Please check your network connection and try again."
            )