# ui/main_window.py
import os
from PySide6.QtWidgets import (
    QMainWindow, QMessageBox, QToolBar, QWidget,
    QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFrame, QStackedWidget,
    QSizePolicy, QScrollArea, QTabWidget, QInputDialog, QGraphicsDropShadowEffect,
    QDialog, QFileDialog, QGroupBox, QRadioButton, QComboBox, QProgressDialog, QLineEdit,
    QButtonGroup
)
from datetime import datetime
from PySide6.QtGui import QIcon, QPixmap, QPainter, QBrush, QColor, QLinearGradient, QAction, QFont, QCursor 
from PySide6.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve, QRect, Signal
from PySide6.QtCore import QBuffer, QByteArray, QIODevice
from PySide6.QtPrintSupport import QPrinter, QPrintPreviewDialog, QPrintPreviewWidget, QPrintDialog
from PySide6.QtPdf import QPdfDocument

# Import your UI forms
from ui.schools_form import SchoolsForm
from ui.users_form import UsersForm
from ui.teachers_form import TeachersForm
from ui.login_logs_form import LoginLogsForm
from ui.audit_logs_form import AuditLogsForm
from ui.audit_base_form import AuditBaseForm
from ui.students_form import StudentsForm
from ui.parents_form import ParentsForm

# Import the new ribbon components
from ui.ribbon_manager import RibbonManager
from ui.ribbon_handlers import RibbonHandlers

from utils.permissions import has_permission
from fpdf import FPDF
from docx import Document
import tempfile
import csv

