# ui/email_config_dialog.py
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                              QLineEdit, QComboBox, QPushButton, QFormLayout,
                              QGroupBox, QMessageBox, QCheckBox, QSpinBox, QTabWidget, QWidget)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon

class EmailConfigDialog(QDialog):
    # Signal emitted when configuration is saved
    config_saved = Signal()
    
    def __init__(self, parent=None, db_connection=None):
        super().__init__(parent)
        self.db_connection = db_connection
        self.setWindowTitle("⚙️ Email Configuration")
        self.setMinimumSize(600, 500)
        
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
        
        # Tab widget for different sections
        tab_widget = QTabWidget()
        
        # Basic Settings Tab
        basic_tab = QWidget()
        basic_layout = QVBoxLayout(basic_tab)
        
        # Email provider group
        provider_group = QGroupBox("Email Provider Settings")
        provider_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        provider_layout = QFormLayout(provider_group)
        provider_layout.setLabelAlignment(Qt.AlignRight)
        
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["Gmail", "Outlook", "Yahoo", "Custom"])
        self.provider_combo.currentTextChanged.connect(self.on_provider_changed)
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
        
        basic_layout.addWidget(provider_group)
        basic_layout.addStretch()
        
        # SMTP Settings Tab (for sending)
        smtp_tab = QWidget()
        smtp_layout = QVBoxLayout(smtp_tab)
        
        smtp_group = QGroupBox("SMTP Settings (Sending Emails)")
        smtp_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        smtp_form = QFormLayout(smtp_group)
        
        self.smtp_server_edit = QLineEdit()
        self.smtp_server_edit.setPlaceholderText("smtp.gmail.com")
        smtp_form.addRow("SMTP Server:", self.smtp_server_edit)
        
        self.smtp_port_spin = QSpinBox()
        self.smtp_port_spin.setRange(1, 65535)
        self.smtp_port_spin.setValue(587)
        smtp_form.addRow("SMTP Port:", self.smtp_port_spin)
        
        self.smtp_ssl_check = QCheckBox("Use SSL/TLS")
        self.smtp_ssl_check.setChecked(True)
        smtp_form.addRow("Security:", self.smtp_ssl_check)
        
        smtp_layout.addWidget(smtp_group)
        smtp_layout.addStretch()
        
        # IMAP Settings Tab (for receiving)
        imap_tab = QWidget()
        imap_layout = QVBoxLayout(imap_tab)
        
        imap_group = QGroupBox("IMAP Settings (Receiving Emails)")
        imap_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        imap_form = QFormLayout(imap_group)
        
        self.imap_server_edit = QLineEdit()
        self.imap_server_edit.setPlaceholderText("imap.gmail.com")
        imap_form.addRow("IMAP Server:", self.imap_server_edit)
        
        self.imap_port_spin = QSpinBox()
        self.imap_port_spin.setRange(1, 65535)
        self.imap_port_spin.setValue(993)
        imap_form.addRow("IMAP Port:", self.imap_port_spin)
        
        self.imap_ssl_check = QCheckBox("Use SSL/TLS")
        self.imap_ssl_check.setChecked(True)
        imap_form.addRow("Security:", self.imap_ssl_check)
        
        # Check interval
        self.check_interval_spin = QSpinBox()
        self.check_interval_spin.setRange(1, 60)
        self.check_interval_spin.setValue(10)
        self.check_interval_spin.setSuffix(" minutes")
        imap_form.addRow("Check Interval:", self.check_interval_spin)
        
        imap_layout.addWidget(imap_group)
        imap_layout.addStretch()
        
        # Add tabs
        tab_widget.addTab(basic_tab, "Basic")
        tab_widget.addTab(smtp_tab, "SMTP (Sending)")
        tab_widget.addTab(imap_tab, "IMAP (Receiving)")
        
        layout.addWidget(tab_widget)
        
        # Help text
        help_label = QLabel(
            "💡 For Gmail/Outlook: Enable 2-factor authentication and generate an App Password. "
            "Do not use your regular password! IMAP must be enabled in your email account settings."
        )
        help_label.setWordWrap(True)
        help_label.setStyleSheet("color: #7f8c8d; font-size: 11px; padding: 10px; background: #f8f9fa; border-radius: 5px;")
        layout.addWidget(help_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        test_btn = QPushButton("Test Connection")
        test_btn.setIcon(QIcon("static/icons/test.png"))
        test_btn.clicked.connect(self.test_connection)
        button_layout.addWidget(test_btn)
        
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setIcon(QIcon("static/icons/cancel.png"))
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        save_btn = QPushButton("Save Configuration")
        save_btn.setIcon(QIcon("static/icons/save.png"))
        save_btn.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold;")
        save_btn.clicked.connect(self.save_config)
        button_layout.addWidget(save_btn)
        
        layout.addLayout(button_layout)
        
    def on_provider_changed(self, provider):
        """Auto-fill settings based on provider"""
        provider = provider.lower()
        
        if provider == "gmail":
            self.smtp_server_edit.setText("smtp.gmail.com")
            self.smtp_port_spin.setValue(587)
            self.imap_server_edit.setText("imap.gmail.com")
            self.imap_port_spin.setValue(993)
            self.smtp_ssl_check.setChecked(True)
            self.imap_ssl_check.setChecked(True)
            
        elif provider == "outlook":
            self.smtp_server_edit.setText("smtp.office365.com")
            self.smtp_port_spin.setValue(587)
            self.imap_server_edit.setText("imap-mail.outlook.com")
            self.imap_port_spin.setValue(993)
            self.smtp_ssl_check.setChecked(True)
            self.imap_ssl_check.setChecked(True)
            
        elif provider == "yahoo":
            self.smtp_server_edit.setText("smtp.mail.yahoo.com")
            self.smtp_port_spin.setValue(587)
            self.imap_server_edit.setText("imap.mail.yahoo.com")
            self.imap_port_spin.setValue(993)
            self.smtp_ssl_check.setChecked(True)
            self.imap_ssl_check.setChecked(True)
        
    def load_config(self):
        """Load existing email configuration"""
        try:
            if self.db_connection:
                cursor = self.db_connection.cursor(dictionary=True)
                cursor.execute("SELECT * FROM email_config WHERE is_active = TRUE LIMIT 1")
                config = cursor.fetchone()
                
                if config:
                    # Set provider
                    provider = config['email_provider'].capitalize()
                    if provider in ["Gmail", "Outlook", "Yahoo", "Custom"]:
                        self.provider_combo.setCurrentText(provider)
                    else:
                        self.provider_combo.setCurrentText("Custom")
                    
                    self.email_edit.setText(config['email_address'])
                    self.password_edit.setText(config['email_password'])
                    self.sender_edit.setText(config.get('default_sender_name', ''))
                    
                    # Load server settings
                    self.smtp_server_edit.setText(config.get('smtp_server', ''))
                    self.smtp_port_spin.setValue(config.get('smtp_port', 587))
                    self.smtp_ssl_check.setChecked(config.get('smtp_use_ssl', True))
                    
                    self.imap_server_edit.setText(config.get('imap_server', ''))
                    self.imap_port_spin.setValue(config.get('imap_port', 993))
                    self.imap_ssl_check.setChecked(config.get('imap_use_ssl', True))
                    
                    self.check_interval_spin.setValue(config.get('check_interval', 10))
                    
        except Exception as e:
            print(f"Error loading email config: {e}")
            
    def save_config(self):
        """Save email configuration to database - use school name only, no hardcoded fallback"""
        if not self.validate_form():
            return
            
        try:
            provider = self.provider_combo.currentText().lower()
            email = self.email_edit.text().strip()
            password = self.password_edit.text().strip()
            
            # Get sender name: use custom name or fetch school name from database
            sender_name = self.sender_edit.text().strip()
            if not sender_name:
                # Fetch school name from database - NO HARDCODED FALLBACK
                sender_name = self.get_school_name()
                if not sender_name:
                    # If no school name found, show error instead of using generic fallback
                    QMessageBox.warning(self, "Configuration Error", 
                        "No school name found in database. Please enter a sender name or add a school first."
                    )
                    return
            
            if self.db_connection:
                cursor = self.db_connection.cursor()
                
                # Deactivate any existing config
                cursor.execute("UPDATE email_config SET is_active = FALSE")
    
                # Get settings based on provider
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
                    imap_server = self.imap_server_edit.text().strip()
                    imap_port = self.imap_port_spin.value()
                    smtp_server = self.smtp_server_edit.text().strip()
                    smtp_port = self.smtp_port_spin.value()
                    
                # Insert new config
                cursor.execute("""
                    INSERT INTO email_config 
                    (email_provider, email_address, email_password, default_sender_name,
                     smtp_server, smtp_port, smtp_use_ssl,
                     imap_server, imap_port, imap_use_ssl,
                     check_interval, is_active)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    provider, email, password, sender_name,
                    smtp_server,
                    smtp_port,
                    self.smtp_ssl_check.isChecked(),
                    imap_server,
                    imap_port,
                    self.imap_ssl_check.isChecked(),
                    self.check_interval_spin.value(),
                    True
                ))
                
                self.db_connection.commit()
                
                # Emit signal that config was saved
                self.config_saved.emit()
                
                QMessageBox.information(self, "Success", 
                    f"Email configuration saved successfully!\n\n"
                    f"Sender name: {sender_name}\n"
                    "You can now send and receive emails from the system."
                )
                self.accept()
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save configuration:\n{str(e)}")
            print(f"Database error: {e}")
    
    def get_school_name(self):
        """Fetch school name from the schools table - returns None if no school found"""
        try:
            if self.db_connection:
                cursor = self.db_connection.cursor(dictionary=True)
                # Get the first active school
                cursor.execute("""
                    SELECT school_name FROM schools 
                    WHERE is_active = TRUE 
                    ORDER BY id LIMIT 1
                """)
                school = cursor.fetchone()
                return school['school_name'] if school else None
        except Exception as e:
            print(f"Error fetching school name: {e}")
            return None
        return None
    
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
                QMessageBox.warning(self, "Validation", "SMTP server is required!")
                return False
            if not self.imap_server_edit.text().strip():
                QMessageBox.warning(self, "Validation", "IMAP server is required!")
                return False
                
        return True
            
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
            

            