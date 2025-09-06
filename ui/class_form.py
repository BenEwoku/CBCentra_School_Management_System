import sys
import os
import traceback
from typing import Optional, Dict, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QDialog,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QMessageBox, QFileDialog, QScrollArea, QFrame, QSizePolicy,
    QGroupBox, QGridLayout, QSpacerItem, QComboBox, QFormLayout, 
    QTabWidget, QMenu, QCheckBox, QDateEdit, QTextEdit, QApplication,
    QSplitter, QListWidget, QListWidgetItem, QProgressDialog
)
from PySide6.QtGui import QFont, QPalette, QIcon, QPixmap, QPainter, QAction, QColor, QTextCursor
from PySide6.QtCore import Qt, Signal, QSize, QDate, QTimer, QDateTime
import mysql.connector
from mysql.connector import Error

# Add parent directory to path to import models
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.models import get_db_connection
from ui.academic_years_form import AcademicYearsForm
from ui.audit_base_form import AuditBaseForm
from ui.terms_form import TermsForm
from ui.student_class_assignment_form import StudentClassAssignmentForm
from utils.permissions import has_permission



class SearchableComboBox(QComboBox):
    """Enhanced ComboBox with real-time search functionality"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setEditable(True)
        self.original_data = []  # Store (display_text, value) pairs
        self.filtered_data = []  # Store currently filtered data
        
        # Configure line edit for better UX
        line_edit = self.lineEdit()
        line_edit.textEdited.connect(self.filter_values)
        line_edit.returnPressed.connect(self.on_return_pressed)
        line_edit.setPlaceholderText("Type to search...")
        
        # Set properties for better dropdown behavior
        self.setMaxVisibleItems(10)
        self.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        
        # Connect signals for better interaction
        self.activated.connect(self.on_item_selected)
        
    def setData(self, data_list):
        """Set the data for the combobox - list of (display_text, value) tuples"""
        self.original_data = data_list.copy()
        self.filtered_data = data_list.copy()
        self.refresh_items()
        
    def refresh_items(self):
        """Refresh combobox items from filtered data"""
        current_text = self.lineEdit().text()
        self.clear()
        
        for display, value in self.filtered_data:
            self.addItem(display, value)
        
        # Restore the text without triggering signals
        self.blockSignals(True)
        self.lineEdit().setText(current_text)
        self.blockSignals(False)
        
    def filter_values(self, text):
        """Filter values based on typed text with real-time updates"""
        if not text.strip():
            # Show all items when text is empty
            self.filtered_data = self.original_data.copy()
            self.refresh_items()
            if not self.view().isVisible():
                self.showPopup()
            return
            
        # Filter data based on search text
        search_text = text.lower().strip()
        self.filtered_data = [
            (display, value) for display, value in self.original_data 
            if search_text in display.lower()
        ]
        
        # Update dropdown items
        self.refresh_items()
        
        # Show dropdown if we have matches
        if self.filtered_data and not self.view().isVisible():
            self.showPopup()
        elif not self.filtered_data and self.view().isVisible():
            self.hidePopup()
        
    def on_return_pressed(self):
        """Handle return pressed to select the first matching item"""
        if self.count() > 0:
            self.setCurrentIndex(0)
            self.on_item_selected(0)
            self.hidePopup()
        
    def on_item_selected(self, index):
        """Handle item selection"""
        if index >= 0:
            selected_text = self.itemText(index)
            self.lineEdit().setText(selected_text)
            self.hidePopup()
    
    def getCurrentValue(self):
        """Get the current selected value (not display text)"""
        current_text = self.lineEdit().text()
        
        # First try to find exact match in filtered data
        for display, value in self.filtered_data:
            if display == current_text:
                return value
        
        # Then try to find exact match in original data
        for display, value in self.original_data:
            if display == current_text:
                return value
                
        # If no exact match and we have a current index, use that
        current_index = self.currentIndex()
        if current_index >= 0 and current_index < self.count():
            return self.itemData(current_index)
            
        return None
    
    def setCurrentValue(self, value):
        """Set current selection by value"""
        for i in range(self.count()):
            if self.itemData(i) == value:
                self.setCurrentIndex(i)
                return True
        return False
    
    def setCurrentTextValue(self, text):
        """Set current selection by display text"""
        for display, value in self.original_data:
            if display == text:
                self.lineEdit().setText(text)
                self.setCurrentValue(value)
                return True
        return False
    
    def keyPressEvent(self, event):
        """Handle key press events for better navigation"""
        if event.key() == Qt.Key.Key_Down and not self.view().isVisible():
            self.showPopup()
        elif event.key() == Qt.Key.Key_Escape:
            self.hidePopup()
        else:
            super().keyPressEvent(event)
    
    def focusInEvent(self, event):
        """Handle focus in event"""
        super().focusInEvent(event)
        # Select all text when focused for easy replacement
        self.lineEdit().selectAll()
    
    def showPopup(self):
        """Override to ensure proper popup behavior"""
        if self.count() > 0:
            super().showPopup()



class ClassesForm(AuditBaseForm):
    class_selected = Signal(int)
    
    def __init__(self, parent=None, user_session=None):
        super().__init__(parent, user_session)
        self.current_class_id = None
        self.term_data = []
        
        # Database connection
        try:
            self.db_connection = get_db_connection()
            self.cursor = self.db_connection.cursor()
        except Error as e:
            QMessageBox.critical(self, "Database Error", f"Failed to connect to database: {e}")
            return
        
        self.setup_ui()
        self.load_data()
        self.apply_permissions()
        
    def setup_ui(self):
        """Setup the main UI with tabs - leveraging AuditBaseForm styling"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Create tab widget with inherited styling
        self.tab_widget = QTabWidget()
        self.tab_widget.setFont(self.fonts['tab'])
        main_layout.addWidget(self.tab_widget)
        
        # Create tabs
        self.class_form_tab = QWidget()
        self.assignments_tab = QWidget()
        self.academic_years_tab = QWidget()
        self.terms_tab = QWidget()
        
        # Add tabs to widget
        self.tab_widget.addTab(self.class_form_tab, "Class Form")
        self.tab_widget.addTab(self.assignments_tab, "Student Class Assignments")
        self.tab_widget.addTab(self.academic_years_tab, "Academic Years")
        self.tab_widget.addTab(self.terms_tab, "Terms")
        
        # Setup each tab
        self.setup_class_form_tab()
        self.setup_assignments_tab()
        self.setup_academic_years_tab()
        self.setup_terms_tab()
        
    def setup_class_form_tab(self):
        """Set up the class form tab with AuditBaseForm styling"""
        # Create splitter for resizable panels
        splitter = QSplitter(Qt.Horizontal)
        
        # Left panel - Form
        left_widget = QWidget()
        left_widget.setMaximumWidth(600)
        left_widget.setMinimumWidth(600)
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(10, 10, 10, 10)
        
        self.setup_form_section(left_layout)
        
        # Right panel - Table
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(10, 10, 10, 10)
        
        self.setup_table_section(right_layout)
        
        # Add widgets to splitter
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([500, 700])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        
        # Add splitter to tab
        tab_layout = QVBoxLayout(self.class_form_tab)
        tab_layout.setContentsMargins(5, 5, 5, 5)
        tab_layout.addWidget(splitter)
        
    def setup_form_section(self, layout):
        """Setup the form section using AuditBaseForm styling"""
        # Header with inherited styling
        header = QLabel("Class Information")
        header.setFont(self.fonts['section'])
        header.setStyleSheet(f"""
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 {self.colors['table_header']}, stop:1 {self.colors['table_header_dark']});
            color: white;
            margin: 10px 0;
            padding: 12px;
            border-radius: 8px;
            font-weight: bold;
            text-transform: uppercase;
            letter-spacing: 1px;
        """)
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setMinimumHeight(60)
        layout.addWidget(header)
        
        # Create scroll area for the form
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # Form container
        form_widget = QWidget()
        form_layout = QVBoxLayout(form_widget)
        form_layout.setSpacing(20)
        form_layout.setContentsMargins(10, 10, 10, 10)
        
        # Form fields group - using inherited GroupBox styling
        form_group = QGroupBox("Class Details")
        form_group.setFont(self.fonts['label'])
        form_layout_inner = QFormLayout(form_group)
        form_layout_inner.setSpacing(15)
    
        # Class Name
        self.class_name = QComboBox()
        self.class_name.setEditable(True)
        self.class_name.addItems(["S1", "S2", "S3", "S4", "S5", "S6"])
        self.class_name.setFont(self.fonts['entry'])
        form_layout_inner.addRow(self.create_styled_label("Class Name*:"), self.class_name)
    
        # Stream
        self.stream = QLineEdit()
        self.stream.setFont(self.fonts['entry'])
        self.stream.setPlaceholderText("e.g., S1A, S1B, S3 East, Science, Arts")
        form_layout_inner.addRow(self.create_styled_label("Stream:"), self.stream)
    
        # Level
        self.level = QComboBox()
        self.level.addItems(["", "O-Level", "A-Level"])
        self.level.setFont(self.fonts['entry'])
        form_layout_inner.addRow(self.create_styled_label("Level:"), self.level)
    
        # Class Teacher (Searchable)
        teacher_container = QHBoxLayout()

        # Create enhanced searchable combobox
        self.class_teacher = SearchableComboBox()
        self.class_teacher.setFont(self.fonts['entry'])
        self.class_teacher.setMinimumHeight(35)  # Better height for visibility
        teacher_container.addWidget(self.class_teacher)
        
        # Refresh button
        refresh_teacher_btn = QPushButton()
        refresh_teacher_btn.setIcon(QIcon("static/icons/refresh.png"))
        refresh_teacher_btn.setIconSize(QSize(20, 20))
        refresh_teacher_btn.setFixedSize(45, 45)
        refresh_teacher_btn.setToolTip("Refresh teacher list")
        refresh_teacher_btn.clicked.connect(self.refresh_teachers)
        refresh_teacher_btn.setProperty("class", "info")
        teacher_container.addWidget(refresh_teacher_btn)
        
        form_layout_inner.addRow(self.create_styled_label("Class Teacher:"), teacher_container)
        
        # Load teachers data
        self.load_teachers()
    
        # Term
        self.term = QComboBox()
        self.term.setFont(self.fonts['entry'])
        form_layout_inner.addRow(self.create_styled_label("Term*:"), self.term)
    
        # Status
        self.status_label = QLabel("New Class")
        self.status_label.setFont(self.fonts['entry'])
        self.status_label.setStyleSheet(f"color: {self.colors['info']}; font-weight: bold;")
        form_layout_inner.addRow(self.create_styled_label("Status:"), self.status_label)
    
        form_layout.addWidget(form_group)
    
        # Load data
        self.load_teachers()
        self.load_terms()
    
        # Buttons using inherited styling
        self.setup_action_buttons(form_layout)
        
        # Set form widget in scroll area
        scroll_area.setWidget(form_widget)
        layout.addWidget(scroll_area)

    def create_styled_label(self, text):
        """Create a label with inherited styling"""
        label = QLabel(text)
        label.setFont(self.fonts['label'])
        return label

    def setup_action_buttons(self, layout):
        """Setup action buttons with icons using inherited styling"""
        buttons_group = QGroupBox("Actions")
        buttons_group.setFont(self.fonts['label'])
        buttons_layout = QVBoxLayout(buttons_group)
    
        # Save
        self.save_btn = QPushButton("Save Class")
        self.save_btn.setIcon(QIcon("static/icons/save.png"))
        self.save_btn.setIconSize(QSize(24, 24))
        self.save_btn.setProperty("class", "success")
        self.save_btn.setFont(self.fonts['button'])
        self.save_btn.clicked.connect(self.save_class)
    
        # Update
        self.update_btn = QPushButton("Update Class")
        self.update_btn.setIcon(QIcon("static/icons/update.png"))
        self.update_btn.setIconSize(QSize(20, 20))
        self.update_btn.setProperty("class", "primary")
        self.update_btn.setFont(self.fonts['button'])
        self.update_btn.clicked.connect(self.update_class)
    
        # Clear
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setIcon(QIcon("static/icons/clear.png"))
        self.clear_btn.setIconSize(QSize(20, 20))
        self.clear_btn.setProperty("class", "secondary")
        self.clear_btn.setFont(self.fonts['button'])
        self.clear_btn.clicked.connect(self.clear_form)
    
        # Delete
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.setIcon(QIcon("static/icons/delete.png"))
        self.delete_btn.setIconSize(QSize(24, 24))
        self.delete_btn.setProperty("class", "danger")
        self.delete_btn.setFont(self.fonts['button'])
        self.delete_btn.clicked.connect(self.delete_class)
    
        # Refresh
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setIcon(QIcon("static/icons/refresh.png"))
        self.refresh_btn.setIconSize(QSize(20, 20))
        self.refresh_btn.setProperty("class", "info")
        self.refresh_btn.setFont(self.fonts['button'])
        self.refresh_btn.clicked.connect(self.refresh_all_data)
    
        # Export
        self.export_btn = QPushButton("Export")
        self.export_btn.setIcon(QIcon("static/icons/export.png"))
        self.export_btn.setIconSize(QSize(20, 20))
        self.export_btn.setProperty("class", "warning")
        self.export_btn.setFont(self.fonts['button'])
        self.export_btn.clicked.connect(self.export_classes)
    
        # Arrange buttons in rows
        row1_layout = QHBoxLayout()
        for btn in [self.save_btn, self.update_btn, self.clear_btn]:
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            row1_layout.addWidget(btn)
        buttons_layout.addLayout(row1_layout)
    
        row2_layout = QHBoxLayout()
        for btn in [self.delete_btn, self.refresh_btn, self.export_btn]:
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            row2_layout.addWidget(btn)
        buttons_layout.addLayout(row2_layout)
    
        layout.addWidget(buttons_group)


    def setup_table_section(self, layout):
        """Setup the table section using inherited styling"""
        # Header with inherited styling
        header = QLabel("Classes Database")
        header.setFont(self.fonts['section'])
        header.setStyleSheet(f"""
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 {self.colors['table_header']}, stop:1 {self.colors['table_header_dark']});
            color: white;
            margin: 10px 0;
            padding: 12px;
            border-radius: 8px;
            font-weight: bold;
            text-transform: uppercase;
            letter-spacing: 1px;
        """)
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setMinimumHeight(60)
        layout.addWidget(header)

        # --- Search frame ---
        search_frame = QFrame()
        search_layout = QHBoxLayout(search_frame)
        
        # Label
        search_label = QLabel("Search Classes:")
        search_label.setFont(self.fonts['label'])
        
        # Search input
        self.search_entry = QLineEdit()
        self.search_entry.setFont(self.fonts['entry'])
        self.search_entry.setPlaceholderText("Enter class name, stream, or teacher...")
        self.search_entry.textChanged.connect(self.on_search_changed)
        self.search_entry.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        # Search button with icon
        search_btn = QPushButton("Search")
        search_btn.setIcon(QIcon("static/icons/search.png"))
        search_btn.setIconSize(QSize(20, 20))
        search_btn.setProperty("class", "primary")
        search_btn.setFont(self.fonts['button'])
        search_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        search_btn.clicked.connect(self.search_classes)
        
        # Clear button with icon
        clear_search_btn = QPushButton("Clear")
        clear_search_btn.setIcon(QIcon("static/icons/clear.png"))
        clear_search_btn.setIconSize(QSize(20, 20))
        clear_search_btn.setProperty("class", "secondary")
        clear_search_btn.setFont(self.fonts['button'])
        clear_search_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        clear_search_btn.clicked.connect(self.clear_search)
        
        # Add widgets to layout
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_entry, stretch=1)  # search box expands
        search_layout.addWidget(search_btn)
        search_layout.addWidget(clear_search_btn)
        
        # Ensure frame can expand horizontally
        search_frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        # Add to parent layout
        layout.addWidget(search_frame)

    
        # Table with inherited styling
        self.class_table = QTableWidget()
        self.setup_table()
        layout.addWidget(self.class_table)
        
        # Table info
        self.table_info = QLabel("Total classes: 0")
        self.table_info.setStyleSheet(f"color: {self.colors['text_secondary']}; font-style: italic;")
        layout.addWidget(self.table_info)

    def setup_table(self):
        """Setup the classes table using inherited styling"""
        headers = ["ID", "Class Name", "Stream", "Level", "Class Teacher", "Term", "Status"]
        self.class_table.setColumnCount(len(headers))
        self.class_table.setHorizontalHeaderLabels(headers)
        
        # Set table properties
        self.class_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.class_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.class_table.setAlternatingRowColors(True)
        self.class_table.setSortingEnabled(True)
        
        # Use inherited fonts
        self.class_table.setFont(self.fonts['table'])
        
        # Header styling
        header = self.class_table.horizontalHeader()
        header.setFont(self.fonts['table_header'])
        
        # ✅ Balanced column widths
        # ID column fixed
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.class_table.setColumnWidth(0, 60)
        
        # Class Name stretches
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        
        # Stream auto-size
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        
        # Level auto-size
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        
        # Class Teacher stretches
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        
        # Term auto-size
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        
        # Status auto-size
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        
        # Last section fills any leftover space
        header.setStretchLastSection(True)
        
        # Connect selection signal
        self.class_table.itemSelectionChanged.connect(self.on_class_select)


    def setup_assignments_tab(self):
        """Set up the student class assignments tab"""
        layout = QVBoxLayout(self.assignments_tab)
        self.assignment_form = StudentClassAssignmentForm(user_session=self.user_session)
        layout.addWidget(self.assignment_form)
        
    def setup_academic_years_tab(self):
        """Set up the academic years tab"""
        layout = QVBoxLayout(self.academic_years_tab)
        self.academic_year_form = AcademicYearsForm(user_session=self.user_session)
        layout.addWidget(self.academic_year_form)
        
    def setup_terms_tab(self):
        """Set up the terms tab"""
        layout = QVBoxLayout(self.terms_tab)
        self.terms_form = TermsForm(user_session=self.user_session)
        layout.addWidget(self.terms_form)
        
    def apply_permissions(self):
        """Apply permissions to form controls using inherited user_session"""
        if not self.user_session:
            # Disable buttons if no session
            for btn in [self.save_btn, self.update_btn, self.delete_btn]:
                btn.setEnabled(False)
            return
            
        can_create = has_permission(self.user_session, 'create_class')
        can_edit = has_permission(self.user_session, 'edit_class')  
        can_delete = has_permission(self.user_session, 'delete_class')
        
        # Set button states
        self.save_btn.setEnabled(can_create)
        self.save_btn.setToolTip("Save new class" if can_create else "Permission required: create_class")
        
        self.update_btn.setEnabled(can_edit)
        self.update_btn.setToolTip("Update selected class" if can_edit else "Permission required: edit_class")
        
        self.delete_btn.setEnabled(can_delete)
        self.delete_btn.setToolTip("Delete selected class" if can_delete else "Permission required: delete_class")

    def load_data(self):
        """Load all necessary data using inherited database connection"""
        try:
            self._ensure_connection()  # Use parent's connection method
            self.load_teachers()
            self.load_terms()
            self.load_classes()
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Failed to load data: {e}")
        
    # Additional improvements to the load_teachers method in ClassesForm:
    def load_teachers(self):
        """Load teachers for dropdown with enhanced formatting"""
        try:
            self._ensure_connection()
            query = '''
                SELECT id, full_name, position, teacher_id_code, email, day_phone
                FROM teachers 
                WHERE is_active = 1 
                ORDER BY full_name
            '''
            self.cursor.execute(query)
            teachers = self.cursor.fetchall()
            
            # Prepare data for searchable combo box with better formatting
            teacher_data = [("-- Select Teacher --", None)]
            for teacher_id, full_name, position, teacher_code, email, day_phone in teachers:
                # Create rich display text for better searchability
                display_parts = [full_name]
                
                if teacher_code:
                    display_parts.append(f"({teacher_code})")
                
                if position:
                    display_parts.append(f"- {position}")
                    
                display_text = " ".join(display_parts)
                teacher_data.append((display_text, teacher_id))
            
            self.class_teacher.setData(teacher_data)
            
            # Set placeholder text for better UX
            self.class_teacher.lineEdit().setPlaceholderText("Type teacher name or code...")
            
        except Error as e:
            QMessageBox.critical(self, "Database Error", f"Failed to load teachers: {e}")

            
    def load_terms(self):
        """Load terms for dropdown"""
        try:
            self._ensure_connection()
            self.cursor.execute('''
                SELECT t.id, t.term_name, ay.year_name
                FROM terms t
                LEFT JOIN academic_years ay ON t.academic_year_id = ay.id
                WHERE t.is_current = 1
                ORDER BY t.start_date DESC
            ''')
            terms = self.cursor.fetchall()
            
            self.term_data = []
            self.term.clear()
            self.term.addItem("-- Select Term --")
            
            for term_id, term_name, year_name in terms:
                display_name = f"{term_name}"
                if year_name:
                    display_name += f" ({year_name})"
                self.term.addItem(display_name)
                self.term_data.append((term_id, display_name))
                
        except Error as e:
            QMessageBox.critical(self, "Database Error", f"Failed to load terms: {e}")
            
    def load_classes(self):
        """Load classes from database"""
        try:
            self._ensure_connection()
            query = '''
                SELECT 
                    c.id, 
                    c.class_name, 
                    c.stream, 
                    c.level, 
                    t.full_name as teacher_name,
                    CONCAT(tr.term_name, COALESCE(CONCAT(' (', ay.year_name, ')'), '')) as term_info,
                    CASE WHEN c.is_active = 1 THEN 'Active' ELSE 'Inactive' END as status
                FROM classes c
                LEFT JOIN teachers t ON c.class_teacher_id = t.id
                LEFT JOIN terms tr ON c.term_id = tr.id
                LEFT JOIN academic_years ay ON tr.academic_year_id = ay.id
                ORDER BY c.class_name, c.stream
            '''
            self.cursor.execute(query)
            classes = self.cursor.fetchall()
            self.update_class_table(classes)
            
        except Error as e:
            QMessageBox.critical(self, "Database Error", f"Failed to load classes: {e}")
            
    def update_class_table(self, classes):
        """Update the class table with data"""
        self.class_table.setRowCount(len(classes))
        
        for row, cls in enumerate(classes):
            for col, value in enumerate(cls):
                item = QTableWidgetItem(str(value) if value is not None else "")
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                
                # Color code status column using inherited colors
                if col == 6:  # Status column
                    if value == "Active":
                        item.setData(Qt.ItemDataRole.ForegroundRole, self.colors['success'])
                    else:
                        item.setData(Qt.ItemDataRole.ForegroundRole, self.colors['danger'])
                
                self.class_table.setItem(row, col, item)
                
        # Update info label
        total_classes = len(classes)
        active_classes = len([cls for cls in classes if cls[6] == "Active"])
        self.table_info.setText(f"Total classes: {total_classes} (Active: {active_classes})")
        
    def on_search_changed(self):
        """Handle search text changes with delay"""
        if hasattr(self, 'search_timer'):
            self.search_timer.stop()
        
        self.search_timer = QTimer()
        self.search_timer.timeout.connect(self.search_classes)
        self.search_timer.setSingleShot(True)
        self.search_timer.start(300)
        
    def search_classes(self):
        """Search classes by name, stream, or teacher"""
        search_term = self.search_entry.text().strip()
        if not search_term:
            self.load_classes()
            return
            
        try:
            self._ensure_connection()
            query = '''
                SELECT 
                    c.id, 
                    c.class_name, 
                    c.stream, 
                    c.level, 
                    t.full_name as teacher_name,
                    CONCAT(tr.term_name, COALESCE(CONCAT(' (', ay.year_name, ')'), '')) as term_info,
                    CASE WHEN c.is_active = 1 THEN 'Active' ELSE 'Inactive' END as status
                FROM classes c
                LEFT JOIN teachers t ON c.class_teacher_id = t.id
                LEFT JOIN terms tr ON c.term_id = tr.id
                LEFT JOIN academic_years ay ON tr.academic_year_id = ay.id
                WHERE (
                    c.class_name LIKE %s OR 
                    c.stream LIKE %s OR 
                    c.level LIKE %s OR
                    t.full_name LIKE %s
                )
                ORDER by c.class_name, c.stream
            '''
            search_pattern = f"%{search_term}%"
            self.cursor.execute(query, (search_pattern, search_pattern, search_pattern, search_pattern))
            classes = self.cursor.fetchall()
            self.update_class_table(classes)
            
        except Error as e:
            QMessageBox.critical(self, "Database Error", f"Failed to search classes: {e}")
            
    def clear_search(self):
        """Clear search and reload all classes"""
        self.search_entry.clear()
        self.load_classes()
        
    def on_class_select(self):
        """Handle class selection from table"""
        try:
            current_row = self.class_table.currentRow()
            if current_row < 0:
                return
                
            class_id_item = self.class_table.item(current_row, 0)
            if not class_id_item:
                return
                
            try:
                class_id = int(class_id_item.text())
            except ValueError:
                return
                
            self.load_class_data(class_id)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to select class: {e}")
            
    def load_class_data(self, class_id):
        """Load class data into form"""
        try:
            self._ensure_connection()
            query = '''
                SELECT 
                    c.id, c.class_name, c.stream, c.level, c.class_teacher_id, c.term_id,
                    t.full_name as teacher_name, t.position, t.teacher_id_code,
                    tr.term_name, ay.year_name, c.is_active
                FROM classes c
                LEFT JOIN teachers t ON c.class_teacher_id = t.id
                LEFT JOIN terms tr ON c.term_id = tr.id
                LEFT JOIN academic_years ay ON tr.academic_year_id = ay.id
                WHERE c.id = %s
            '''
            self.cursor.execute(query, (class_id,))
            class_data = self.cursor.fetchone()
            
            if class_data:
                self.current_class_id = class_id
                
                # Populate form fields
                self.class_name.setCurrentText(class_data[1] or "")
                self.stream.setText(class_data[2] or "")
                self.level.setCurrentText(class_data[3] or "")
                
                # Set teacher
                if class_data[6] and class_data[8]:
                    teacher_display = f"{class_data[6]} ({class_data[8]})"
                    if class_data[7]:
                        teacher_display += f" - {class_data[7]}"
                    self.class_teacher.setCurrentText(teacher_display)
                else:
                    self.class_teacher.setCurrentText("-- Select Teacher --")
                    
                # Set term
                if class_data[9]:
                    term_display = class_data[9]
                    if class_data[10]:
                        term_display += f" ({class_data[10]})"
                    
                    for i in range(self.term.count()):
                        if self.term.itemText(i) == term_display:
                            self.term.setCurrentIndex(i)
                            break
                else:
                    self.term.setCurrentIndex(0)
                
                # Update status with inherited colors
                status = "Active" if class_data[11] else "Inactive"
                status_color = self.colors['success'] if class_data[11] else self.colors['danger']
                self.status_label.setText(status)
                self.status_label.setStyleSheet(f"color: {status_color}; font-weight: bold;")
                
        except Error as e:
            QMessageBox.critical(self, "Database Error", f"Failed to load class data: {e}")
            
    def get_selected_term_id(self):
        """Get the selected term ID"""
        if self.term.currentIndex() <= 0:
            return None
        
        selected_text = self.term.currentText()
        for term_id, term_display in self.term_data:
            if term_display == selected_text:
                return term_id
        return None
        
    def validate_form(self):
        """Validate form data before saving/updating"""
        if not self.class_name.currentText().strip():
            QMessageBox.warning(self, "Validation Error", "Class name is required.")
            self.class_name.setFocus()
            return False
            
        if self.get_selected_term_id() is None:
            QMessageBox.warning(self, "Validation Error", "Please select a term.")
            self.term.setFocus()
            return False
            
        return True
        
    def check_for_duplicates(self, exclude_id=None):
        """Check if class already exists using inherited database connection"""
        try:
            self._ensure_connection()
            class_name = self.class_name.currentText().strip()
            stream = self.stream.text().strip()
            level = self.level.currentText().strip()
            term_id = self.get_selected_term_id()
            
            query = '''
                SELECT id, class_name, stream, level 
                FROM classes 
                WHERE is_active = 1 
                AND LOWER(class_name) = LOWER(%s) 
                AND LOWER(COALESCE(stream, '')) = LOWER(%s)
                AND LOWER(COALESCE(level, '')) = LOWER(%s)
                AND term_id = %s
            '''
            params = [class_name, stream, level, term_id]
            
            if exclude_id:
                query += " AND id != %s"
                params.append(exclude_id)
                
            self.cursor.execute(query, params)
            existing = self.cursor.fetchone()
            
            if existing:
                duplicate_info = f"Class: {existing[1]}"
                if existing[2]:
                    duplicate_info += f", Stream: {existing[2]}"
                if existing[3]:
                    duplicate_info += f", Level: {existing[3]}"
                    
                return True, f"Duplicate found: {duplicate_info}"
                
            return False, "No duplicates found"
            
        except Exception as e:
            return True, f"Error checking duplicates: {e}"
            
    def save_class(self):
        """Save new class to database using inherited methods"""
        if not has_permission(self.user_session, 'create_class'):
            QMessageBox.warning(self, "Permission Denied", "You don't have permission to create classes.")
            return
            
        if not self.validate_form():
            return
    
        try:
            self._ensure_connection()
            
            # Check for duplicates
            is_duplicate, duplicate_msg = self.check_for_duplicates()
            if is_duplicate:
                QMessageBox.warning(self, "Duplicate Class", duplicate_msg)
                return
    
            teacher_id = self.class_teacher.getCurrentValue()
            term_id = self.get_selected_term_id()
            school_id = self.user_session.get('school_id', 1) if self.user_session else 1
            
            # Insert new class
            query = '''
                INSERT INTO classes (
                    school_id, class_name, stream, level, class_teacher_id, term_id
                ) VALUES (%s, %s, %s, %s, %s, %s)
            '''
            values = (
                school_id,
                self.class_name.currentText().strip(),
                self.stream.text().strip() or None,
                self.level.currentText().strip() or None,
                teacher_id,
                term_id
            )
            
            self.cursor.execute(query, values)
            class_id = self.cursor.lastrowid
            self.db_connection.commit()
            
            # Log audit action using inherited method
            self.log_audit_action(
                action="CREATE",
                table_name="classes",
                record_id=class_id,
                description=f"Created class '{values[1]}' {values[2] or ''} ({values[3] or ''})"
            )
            
            QMessageBox.information(self, "Success", "Class saved successfully!")
            self.update_status("Class saved successfully!", "success")
            
            self.clear_form()
            self.load_classes()
    
        except Error as e:
            self.db_connection.rollback()
            QMessageBox.critical(self, "Database Error", f"Failed to save class: {e}")
            self.update_status("Failed to save class", "danger")
            
    def update_class(self):
        """Update existing class using inherited methods"""
        if not has_permission(self.user_session, 'edit_class'):
            QMessageBox.warning(self, "Permission Denied", "You don't have permission to edit classes.")
            return
            
        if not self.current_class_id:
            QMessageBox.warning(self, "Error", "No class selected for update")
            return
    
        if not self.validate_form():
            return
    
        try:
            self._ensure_connection()
            
            # Check for duplicates
            is_duplicate, duplicate_msg = self.check_for_duplicates(exclude_id=self.current_class_id)
            if is_duplicate:
                QMessageBox.warning(self, "Duplicate Class", duplicate_msg)
                return
    
            teacher_id = self.class_teacher.getCurrentValue()
            term_id = self.get_selected_term_id()
            
            # Update class
            query = '''
                UPDATE classes SET
                    class_name = %s, stream = %s, level = %s, 
                    class_teacher_id = %s, term_id = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            '''
            values = (
                self.class_name.currentText().strip(),
                self.stream.text().strip() or None,
                self.level.currentText().strip() or None,
                teacher_id,
                term_id,
                self.current_class_id
            )
            
            self.cursor.execute(query, values)
            self.db_connection.commit()
            
            # Log audit action using inherited method
            self.log_audit_action(
                action="UPDATE",
                table_name="classes",
                record_id=self.current_class_id,
                description=f"Updated class '{values[0]}' {values[1] or ''} ({values[2] or ''})"
            )
            
            QMessageBox.information(self, "Success", "Class updated successfully!")
            self.update_status("Class updated successfully!", "success")
            
            self.clear_form()
            self.load_classes()

        except Error as e:
            self.db_connection.rollback()
            QMessageBox.critical(self, "Database Error", f"Failed to update class: {e}")
            self.update_status("Failed to update class", "danger")
            
    def delete_class(self):
        """Delete (soft delete) selected class using inherited methods"""
        if not has_permission(self.user_session, 'delete_class'):
            QMessageBox.warning(self, "Permission Denied", "You don't have permission to delete classes.")
            return
            
        if not self.current_class_id:
            QMessageBox.warning(self, "Error", "No class selected for deletion")
            return
            
        # Get class info for confirmation
        class_name = self.class_name.currentText()
        stream = self.stream.text()
        display_name = f"{class_name}"
        if stream:
            display_name += f" {stream}"
            
        # Check for students in this class
        try:
            self._ensure_connection()
            self.cursor.execute(
                "SELECT COUNT(*) FROM student_class_assignments WHERE class_id = %s", 
                (self.current_class_id,)
            )
            student_count = self.cursor.fetchone()[0]
            
            if student_count > 0:
                reply = QMessageBox.question(
                    self,
                    "Confirm Delete", 
                    f"This class has {student_count} student(s) assigned to it.\n"
                    f"Are you sure you want to delete '{display_name}'?\n\n"
                    "This will also remove all student assignments.",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
            else:
                reply = QMessageBox.question(
                    self,
                    "Confirm Delete", 
                    f"Are you sure you want to delete class '{display_name}'?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
            
            if reply != QMessageBox.StandardButton.Yes:
                return
                
            # Soft delete the class
            self.cursor.execute(
                "UPDATE classes SET is_active = 0, updated_at = CURRENT_TIMESTAMP WHERE id = %s", 
                (self.current_class_id,)
            )
            self.db_connection.commit()
            
            # Log audit action using inherited method
            self.log_audit_action(
                action="DELETE",
                table_name="classes",
                record_id=self.current_class_id,
                description=f"Deleted class '{display_name}' (soft delete)"
            )
            
            QMessageBox.information(self, "Success", "Class deleted successfully!")
            self.update_status("Class deleted successfully!", "success")
            
            self.clear_form()
            self.load_classes()
            
        except Error as e:
            self.db_connection.rollback()
            QMessageBox.critical(self, "Database Error", f"Failed to delete class: {e}")
            self.update_status("Failed to delete class", "danger")
                
    def clear_form(self):
        """Clear all form fields"""
        self.class_name.setCurrentIndex(-1)
        self.stream.clear()
        self.level.setCurrentIndex(0)
        self.class_teacher.setCurrentText("-- Select Teacher --")
        self.term.setCurrentIndex(0)
        self.current_class_id = None
        
        self.update_status("New Class", "info")
        
    def update_status(self, message, status_type="info"):
        """Update status label with inherited colors"""
        color_map = {
            "success": self.colors['success'],
            "danger": self.colors['danger'],
            "warning": self.colors['warning'],
            "info": self.colors['info']
        }
        
        color = color_map.get(status_type, self.colors['info'])
        self.status_label.setText(message)
        self.status_label.setStyleSheet(f"color: {color}; font-weight: bold;")
        
    # Enhanced refresh_teachers method:
    def refresh_teachers(self):
        """Enhanced refresh method that preserves user selection"""
        try:
            # Force database commit
            self.db_connection.commit()
            
            # Save current selection details
            current_text = self.class_teacher.lineEdit().text()
            current_value = self.class_teacher.getCurrentValue()
            
            # Reload teacher data
            self.load_teachers()
            
            # Try to restore selection by value first, then by text
            if current_value:
                if not self.class_teacher.setCurrentValue(current_value):
                    self.class_teacher.setCurrentTextValue(current_text)
            elif current_text and current_text != "-- Select Teacher --":
                if not self.class_teacher.setCurrentTextValue(current_text):
                    self.class_teacher.lineEdit().setText(current_text)
            
            self.update_status("Teacher list refreshed", "info")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to refresh teachers: {e}")

            
    def refresh_all_data(self):
        """Refresh all data using inherited methods"""
        try:
            #force
            self.db_connection.commit()
            
            self.load_teachers()
            self.load_terms()
            self.load_classes()
            
            self.update_status("All data refreshed successfully", "success")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to refresh data: {e}")
            
    def export_classes(self):
        """Export classes to Excel using inherited export method"""
        try:
            self._ensure_connection()
            
            # Get data for export
            query = '''
                SELECT 
                    c.class_name, c.stream, c.level,
                    t.full_name as teacher_name,
                    tr.term_name,
                    ay.year_name,
                    CASE WHEN c.is_active = 1 THEN 'Active' ELSE 'Inactive' END as status,
                    c.created_at
                FROM classes c
                LEFT JOIN teachers t ON c.class_teacher_id = t.id
                LEFT JOIN terms tr ON c.term_id = tr.id
                LEFT JOIN academic_years ay ON tr.academic_year_id = ay.id
                ORDER BY c.class_name, c.stream
            '''
            self.cursor.execute(query)
            classes = self.cursor.fetchall()
            
            if not classes:
                QMessageBox.information(self, "No Data", "No classes to export.")
                return

            headers = [
                'Class Name', 'Stream', 'Level', 'Class Teacher', 
                'Term', 'Academic Year', 'Status', 'Created Date'
            ]
            
            # Convert to proper format for export
            data = []
            for cls in classes:
                row = []
                for i, value in enumerate(cls):
                    if i == 7 and value:  # created_at date
                        row.append(value.strftime('%Y-%m-%d %H:%M:%S'))
                    else:
                        row.append(str(value) if value is not None else '')
                data.append(row)

            # Use inherited school info method
            school_info = self.get_school_info()
            title = f"{school_info['name']} - Classes Export"

            # Use inherited export method
            self.export_with_green_header(
                data=data,
                headers=headers,
                filename_prefix="classes_export",
                title=title
            )
            
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export classes: {str(e)}")
            
    def closeEvent(self, event):
        """Cleanup when the form is closed"""
        try:
            if hasattr(self, 'cursor') and self.cursor:
                self.cursor.close()
            if hasattr(self, 'db_connection') and self.db_connection:
                self.db_connection.close()
        except Exception as e:
            print(f"Error closing database connection: {e}")
        
        event.accept()