class MainWindow(QMainWindow):
    # Signals
    logout_requested = Signal()
    user_session_updated = Signal(dict)
    
    def __init__(self, config=None, parent=None, user_session=None, db_connection=None, app_paths=None):
        super().__init__(parent)
        
        # Store instance variables
        self.user_session = user_session or {}
        self.app_config = config or {}
        self.db_connection = db_connection
        self.app_paths = app_paths or {}
        
        # Create AuditBaseForm instance for styling and utilities
        self.audit_base = AuditBaseForm(user_session=user_session)
        
        # Inherit all styling from AuditBaseForm
        self.setStyleSheet(self.audit_base.styleSheet())
        self.colors = self.audit_base.colors
        self.fonts = self.audit_base.fonts
        
        # Store reference to audit methods
        self.log_audit_action = self.audit_base.log_audit_action
        self.export_with_green_header = self.audit_base.export_with_green_header
        self.get_school_info = self.audit_base.get_school_info
        
        # Initialize ribbon components AFTER setting up colors and fonts
        self.ribbon_manager = RibbonManager(self)
        self.ribbon_handlers = RibbonHandlers(self)
        
        # Use the passed parameters
        self.app_config = config or {
            'name': 'CBCentra School Management System',
            'window_title': 'CBCentra SMS Desktop', 
            'min_size': (1024, 768),
            'default_size': (1200, 700)
        }
        
        # Ensure user_session is properly set up
        if isinstance(user_session, dict):
            self.user_session = user_session.copy()
        else:
            # Use safe fallback session
            self.user_session = {
                'user_id': 1,
                'username': 'admin',
                'role': 'admin', 
                'full_name': 'System Administrator',
                'ip_address': '127.0.0.1',
                'permissions': [
                    'view_all_data', 'edit_all_data', 'create_user', 'delete_user',
                    'view_login_logs', 'view_audit_logs', 'export_all_data',
                    'manage_system_settings', 'backup_database'
                ]
            }
        
        # Auto-generate permissions if missing
        if 'permissions' not in self.user_session or self.user_session['permissions'] is None:
            try:
                from utils.permissions import get_role_permissions
                role = self.user_session.get('role', 'user')
                self.user_session['permissions'] = get_role_permissions(role)
                print(f"Permissions auto-generated for role '{role}': {self.user_session['permissions']}")
            except Exception as e:
                print(f"Failed to load permissions: {e}")
                self.user_session['permissions'] = ['view_own_profile'] if self.user_session.get('role') != 'admin' else [
                    'view_login_logs', 'view_audit_logs', 'view_all_data'
                ]
        
        self.db_connection = db_connection
        self.app_paths = app_paths or {
            'icons': 'static/icons',
            'images': 'static/images',
            'app_icon': 'static/images/programlogo.png'
        }
        
        self.sidebar_visible = False
        self.ribbon_visible = True
        self.current_pdf_bytes = None
        self.current_file_path = None
        self.current_file_type = None

        self.init_ui()
        self.setup_window()
        
    def setup_window(self):
        self.setWindowTitle(self.app_config['window_title'])
        self.setGeometry(100, 100, *self.app_config['default_size'])
        self.setMinimumSize(*self.app_config['min_size'])
        if os.path.exists(self.app_paths['app_icon']):
            self.setWindowIcon(QIcon(self.app_paths['app_icon']))
    
    def init_ui(self):
        self.create_main_tabs()
        # Use the ribbon manager to create ribbon panel
        self.ribbon_manager.create_ribbon_panel()
        self.create_sidebar()
        
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)
        self.create_content_pages()
        
        # Update status bar with user info
        user_info = f"Ready - CBCentra School Management System | User: {self.user_session.get('full_name', 'Unknown')}"
        self.statusBar().showMessage(user_info)
    
        self.sidebar_animation = QPropertyAnimation(self.sidebar_frame, b"geometry")
        self.sidebar_animation.setDuration(300)
        self.sidebar_animation.setEasingCurve(QEasingCurve.OutCubic)
    
        self.overlay_animation = QPropertyAnimation(self.sidebar_overlay, b"windowOpacity")
        self.overlay_animation.setDuration(300)
        
        # Update UI for current user session
        self.update_ui_for_user_session()

    def toggle_ribbon(self):
        """Toggle ribbon visibility - now delegates to ribbon manager"""
        self.ribbon_manager.toggle_ribbon_visibility()
    
    def update_ribbon_panel(self, main_tab):
        """Update ribbon panel - now delegates to ribbon manager"""
        self.ribbon_manager.update_ribbon_panel(main_tab)

    # === DELEGATE RIBBON ACTIONS TO HANDLERS ===
    # User Management Actions
    def add_new_user(self):
        return self.ribbon_handlers.add_new_user()
    
    def refresh_user_data(self):
        return self.ribbon_handlers.refresh_user_data()
    
    def execute_user_export_dialog(self):
        return self.ribbon_handlers.execute_user_export_dialog()

    # Staff/Teachers Actions  
    def show_teachers_form(self):
        return self.ribbon_handlers.show_teachers_form()
    
    def add_new_teacher(self):
        return self.ribbon_handlers.add_new_teacher()
    
    def export_teachers_data(self):
        return self.ribbon_handlers.export_teachers_data()
    
    def import_teachers_data(self):
        return self.ribbon_handlers.import_teachers_data()
    
    def generate_teacher_summary(self):
        return self.ribbon_handlers.generate_teacher_summary()
    
    def refresh_teachers_data(self):
        return self.ribbon_handlers.refresh_teachers_data()
    
    def generate_teacher_profile(self):
        return self.ribbon_handlers.generate_teacher_profile()

    # Parents Actions
    def show_parents_form(self):
        return self.ribbon_handlers.show_parents_form()
    
    def add_new_parent(self):
        return self.ribbon_handlers.add_new_parent()
    
    def refresh_parents_data(self):
        return self.ribbon_handlers.refresh_parents_data()
    
    def import_parents_data(self):
        return self.ribbon_handlers.import_parents_data()
    
    def generate_parent_summary(self):
        return self.ribbon_handlers.generate_parent_summary()
    
    def generate_parent_profile(self):
        return self.ribbon_handlers.generate_parent_profile()
    
    def search_parents(self):
        return self.ribbon_handlers.search_parents()
    
    def manage_parent_contacts(self):
        return self.ribbon_handlers.manage_parent_contacts()
    
    def view_parent_children(self):
        return self.ribbon_handlers.view_parent_children()
    
    def backup_parent_data(self):
        return self.ribbon_handlers.backup_parent_data()
    
    def validate_parent_data(self):
        return self.ribbon_handlers.validate_parent_data()

    # Security & Reports Actions
    def show_login_logs(self):
        return self.ribbon_handlers.show_login_logs()
    
    def show_audit_logs(self):
        return self.ribbon_handlers.show_audit_logs()
    
    def generate_security_report(self):
        return self.ribbon_handlers.generate_security_report()

    # Global System Actions
    def refresh_all_data(self):
        return self.ribbon_handlers.refresh_all_data()
    
    def settings_action(self):
        return self.ribbon_handlers.settings_action()
    
    def new_action(self):
        return self.ribbon_handlers.new_action()
    
    def open_action(self):
        return self.ribbon_handlers.open_action()
    
    def print_action(self):
        return self.ribbon_handlers.print_action()


     #methods in mainwindow
    def safe_disconnect(self, signal, slot):
        try:
            signal.disconnect(slot)
        except (RuntimeWarning, RuntimeError, TypeError):
            pass

    # Add this method to your MainWindow class in ui/main_window.py
    def update_user_session(self, new_session_data):
        """Update user session data - CORRECTED METHOD"""
        if isinstance(new_session_data, dict):
            # Update the dictionary directly
            self.user_session.update(new_session_data)
        else:
            # Replace entire session
            self.user_session = new_session_data
        
        # Update UI elements that depend on user session
        self.update_ui_for_user_session()
        self.update_profile_picture()
        self.update_profile_tooltip()
        
        # Emit signal to notify other components
        self.user_session_updated.emit(self.user_session.copy())
        
    def get_user_session(self):
        """Get copy of current user session"""
        return self.user_session.copy() if self.user_session else {}
    
    def update_ui_for_user_session(self):
        """Update UI based on current user session"""
        if not self.user_session:
            return
            
        # Update window title
        username = self.user_session.get('username', 'User')
        title = f"{self.app_config.get('window_title', 'CBCentra')} - {username}"
        self.setWindowTitle(title)
        
        # Update status bar
        if hasattr(self, 'statusBar'):
            user_info = f"Logged in as: {self.user_session.get('full_name', 'User')} ({self.user_session.get('role', 'Unknown')})"
            self.statusBar().showMessage(user_info)
        
        # Update any UI labels that show user info
        if hasattr(self, 'user_name_label'):
            self.user_name_label.setText(self.user_session.get('full_name', 'User'))
            
        if hasattr(self, 'user_role_label'):
            self.user_role_label.setText(self.user_session.get('role', 'User'))
            
    def update_profile_picture(self):
        """Update profile picture when session changes"""
        if not hasattr(self, 'profile_pic'):
            return
    
        size = 36
        profile_pixmap = None
        profile_image_path = self.user_session.get('profile_image')
    
        if profile_image_path:
            full_path = os.path.join("static", profile_image_path.lstrip("/\\"))
            if os.path.exists(full_path):
                profile_pixmap = QPixmap(full_path)
    
        if not profile_pixmap or profile_pixmap.isNull():
            fallback_path = "static/icons/profile.png"
            if os.path.exists(fallback_path):
                profile_pixmap = QPixmap(fallback_path)
    
        if profile_pixmap and not profile_pixmap.isNull():
            circular_pixmap = self.create_circular_pixmap(profile_pixmap, size)
            self.profile_pic.setPixmap(circular_pixmap)
        else:
            self.profile_pic.setPixmap(self.create_profile_placeholder(size))
        
    
    def on_logout(self):
        """Handle logout request"""
        reply = QMessageBox.question(
            self,
            "Confirm Logout", 
            "Are you sure you want to logout?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.logout_requested.emit()

    def toggle_sidebar(self):
        self.safe_disconnect(self.overlay_animation.finished, self.sidebar_overlay.hide)
        self.safe_disconnect(self.sidebar_animation.finished, self.sidebar_frame.hide)

        if self.sidebar_visible:
            self.sidebar_animation.setStartValue(QRect(0, 80, 300, self.sidebar_frame.height()))
            self.sidebar_animation.setEndValue(QRect(-300, 80, 300, self.sidebar_frame.height()))
            self.overlay_animation.setStartValue(1.0)
            self.overlay_animation.setEndValue(0.0)
            self.overlay_animation.finished.connect(lambda: self.sidebar_overlay.hide())
            self.sidebar_animation.finished.connect(lambda: self.sidebar_frame.hide())
            self.sidebar_visible = False
            if self.tab_buttons:
                self.tab_buttons[0].setChecked(False)
        else:
            self.sidebar_overlay.setGeometry(0, 0, self.width(), self.height())
            self.sidebar_overlay.show()
            self.sidebar_overlay.raise_()
            self.overlay_animation.setStartValue(0.0)
            self.overlay_animation.setEndValue(1.0)
            self.sidebar_frame.show()
            self.sidebar_frame.raise_()
            for child in self.findChildren(QWidget):
                if child not in [self.sidebar_frame, self.sidebar_overlay]:
                    child.stackUnder(self.sidebar_overlay)
            self.sidebar_animation.setStartValue(QRect(-300, 80, 300, self.sidebar_frame.height()))
            self.sidebar_animation.setEndValue(QRect(0, 80, 300, self.sidebar_frame.height()))
            self.sidebar_visible = True
            if self.tab_buttons:
                self.tab_buttons[0].setChecked(True)
        self.sidebar_animation.start()
        self.overlay_animation.start()

    # In your MainWindow class, replace the PDF-related methods with these:
    
    def show_pdf_preview_dialog(self, pdf_bytes):
        """Show PDF using the new viewer"""
        try:
            from utils.pdf_utils import view_pdf
            view_pdf(pdf_bytes, parent=self)
        except ImportError:
            # Fallback if utils module is not available
            QMessageBox.critical(self, "Error", "PDF viewer utilities not available")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to show PDF: {str(e)}")
    
    def preview_pdf_bytes(self, pdf_bytes):
        """Preview PDF bytes - alias for show_pdf_preview_dialog"""
        self.show_pdf_preview_dialog(pdf_bytes)
    
    # Update your file open methods to use the new viewer:
    def open_preview_pdf(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select PDF file", "", "PDF Files (*.pdf)")
        if file_path:
            try:
                with open(file_path, "rb") as f:
                    pdf_bytes = f.read()
                self.current_pdf_bytes = pdf_bytes
                self.current_file_path = file_path
                self.current_file_type = "pdf"
                self.show_pdf_preview_dialog(pdf_bytes)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to open PDF: {str(e)}")

    def ask_page_range(self, max_pages):
        """Ask user for page range to print"""
        text, ok = QInputDialog.getText(
            self, "Page Range",
            f"Enter pages to print (1-{max_pages}), e.g., 1-{max_pages} or 1-3 or 2",
            text=f"1-{max_pages}"
        )
        if ok:
            try:
                if '-' in text:
                    start_str, end_str = text.split('-')
                    start, end = int(start_str) - 1, int(end_str)
                else:
                    start = int(text) - 1
                    end = start + 1
                if start < 0 or end > max_pages or start >= end:
                    raise ValueError("Invalid page range")
                return start, end
            except Exception:
                QMessageBox.warning(self, "Invalid Input", "Please enter a valid page range (e.g. 1-3)")
        return None, None

    # --- your existing UI, ribbon, sidebar, main tabs, and other methods follow here -

    def create_profile_section(self):
        """Create a modern profile section with user name, profile pic, and ribbon toggle."""
        size = 36  # profile pic size
    
        # --- Container for profile elements ---
        profile_container = QWidget()
        profile_container.setObjectName("profileContainer")
        profile_container.setStyleSheet("""
            QWidget#profileContainer {
                background: transparent;
                border: none;
                margin: 0px;
                padding: 0px;
            }
        """)
        profile_layout = QHBoxLayout(profile_container)
        profile_layout.setContentsMargins(0, 0, 0, 0)
        profile_layout.setSpacing(8)
        profile_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
    
        # --- User name label ---
        self.user_name_label = QLabel(self.user_session.get('full_name', 'User'))
        self.user_name_label.setObjectName("userName")
        self.user_name_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self.user_name_label.setStyleSheet("""
            QLabel#userName {
                color: white;
                font-size: 13px;
                font-weight: 500;
                background: transparent;
                border: none;
                margin: 0px;
                padding: 0px 4px;
            }
        """)
        profile_layout.addWidget(self.user_name_label)
    
        # --- Profile picture with enhanced styling ---
        self.profile_pic = QLabel()
        self.profile_pic.setObjectName("profilePic")
        self.profile_pic.setFixedSize(size, size)
        self.profile_pic.setScaledContents(True)
        self.profile_pic.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Enhanced profile picture styling
        self.profile_pic.setStyleSheet(f"""
            QLabel#profilePic {{
                border: 2px solid rgba(255, 255, 255, 0.8);
                border-radius: {size//2}px;
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #3498db, stop: 1 #2980b9);
                margin: 0px;
                padding: 0px;
            }}
            QLabel#profilePic:hover {{
                border: 2px solid rgba(255, 255, 255, 1.0);
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #5dade2, stop: 1 #3498db);
            }}
        """)
    
        # Load profile image or create enhanced placeholder
        profile_pixmap = self.load_profile_image(size)
        self.profile_pic.setPixmap(profile_pixmap)
        
        # Make profile picture clickable with cursor change
        self.profile_pic.setCursor(Qt.PointingHandCursor)
        self.profile_pic.mousePressEvent = self.on_profile_clicked
        
        # Enhanced tooltip
        self.update_profile_tooltip()
        
        profile_layout.addWidget(self.profile_pic)
    
        # --- Ribbon toggle button ---
        self.ribbon_toggle_btn = QPushButton("▴")
        self.ribbon_toggle_btn.setObjectName("ribbonToggle")
        self.ribbon_toggle_btn.setToolTip("Toggle Ribbon Visibility")
        self.ribbon_toggle_btn.setFixedHeight(size)
        self.ribbon_toggle_btn.clicked.connect(self.toggle_ribbon)
        profile_layout.addWidget(self.ribbon_toggle_btn)
            
        # Add the profile container to toolbar
        self.main_tabbar.addWidget(profile_container)

    def load_profile_image(self, size):
        """Load and process profile image with fallback to enhanced placeholder"""
        profile_pixmap = None
        profile_image_path = self.user_session.get('profile_image')
        
        if profile_image_path:
            full_path = os.path.join("static", profile_image_path.lstrip("/\\"))
            if os.path.exists(full_path):
                original_pixmap = QPixmap(full_path)
                if not original_pixmap.isNull():
                    profile_pixmap = self.create_circular_pixmap(original_pixmap, size)
    
        # Try fallback image
        if not profile_pixmap or profile_pixmap.isNull():
            fallback_path = "static/icons/profile.png"
            if os.path.exists(fallback_path):
                fallback_pixmap = QPixmap(fallback_path)
                if not fallback_pixmap.isNull():
                    profile_pixmap = self.create_circular_pixmap(fallback_pixmap, size)
    
        # If still no image, create enhanced placeholder
        if not profile_pixmap or profile_pixmap.isNull():
            profile_pixmap = self.create_enhanced_profile_placeholder(size)
    
        return profile_pixmap

    def create_enhanced_profile_placeholder(self, size):
        """Create a more professional and recognizable profile placeholder"""
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Create professional gradient background
        gradient = QLinearGradient(0, 0, size, size)
        gradient.setColorAt(0, QColor("#ffffff"))  # Professional blue
        gradient.setColorAt(0.5, QColor("#357abd"))
        gradient.setColorAt(1, QColor("#2e6ba8"))
        
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(0, 0, size, size)
        
        # Draw user icon with better proportions
        painter.setBrush(QBrush(QColor("white")))
        painter.setPen(Qt.NoPen)
        
        # Head (circle)
        head_size = size // 4
        head_x = (size - head_size) // 2
        head_y = size // 4
        painter.drawEllipse(head_x, head_y, head_size, head_size)
        
        # Body (rounded rectangle/ellipse)
        body_width = size // 2
        body_height = size // 3
        body_x = (size - body_width) // 2
        body_y = size // 2 + 2
        painter.drawEllipse(body_x, body_y, body_width, body_height)
        
        # Add initials if available
        full_name = self.user_session.get('full_name', 'User')
        if full_name and full_name != 'User':
            initials = ''.join([word[0].upper() for word in full_name.split()[:2]])
            painter.setPen(QColor("white"))
            painter.setFont(QFont("Arial", size//4, QFont.Weight.Bold))
            
            # Clear the center and draw initials
            painter.setBrush(QBrush(gradient))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(2, 2, size-4, size-4)
            
            painter.setPen(QColor("white"))
            painter.drawText(pixmap.rect(), Qt.AlignCenter, initials)
        
        painter.end()
        return pixmap

    def on_profile_clicked(self, event):
        """Handle profile picture click - show user menu or profile options"""
        from PySide6.QtWidgets import QMenu
        
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: white;
                border: 1px solid #ccc;
                border-radius: 8px;
                padding: 4px;
            }
            QMenu::item {
                padding: 8px 16px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #f0f0f0;
            }
        """)
        
        # Add menu actions
        profile_action = menu.addAction("View Profile")
        profile_action.triggered.connect(self.show_user_profile)
        
        settings_action = menu.addAction("Account Settings")
        settings_action.triggered.connect(self.show_account_settings)
        
        menu.addSeparator()
        
        logout_action = menu.addAction("Logout")
        logout_action.triggered.connect(self.on_logout)
        
        # Show menu at profile picture position
        menu.exec(self.profile_pic.mapToGlobal(self.profile_pic.rect().bottomLeft()))
    
    def show_user_profile(self):
        """Show user profile dialog"""
        QMessageBox.information(self, "Profile", f"User Profile for: {self.user_session.get('full_name', 'User')}")
    
    def show_account_settings(self):
        """Show account settings dialog"""
        QMessageBox.information(self, "Settings", "Account settings will be available in the next update.")

    def update_profile_tooltip(self):
        """Update the profile picture tooltip when session changes"""
        if not hasattr(self, 'profile_pic'):
            return
    
        full_name = self.user_session.get('full_name', 'User')
        position = self.user_session.get('position', 'N/A')
        login_time = self.user_session.get('login_time', 'Unknown')
    
        try:
            login_dt = datetime.fromisoformat(login_time)
            login_str = login_dt.strftime('%Y-%m-%d %H:%M')
        except:
            login_str = 'Just now'
    
        tooltip_text = f"""
        <b>Full Name:</b> {full_name}<br>
        <b>Position:</b> {position}<br>
        <b>Status:</b> <span style="color: #00aa00;">Signed In</span><br>
        <b>Since:</b> {login_str}
        """.strip()
    
        self.profile_pic.setToolTip(tooltip_text)
    
    def create_main_tabs(self):
        """Create the main navigation tabs"""
        self.main_tabbar = QToolBar("Main Tabs")
        self.main_tabbar.setObjectName("mainTabs")
        self.main_tabbar.setMovable(False)
        self.addToolBar(Qt.TopToolBarArea, self.main_tabbar)
        
        # Add menu toggle button first
        menu_btn = QPushButton("☰")
        menu_btn.setObjectName("tabButton")
        menu_btn.setToolTip("Toggle Menu")
        menu_btn.setCheckable(True)
        menu_btn.clicked.connect(self.toggle_sidebar)
        self.main_tabbar.addWidget(menu_btn)
        
        self.tab_buttons = [menu_btn]
        tabs = [
            "Dashboard", "Schools", "Staff", "Parents", "Students",
            "Exams", "Activities", "Finance", "Others"
        ]
        
        for text in tabs:
            btn = QPushButton(text)
            btn.setObjectName("tabButton")
            btn.setCheckable(True)
            btn.clicked.connect(lambda _, t=text: self.on_tab_clicked(t))
            self.main_tabbar.addWidget(btn)
            self.tab_buttons.append(btn)
        
        self.tab_buttons[1].setChecked(True)
    
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        spacer.setStyleSheet("background: transparent;")
        self.main_tabbar.addWidget(spacer)
    
        # Create profile section (now includes the toggle button)
        self.create_profile_section()

    def create_content_pages(self):
        """Create all content pages for the application"""
        # Initialize users_form early
        self.users_form = UsersForm(parent=self, user_session=self.user_session)
    
        # Dashboard Page (now with tabs)
        dashboard_page = self.create_dashboard_page()
        self.stacked_widget.addWidget(dashboard_page)
    
        # Schools Page
        self.schools_form = SchoolsForm(self)
        self.stacked_widget.addWidget(self.schools_form)
    
        # Staff Page (TeachersForm)
        self.staff_form = TeachersForm(parent=self, user_session=self.user_session)
        self.stacked_widget.addWidget(self.staff_form)

        # Parents Page (ParentsForm)
        self.parents_form = ParentsForm(parent=self, user_session=self.user_session)
        self.stacked_widget.addWidget(self.parents_form)

        # Students Page (StudentsForm)
        self.students_form = StudentsForm(parent=self, user_session=self.user_session)
        self.stacked_widget.addWidget(self.students_form)

    
        # Other pages (exams to Others)
        for i in range(5, 8):  # exams (3) to Others (7)
            page = QWidget()
            layout = QVBoxLayout(page)
            layout.setContentsMargins(20, 20, 20, 20)
            page_label = QLabel(f"Content for Module {i+1} - Coming Soon")
            page_label.setStyleSheet("""
                font-size: 18px;
                color: #6c757d;
                padding: 40px;
                text-align: center;
            """)
            page_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(page_label)
            self.stacked_widget.addWidget(page)

    def create_dashboard_page(self):
        """Create dashboard page with flat tabs: Overview, User Management, Permissions, Login Activity, Audit Trail"""
        dashboard_page = QWidget()
        dashboard_layout = QVBoxLayout(dashboard_page)
        dashboard_layout.setContentsMargins(0, 10, 0, 0)
    
        # ✅ Create tab widget FIRST
        self.dashboard_tabs = QTabWidget()
        self.dashboard_tabs.setDocumentMode(True)
        self.dashboard_tabs.setTabPosition(QTabWidget.North)
    
        # 1. Overview Tab
        overview_tab = QWidget()
        overview_layout = QVBoxLayout(overview_tab)
        welcome_label = QLabel("Welcome to CBCentra School Management System")
        welcome_label.setStyleSheet("""
            font-size: 24px;
            font-weight: 600;
            color: #2c3e50;
            padding: 20px;
            text-align: center;
        """)
        welcome_label.setAlignment(Qt.AlignCenter)
        overview_layout.addWidget(welcome_label)
        self.dashboard_tabs.addTab(overview_tab, "Overview")
        self.dashboard_tabs.setTabIcon(0, QIcon("static/icons/home.jpg"))
    
        # 2. User Management Tab
        self.users_form = UsersForm(parent=self, user_session=self.user_session)
        self.dashboard_tabs.addTab(self.users_form, "User Management")
        self.dashboard_tabs.setTabIcon(1, QIcon("static/icons/users.png"))
    
        # 3. Permissions Tab (Admin & Headteacher Only)
        if has_permission(self.user_session, "manage_system_settings"):
            from ui.permissions_form import PermissionsForm
            self.permissions_form = PermissionsForm(parent=self, user_session=self.user_session)
            self.dashboard_tabs.addTab(self.permissions_form, "Permissions")
            self.dashboard_tabs.setTabIcon(self.dashboard_tabs.count() - 1, QIcon("static/icons/lock.png"))
    
        # 4. User Permissions Tab (Admin Only)
        if has_permission(self.user_session, "manage_system_settings"):
            from ui.user_permissions_form import UserPermissionsForm
            self.user_perms_tab = UserPermissionsForm(parent=self, user_session=self.user_session)
            self.dashboard_tabs.addTab(self.user_perms_tab, "User Permissions")
            self.dashboard_tabs.setTabIcon(self.dashboard_tabs.count() - 1, QIcon("static/icons/user-star.png"))
    
        # 5. Login Activity Tab
        login_logs_tab = QWidget()
        login_logs_layout = QVBoxLayout(login_logs_tab)
        self.login_logs_form = LoginLogsForm(user_session=self.user_session)
        login_logs_layout.addWidget(self.login_logs_form)
        self.dashboard_tabs.addTab(login_logs_tab, "Login Activity")
        self.dashboard_tabs.setTabIcon(3 if has_permission(self.user_session, "manage_system_settings") else 2, QIcon("static/icons/login.png"))
    
        # 6. Audit Trail Tab
        audit_logs_tab = QWidget()
        audit_logs_layout = QVBoxLayout(audit_logs_tab)
        self.audit_logs_form = AuditLogsForm(parent=audit_logs_tab, user_session=self.user_session)
        audit_logs_layout.addWidget(self.audit_logs_form)
        self.dashboard_tabs.addTab(audit_logs_tab, "Audit Trail")
        self.dashboard_tabs.setTabIcon(4 if has_permission(self.user_session, "manage_system_settings") else 3, QIcon("static/icons/audit.jpg"))
    
        # ✅ Add tabs to layout
        dashboard_layout.addWidget(self.dashboard_tabs)
    
        return dashboard_page
    
    def toggle_ribbon(self):
        """Toggle ribbon visibility with animation"""
        if self.ribbon_visible:
            # Hide ribbon
            self.ribbon_toolbar.setFixedHeight(0)
            self.ribbon_toggle_btn.setText("▾")
            self.ribbon_visible = False
        else:
            # Show ribbon
            self.ribbon_toolbar.setFixedHeight(90)
            self.ribbon_toggle_btn.setText("▴")
            self.ribbon_visible = True

    def create_circular_pixmap(self, pixmap, size):
        """Create a circular version of the pixmap"""
        # Scale the pixmap to the desired size
        scaled_pixmap = pixmap.scaled(size, size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        
        # Create a new pixmap with transparency
        circular_pixmap = QPixmap(size, size)
        circular_pixmap.fill(Qt.transparent)
        
        # Create a painter to draw the circular image
        painter = QPainter(circular_pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Create a circular clipping path
        painter.setBrush(QBrush(scaled_pixmap))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(0, 0, size, size)
        painter.end()
        
        return circular_pixmap


    def create_sidebar(self):
        """Create modern floating sidebar with darker gradient background, full height, and animations"""
        # Create overlay background
        self.sidebar_overlay = QFrame(self)
        self.sidebar_overlay.setStyleSheet("background-color: rgba(0, 0, 0, 0.3);")
        self.sidebar_overlay.setGeometry(0, 0, self.width(), self.height())
        self.sidebar_overlay.hide()
        self.sidebar_overlay.mousePressEvent = lambda e: self.toggle_sidebar()
    
        # Create sidebar frame
        self.sidebar_frame = QFrame(self)
        self.sidebar_frame.setObjectName("sideMenu")
        self.sidebar_frame.setFixedWidth(300)
    
        # 🔥 Set full height: starts at y=80 (mainTabs + ribbon), goes to bottom
        self.sidebar_frame.setFixedHeight(self.height() - 80)
        self.sidebar_frame.move(-300, 80)  # Aligns with bottom of ribbon
    
        self.sidebar_frame.setWindowFlags(Qt.Widget | Qt.FramelessWindowHint)
        self.sidebar_frame.setAttribute(Qt.WA_TranslucentBackground, False)
        self.sidebar_frame.raise_()
        self.sidebar_frame.setParent(self)
    
        # Drop shadow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(25)
        shadow.setColor(QColor(0, 0, 0, 120))
        shadow.setOffset(6, 6)
        self.sidebar_frame.setGraphicsEffect(shadow)
    
        # 🔥 Apply DARKER gradient background (deeper than main tabs)
        self.sidebar_frame.setStyleSheet("""
            QFrame#sideMenu {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #002B5B,
                    stop:1 #001F44
                );
                border: 1px solid #001428;
                border-radius: 12px;
            }
        """)
    
        # Main sidebar layout
        layout = QVBoxLayout(self.sidebar_frame)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)
    
        # --- Menu Header ---
        menu_header = QLabel(" MENU ")
        menu_header.setObjectName("menuHeader")
        menu_header.setStyleSheet(f"""
            QLabel#menuHeader {{
                background-color: {self.colors['main_tab_gradient_start']};  /* Blue background */
                color: white;
                font-size: 14px;
                font-weight: bold;
                letter-spacing: 1px;
                padding: 6px 8px;
                border-radius: 6px;
                border: 1px solid {self.colors['main_tab_border']};
            }}
        """)
        menu_header.setAlignment(Qt.AlignLeft)
        layout.addWidget(menu_header)
    
        # --- Action Buttons ---
        actions = [
            ("Home", self.home_action, "home.png"),
            ("Dashboard", self.dashboard_action, "dashboard.png"),
            ("Info", self.info_action, "info.png"),
            ("Print", self.print_action, "print.png"),
            ("Import", self.import_action, "import.png"),
            ("Export", self.export_action, "export.png"),
            ("Settings", self.settings_action, "settings.png"),
            ("Options", self.options_action, "options.png"),
            ("Quit", self.close, "quit.jpg")
        ]
    
        for name, func, icon in actions:
            btn = QPushButton(f"  {name}")
            btn.setObjectName("menuAction")
            btn.setProperty("menuActionName", name.lower())  # For tracking
        
            icon_path = f"static/icons/{icon}"
            if os.path.exists(icon_path):
                btn.setIcon(QIcon(icon_path))
                btn.setIconSize(QSize(20, 20))
        
            btn.setStyleSheet(f"""
                QPushButton#menuAction {{
                    background-color: {self.colors['background']};
                    color: {self.colors['text_primary']};
                    border: 1px solid {self.colors['border']};
                    border-radius: 8px;
                    padding: 10px 14px;
                    font-size: 13px;
                    font-weight: 500;
                    text-align: left;
                    min-height: 40px;
                    max-height: 40px;
                }}
                QPushButton#menuAction:hover {{
                    background-color: {self.colors['surface']};
                }}
                QPushButton#menuAction:checked {{
                    background-color: #d0e0f0;
                    border-color: {self.colors['primary']};
                    font-weight: bold;
                }}
            """)
        
            btn.setCheckable(True)  # Allow checked state
            btn.clicked.connect(lambda checked, f=func: self.on_sidebar_button_clicked(f, btn))
            layout.addWidget(btn)
    
        layout.addStretch()
    
        # Sidebar animations
        self.sidebar_animation = QPropertyAnimation(self.sidebar_frame, b"geometry")
        self.sidebar_animation.setDuration(300)
        self.sidebar_animation.setEasingCurve(QEasingCurve.OutCubic)
    
        # Overlay fade animation
        self.overlay_animation = QPropertyAnimation(self.sidebar_overlay, b"windowOpacity")
        self.overlay_animation.setDuration(300)
    
    def toggle_sidebar(self):
        """Animate sidebar in and out with proper z-order management and overlay"""
        if self.sidebar_visible:
            # Hide sidebar and overlay
            self.sidebar_animation.setStartValue(QRect(0, 80, 300, self.sidebar_frame.height()))
            self.sidebar_animation.setEndValue(QRect(-300, 80, 300, self.sidebar_frame.height()))
            
            # Fade out overlay
            self.overlay_animation.setStartValue(1.0)
            self.overlay_animation.setEndValue(0.0)
            
            # Safely disconnect signals
            try:
                if self.overlay_animation.finished:
                    self.overlay_animation.finished.disconnect()
            except RuntimeError:
                pass
            
            try:
                if self.sidebar_animation.finished:
                    self.sidebar_animation.finished.disconnect()
            except RuntimeError:
                pass
            
            self.overlay_animation.finished.connect(lambda: self.sidebar_overlay.hide())
            self.sidebar_animation.finished.connect(lambda: self.sidebar_frame.hide())
            self.sidebar_visible = False
            
            # Uncheck menu button
            if self.tab_buttons:
                self.tab_buttons[0].setChecked(False)
            
        else:
            # Show overlay first
            self.sidebar_overlay.setGeometry(0, 0, self.width(), self.height())
            self.sidebar_overlay.show()
            self.sidebar_overlay.raise_()
            
            # Fade in overlay
            self.overlay_animation.setStartValue(0.0)
            self.overlay_animation.setEndValue(1.0)
            
            # Safely disconnect any previous connections
            try:
                if self.overlay_animation.finished:
                    self.overlay_animation.finished.disconnect()
            except RuntimeError:
                pass
            
            try:
                if self.sidebar_animation.finished:
                    self.sidebar_animation.finished.disconnect()
            except RuntimeError:
                pass
            
            # Show sidebar
            self.sidebar_frame.show()
            self.sidebar_frame.raise_()
            
            # Force the sidebar to be above everything
            for child in self.findChildren(QWidget):
                if child not in [self.sidebar_frame, self.sidebar_overlay]:
                    child.stackUnder(self.sidebar_overlay)
            
            self.sidebar_animation.setStartValue(QRect(-300, 80, 300, self.sidebar_frame.height()))
            self.sidebar_animation.setEndValue(QRect(0, 80, 300, self.sidebar_frame.height()))
            self.sidebar_visible = True
            
            # Check menu button
            if self.tab_buttons:
                self.tab_buttons[0].setChecked(True)
        
        # Start both animations
        self.sidebar_animation.start()
        self.overlay_animation.start()

    def on_sidebar_button_clicked(self, func, button):
        """Handle sidebar button click with visual feedback"""
        # Uncheck all other buttons
        for child in self.sidebar_frame.findChildren(QPushButton, "menuAction"):
            if child is not button:
                child.setChecked(False)
        # Execute action
        func()

    def on_tab_clicked(self, tab_name):
        """Handle tab clicks"""
        # Update tab visual state
        for i, btn in enumerate(self.tab_buttons):
            btn.setChecked(btn.text() == tab_name)
        
        # Update ribbon panel
        self.update_ribbon_panel(tab_name)
        
        # Switch to appropriate page
        tab_mapping = {
            "Menu": 0,
            "Dashboard": 0,
            "Schools": 1,
            "Staff": 2,  # This matches the index where we added TeachersForm
            "Parents": 3,
            "Students": 4,
            "Exams": 5,
            "Activities": 6,
            "Finance": 7,
            "Others": 8
        }
        
        page_index = tab_mapping.get(tab_name, 0)
        self.stacked_widget.setCurrentIndex(page_index)
        
        # Update status bar
        self.statusBar().showMessage(f"Current Section: {tab_name}")
        
        # Special handling for Staff tab
        if tab_name == "Staff" and hasattr(self, 'staff_form'):
            self.staff_form.load_teachers()
            self.staff_form.load_schools()


    def mousePressEvent(self, event):
        """Handle clicks outside sidebar to close it"""
        if self.sidebar_visible:
            sidebar_rect = self.sidebar_frame.geometry()
            # Use globalPosition() for Qt6 compatibility instead of deprecated pos()
            if hasattr(event, 'globalPosition'):
                click_pos = event.globalPosition().toPoint()
                click_pos = self.mapFromGlobal(click_pos)
            else:
                click_pos = event.pos()  # Fallback for older Qt versions
            
            if not sidebar_rect.contains(click_pos):
                self.toggle_sidebar()
                self.tab_buttons[0].setChecked(False)
        super().mousePressEvent(event)
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'sidebar_frame'):
            new_height = self.height() - 80  # Starts below ribbon
            self.sidebar_frame.setFixedHeight(new_height)
            if self.sidebar_visible:
                self.sidebar_frame.move(0, 80)
            else:
                self.sidebar_frame.move(-300, 80)
        if hasattr(self, 'sidebar_overlay'):
            self.sidebar_overlay.setGeometry(0, 0, self.width(), self.height())
    
    def showEvent(self, event):
        """Ensure sidebar is properly positioned when window is shown"""
        super().showEvent(event)
        if hasattr(self, 'sidebar_frame'):
            # Make sure sidebar is properly layered
            self.sidebar_frame.raise_()
            if hasattr(self, 'sidebar_overlay'):
                self.sidebar_overlay.stackUnder(self.sidebar_frame)
    
    def paintEvent(self, event):
        """Ensure sidebar stays on top during paint events"""
        super().paintEvent(event)
        if hasattr(self, 'sidebar_frame') and self.sidebar_visible:
            self.sidebar_overlay.raise_()
            self.sidebar_frame.raise_()

    # Action Methods
    def home_action(self):
        self.stacked_widget.setCurrentIndex(0)
        self.update_ribbon_panel("Dashboard")
        for btn in self.tab_buttons:
            btn.setChecked(False)
        self.toggle_sidebar()

    def dashboard_action(self):
        self.stacked_widget.setCurrentIndex(0)
        self.update_ribbon_panel("Dashboard")
        for btn in self.tab_buttons:
            btn.setChecked(False)
        self.toggle_sidebar()

    def new_action(self):
        QMessageBox.information(self, "New", "Create new item")
        self.toggle_sidebar()

    def open_action(self):
        QMessageBox.information(self, "Open", "Open existing item")
        self.toggle_sidebar()

    def info_action(self):
        QMessageBox.about(self, "About CBCentra SMS", 
                         "CBCentra School Management System v1.0.0\n\n"
                         "A comprehensive solution for modern school management.")
        self.toggle_sidebar()

    def print_action(self):
        QMessageBox.information(self, "Print", "Print current document")
        self.toggle_sidebar()

    def import_action(self):
        QMessageBox.information(self, "Import", "Import data from external source")
        self.toggle_sidebar()

    def export_action(self):
        QMessageBox.information(self, "Export", "Export data to external format")
        self.toggle_sidebar()

    def settings_action(self):
        QMessageBox.information(self, "Settings", "Open system settings")
        self.toggle_sidebar()

    def options_action(self):
        QMessageBox.information(self, "Options", "Configure application options")
        self.toggle_sidebar()


    def closeEvent(self, event):
        reply = QMessageBox.question(
            self, "Confirm Exit", 
            "Are you sure you want to exit CBCentra School Management System?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            if self.db_connection:
                self.db_connection.close()
            event.accept()
        else:
            event.ignore()
