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
from PySide6.QtGui import QIcon, QPixmap, QPainter, QBrush, QColor, QLinearGradient, QAction
from PySide6.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve, QRect, Signal
from PySide6.QtCore import QBuffer, QByteArray, QIODevice
from PySide6.QtPrintSupport import QPrinter, QPrintPreviewDialog, QPrintPreviewWidget, QPrintDialog
from PySide6.QtPdf import QPdfDocument
from ui.schools_form import SchoolsForm
from ui.users_form import UsersForm
from ui.teachers_form import TeachersForm
from ui.login_logs_form import LoginLogsForm
from ui.audit_logs_form import AuditLogsForm
from ui.audit_base_form import AuditBaseForm
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
        
        # 🔥 INHERIT ALL STYLING from AuditBaseForm
        self.setStyleSheet(self.audit_base.styleSheet())
        self.colors = self.audit_base.colors
        self.fonts = self.audit_base.fonts
        
        # Store reference to audit methods
        self.log_audit_action = self.audit_base.log_audit_action
        self.export_with_green_header = self.audit_base.export_with_green_header
        self.get_school_info = self.audit_base.get_school_info
        
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
                print(f"🔁 Permissions auto-generated for role '{role}': {self.user_session['permissions']}")
            except Exception as e:
                print(f"❌ Failed to load permissions: {e}")
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
        #self.apply_styles()
        self.create_main_tabs()
        self.create_ribbon_panel()
        self.create_sidebar()
        #self.create_logout_action()
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
            fallback_path = "static/icons/profile.jpg"
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
        """Create a modern profile section with user name and toggle button"""
        size = 36
        
        # Create container for profile elements
        profile_container = QWidget()
        profile_layout = QHBoxLayout(profile_container)
        profile_layout.setContentsMargins(0, 0, 0, 0)
        profile_layout.setSpacing(10)
        
        # User name label - use actual user session data
        self.user_name_label = QLabel(self.user_session.get('full_name', 'User'))
        self.user_name_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 13px;
                font-weight: 500;
                padding-right: 5px;
            }
        """)
        profile_layout.addWidget(self.user_name_label)
        
        # Profile picture
        self.profile_pic = QLabel()
        self.profile_pic.setObjectName("profilePic")
        self.profile_pic.setFixedSize(size, size)
        self.profile_pic.setScaledContents(True)
        
        # Try to load profile image, create placeholder if not found
        # Try to load profile image, create placeholder if not found
        profile_pixmap = None
        profile_image_path = self.user_session.get('profile_image')
        
        if profile_image_path:
            full_path = os.path.join("static", profile_image_path.lstrip("/\\"))
            if os.path.exists(full_path):
                profile_pixmap = QPixmap(full_path)
        
        if not profile_pixmap or profile_pixmap.isNull():
            fallback_path = "static/icons/profile.jpg"
            if os.path.exists(fallback_path):
                profile_pixmap = QPixmap(fallback_path)
        
        if profile_pixmap and not profile_pixmap.isNull():
            circular_pixmap = self.create_circular_pixmap(profile_pixmap, size)
        else:
            circular_pixmap = self.create_profile_placeholder(size)
        
        # ✅ Set tooltip with user info
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
        self.profile_pic.setPixmap(circular_pixmap)
        
        profile_layout.addWidget(self.profile_pic)
        
        # Ribbon toggle button
        self.ribbon_toggle_btn = QPushButton("▴")
        self.ribbon_toggle_btn.setObjectName("ribbonToggle")
        self.ribbon_toggle_btn.setToolTip("Toggle Ribbon Visibility")
        self.ribbon_toggle_btn.clicked.connect(self.toggle_ribbon)
        profile_layout.addWidget(self.ribbon_toggle_btn)
        
        # Add the complete profile container to the toolbar
        self.main_tabbar.addWidget(profile_container)

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
            "Dashboard", "Schools", "Staff", "Students",
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
    
        # Other pages (Students to Others)
        for i in range(3, 8):  # Students (3) to Others (7)
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
        dashboard_layout.setContentsMargins(0, 0, 0, 0)
    
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

    def create_profile_placeholder(self, size):
        """Create a modern placeholder for profile picture"""
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Create gradient background
        gradient = QLinearGradient(0, 0, size, size)
        gradient.setColorAt(0, QColor("#3498db"))
        gradient.setColorAt(1, QColor("#2980b9"))
        
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(0, 0, size, size)
        
        # Draw user icon (simplified)
        painter.setBrush(QBrush(QColor("white")))
        # Head
        painter.drawEllipse(size//3, size//4, size//3, size//3)
        # Body
        painter.drawEllipse(size//4, size//2, size//2, size//2)
        
        painter.end()
        return pixmap

    def create_ribbon_panel(self):
        """Create the modern ribbon-style panel"""
        self.ribbon_container = QWidget()
        self.ribbon_container.setObjectName("ribbonContainer")
        self.ribbon_container.setFixedHeight(90)

        ribbon_layout = QVBoxLayout(self.ribbon_container)
        ribbon_layout.setContentsMargins(0, 0, 0, 0)
        ribbon_layout.setSpacing(0)

        # Modern ribbon title
        #self.ribbon_title = QLabel("Dashboard")
        #self.ribbon_title.setObjectName("ribbonTitle")
        #self.ribbon_title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        #ribbon_layout.addWidget(self.ribbon_title)

        # Scrollable ribbon area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setFrameShape(QFrame.NoFrame)

        self.ribbon_panel = QWidget()
        self.ribbon_panel.setObjectName("ribbonPanel")
        self.ribbon_panel_layout = QHBoxLayout(self.ribbon_panel)
        self.ribbon_panel_layout.setContentsMargins(10, 3, 10, 5)
        self.ribbon_panel_layout.setSpacing(8)

        scroll_area.setWidget(self.ribbon_panel)
        ribbon_layout.addWidget(scroll_area)

        self.addToolBarBreak(Qt.TopToolBarArea)
        self.ribbon_toolbar = QToolBar("Ribbon")
        self.ribbon_toolbar.setMovable(False)
        self.ribbon_toolbar.addWidget(self.ribbon_container)
        self.addToolBar(Qt.TopToolBarArea, self.ribbon_toolbar)

        self.update_ribbon_panel("Dashboard")

    def create_ribbon_group(self, title, actions):
        """Create a modern ribbon group with enhanced styling"""
        group = QWidget()
        group.setObjectName("ribbonGroup")
        
        # Add shadow effect to ribbon group since CSS box-shadow doesn't work
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(8)
        shadow.setColor(QColor(0, 0, 0, 30))
        shadow.setOffset(0, 2)
        group.setGraphicsEffect(shadow)
        
        layout = QVBoxLayout(group)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Buttons container
        buttons_container = QWidget()
        buttons_layout = QHBoxLayout(buttons_container)
        buttons_layout.setContentsMargins(6, 5, 6, 5)
        buttons_layout.setSpacing(3)

        for action in actions:
            btn = QPushButton()
            btn.setObjectName("ribbonButton")
            btn.setToolTip(action["name"])
            
            # Load icon (handle both .jpg and .png)
            icon_path = f"static/icons/{action['icon']}"
            if not os.path.exists(icon_path):
                # Try with .jpg extension if .png doesn't exist
                icon_path = icon_path.replace('.png', '.jpg')
            
            if os.path.exists(icon_path):
                btn.setIcon(QIcon(icon_path))
            else:
                # Create a simple placeholder icon
                btn.setText(action["name"][:2].upper())
            
            btn.setIconSize(QSize(32, 32))
            if "handler" in action:
                btn.clicked.connect(action["handler"])
            buttons_layout.addWidget(btn)

        layout.addWidget(buttons_container)

        # Modern group title
        title_label = QLabel(title)
        title_label.setObjectName("ribbonGroupTitle")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        return group

    def update_ribbon_panel(self, main_tab):
        """Update ribbon panel with modern styling"""
        # Keep this — but just set clean title
        #self.ribbon_title.setText(main_tab)
    
        # Clear existing content
        while self.ribbon_panel_layout.count():
            item = self.ribbon_panel_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
    
        #  Keep your existing ribbon_groups logic
        ribbon_groups = {
            "Dashboard": [
                {"title": "View", "actions": [
                    {"name": "Overview", "icon": "overview.jpg", "handler": lambda: self.dashboard_tabs.setCurrentIndex(0)},
                    {"name": "Statistics", "icon": "statistics.jpg"},
                    {"name": "Print", "icon": "print.jpg", "handler": lambda: self.dashboard_tabs.setCurrentIndex(2)}
                ]},
                {"title": "User Management", "actions": [
                    {"name": "Manage Users", "icon": "users.png", "handler": lambda: self.dashboard_tabs.setCurrentIndex(1)},
                    {"name": "Add User", "icon": "adduser.jpg", "handler": self.add_new_user},
                    {"name": "Export User Data", "icon": "export.jpg", "handler": self.execute_user_export_dialog},
                    {"name": "Refresh", "icon": "refresh.jpg", "handler": self.refresh_user_data}
                ]},
                {"title": "Security & Reports", "actions": [
                    {"name": "Login Logs", "icon": "security.jpg", "handler": self.show_login_logs},
                    {"name": "Audit Trail", "icon": "audit.jpg", "handler": self.show_audit_logs},
                    {"name": "Security Report", "icon": "report_security.jpg", "handler": self.generate_security_report}
                ]},
                {"title": "Tools", "actions": [
                    {"name": "Settings", "icon": "settings.jpg", "handler": self.settings_action},
                    {"name": "Global Refresh", "icon": "refresh_all.jpg", "handler": self.refresh_all_data}
                ]}
            ],
            "Schools": [
                {"title": "Manage", "actions": [
                    {"name": "List Schools", "icon": "info.jpg"},
                    {"name": "Add New", "icon": "new.jpg"},
                    {"name": "Import", "icon": "import.jpg"}
                ]},
                {"title": "Configuration", "actions": [
                    {"name": "Settings", "icon": "settings.jpg"},
                    {"name": "Options", "icon": "options.jpg"},
                    {"name": "Export", "icon": "export.jpg"}
                ]}
            ],
            "Staff": [
                {"title": "Staff Records", "actions": [
                    {"name": "Teachers", "icon": "teacher.jpg", "handler": self.show_teachers_form},
                    {"name": "Add Teacher", "icon": "addstaff.jpg", "handler": self.add_new_teacher},
                    {"name": "View Teacher Summaries", "icon": "view.jpg", "handler": self.generate_teacher_summary}
                ]},
                {"title": "Actions", "actions": [
                    {"name": "Refresh", "icon": "refresh.jpg", "handler": self.refresh_teachers_data},
                    {"name": "Generate Teacher Form", "icon": "report.jpg", "handler": self.generate_teacher_profile},
                    {"name": "Print", "icon": "print.jpg"}
                ]},
                {"title": "Import & Export", "actions": [
                    {"name": "Import Teacher Data (CSV)", "icon": "import.jpg", "handler": self.import_teachers_data},
                    {"name": "Export Teacher Data (Excel)", "icon": "export.jpg", "handler": self.export_teachers_data}
                ]}
            ]
        }.get(main_tab, [
            {"title": "Common", "actions": [
                {"name": "New", "icon": "new.jpg", "handler": self.new_action},
                {"name": "Open", "icon": "open.jpg", "handler": self.open_action},
                {"name": "Print", "icon": "print.jpg", "handler": self.print_action}
            ]},
            {"title": "Actions", "actions": [
                {"name": "Settings", "icon": "settings.jpg", "handler": self.settings_action},
                {"name": "Options", "icon": "options.jpg"}
            ]}
        ])
    
        for group in ribbon_groups:
            ribbon_group = self.create_ribbon_group(group["title"], group["actions"])
            self.ribbon_panel_layout.addWidget(ribbon_group)
    
        self.ribbon_panel_layout.addStretch()
    
    # Ribbon button handlers
    #for users
    def open_users_form(self):
        """Open the users management form in dashboard"""
        self.on_tab_clicked("Dashboard")
        self.dashboard_tabs.setCurrentIndex(1)  # Switch to Users tab
        self.statusBar().showMessage("User Management - Ready to manage system users")

    def add_new_user(self):
        """Quick action to add a new user"""
        self.on_tab_clicked("Dashboard")
        self.dashboard_tabs.setCurrentIndex(1)  # Switch to Users tab
        if hasattr(self, 'users_form'):
            self.users_form.clear_form()
        self.statusBar().showMessage("Ready to add new user")

    def refresh_user_data(self):
        """Refresh user data in the dashboard users form"""
        self.on_tab_clicked("Dashboard")
        self.dashboard_tabs.setCurrentIndex(1)  # Switch to Users tab
        
        if hasattr(self, 'users_form'):
            try:
                # Call the refresh method on your users form
                self.users_form.refresh_data()
                self.statusBar().showMessage("User data refreshed successfully!")
            except Exception as e:
                self.statusBar().showMessage(f"Error refreshing user data: {str(e)}")
                QMessageBox.critical(self, "Refresh Error", f"Failed to refresh user data: {e}")
        else:
            self.statusBar().showMessage("Users form not available for refresh")
            QMessageBox.warning(self, "Refresh Failed", "Users form is not initialized")

    def execute_user_export_dialog(self):
        """Open export dialog and safely call users_form.export_users"""
        if not hasattr(self, 'users_form') or self.users_form is None:
            QMessageBox.warning(self, "Error", "User management form not available.")
            return
    
        # Get filename
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export Users",
            f"users_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "CSV Files (*.csv);;Excel Files (*.xlsx);;PDF Files (*.pdf);;All Files (*)"
        )
        if not filename:
            return  # Cancelled
    
        try:
            success = self.users_form.export_users(filename)
            if success:
                QMessageBox.information(self, "Success", f"Users exported to:\n{os.path.basename(filename)}")
                self.statusBar().showMessage(f"Exported user data to {os.path.basename(filename)}")
            else:
                QMessageBox.critical(self, "Export Failed", "Could not export data.")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export: {str(e)}")

    def export_login_statistics(self, filename):
        """Export user login statistics"""
        try:
            query = '''
                SELECT u.username, u.full_name, u.role,
                       COUNT(ll.id) as total_logins,
                       SUM(CASE WHEN ll.login_status = 'success' THEN 1 ELSE 0 END) as successful_logins,
                       SUM(CASE WHEN ll.login_status = 'failed' THEN 1 ELSE 0 END) as failed_logins,
                       MAX(ll.login_time) as last_login
                FROM users u
                LEFT JOIN login_logs ll ON u.id = ll.user_id
                GROUP BY u.id, u.username, u.full_name, u.role
                ORDER BY total_logins DESC
            '''
            
            self.users_form.cursor.execute(query)
            login_stats = self.users_form.cursor.fetchall()
            
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['Username', 'Full Name', 'Role', 'Total Logins', 
                               'Successful Logins', 'Failed Logins', 'Last Login'])
                writer.writerows(login_stats)
            
            return True
            
        except Exception as e:
            print(f"Export login statistics error: {e}")
            return False
        
    #for staff/teachers
    def show_teachers_form(self):
        """Switch to teachers form and ensure it's visible"""
        self.on_tab_clicked("Staff")
        if hasattr(self, 'staff_form'):
            self.staff_form.load_teachers()
    
    def add_new_teacher(self):
        """Prepare the form for adding a new teacher"""
        self.on_tab_clicked("Staff")
        if hasattr(self, 'staff_form'):
            self.staff_form.clear_fields()
            self.staff_form.tab_widget.setCurrentIndex(0)  # Switch to form tab
    
    def export_teachers_data(self):
        """Export teachers data to Excel"""
        self.on_tab_clicked("Staff")
        if hasattr(self, 'staff_form'):
            self.staff_form.export_teachers_data()

    def import_teachers_data(self):
        """Export teachers data to Excel"""
        self.on_tab_clicked("Staff")
        if hasattr(self, 'staff_form'):
            self.staff_form.import_teachers_data()

    def generate_teacher_summary(self):
        """Export teachers data to Excel"""
        self.on_tab_clicked("Staff")
        if hasattr(self, 'staff_form'):
            self.staff_form.generate_teacher_report()
    
    def refresh_teachers_data(self):
        """Refresh teachers data"""
        self.on_tab_clicked("Staff")
        if hasattr(self, 'staff_form'):
            self.staff_form.load_teachers()
            self.staff_form.load_schools()
            QMessageBox.information(self, "Refreshed", "Teacher data has been refreshed")
    
    def print_teachers_list(self):
        """Print teachers list (placeholder)"""
        QMessageBox.information(self, "Print", "Print functionality will be implemented here")


    # Add this method to your MainWindow class for the generate teacher report functionality
    def generate_teacher_profile(self):
        """Generate teacher report from the staff form"""
        if not hasattr(self, 'staff_form'):
            QMessageBox.warning(self, "Error", "Staff form not loaded")
            return
        
        teacher_id = getattr(self.staff_form, 'current_teacher_id', None)
        if not teacher_id:
            QMessageBox.warning(self, "Warning", "Please select a teacher")
            return
        
        try:
            pdf_bytes = self.staff_form.generate_teacher_profile_pdf(teacher_id)
            self.show_pdf_preview_dialog(pdf_bytes)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate PDF:\n{str(e)}")

    def print_loaded_pdf(self):
        """Print the currently loaded PDF bytes"""
        try:
            if not hasattr(self, 'current_pdf_bytes') or not self.current_pdf_bytes:
                QMessageBox.warning(self, "No PDF", "No PDF is currently loaded for printing")
                return
                
            # Use the PDF utilities to print
            try:
                from utils.pdf_utils import print_pdf
                print_pdf(self.current_pdf_bytes, parent=self)
            except ImportError:
                # Fallback if utils module not available
                QMessageBox.information(self, "Print", "PDF print utilities not available")
                
        except Exception as e:
            QMessageBox.critical(self, "Print Error", f"Failed to print PDF:\n{str(e)}")


    #for login logs
    def show_login_logs(self):
        """Show Login Activity tab directly"""
        if not has_permission(self.user_session, "view_login_logs"):
            QMessageBox.warning(self, "Permission Denied", "You don't have permission to view login logs.")
            return
    
        self.on_tab_clicked("Dashboard")
        self.dashboard_tabs.setCurrentIndex(2)  # Login Activity is now tab 2
        self.login_logs_form.load_login_logs()
        self.statusBar().showMessage("Login activity logs loaded")
    
    def show_audit_logs(self):
        """Show Audit Trail tab directly"""
        if not has_permission(self.user_session, "view_audit_logs"):
            QMessageBox.warning(self, "Permission Denied", "You don't have permission to view audit logs.")
            return
    
        self.on_tab_clicked("Dashboard")
        self.dashboard_tabs.setCurrentIndex(3)  # Audit Trail is now tab 3
        self.audit_logs_form.load_audit_logs()
        self.statusBar().showMessage("Audit trail logs loaded")
    
    def export_audit_reports(self):
        """Export audit reports"""
        self.on_tab_clicked("Dashboard")
        self.dashboard_tabs.setCurrentIndex(2)  # Reports tab
        
        if hasattr(self, 'audit_logs_form'):
            try:
                self.audit_logs_form.export_logs()
                self.statusBar().showMessage("Audit reports exported successfully!")
            except Exception as e:
                self.statusBar().showMessage(f"Error exporting audit reports: {str(e)}")
                QMessageBox.critical(self, "Export Error", f"Failed to export audit reports: {e}")
        else:
            self.statusBar().showMessage("Audit logs form not available for export")
    
    def generate_security_report(self):
        """Generate security report (placeholder)"""
        self.on_tab_clicked("Dashboard")
        self.dashboard_tabs.setCurrentIndex(2)  # Reports tab
        QMessageBox.information(self, "Coming Soon", "Security reports feature will be available in the next update")

    #Global refresh all data
    def refresh_all_data(self):
        """Refresh all data across dashboard tabs"""
        current_tab = self.dashboard_tabs.currentIndex()
        
        # Refresh based on current dashboard tab
        if current_tab == 0:  # Overview tab
            self.load_dashboard_stats()
            self.statusBar().showMessage("Dashboard overview refreshed!")
        elif current_tab == 1 and hasattr(self, 'users_form'):  # Users tab
            self.refresh_user_data()
        elif current_tab == 2:  # Reports tab
            # Refresh based on which reports subtab is active
            current_report_tab = self.reports_tabs.currentIndex()
            if current_report_tab == 0 and hasattr(self, 'login_logs_form'):  # Login Logs
                self.login_logs_form.load_login_logs()
                self.statusBar().showMessage("Login logs refreshed!")
            else:
                self.statusBar().showMessage("Reports data refreshed!")
        else:
            self.statusBar().showMessage("Refresh completed")
 

    #for system
    def settings_action(self):
        """Handle settings action"""
        QMessageBox.information(self, "Settings", "Settings panel will be implemented here.")

    def new_action(self):
        """Handle new action"""
        QMessageBox.information(self, "New", "New action triggered from ribbon.")

    def open_action(self):
        """Handle open action"""
        QMessageBox.information(self, "Open", "Open action triggered from ribbon.")

    def print_action(self):
        """Handle print action"""
        QMessageBox.information(self, "Print", "Print action triggered from ribbon.")

    def create_sidebar(self):
        """Create modern floating sidebar with animations"""
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
        self.sidebar_frame.setFixedHeight(self.height() - 140)  # Adjust for toolbar height
        self.sidebar_frame.move(-300, 80)
    
        self.sidebar_frame.setWindowFlags(Qt.Widget | Qt.FramelessWindowHint)
        self.sidebar_frame.setAttribute(Qt.WA_TranslucentBackground, False)
        self.sidebar_frame.raise_()
        self.sidebar_frame.setParent(self)
    
        # Drop shadow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(25)
        shadow.setColor(QColor(0, 0, 0, 120))
        shadow.setOffset(8, 8)
        self.sidebar_frame.setGraphicsEffect(shadow)
    
        # Main sidebar layout
        layout = QVBoxLayout(self.sidebar_frame)
        layout.setContentsMargins(15, 30, 15, 15)
        layout.setSpacing(8)
    
        # --- Menu Header ---
        menu_header = QLabel("MENU")
        menu_header.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 18px;
                font-weight: bold;
                letter-spacing: 2px;
            }
        """)
        menu_header.setAlignment(Qt.AlignLeft)
        layout.addWidget(menu_header)
    
        # --- Title Container ---
        title_container = QWidget()
        title_container.setStyleSheet("""
            QWidget {
                background: rgba(0, 0, 0, 0.2);
                border-radius: 8px;
                border: 1px solid rgba(255, 255, 255, 0.1);
                margin-bottom: 10px;
            }
        """)
        title_layout = QVBoxLayout(title_container)
        title_layout.setContentsMargins(15, 15, 15, 15)
    
        title = QLabel("CBCentra SMS")
        title.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 22px;
                font-weight: bold;
                background: transparent;
            }
        """)
        title.setAlignment(Qt.AlignCenter)
    
        subtitle = QLabel("School Management System")
        subtitle.setStyleSheet("""
            QLabel {
                color: #e0e0e0;
                font-size: 12px;
                font-weight: normal;
                background: transparent;
            }
        """)
        subtitle.setAlignment(Qt.AlignCenter)
    
        title_layout.addWidget(title)
        title_layout.addWidget(subtitle)
        layout.addWidget(title_container)
    
        # --- Action Buttons ---
        actions = [
            ("Home", self.home_action, "home.jpg"),
            ("Dashboard", self.dashboard_action, "dashboard.jpg"),
            ("New", self.new_action, "new.jpg"),
            ("Open", self.open_action, "open.jpg"),
            ("Info", self.info_action, "info.jpg"),
            ("Print", self.print_action, "print.jpg"),
            ("Import", self.import_action, "import.jpg"),
            ("Export", self.export_action, "export.jpg"),
            ("Settings", self.settings_action, "settings.jpg"),
            ("Options", self.options_action, "options.jpg"),
            ("Quit", self.close, "quit.jpg")
        ]
    
        for name, func, icon in actions:
            btn = QPushButton(f"  {name}")
            btn.setObjectName("menuAction")
    
            icon_path = f"static/icons/{icon}"
            if os.path.exists(icon_path):
                btn.setIcon(QIcon(icon_path))
                btn.setIconSize(QSize(28, 28))
    
            btn.clicked.connect(func)
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
            "Students": 3,
            "Exams": 4,
            "Activities": 5,
            "Finance": 6,
            "Others": 7
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
        """Handle window resize to adjust sidebar height"""
        super().resizeEvent(event)
        if hasattr(self, 'sidebar_frame'):
            new_height = self.height() - 140
            self.sidebar_frame.setFixedHeight(new_height)
            # Ensure sidebar stays on top after resize
            if self.sidebar_visible:
                self.sidebar_frame.raise_()
        
        # Resize overlay to match window
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
