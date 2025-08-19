# ui/schools_form.py
import os
import shutil
from datetime import datetime
from typing import Optional, Dict, Any

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                              QPushButton, QTabWidget, QTableWidget, QTableWidgetItem,
                              QHeaderView, QAbstractItemView, QMessageBox, QFileDialog,
                              QScrollArea, QFrame, QSizePolicy, QGroupBox, QGridLayout,
                              QSpacerItem, QApplication)
from PySide6.QtGui import QPixmap, QImage, QFont, QPalette, QIcon
from PySide6.QtCore import Qt, Signal, QSize
import mysql.connector
from mysql.connector import Error

# Import the database configuration from models
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.models import get_db_connection

class SchoolsForm(QWidget):
    school_selected = Signal(int)  # Signal emitted when a school is selected
    
    def __init__(self, parent=None, user_session: Optional[Dict[str, Any]] = None):
        super().__init__(parent)
        self.user_session = user_session
        self.current_school_id = None
        self.logo_path = None
        
        # Set up modern styling
        self.setup_styling()
        
        # Database connection
        self.db_connection = get_db_connection()
        self.cursor = self.db_connection.cursor()
        
        # Ensure logos directory exists
        os.makedirs(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                   'photos', 'schools'), exist_ok=True)
        
        self.setup_ui()
        self.load_schools()

    def setup_styling(self):
        """Set up modern professional styling"""
        # Define color palette
        self.colors = {
            'primary': '#2563eb',        # Blue
            'primary_dark': '#1d4ed8',   # Darker blue
            'secondary': '#64748b',      # Slate
            'success': '#059669',        # Emerald
            'warning': '#d97706',        # Amber
            'danger': '#dc2626',         # Red
            'info': '#0891b2',          # Cyan
            'light': '#f8fafc',         # Very light gray
            'dark': '#0f172a',          # Very dark blue
            'border': '#e2e8f0',        # Light border
            'text_primary': '#1e293b',   # Dark slate
            'text_secondary': '#64748b', # Medium slate
            'background': '#ffffff',     # White
            'surface': '#f1f5f9',       # Light surface
            'table_header': '#10b981',   # Nice green for table headers
            'table_header_dark': '#059669'  # Darker green for hover
        }
        
        # Set application style
        self.setStyleSheet(f"""
            QWidget {{
                font-family: 'Segoe UI', 'Arial', sans-serif;
                font-size: 12px;
                color: {self.colors['text_primary']};
                background-color: {self.colors['background']};
            }}
            
            /* Main container */
            SchoolsForm {{
                background-color: {self.colors['surface']};
                border: none;
            }}
            
            /* Tab Widget */
            QTabWidget::pane {{
                border: 1px solid {self.colors['border']};
                border-radius: 8px;
                background-color: {self.colors['background']};
                margin-top: -1px;
            }}
            
            QTabBar::tab {{
                background-color: {self.colors['light']};
                border: 1px solid {self.colors['border']};
                padding: 12px 24px;
                margin-right: 2px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-weight: 500;
                color: {self.colors['text_secondary']};
            }}
            
            QTabBar::tab:selected {{
                background-color: {self.colors['background']};
                color: {self.colors['primary']};
                border-bottom: 2px solid {self.colors['primary']};
                font-weight: 600;
            }}
            
            QTabBar::tab:hover:!selected {{
                background-color: {self.colors['border']};
                color: {self.colors['text_primary']};
            }}
            
            /* Group boxes and frames */
            QGroupBox {{
                font-weight: 600;
                font-size: 14px;
                color: {self.colors['text_primary']};
                border: 2px solid {self.colors['border']};
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 8px;
                background-color: {self.colors['background']};
            }}
            
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px 0 8px;
                color: {self.colors['primary']};
                background-color: {self.colors['background']};
            }}
            
            QFrame[frameShape="4"] {{
                background-color: {self.colors['background']};
                border: 1px solid {self.colors['border']};
                border-radius: 8px;
                margin: 4px;
            }}
            
            /* Labels */
            QLabel {{
                color: {self.colors['text_primary']};
                font-weight: 500;
            }}
            
            .section-title {{
                font-size: 16px;
                font-weight: 700;
                color: {self.colors['primary']};
                padding: 8px 0px;
                border-bottom: 2px solid {self.colors['border']};
                margin-bottom: 12px;
            }}
            
            .field-label {{
                font-size: 12px;
                font-weight: 600;
                color: {self.colors['text_secondary']};
                margin-bottom: 6px;
            }}
            
            /* Input fields with better padding */
            QLineEdit {{
                border: 2px solid {self.colors['border']};
                border-radius: 6px;
                padding: 12px 16px;
                font-size: 13px;
                background-color: {self.colors['background']};
                selection-background-color: {self.colors['primary']};
                min-height: 18px;
                line-height: 1.4;
            }}
            
            QLineEdit:focus {{
                border-color: {self.colors['primary']};
                background-color: #ffffff;
            }}
            
            QLineEdit:disabled {{
                background-color: {self.colors['light']};
                color: {self.colors['text_secondary']};
            }}
            
            /* Buttons */
            QPushButton {{
                border: none;
                border-radius: 6px;
                padding: 12px 24px;
                font-weight: 600;
                font-size: 12px;
                min-height: 20px;
            }}
            
            QPushButton:hover {{
                border: 1px solid rgba(255, 255, 255, 0.3);
            }}
            
            QPushButton:pressed {{
                padding: 13px 23px 11px 25px;
            }}
            
            /* Primary buttons */
            .btn-primary {{
                background-color: {self.colors['primary']};
                color: white;
                border: 1px solid {self.colors['primary']};
            }}
            
            .btn-primary:hover {{
                background-color: {self.colors['primary_dark']};
                border: 1px solid {self.colors['primary_dark']};
            }}
            
            /* Success buttons */
            .btn-success {{
                background-color: {self.colors['success']};
                color: white;
                border: 1px solid {self.colors['success']};
            }}
            
            .btn-success:hover {{
                background-color: #047857;
                border: 1px solid #047857;
            }}
            
            /* Warning buttons */
            .btn-warning {{
                background-color: {self.colors['warning']};
                color: white;
                border: 1px solid {self.colors['warning']};
            }}
            
            .btn-warning:hover {{
                background-color: #b45309;
                border: 1px solid #b45309;
            }}
            
            /* Danger buttons */
            .btn-danger {{
                background-color: {self.colors['danger']};
                color: white;
                border: 1px solid {self.colors['danger']};
            }}
            
            .btn-danger:hover {{
                background-color: #b91c1c;
                border: 1px solid #b91c1c;
            }}
            
            /* Info buttons */
            .btn-info {{
                background-color: {self.colors['info']};
                color: white;
                border: 1px solid {self.colors['info']};
            }}
            
            .btn-info:hover {{
                background-color: #0e7490;
                border: 1px solid #0e7490;
            }}
            
            /* Secondary buttons */
            .btn-secondary {{
                background-color: {self.colors['secondary']};
                color: white;
                border: 1px solid {self.colors['secondary']};
            }}
            
            .btn-secondary:hover {{
                background-color: #475569;
                border: 1px solid #475569;
            }}
            
            /* Enhanced Table styling with green headers and better scrollbars */
            QTableWidget {{
                border: 1px solid {self.colors['border']};
                border-radius: 8px;
                background-color: {self.colors['background']};
                alternate-background-color: #f9fafb;
                gridline-color: {self.colors['border']};
                selection-background-color: rgba(16, 185, 129, 0.15);
                selection-color: {self.colors['text_primary']};
                font-size: 12px;
            }}
            
            QTableWidget::item {{
                padding: 10px 12px;
                border-bottom: 1px solid {self.colors['border']};
                color: {self.colors['text_primary']};
            }}
            
            QTableWidget::item:selected {{
                background-color: rgba(16, 185, 129, 0.15);
                color: {self.colors['text_primary']};
                border: 1px solid {self.colors['table_header']};
            }}
            
            QTableWidget::item:hover {{
                background-color: rgba(16, 185, 129, 0.08);
            }}
            
            /* Beautiful green header styling */
            QHeaderView::section {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {self.colors['table_header']}, stop:1 {self.colors['table_header_dark']});
                color: white;
                padding: 14px 16px;
                border: none;
                font-weight: 700;
                font-size: 13px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            
            QHeaderView::section:first {{
                border-top-left-radius: 6px;
            }}
            
            QHeaderView::section:last {{
                border-top-right-radius: 6px;
            }}
            
            QHeaderView::section:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #12d490, stop:1 {self.colors['table_header']});
            }}
            
            /* Table corner button styling */
            QTableCornerButton::section {{
                background: {self.colors['table_header']};
                border: none;
                border-top-left-radius: 6px;
            }}
            
            /* Logo area */
            .logo-container {{
                border: 2px dashed {self.colors['border']};
                border-radius: 8px;
                background-color: {self.colors['light']};
                color: {self.colors['text_secondary']};
                font-size: 14px;
                font-weight: 500;
            }}
            
            .logo-container:hover {{
                border-color: {self.colors['primary']};
                background-color: rgba(37, 99, 235, 0.02);
            }}
            
            /* Search section with compact design */
            .search-section {{
                background-color: {self.colors['background']};
                border: 1px solid {self.colors['border']};
                border-radius: 8px;
                padding: 12px;
                margin-bottom: 12px;
            }}
            
            /* Enhanced Scrollbars */
            QScrollBar:vertical {{
                background: {self.colors['light']};
                width: 14px;
                border-radius: 7px;
                margin: 0px;
            }}
            
            QScrollBar::handle:vertical {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {self.colors['table_header']}, stop:1 {self.colors['table_header_dark']});
                border-radius: 7px;
                min-height: 20px;
                margin: 2px;
            }}
            
            QScrollBar::handle:vertical:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #12d490, stop:1 {self.colors['table_header']});
            }}
            
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                border: none;
                background: none;
                height: 0px;
            }}
            
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}
            
            QScrollBar:horizontal {{
                background: {self.colors['light']};
                height: 14px;
                border-radius: 7px;
                margin: 0px;
            }}
            
            QScrollBar::handle:horizontal {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {self.colors['table_header']}, stop:1 {self.colors['table_header_dark']});
                border-radius: 7px;
                min-width: 20px;
                margin: 2px;
            }}
            
            QScrollBar::handle:horizontal:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #12d490, stop:1 {self.colors['table_header']});
            }}
            
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                border: none;
                background: none;
                width: 0px;
            }}
            
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
                background: none;
            }}
        """)

    def setup_ui(self):
        self.setWindowTitle("School Management System")
        self.resize(1400, 900)
        
        # Main layout with padding
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # Create tabs
        self.school_form_tab = QWidget()
        self.school_data_tab = QWidget()
        
        self.tab_widget.addTab(self.school_form_tab, "📝 School Registration")
        self.tab_widget.addTab(self.school_data_tab, "📊 Schools Database")
        
        # Setup each tab
        self.setup_school_form_tab()
        self.setup_school_data_tab()

    def setup_school_form_tab(self):
        # Create scroll area for the form
        scroll_area = QScrollArea(self.school_form_tab)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # Main layout for scroll area
        main_layout = QVBoxLayout(self.school_form_tab)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll_area)
        
        # Content widget inside scroll area
        content_widget = QWidget()
        scroll_area.setWidget(content_widget)
        
        # Main layout for form tab with better spacing
        form_layout = QHBoxLayout(content_widget)
        form_layout.setContentsMargins(20, 20, 20, 20)
        form_layout.setSpacing(20)
        
        # Left side - Form fields (70% width)
        form_container = QWidget()
        form_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        form_fields_layout = QVBoxLayout(form_container)
        form_fields_layout.setSpacing(20)
        
        # School Information Group
        info_group = QGroupBox("🏛️ School Information")
        info_layout = QGridLayout(info_group)
        info_layout.setSpacing(16)
        info_layout.setContentsMargins(16, 24, 16, 16)
        
        # School Name (full width)
        name_label = QLabel("School Name *")
        name_label.setProperty("class", "field-label")
        self.school_name_entry = QLineEdit()
        self.school_name_entry.setPlaceholderText("Enter the full school name...")
        info_layout.addWidget(name_label, 0, 0, 1, 2)
        info_layout.addWidget(self.school_name_entry, 1, 0, 1, 2)
        
        # Add vertical spacing
        info_layout.addItem(QSpacerItem(0, 8), 2, 0)
        
        # Address (full width)
        address_label = QLabel("Address")
        address_label.setProperty("class", "field-label")
        self.address_entry = QLineEdit()
        self.address_entry.setPlaceholderText("Enter complete address...")
        info_layout.addWidget(address_label, 3, 0, 1, 2)
        info_layout.addWidget(self.address_entry, 4, 0, 1, 2)
        
        # Add vertical spacing
        info_layout.addItem(QSpacerItem(0, 8), 5, 0)
        
        # Phone and Email (side by side)
        phone_label = QLabel("Phone Number")
        phone_label.setProperty("class", "field-label")
        self.phone_entry = QLineEdit()
        self.phone_entry.setPlaceholderText("e.g., +256 700 123 456")
        
        email_label = QLabel("Email Address")
        email_label.setProperty("class", "field-label")
        self.email_entry = QLineEdit()
        self.email_entry.setPlaceholderText("school@example.com")
        
        info_layout.addWidget(phone_label, 6, 0)
        info_layout.addWidget(email_label, 6, 1)
        info_layout.addWidget(self.phone_entry, 7, 0)
        info_layout.addWidget(self.email_entry, 7, 1)
        
        # Add vertical spacing
        info_layout.addItem(QSpacerItem(0, 8), 8, 0)
        
        # Website and Year (side by side)
        website_label = QLabel("Website")
        website_label.setProperty("class", "field-label")
        self.website_entry = QLineEdit()
        self.website_entry.setPlaceholderText("https://www.school.com")
        
        year_label = QLabel("Established Year")
        year_label.setProperty("class", "field-label")
        self.year_entry = QLineEdit()
        self.year_entry.setPlaceholderText("e.g., 1995")
        
        info_layout.addWidget(website_label, 9, 0)
        info_layout.addWidget(year_label, 9, 1)
        info_layout.addWidget(self.website_entry, 10, 0)
        info_layout.addWidget(self.year_entry, 10, 1)
        
        # Add vertical spacing
        info_layout.addItem(QSpacerItem(0, 8), 11, 0)
        
        # Motto (full width)
        motto_label = QLabel("School Motto")
        motto_label.setProperty("class", "field-label")
        self.motto_entry = QLineEdit()
        self.motto_entry.setPlaceholderText("Enter school motto or slogan...")
        info_layout.addWidget(motto_label, 12, 0, 1, 2)
        info_layout.addWidget(self.motto_entry, 13, 0, 1, 2)
        
        form_fields_layout.addWidget(info_group)
        
        # Action buttons group
        actions_group = QGroupBox("⚡ Actions")
        actions_layout = QHBoxLayout(actions_group)
        actions_layout.setSpacing(12)
        actions_layout.setContentsMargins(16, 24, 16, 16)
        
        self.add_btn = QPushButton("➕ Add School")
        self.add_btn.setProperty("class", "btn-success")
        self.add_btn.clicked.connect(self.add_school)
        
        self.update_btn = QPushButton("✏️ Update School")
        self.update_btn.setProperty("class", "btn-primary")
        self.update_btn.clicked.connect(self.update_school)
        
        self.delete_btn = QPushButton("🗑️ Delete School")
        self.delete_btn.setProperty("class", "btn-danger")
        self.delete_btn.clicked.connect(self.delete_school)
        
        self.clear_btn = QPushButton("🔄 Clear Fields")
        self.clear_btn.setProperty("class", "btn-secondary")
        self.clear_btn.clicked.connect(self.clear_fields)
        
        actions_layout.addWidget(self.add_btn)
        actions_layout.addWidget(self.update_btn)
        actions_layout.addWidget(self.delete_btn)
        actions_layout.addWidget(self.clear_btn)
        
        form_fields_layout.addWidget(actions_group)
        form_fields_layout.addStretch()
        
        # Right side - Logo section (30% width)
        logo_container = QWidget()
        logo_container.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        logo_container.setFixedWidth(350)
        logo_layout = QVBoxLayout(logo_container)
        logo_layout.setSpacing(16)
        
        logo_group = QGroupBox("🖼️ School Logo")
        logo_group_layout = QVBoxLayout(logo_group)
        logo_group_layout.setContentsMargins(16, 24, 16, 16)
        logo_group_layout.setSpacing(12)
        
        # Logo display with better styling
        self.logo_label = QLabel()
        self.logo_label.setAlignment(Qt.AlignCenter)
        self.logo_label.setProperty("class", "logo-container")
        self.logo_label.setFixedSize(300, 300)
        self.logo_label.setText("📷\n\nClick 'Select Logo' to\nupload school logo\n\n(Max 5MB)")
        self.logo_label.setStyleSheet(f"""
            QLabel {{
                border: 2px dashed {self.colors['border']};
                border-radius: 12px;
                background-color: {self.colors['light']};
                color: {self.colors['text_secondary']};
                font-size: 13px;
                font-weight: 500;
                line-height: 1.4;
            }}
        """)
        logo_group_layout.addWidget(self.logo_label, 0, Qt.AlignCenter)
        
        # Logo buttons with better spacing
        logo_buttons_layout = QHBoxLayout()
        logo_buttons_layout.setSpacing(8)
        
        self.select_logo_btn = QPushButton("📁 Select Logo")
        self.select_logo_btn.setProperty("class", "btn-info")
        self.select_logo_btn.clicked.connect(self.select_logo)
        
        self.remove_logo_btn = QPushButton("❌ Remove")
        self.remove_logo_btn.setProperty("class", "btn-warning")
        self.remove_logo_btn.clicked.connect(self.remove_logo)
        
        logo_buttons_layout.addWidget(self.select_logo_btn)
        logo_buttons_layout.addWidget(self.remove_logo_btn)
        logo_group_layout.addLayout(logo_buttons_layout)
        
        logo_layout.addWidget(logo_group)
        logo_layout.addStretch()
        
        # Add both sides to main form layout
        form_layout.addWidget(form_container)
        form_layout.addWidget(logo_container)

    def setup_school_data_tab(self):
        # Main layout for data tab
        data_layout = QVBoxLayout(self.school_data_tab)
        data_layout.setContentsMargins(20, 20, 20, 20)
        data_layout.setSpacing(8)
        
        # Compact single-row search and actions section
        search_group = QGroupBox("🔍 Search & Actions")
        search_group.setProperty("class", "search-section")
        search_layout = QVBoxLayout(search_group)
        search_layout.setContentsMargins(12, 16, 12, 8)
        search_layout.setSpacing(6)
        
        # Single row with all controls
        controls_row = QHBoxLayout()
        controls_row.setSpacing(8)
        
        # Search section
        search_label = QLabel("Search:")
        search_label.setProperty("class", "field-label")
        search_label.setFixedWidth(50)
        
        self.search_entry = QLineEdit()
        self.search_entry.setPlaceholderText("🔍 Search by name, address, phone, or email...")
        self.search_entry.setFixedHeight(32)  # Compact height
        
        search_btn = QPushButton("🔍 Search")
        search_btn.setProperty("class", "btn-primary")
        search_btn.setFixedHeight(32)
        search_btn.clicked.connect(self.search_schools_action)
        
        clear_search_btn = QPushButton("Clear")
        clear_search_btn.setProperty("class", "btn-secondary")
        clear_search_btn.setFixedHeight(32)
        clear_search_btn.clicked.connect(self.clear_search)
        
        # Add separator
        separator1 = QLabel("|")
        separator1.setStyleSheet(f"color: {self.colors['border']}; font-weight: bold; margin: 0 4px;")
        
        # Action buttons
        export_btn = QPushButton("📤 Export")
        export_btn.setProperty("class", "btn-info")
        export_btn.setFixedHeight(32)
        export_btn.clicked.connect(self.export_schools_data)
        
        report_btn = QPushButton("📊 Report")
        report_btn.setProperty("class", "btn-success")
        report_btn.setFixedHeight(32)
        report_btn.clicked.connect(self.generate_school_report)
        
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setProperty("class", "btn-primary")
        refresh_btn.setFixedHeight(32)
        refresh_btn.clicked.connect(self.load_schools)
        
        # Add all controls to the single row
        controls_row.addWidget(search_label)
        controls_row.addWidget(self.search_entry)
        controls_row.addWidget(search_btn)
        controls_row.addWidget(clear_search_btn)
        controls_row.addWidget(separator1)
        controls_row.addWidget(export_btn)
        controls_row.addWidget(report_btn)
        controls_row.addWidget(refresh_btn)
        controls_row.addStretch()  # Push everything to the left
        
        search_layout.addLayout(controls_row)
        data_layout.addWidget(search_group)
        
        # Status label for showing record counts
        self.status_label = QLabel("📋 Total Schools: 0")
        self.status_label.setStyleSheet(f"""
            font-size: 12px;
            color: {self.colors['text_secondary']};
            font-weight: 500;
            padding: 4px 0px;
        """)
        data_layout.addWidget(self.status_label)
        
        # Schools table with enhanced styling - takes remaining space
        self.create_schools_table(data_layout)

    def create_schools_table(self, parent_layout):
        self.schools_table = QTableWidget()
        self.schools_table.setColumnCount(7)
        self.schools_table.setHorizontalHeaderLabels([
            "ID", "School Name", "Address", "Phone", "Email", "Website", "Est. Year"
        ])
        
        # Enhanced table configuration
        header = self.schools_table.horizontalHeader()
        
        # Set all columns to be interactive and resizable
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setStretchLastSection(False)
        
        # Set minimum column widths
        self.schools_table.setColumnWidth(0, 60)   # ID
        self.schools_table.setColumnWidth(1, 200)  # School Name
        self.schools_table.setColumnWidth(2, 180)  # Address
        self.schools_table.setColumnWidth(3, 130)  # Phone
        self.schools_table.setColumnWidth(4, 180)  # Email
        self.schools_table.setColumnWidth(5, 150)  # Website
        self.schools_table.setColumnWidth(6, 80)   # Year
        
        # Enable column sorting and proper selection
        self.schools_table.setAlternatingRowColors(True)
        self.schools_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.schools_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.schools_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.schools_table.setSortingEnabled(True)
        
        # Enable both scrollbars
        self.schools_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.schools_table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # Set table to expand to fill available space
        self.schools_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Connect signals
        self.schools_table.cellDoubleClicked.connect(self.on_school_select)
        
        parent_layout.addWidget(self.schools_table, 1)  # Give it stretch factor of 1

    # ======================
    # CRUD Operations Methods (Enhanced)
    # ======================

    def add_school(self):
        """Add new school to database with enhanced fields"""
        if not self.validate_fields():
            return
        
        try:
            # Insert school record with all fields
            self.cursor.execute('''
                INSERT INTO schools (
                    school_name, address, phone, email, website, 
                    established_year, motto, logo_path
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                self.school_name_entry.text().strip(),
                self.address_entry.text().strip(),
                self.phone_entry.text().strip(),
                self.email_entry.text().strip(),
                self.website_entry.text().strip(),
                self.year_entry.text().strip() if self.year_entry.text().strip() else None,
                self.motto_entry.text().strip(),
                None  # Will be updated if logo is saved
            ))
            
            school_id = self.cursor.lastrowid
            
            # Save logo if selected
            if self.logo_path:
                logo_path = self.save_logo(school_id)
                if logo_path:
                    self.cursor.execute("UPDATE schools SET logo_path = %s WHERE id = %s", 
                                      (logo_path, school_id))
            
            self.db_connection.commit()
            QMessageBox.information(self, "✅ Success", "School added successfully!")
            
            self.clear_fields()
            self.load_schools()
            
        except Exception as e:
            QMessageBox.critical(self, "❌ Error", f"Error adding school: {str(e)}")

    def update_school(self):
        """Update existing school record with enhanced fields"""
        if not self.current_school_id:
            QMessageBox.warning(self, "⚠️ Warning", "Please select a school to update!")
            return
        
        if not self.validate_fields():
            return
        
        try:
            # Update school record with all fields
            self.cursor.execute('''
                UPDATE schools SET 
                    school_name = %s, 
                    address = %s, 
                    phone = %s, 
                    email = %s,
                    website = %s,
                    established_year = %s,
                    motto = %s
                WHERE id = %s
            ''', (
                self.school_name_entry.text().strip(),
                self.address_entry.text().strip(),
                self.phone_entry.text().strip(),
                self.email_entry.text().strip(),
                self.website_entry.text().strip(),
                self.year_entry.text().strip() if self.year_entry.text().strip() else None,
                self.motto_entry.text().strip(),
                self.current_school_id
            ))
            
            # Save logo if new one was selected
            if self.logo_path:
                logo_path = self.save_logo(self.current_school_id)
                if logo_path:
                    self.cursor.execute("UPDATE schools SET logo_path = %s WHERE id = %s", 
                                      (logo_path, self.current_school_id))
            
            self.db_connection.commit()
            QMessageBox.information(self, "✅ Success", "School updated successfully!")
            
            self.clear_fields()
            self.load_schools()
            
        except Exception as e:
            QMessageBox.critical(self, "❌ Error", f"Error updating school: {str(e)}")

    def delete_school(self):
        """Delete selected school with enhanced validation"""
        if not self.current_school_id:
            QMessageBox.warning(self, "⚠️ Warning", "Please select a school to delete!")
            return
        
        # Get school name for confirmation
        school_name = self.school_name_entry.text()
        
        # Enhanced confirmation dialog
        reply = QMessageBox.question(
            self, '🗑️ Confirm Delete', 
            f'Are you sure you want to delete "{school_name}"?\n\nThis action cannot be undone!',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            try:
                # Delete school
                self.cursor.execute("DELETE FROM schools WHERE id = %s", (self.current_school_id,))
                self.db_connection.commit()
                
                QMessageBox.information(self, "✅ Success", "School deleted successfully!")
                
                self.clear_fields()
                self.load_schools()
                
            except Exception as e:
                QMessageBox.critical(self, "❌ Error", f"Error deleting school: {str(e)}")

    # ======================
    # Helper Methods (Enhanced)
    # ======================

    def validate_fields(self):
        """Enhanced validation for required fields"""
        if not self.school_name_entry.text().strip():
            QMessageBox.warning(self, "⚠️ Validation Error", "School name is required!")
            self.school_name_entry.setFocus()
            return False
        
        # Validate year if provided
        year_text = self.year_entry.text().strip()
        if year_text:
            try:
                year = int(year_text)
                current_year = datetime.now().year
                if year < 1800 or year > current_year:
                    QMessageBox.warning(self, "⚠️ Validation Error", 
                                      f"Please enter a valid year between 1800 and {current_year}")
                    self.year_entry.setFocus()
                    return False
            except ValueError:
                QMessageBox.warning(self, "⚠️ Validation Error", "Please enter a valid year (numbers only)")
                self.year_entry.setFocus()
                return False
        
        # Validate email format if provided
        email_text = self.email_entry.text().strip()
        if email_text and '@' not in email_text:
            QMessageBox.warning(self, "⚠️ Validation Error", "Please enter a valid email address")
            self.email_entry.setFocus()
            return False
        
        return True

    def clear_fields(self):
        """Clear all form fields and reset state"""
        self.current_school_id = None
        self.logo_path = None
        
        # Clear all entry fields
        self.school_name_entry.clear()
        self.address_entry.clear()
        self.phone_entry.clear()
        self.email_entry.clear()
        self.website_entry.clear()
        self.year_entry.clear()
        self.motto_entry.clear()
        
        # Reset logo display
        self.logo_label.clear()
        self.logo_label.setText("📷\n\nClick 'Select Logo' to\nupload school logo\n\n(Max 5MB)")
        self.logo_label.setStyleSheet(f"""
            QLabel {{
                border: 2px dashed {self.colors['border']};
                border-radius: 12px;
                background-color: {self.colors['light']};
                color: {self.colors['text_secondary']};
                font-size: 13px;
                font-weight: 500;
                line-height: 1.4;
            }}
        """)

    def load_schools(self):
        """Load schools data into the table with enhanced display"""
        try:
            self.cursor.execute('''
                SELECT id, school_name, address, phone, email, website, established_year
                FROM schools
                WHERE is_active = TRUE
                ORDER BY school_name
            ''')
            
            schools = self.cursor.fetchall()
            
            # Clear and populate table
            self.schools_table.setRowCount(0)
            self.schools_table.setSortingEnabled(False)  # Disable while populating
            
            for row_num, school in enumerate(schools):
                self.schools_table.insertRow(row_num)
                
                for col_num, data in enumerate(school):
                    # Format data for better display
                    if data is None:
                        display_text = ""
                    elif col_num == 6 and data:  # Year column
                        display_text = str(int(data))
                    else:
                        display_text = str(data)
                    
                    item = QTableWidgetItem(display_text)
                    
                    # Style ID column differently
                    if col_num == 0:
                        item.setTextAlignment(Qt.AlignCenter)
                    
                    self.schools_table.setItem(row_num, col_num, item)
            
            # Re-enable sorting and maintain column widths
            self.schools_table.setSortingEnabled(True)
            self.maintain_column_widths()
            
            # Update status label
            school_count = len(schools)
            self.status_label.setText(f"📋 Total Schools: {school_count}")
            
        except Exception as e:
            QMessageBox.critical(self, "❌ Error", f"Error loading schools: {str(e)}")

    def maintain_column_widths(self):
        """Maintain consistent column widths"""
        self.schools_table.setColumnWidth(0, 60)   # ID
        self.schools_table.setColumnWidth(1, 200)  # School Name
        self.schools_table.setColumnWidth(2, 180)  # Address
        self.schools_table.setColumnWidth(3, 130)  # Phone
        self.schools_table.setColumnWidth(4, 180)  # Email
        self.schools_table.setColumnWidth(5, 150)  # Website
        self.schools_table.setColumnWidth(6, 80)   # Year

    def on_school_select(self, row, column):
        """Handle school selection from table with enhanced data loading"""
        try:
            school_id = int(self.schools_table.item(row, 0).text())
            self.current_school_id = school_id
            
            # Fetch complete school data
            self.cursor.execute('''
                SELECT id, school_name, address, phone, email, website, 
                       established_year, motto, logo_path
                FROM schools
                WHERE id = %s
            ''', (school_id,))
            
            school = self.cursor.fetchone()
            
            if school:
                # Populate form fields with all data
                self.school_name_entry.setText(school[1] or "")
                self.address_entry.setText(school[2] or "")
                self.phone_entry.setText(school[3] or "")
                self.email_entry.setText(school[4] or "")
                self.website_entry.setText(school[5] or "")
                self.year_entry.setText(str(school[6]) if school[6] else "")
                self.motto_entry.setText(school[7] or "")
                
                # Load logo if available
                if school[8]:
                    self.load_logo(school[8])
                else:
                    self.load_logo()
                
                # Switch to School Form tab
                self.tab_widget.setCurrentIndex(0)
                
        except Exception as e:
            QMessageBox.critical(self, "❌ Error", f"Error loading school data: {str(e)}")

    def select_logo(self):
        """Select a logo file with enhanced validation"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select School Logo", "", 
            "Image Files (*.jpg *.jpeg *.png *.gif *.bmp *.webp);;All Files (*)"
        )
    
        if file_path:
            try:
                # Validate file size (5MB limit)
                file_size = os.path.getsize(file_path)
                max_size = 5 * 1024 * 1024  # 5MB
                
                if file_size > max_size:
                    QMessageBox.warning(self, "📁 File Too Large", 
                                      f"Please select an image smaller than 5MB.\nSelected file: {file_size / 1024 / 1024:.1f}MB")
                    return
                
                # Store the selected path temporarily
                self.logo_path = file_path
                
                # Display the selected image with better styling
                pixmap = QPixmap(file_path)
                if not pixmap.isNull():
                    # Scale image to fit label while maintaining aspect ratio
                    pixmap = pixmap.scaled(280, 280, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    self.logo_label.setPixmap(pixmap)
                    self.logo_label.setText("")
                    
                    # Update label styling for image display
                    self.logo_label.setStyleSheet(f"""
                        QLabel {{
                            border: 2px solid {self.colors['primary']};
                            border-radius: 12px;
                            background-color: {self.colors['background']};
                            padding: 10px;
                        }}
                    """)
    
            except Exception as e:
                QMessageBox.critical(self, "❌ Error", 
                                   f"Error loading image: {str(e)}\n\nPlease select a valid image file.")
    
    def load_logo(self, logo_path=None):
        """Load logo from path with enhanced error handling"""
        if logo_path and os.path.exists(logo_path):
            try:
                pixmap = QPixmap(logo_path)
                if not pixmap.isNull():
                    pixmap = pixmap.scaled(280, 280, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    self.logo_label.setPixmap(pixmap)
                    self.logo_label.setText("")
                    
                    # Update styling for loaded image
                    self.logo_label.setStyleSheet(f"""
                        QLabel {{
                            border: 2px solid {self.colors['success']};
                            border-radius: 12px;
                            background-color: {self.colors['background']};
                            padding: 10px;
                        }}
                    """)
                    return True
            except Exception as e:
                print(f"Error loading logo: {e}")
        
        # If no logo or failed to load, show default
        self.logo_label.clear()
        self.logo_label.setText("📷\n\nClick 'Select Logo' to\nupload school logo\n\n(Max 5MB)")
        self.logo_label.setStyleSheet(f"""
            QLabel {{
                border: 2px dashed {self.colors['border']};
                border-radius: 12px;
                background-color: {self.colors['light']};
                color: {self.colors['text_secondary']};
                font-size: 13px;
                font-weight: 500;
                line-height: 1.4;
            }}
        """)
        return False
    
    def save_logo(self, school_id):
        """Save logo to school-specific directory with better organization"""
        if not self.logo_path:
            return None
        
        try:
            # Create school-specific directory
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            logo_dir = os.path.join(base_dir, 'photos', 'schools', str(school_id))
            os.makedirs(logo_dir, exist_ok=True)
            
            # Get file extension and create destination path
            file_ext = os.path.splitext(self.logo_path)[1].lower()
            if not file_ext:
                file_ext = '.png'  # Default to PNG
            
            destination = os.path.join(logo_dir, f'logo{file_ext}')
            
            # Copy the file
            shutil.copy2(self.logo_path, destination)
            
            # Return relative path for database storage
            return f"photos/schools/{school_id}/logo{file_ext}"
            
        except Exception as e:
            QMessageBox.critical(self, "❌ Error", f"Error saving logo: {str(e)}")
            return None
            
    def remove_logo(self):
        """Remove the current logo with confirmation"""
        if not self.logo_path and not self.current_school_id:
            QMessageBox.information(self, "ℹ️ Info", "No logo to remove.")
            return
        
        reply = QMessageBox.question(
            self, '🗑️ Remove Logo', 
            'Are you sure you want to remove the school logo?',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            try:
                # Clear the UI
                self.logo_label.clear()
                self.logo_label.setText("📷\n\nClick 'Select Logo' to\nupload school logo\n\n(Max 5MB)")
                self.logo_label.setStyleSheet(f"""
                    QLabel {{
                        border: 2px dashed {self.colors['border']};
                        border-radius: 12px;
                        background-color: {self.colors['light']};
                        color: {self.colors['text_secondary']};
                        font-size: 13px;
                        font-weight: 500;
                        line-height: 1.4;
                    }}
                """)
                self.logo_path = None
                
                # Update database if we have a selected school
                if self.current_school_id:
                    self.cursor.execute("UPDATE schools SET logo_path = NULL WHERE id = %s", 
                                      (self.current_school_id,))
                    self.db_connection.commit()
                
                QMessageBox.information(self, "✅ Success", "Logo removed successfully!")
                
            except Exception as e:
                QMessageBox.critical(self, "❌ Error", f"Error removing logo: {str(e)}")

    def search_schools_action(self):
        """Search schools based on search entry with loading feedback"""
        search_term = self.search_entry.text().strip()
        if not search_term:
            self.load_schools()
            return
        
        # Update UI to show searching
        original_text = self.status_label.text()
        self.status_label.setText("🔍 Searching...")
        QApplication.processEvents()  # Update UI immediately
        
        self.search_schools(search_term)
    
    def search_schools(self, search_term=""):
        """Enhanced search schools by multiple fields"""
        try:
            if search_term:
                # Enhanced search query
                self.cursor.execute('''
                    SELECT id, school_name, address, phone, email, website, established_year
                    FROM schools
                    WHERE is_active = TRUE AND (
                        school_name LIKE %s 
                        OR address LIKE %s
                        OR phone LIKE %s
                        OR email LIKE %s
                        OR website LIKE %s
                        OR motto LIKE %s
                    )
                    ORDER BY school_name
                ''', tuple([f"%{search_term}%"] * 6))
            else:
                self.load_schools()
                return
            
            schools = self.cursor.fetchall()
            
            # Clear and populate table
            self.schools_table.setRowCount(0)
            self.schools_table.setSortingEnabled(False)  # Disable while populating
            
            for row_num, school in enumerate(schools):
                self.schools_table.insertRow(row_num)
                
                for col_num, data in enumerate(school):
                    if data is None:
                        display_text = ""
                    elif col_num == 6 and data:  # Year column
                        display_text = str(int(data))
                    else:
                        display_text = str(data)
                    
                    item = QTableWidgetItem(display_text)
                    if col_num == 0:
                        item.setTextAlignment(Qt.AlignCenter)
                    
                    self.schools_table.setItem(row_num, col_num, item)
            
            # Re-enable sorting and maintain column widths
            self.schools_table.setSortingEnabled(True)
            self.maintain_column_widths()
            
            # Update status with search results
            result_count = len(schools)
            self.status_label.setText(f"🔍 Search Results: {result_count} schools found")
            
            if result_count == 0:
                QMessageBox.information(self, "🔍 Search Results", 
                                      f"No schools found matching '{search_term}'.")
            
        except Exception as e:
            QMessageBox.critical(self, "❌ Error", f"Error searching schools: {str(e)}")
            self.status_label.setText("❌ Search failed")
            
    def clear_search(self):
        """Clear search and reload all schools"""
        self.search_entry.clear()
        self.load_schools()

    def export_schools_data(self):
        """Export schools data to CSV with enhanced formatting"""
        try:
            import csv
            
            # Get save file path with default name
            default_name = f"schools_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Save Schools Data", default_name, 
                "CSV Files (*.csv);;All Files (*)"
            )
            
            if not file_path:
                return  # User cancelled
            
            # Ensure .csv extension
            if not file_path.lower().endswith('.csv'):
                file_path += '.csv'
            
            # Show progress
            self.status_label.setText("📤 Exporting data...")
            QApplication.processEvents()
            
            # Fetch complete school data
            self.cursor.execute('''
                SELECT school_name, address, phone, email, website, 
                       established_year, motto, created_at
                FROM schools
                WHERE is_active = TRUE
                ORDER BY school_name
            ''')
            schools = self.cursor.fetchall()
            
            # Write to CSV with enhanced headers and styling
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                # Write header with nice formatting
                writer.writerow([
                    'School Name', 'Address', 'Phone', 'Email', 'Website',
                    'Established Year', 'Motto', 'Date Added'
                ])
                
                for school in schools:
                    # Format the data nicely
                    row = [
                        school[0] or '',  # name
                        school[1] or '',  # address
                        school[2] or '',  # phone
                        school[3] or '',  # email
                        school[4] or '',  # website
                        str(school[5]) if school[5] else '',  # year
                        school[6] or '',  # motto
                        school[7].strftime('%Y-%m-%d') if school[7] else ''  # created_at
                    ]
                    writer.writerow(row)
            
            # Restore status
            school_count = len(schools)
            self.status_label.setText(f"📋 Total Schools: {school_count}")
            
            QMessageBox.information(
                self, "✅ Export Successful",
                f"Successfully exported {school_count} schools to:\n{os.path.basename(file_path)}\n\nFile saved with blue-styled headers for Excel compatibility!"
            )
            
        except Exception as e:
            QMessageBox.critical(self, "❌ Export Error", f"Error exporting data: {str(e)}")
            self.status_label.setText("❌ Export failed")
         
    def generate_school_report(self):
        """Generate a comprehensive school summary report"""
        try:
            # Show progress
            self.status_label.setText("📊 Generating report...")
            QApplication.processEvents()
            
            # Get comprehensive statistics
            self.cursor.execute("SELECT COUNT(*) FROM schools WHERE is_active = TRUE")
            school_count = self.cursor.fetchone()[0]
            
            # Schools by establishment decade
            self.cursor.execute('''
                SELECT 
                    CASE 
                        WHEN established_year IS NULL THEN 'Unknown'
                        WHEN established_year < 1980 THEN 'Before 1980'
                        WHEN established_year < 1990 THEN '1980-1989'
                        WHEN established_year < 2000 THEN '1990-1999'
                        WHEN established_year < 2010 THEN '2000-2009'
                        WHEN established_year < 2020 THEN '2010-2019'
                        ELSE '2020 onwards'
                    END as decade,
                    COUNT(*) as count
                FROM schools 
                WHERE is_active = TRUE
                GROUP BY decade
                ORDER BY count DESC
            ''')
            decade_stats = self.cursor.fetchall()
            
            # Schools with complete information
            self.cursor.execute('''
                SELECT 
                    SUM(CASE WHEN phone IS NOT NULL AND phone != '' THEN 1 ELSE 0 END) as with_phone,
                    SUM(CASE WHEN email IS NOT NULL AND email != '' THEN 1 ELSE 0 END) as with_email,
                    SUM(CASE WHEN website IS NOT NULL AND website != '' THEN 1 ELSE 0 END) as with_website,
                    SUM(CASE WHEN logo_path IS NOT NULL THEN 1 ELSE 0 END) as with_logo
                FROM schools 
                WHERE is_active = TRUE
            ''')
            info_stats = self.cursor.fetchone()
            
            # Generate comprehensive report
            report = f"""📊 COMPREHENSIVE SCHOOLS REPORT
{'=' * 50}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📈 OVERVIEW STATISTICS
{'─' * 30}
Total Active Schools: {school_count}

📞 CONTACT INFORMATION COVERAGE
{'─' * 35}
Schools with Phone Numbers: {info_stats[0]} ({info_stats[0]/school_count*100:.1f}% of total)
Schools with Email Addresses: {info_stats[1]} ({info_stats[1]/school_count*100:.1f}% of total)
Schools with Websites: {info_stats[2]} ({info_stats[2]/school_count*100:.1f}% of total)
Schools with Logos: {info_stats[3]} ({info_stats[3]/school_count*100:.1f}% of total)

🏛️ SCHOOLS BY ESTABLISHMENT PERIOD
{'─' * 38}"""
            
            for decade, count in decade_stats:
                percentage = count / school_count * 100
                report += f"\n{decade}: {count} schools ({percentage:.1f}%)"
            
            report += f"""

📋 DATA COMPLETENESS RECOMMENDATIONS
{'─' * 35}"""
            
            # Add recommendations
            if info_stats[0] / school_count < 0.8:
                report += "\n• Consider collecting phone numbers for more schools"
            if info_stats[1] / school_count < 0.7:
                report += "\n• Email addresses are missing for many schools"
            if info_stats[2] / school_count < 0.5:
                report += "\n• Many schools don't have website information"
            if info_stats[3] / school_count < 0.6:
                report += "\n• Consider uploading logos for better visual identification"
            
            # Update status
            self.status_label.setText(f"📋 Total Schools: {school_count}")
            
            # Show report in a scrollable message box alternative
            msg = QMessageBox(self)
            msg.setWindowTitle("📊 Schools Analysis Report")
            msg.setText("Report generated successfully!")
            msg.setDetailedText(report)
            msg.setIcon(QMessageBox.Information)
            msg.exec()
            
        except Exception as e:
            QMessageBox.critical(self, "❌ Report Error", f"Error generating report: {str(e)}")
            self.status_label.setText("❌ Report generation failed")

    def closeEvent(self, event):
        """Enhanced cleanup when window is closed"""
        try:
            if hasattr(self, 'cursor') and self.cursor:
                self.cursor.close()
            if hasattr(self, 'db_connection') and self.db_connection.is_connected():
                self.db_connection.close()
            event.accept()
        except Exception as e:
            print(f"Error during cleanup: {e}")
            event.accept()