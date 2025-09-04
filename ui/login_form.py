#login_form.py
import sys
import os
from typing import Optional, Dict, Any
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QMessageBox, QFrame, QApplication, QDialog
)
from PySide6.QtGui import QFont, QPixmap
from PySide6.QtCore import Qt, Signal
import mysql.connector
from mysql.connector import Error

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.models import get_db_connection
from utils.auth import verify_password
from utils.permissions import has_permission


class LoginForm(QDialog):
    login_successful = Signal(dict)  # Signal emitted with user session data

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("LoginForm")  # Set object name
        self.setup_ui()
        self.setup_styling()

    def setup_styling(self):
        self.setStyleSheet("""
            /* Set font on container for inheritance */
            QWidget#LoginForm {
                font-family: 'Segoe UI', 'Arial', sans-serif;
            }
    
            /* Set background on container */
            QWidget#LoginForm {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f1f5f9,
                    stop:1 #e2e8f0);
            }
    
            /* Now style the UI components */
            QFrame#login_frame {
                background-color: #ffffff;
                border-radius: 15px;
                border: 2px solid #cbd5e1;
            }
    
            QLabel {
                color: #1e293b;
                font-weight: 500;
            }
            
            QFrame#login_frame {
                background-color: #ffffff;
                border-radius: 15px;
                border: 2px solid #cbd5e1;
            }

            QLabel {
                color: #1e293b;
                font-weight: 500;
            }

            QLabel#title_label {
                font-size: 28px;
                font-weight: 700;
                color: #1e40af;
            }

            QLabel#subtitle_label {
                font-size: 14px;
                color: #64748b;
            }

            QLineEdit {
                background-color: #ffffff;
                border: 2px solid #cbd5e1;
                border-radius: 8px;
                padding: 12px 16px;
                font-size: 14px;
                color: #1e293b;
                selection-background-color: #10b981;
                selection-color: white;
            }

            QLineEdit:focus {
                border: 2px solid #3b82f6;
                background-color: #ffffff;
                outline: none;
            }

            QPushButton {
                background-color: #10b981;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 15px 25px;
                font-size: 16px;
                font-weight: 600;
            }

            QPushButton:hover {
                background-color: #059669;
            }

            QPushButton:pressed {
                background-color: #047857;
            }

            QPushButton#forgot_btn {
                background-color: transparent;
                color: #3b82f6;
                padding: 5px 10px;
                font-size: 12px;
                text-decoration: underline;
            }

            QPushButton#toggle_password {
                background-color: transparent;
                color: #64748b;
                font-size: 13px;
                text-decoration: none;
                padding: 0;
                border: none;
            }

            QPushButton#toggle_password:hover {
                color: #3b82f6;
                text-decoration: underline;
            }

            /* ✅ Custom QMessageBox Styling */
            QMessageBox {
                background-color: #ffffff;
                border: none;
            }

            QMessageBox QLabel {
                color: #1e293b;
                font-weight: 500;
                font-size: 15px;
            }

            QMessageBox QPushButton {
                background-color: #10b981;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: 600;
                min-width: 60px;
                min-height: 24px;
            }

            QMessageBox QPushButton:hover {
                background-color: #059669;
            }

            QMessageBox QPushButton:pressed {
                background-color: #047857;
            }

            QMessageBox QPushButton#qt_msgbox_button {
                margin: 0 4px;
            }
        """)
        
    def setup_ui(self):
        """Setup the login UI with centered layout and show/hide password"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(150, 40, 150, 40)
        main_layout.setAlignment(Qt.AlignCenter)

        # Login frame
        login_frame = QFrame()
        login_frame.setObjectName("login_frame")
        login_frame.setFixedSize(500, 600)

        frame_layout = QVBoxLayout(login_frame)
        frame_layout.setContentsMargins(40, 40, 40, 40)
        frame_layout.setSpacing(25)

        # Logo and title
        logo_layout = QVBoxLayout()
        logo_layout.setAlignment(Qt.AlignCenter)

        logo_label = QLabel()
        logo_path = "static/images/logo.png"
        if os.path.exists(logo_path):
            logo_label.setPixmap(QPixmap(logo_path).scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            logo_label.setText("📚")
            logo_label.setStyleSheet("font-size: 48px;")
        logo_label.setAlignment(Qt.AlignCenter)

        title_label = QLabel("CBCentra School Management")
        title_label.setObjectName("title_label")
        title_label.setAlignment(Qt.AlignCenter)

        subtitle_label = QLabel("Secure Login Portal")
        subtitle_label.setObjectName("subtitle_label")
        subtitle_label.setAlignment(Qt.AlignCenter)

        logo_layout.addWidget(logo_label)
        logo_layout.addWidget(title_label)
        logo_layout.addWidget(subtitle_label)
        frame_layout.addLayout(logo_layout)

        # Form fields
        form_layout = QVBoxLayout()
        form_layout.setSpacing(15)

        # Username
        username_label = QLabel("Username:")
        self.username_entry = QLineEdit()
        self.username_entry.setPlaceholderText("Enter your username")
        self.username_entry.setText("admin")  # Remove in production
        self.username_entry.setAttribute(Qt.WA_MacShowFocusRect, False)  # 🔥 Remove focus glow

        # Password
        password_label = QLabel("Password:")
        self.password_entry = QLineEdit()
        self.password_entry.setPlaceholderText("Enter your password")
        self.password_entry.setEchoMode(QLineEdit.Password)
        self.password_entry.setText("admin123")  # Remove in production
        self.password_entry.setAttribute(Qt.WA_MacShowFocusRect, False)  # 🔥 Remove focus glow

        # Toggle Show/Hide Password
        self.toggle_password_btn = QPushButton("Show Password")
        self.toggle_password_btn.setObjectName("toggle_password")
        self.toggle_password_btn.setCheckable(True)
        self.toggle_password_btn.setChecked(False)
        self.toggle_password_btn.clicked.connect(self.toggle_password_visibility)

        # Layout for password field + toggle
        password_row = QHBoxLayout()
        password_row.addWidget(self.password_entry)
        password_row.addWidget(self.toggle_password_btn)

        form_layout.addWidget(username_label)
        form_layout.addWidget(self.username_entry)
        form_layout.addWidget(password_label)
        form_layout.addLayout(password_row)

        frame_layout.addLayout(form_layout)

        # Forgot password
        forgot_layout = QHBoxLayout()
        forgot_layout.addStretch()
        forgot_btn = QPushButton("Forgot Password?")
        forgot_btn.setObjectName("forgot_btn")
        forgot_btn.clicked.connect(self.on_forgot_password)
        forgot_layout.addWidget(forgot_btn)
        frame_layout.addLayout(forgot_layout)

        # Login button
        login_btn = QPushButton("Login to System")
        login_btn.clicked.connect(self.on_login_attempt)
        frame_layout.addWidget(login_btn)

        # Enter key support
        self.password_entry.returnPressed.connect(login_btn.click)

        # Add frame to main layout (centered)
        main_layout.addWidget(login_frame, alignment=Qt.AlignCenter)

    def toggle_password_visibility(self):
        """Toggle password visibility"""
        if self.toggle_password_btn.isChecked():
            self.password_entry.setEchoMode(QLineEdit.Normal)
            self.toggle_password_btn.setText("Hide Password")
        else:
            self.password_entry.setEchoMode(QLineEdit.Password)
            self.toggle_password_btn.setText("Show Password")

    def on_login_attempt(self):
        """Handle login attempt"""
        username = self.username_entry.text().strip()
        password = self.password_entry.text().strip()
    
        if not username or not password:
            QMessageBox.warning(self, "Login Failed", "Please enter both username and password")
            return
    
        connection = None
        cursor = None
    
        try:
            connection = get_db_connection()
            if not connection:
                QMessageBox.critical(self, "Database Error", "Cannot connect to database")
                return
    
            cursor = connection.cursor(dictionary=True)
            query = """
                SELECT u.*, s.school_name 
                FROM users u 
                LEFT JOIN schools s ON u.school_id = s.id 
                WHERE u.username = %s
            """
            cursor.execute(query, (username,))
            user = cursor.fetchone()
    
            # Get teacher photo and position if available
            photo_path = None
            position = 'N/A'
            if user:
                teacher_query = """
                    SELECT position, photo_path 
                    FROM teachers 
                    WHERE full_name = %s OR email = %s
                """
                cursor.execute(teacher_query, (user.get('full_name'), user.get('username')))
                teacher = cursor.fetchone()
                if teacher:
                    photo_path = teacher['photo_path']
                    position = teacher['position']
    
            if not user:
                try:
                    self.log_login_attempt(username, "failed", "User not found")
                except Exception as e:
                    print(f"Failed to log login attempt: {e}")
                QMessageBox.warning(self, "Login Failed", "Invalid username")
                return
    
            if user.get('is_active') is not None and not user['is_active']:
                QMessageBox.warning(self, "Login Failed", "Account is disabled")
                return
    
            # Verify password
            stored_password = user.get('password_hash', user.get('password', ''))
            password_valid = False
            try:
                password_valid = verify_password(password, stored_password)
            except Exception as e:
                print(f"Password verification error: {e}")
                password_valid = (password == stored_password)
    
            if not password_valid:
                try:
                    self.update_failed_attempts(user['id'])
                    self.log_login_attempt(user['id'], "failed", "Wrong password")
                except Exception as e:
                    print(f"Failed to update login attempts: {e}")
                QMessageBox.warning(self, "Login Failed", "Invalid password")
                return
    
            # Check if account is locked
            if user.get('account_locked_until') and user['account_locked_until'] > datetime.now():
                lock_time = user['account_locked_until'].strftime("%Y-%m-%d %H:%M:%S")
                QMessageBox.warning(
                    self, "Account Locked",
                    f"Account is locked until {lock_time}. Please contact administrator."
                )
                return
    
            # Reset failed attempts and update login info
            try:
                self.reset_failed_attempts(user['id'])
                self.update_last_login(user['id'])
                self.log_login_attempt(user['id'], "success", "Login successful")
            except Exception as e:
                print(f"Failed to update login metadata: {e}")
    
            # ✅ Build user session
            user_session = {
                'user_id': int(user['id']) if user['id'] is not None else None,
                'username': str(user['username']) if user['username'] else '',
                'full_name': str(user.get('full_name', user['username'])) if user.get('full_name') else str(user['username']),
                'role': str(user.get('role', 'user')),
                'school_id': int(user['school_id']) if user.get('school_id') is not None else None,
                'school_name': str(user.get('school_name', 'No School Assigned')),
                'permissions': self.get_user_permissions(user.get('role', 'user')),
                'login_time': datetime.now().isoformat(),
                'ip_address': str(self.get_client_ip()),
                'position': position,
                'profile_image': photo_path
            }
    
            print(f"✅ Login successful for user: {user_session['username']}")
    
            # ✅ Emit session
            try:
                self.login_successful.emit(user_session)
            except Exception as e:
                print(f"Signal emission error: {e}")
                # Fallback minimal session
                fallback_session = {
                    'user_id': user['id'],
                    'username': user['username'],
                    'full_name': user.get('full_name', user['username']),
                    'role': user.get('role', 'user')
                }
                self.login_successful.emit(fallback_session)
    
            # ✅ Close dialog — this returns 1 from exec()
            self.accept()
    
        except Error as e:
            print(f"❌ Database error: {e}")
            QMessageBox.critical(self, "Database Error", f"Login failed: {str(e)}")
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            QMessageBox.critical(self, "Unexpected Error", f"An unexpected error occurred: {str(e)}")
        finally:
            # Clean up DB resources
            if cursor:
                try:
                    cursor.close()
                except:
                    pass
            if connection and connection.is_connected():
                try:
                    connection.close()
                except:
                    pass
                
    def get_user_permissions(self, role):
        try:
            from utils.permissions import get_role_permissions
            permissions = get_role_permissions(role)
            return [str(p) for p in permissions] if permissions else []
        except Exception as e:
            print(f"Error getting permissions: {e}")
            if role == 'admin':
                return ['view_all_data', 'edit_all_data', 'create_user', 'delete_user']
            elif role == 'headteacher':
                return ['view_academic_data', 'edit_academic_data']
            else:
                return ['view_own_profile']

    def update_failed_attempts(self, user_id):
        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            cursor.execute("DESCRIBE users")
            columns = [col[0] for col in cursor.fetchall()]
            if 'failed_login_attempts' in columns:
                query = "UPDATE users SET failed_login_attempts = failed_login_attempts + 1 WHERE id = %s"
                cursor.execute(query, (user_id,))
                if 'account_locked_until' in columns:
                    lock_query = """
                        UPDATE users 
                        SET account_locked_until = DATE_ADD(NOW(), INTERVAL 1 HOUR)
                        WHERE id = %s AND failed_login_attempts >= 5
                    """
                    cursor.execute(lock_query, (user_id,))
                connection.commit()
            cursor.close()
            connection.close()
        except Error:
            pass

    def reset_failed_attempts(self, user_id):
        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            cursor.execute("DESCRIBE users")
            columns = [col[0] for col in cursor.fetchall()]
            update_parts = []
            if 'failed_login_attempts' in columns:
                update_parts.append("failed_login_attempts = 0")
            if 'account_locked_until' in columns:
                update_parts.append("account_locked_until = NULL")
            if update_parts:
                query = f"UPDATE users SET {', '.join(update_parts)} WHERE id = %s"
                cursor.execute(query, (user_id,))
                connection.commit()
            cursor.close()
            connection.close()
        except Error:
            pass

    def update_last_login(self, user_id):
        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            cursor.execute("DESCRIBE users")
            columns = [col[0] for col in cursor.fetchall()]
            if 'last_login' in columns:
                query = "UPDATE users SET last_login = NOW() WHERE id = %s"
                cursor.execute(query, (user_id,))
                connection.commit()
            cursor.close()
            connection.close()
        except Error:
            pass

    def log_login_attempt(self, user_identifier, status, reason):
        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            cursor.execute("SHOW TABLES LIKE 'login_logs'")
            if not cursor.fetchone():
                cursor.close()
                connection.close()
                return
            if isinstance(user_identifier, int):
                query = """
                    INSERT INTO login_logs (user_id, login_status, failure_reason, ip_address)
                    VALUES (%s, %s, %s, %s)
                """
                params = (user_identifier, status, reason, self.get_client_ip())
            else:
                query = """
                    INSERT INTO login_logs (login_status, failure_reason, ip_address, user_agent)
                    VALUES (%s, %s, %s, %s)
                """
                params = (status, reason, self.get_client_ip(), "Login Form")
            cursor.execute(query, params)
            connection.commit()
            cursor.close()
            connection.close()
        except Error as e:
            print(f"Failed to log login attempt: {e}")

    def get_client_ip(self):
        return "127.0.0.1"

    def on_forgot_password(self):
        QMessageBox.information(self, "Forgot Password",
                              "Please contact your system administrator to reset your password.")


# Example usage
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = QWidget()
    layout = QVBoxLayout(window)
    login_form = LoginForm()
    login_form.login_successful.connect(lambda session: print("Logged in:", session))
    layout.addWidget(login_form)
    window.setWindowTitle("CBCentra Login")
    window.resize(1024, 768)
    window.show()
    sys.exit(app.exec())