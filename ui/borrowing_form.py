# ui/borrowing_form.py
import os
import sys
from datetime import datetime, timedelta
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QDialog,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QMessageBox, QComboBox, QDateEdit, QGroupBox, QFormLayout, QTabWidget,
    QSpinBox, QTextEdit, QApplication
)
from PySide6.QtGui import QFont, QPalette, QIcon, QPixmap, QPainter, QAction, QColor, QTextCursor
from PySide6.QtCore import Qt, Signal, QSize, QDate, QTimer, QDateTime
import mysql.connector
from mysql.connector import Error
from ui.audit_base_form import AuditBaseForm
from models.models import get_db_connection

class BorrowingManagementForm(AuditBaseForm):
    def __init__(self, parent=None, user_session=None):
        super().__init__(parent, user_session)
        self.user_session = user_session
        self.selected_record_id = None
        
        # Database connection
        try:
            self.db_connection = get_db_connection()
            self.cursor = self.db_connection.cursor(buffered=True, dictionary=True)
        except Error as e:
            QMessageBox.critical(self, "Database Error", f"Failed to connect to database: {e}")
            return
        
        # Data storage
        self.borrowing_data = []
        self.filtered_data = []
        self.books_data = []
        self.students_data = []
        self.teachers_data = []
        
        self.setup_ui()
        self.load_data()
        
    def setup_ui(self):
        """Setup the borrowing management UI"""
        self.setWindowTitle("Book Borrowing Management")
        self.setMinimumSize(1200, 800)
        
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # Search and filter section
        search_group = QGroupBox("Search & Filter")
        search_group.setProperty("class", "search-section")
        search_layout = QHBoxLayout(search_group)
        search_layout.setContentsMargins(12, 16, 12, 8)
        search_layout.setSpacing(8)
        
        search_label = QLabel("Search:")
        search_label.setProperty("class", "field-label")
        search_layout.addWidget(search_label)
        
        self.search_entry = QLineEdit()
        self.search_entry.setProperty("class", "form-control")
        self.search_entry.setPlaceholderText("Search by book title, student/teacher name...")
        self.search_entry.textChanged.connect(self.search_records)
        search_layout.addWidget(self.search_entry)
        
        status_label = QLabel("Status:")
        status_label.setProperty("class", "field-label")
        search_layout.addWidget(status_label)
        
        self.status_filter = QComboBox()
        self.status_filter.setProperty("class", "form-control")
        self.status_filter.addItems(["All", "Borrowed", "Returned", "Overdue"])
        self.status_filter.currentTextChanged.connect(self.filter_by_status)
        search_layout.addWidget(self.status_filter)
        
        clear_btn = QPushButton("Clear Filters")
        clear_btn.setProperty("class", "secondary")
        clear_btn.setIcon(QIcon("static/icons/clear.png"))
        clear_btn.setIconSize(QSize(16, 16))
        clear_btn.clicked.connect(self.clear_filters)
        search_layout.addWidget(clear_btn)
        
        main_layout.addWidget(search_group)
        
        # Action buttons
        action_layout = QHBoxLayout()
        action_layout.setSpacing(10)
        
        borrow_btn = QPushButton("Borrow Book")
        borrow_btn.setProperty("class", "success")
        borrow_btn.setIcon(QIcon("static/icons/add.png"))
        borrow_btn.setIconSize(QSize(16, 16))
        borrow_btn.clicked.connect(self.borrow_book)
        action_layout.addWidget(borrow_btn)
        
        return_btn = QPushButton("Return Book")
        return_btn.setProperty("class", "primary")
        return_btn.setIcon(QIcon("static/icons/return.png"))
        return_btn.setIconSize(QSize(16, 16))
        return_btn.clicked.connect(self.return_book)
        action_layout.addWidget(return_btn)
        
        renew_btn = QPushButton("Renew Loan")
        renew_btn.setProperty("class", "info")
        renew_btn.setIcon(QIcon("static/icons/renew.png"))
        renew_btn.setIconSize(QSize(16, 16))
        renew_btn.clicked.connect(self.renew_loan)
        action_layout.addWidget(renew_btn)
        
        delete_btn = QPushButton("Delete Record")
        delete_btn.setProperty("class", "danger")
        delete_btn.setIcon(QIcon("static/icons/delete.png"))
        delete_btn.setIconSize(QSize(16, 16))
        delete_btn.clicked.connect(self.delete_record)
        action_layout.addWidget(delete_btn)
        
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setProperty("class", "warning")
        refresh_btn.setIcon(QIcon("static/icons/refresh.png"))
        refresh_btn.setIconSize(QSize(16, 16))
        refresh_btn.clicked.connect(self.refresh_data)
        action_layout.addWidget(refresh_btn)
        
        action_layout.addStretch()
        main_layout.addLayout(action_layout)
        
        # Borrowing records table
        self.records_table = QTableWidget()
        self.records_table.setColumnCount(10)
        self.records_table.setHorizontalHeaderLabels([
            "ID", "Book", "Borrower", "Type", "Borrow Date", "Due Date", 
            "Return Date", "Status", "Days Left", "Fine"
        ])
        self.records_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.records_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.records_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.records_table.cellClicked.connect(self.on_record_row_click)
        self.records_table.setAlternatingRowColors(True)
        self.records_table.setProperty("class", "data-table")
        
        main_layout.addWidget(self.records_table)
        
        # Status info
        self.info_label = QLabel("Select a record to manage")
        self.info_label.setProperty("class", "info-label")
        main_layout.addWidget(self.info_label)
        
    # In your BorrowingManagementForm.load_data() method, change the SQL query:
    def load_data(self):
        """Load all data from database"""
        try:
            # Load borrowing records with related data - FIXED: Use surname instead of last_name
            self.cursor.execute("""
                SELECT br.*, 
                       b.title as book_title, 
                       b.isbn as book_isbn,
                       COALESCE(s.first_name, t.first_name) as first_name,
                       COALESCE(s.surname, t.surname) as last_name,  
                       CASE 
                           WHEN br.student_id IS NOT NULL THEN 'Student' 
                           ELSE 'Teacher' 
                       END as borrower_type,
                       DATEDIFF(br.due_date, CURDATE()) as days_left,
                       CASE 
                           WHEN br.status = 'Overdue' THEN 
                               DATEDIFF(CURDATE(), br.due_date) * 10 
                           ELSE 0 
                       END as fine_amount
                FROM borrowing_records br
                LEFT JOIN books b ON br.book_id = b.id
                LEFT JOIN students s ON br.student_id = s.id
                LEFT JOIN teachers t ON br.teacher_id = t.id
                ORDER BY br.borrow_date DESC
            """)
            self.borrowing_data = self.cursor.fetchall()
            self.filtered_data = self.borrowing_data.copy()

            # Load available books (only those with available_quantity > 0)
            self.cursor.execute("""
                SELECT id, title, isbn, available_quantity 
                FROM books 
                WHERE available_quantity > 0 
                ORDER BY title
            """)
            self.books_data = self.cursor.fetchall()
            
            # Load students
            self.cursor.execute("SELECT id, first_name, surname FROM students ORDER BY first_name")
            self.students_data = self.cursor.fetchall()
            
            # Load teachers
            self.cursor.execute("SELECT id, first_name, surname FROM teachers ORDER BY first_name")
            self.teachers_data = self.cursor.fetchall()
            
            # Update UI
            self.update_records_table()
            
        except Error as e:
            QMessageBox.critical(self, "Database Error", f"Failed to load data: {e}")
            print(f"Database error: {e}")
            
    def update_records_table(self):
        """Update the records table with current data"""
        self.records_table.setRowCount(0)
        
        for row, record in enumerate(self.filtered_data):
            self.records_table.insertRow(row)
            
            # Format borrower name
            borrower_name = f"{record['first_name']} {record['last_name']}" if record['first_name'] else "Unknown"
            
            # Add items to table
            self.records_table.setItem(row, 0, QTableWidgetItem(str(record['id'])))
            self.records_table.setItem(row, 1, QTableWidgetItem(f"{record['book_title']} ({record['book_isbn']})"))
            self.records_table.setItem(row, 2, QTableWidgetItem(borrower_name))
            self.records_table.setItem(row, 3, QTableWidgetItem(record['borrower_type']))
            self.records_table.setItem(row, 4, QTableWidgetItem(str(record['borrow_date'])))
            self.records_table.setItem(row, 5, QTableWidgetItem(str(record['due_date'])))
            self.records_table.setItem(row, 6, QTableWidgetItem(str(record['return_date'] or "Not returned")))
            self.records_table.setItem(row, 7, QTableWidgetItem(record['status']))
            self.records_table.setItem(row, 8, QTableWidgetItem(str(record['days_left'])))
            self.records_table.setItem(row, 9, QTableWidgetItem(str(record['fine_amount'])))
            
        self.info_label.setText(f"Showing {len(self.filtered_data)} of {len(self.borrowing_data)} records")
        
    def on_record_row_click(self, row, column):
        """Handle record row selection"""
        if row < 0 or row >= len(self.filtered_data):
            return
            
        record_id = self.records_table.item(row, 0).text()
        self.selected_record_id = int(record_id)
        
        book_title = self.records_table.item(row, 1).text()
        self.info_label.setText(f"Selected: {book_title}")
        
    def search_records(self):
        """Search records based on search text"""
        search_text = self.search_entry.text().lower().strip()
        
        if not search_text:
            self.filtered_data = self.borrowing_data.copy()
        else:
            self.filtered_data = [
                record for record in self.borrowing_data
                if (search_text in record['book_title'].lower() or 
                    search_text in (record['first_name'] or '').lower() or 
                    search_text in (record['last_name'] or '').lower())
            ]
            
        self.update_records_table()
        
    def filter_by_status(self):
        """Filter records by status"""
        status = self.status_filter.currentText()
        
        if status == "All":
            self.filtered_data = self.borrowing_data.copy()
        else:
            self.filtered_data = [record for record in self.borrowing_data if record['status'] == status]
            
        self.update_records_table()
        
    def clear_filters(self):
        """Clear all filters"""
        self.search_entry.clear()
        self.status_filter.setCurrentIndex(0)
        self.filtered_data = self.borrowing_data.copy()
        self.update_records_table()
        
    def borrow_book(self):
        """Open dialog to borrow a new book"""
        dialog = BorrowDialog(self, books=self.books_data, 
                            students=self.students_data, teachers=self.teachers_data)
        if dialog.exec() == QDialog.Accepted:
            borrow_data = dialog.get_borrow_data()
            self.process_borrowing(borrow_data)
            
    def return_book(self):
        """Return selected book"""
        if not self.selected_record_id:
            QMessageBox.warning(self, "Warning", "Please select a borrowing record to return.")
            return
            
        # Find the selected record
        selected_record = None
        for record in self.borrowing_data:
            if record['id'] == self.selected_record_id:
                selected_record = record
                break
                
        if not selected_record:
            QMessageBox.warning(self, "Error", "Selected record not found.")
            return
            
        if selected_record['status'] == 'Returned':
            QMessageBox.warning(self, "Warning", "This book has already been returned.")
            return
            
        reply = QMessageBox.question(
            self, "Confirm Return",
            f"Are you sure you want to mark '{selected_record['book_title']}' as returned?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                # Update borrowing record
                self.cursor.execute("""
                    UPDATE borrowing_records 
                    SET return_date = CURDATE(), status = 'Returned'
                    WHERE id = %s
                """, (self.selected_record_id,))
                
                # Update book available quantity
                self.cursor.execute("""
                    UPDATE books 
                    SET available_quantity = available_quantity + 1
                    WHERE id = %s
                """, (selected_record['book_id'],))
                
                self.db_connection.commit()
                QMessageBox.information(self, "Success", "Book returned successfully!")
                self.load_data()
                
            except Error as e:
                QMessageBox.critical(self, "Database Error", f"Failed to return book: {e}")
                
    def renew_loan(self):
        """Renew selected book loan"""
        if not self.selected_record_id:
            QMessageBox.warning(self, "Warning", "Please select a borrowing record to renew.")
            return
            
        # Find the selected record
        selected_record = None
        for record in self.borrowing_data:
            if record['id'] == self.selected_record_id:
                selected_record = record
                break
                
        if not selected_record:
            QMessageBox.warning(self, "Error", "Selected record not found.")
            return
            
        if selected_record['status'] == 'Returned':
            QMessageBox.warning(self, "Warning", "Cannot renew a returned book.")
            return
            
        # Calculate new due date (extend by 14 days)
        current_due_date = selected_record['due_date']
        new_due_date = current_due_date + timedelta(days=14)
        
        reply = QMessageBox.question(
            self, "Confirm Renewal",
            f"Renew '{selected_record['book_title']}' until {new_due_date}?",
            QMessageBox.Yes | QBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                self.cursor.execute("""
                    UPDATE borrowing_records 
                    SET due_date = %s, status = 'Borrowed'
                    WHERE id = %s
                """, (new_due_date, self.selected_record_id))
                
                self.db_connection.commit()
                QMessageBox.information(self, "Success", "Loan renewed successfully!")
                self.load_data()
                
            except Error as e:
                QMessageBox.critical(self, "Database Error", f"Failed to renew loan: {e}")
                
    def delete_record(self):
        """Delete selected borrowing record"""
        if not self.selected_record_id:
            QMessageBox.warning(self, "Warning", "Please select a record to delete.")
            return
            
        # Find the selected record
        selected_record = None
        for record in self.borrowing_data:
            if record['id'] == self.selected_record_id:
                selected_record = record
                break
                
        if not selected_record:
            QMessageBox.warning(self, "Error", "Selected record not found.")
            return
            
        if selected_record['status'] != 'Returned':
            reply = QMessageBox.warning(
                self, "Confirm Delete",
                f"This book hasn't been returned yet. Are you sure you want to delete this record?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return
                
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete the record for '{selected_record['book_title']}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                # If book wasn't returned, update available quantity
                if selected_record['status'] != 'Returned':
                    self.cursor.execute("""
                        UPDATE books 
                        SET available_quantity = available_quantity + 1
                        WHERE id = %s
                    """, (selected_record['book_id'],))
                
                self.cursor.execute("DELETE FROM borrowing_records WHERE id = %s", (self.selected_record_id,))
                self.db_connection.commit()
                QMessageBox.information(self, "Success", "Record deleted successfully!")
                self.load_data()
                
            except Error as e:
                QMessageBox.critical(self, "Database Error", f"Failed to delete record: {e}")
                
    def process_borrowing(self, borrow_data):
        """Process new book borrowing"""
        try:
            # Start transaction
            self.db_connection.start_transaction()
            
            # Insert borrowing record
            query = """
                INSERT INTO borrowing_records (book_id, student_id, teacher_id, borrow_date, due_date, status)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            values = (
                borrow_data['book_id'],
                borrow_data['student_id'],
                borrow_data['teacher_id'],
                borrow_data['borrow_date'],
                borrow_data['due_date'],
                'Borrowed'
            )
            
            self.cursor.execute(query, values)
            
            # Update book available quantity
            self.cursor.execute("""
                UPDATE books 
                SET available_quantity = available_quantity - 1
                WHERE id = %s AND available_quantity > 0
            """, (borrow_data['book_id'],))
            
            # Check if book was actually updated
            if self.cursor.rowcount == 0:
                raise Exception("Book is not available for borrowing")
            
            self.db_connection.commit()
            QMessageBox.information(self, "Success", "Book borrowed successfully!")
            self.load_data()
            
        except Exception as e:
            self.db_connection.rollback()
            QMessageBox.critical(self, "Error", f"Failed to borrow book: {e}")
            
    def refresh_data(self):
        """Refresh all data from database"""
        self.load_data()
        QMessageBox.information(self, "Success", "Data refreshed successfully!")
        
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


class BorrowDialog(QDialog):
    def __init__(self, parent=None, books=None, students=None, teachers=None):
        super().__init__(parent)
        self.books = books or []
        self.students = students or []
        self.teachers = teachers or []
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("Borrow Book")
        self.setMinimumSize(500, 400)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Form
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        
        # Book selection
        self.book_combo = QComboBox()
        self.book_combo.setProperty("class", "form-control")
        self.book_combo.addItem("Select Book", None)
        for book in self.books:
            self.book_combo.addItem(f"{book['title']} (ISBN: {book['isbn']})", book['id'])
        
        # Borrower type selection
        self.borrower_type_combo = QComboBox()
        self.borrower_type_combo.setProperty("class", "form-control")
        self.borrower_type_combo.addItem("Student", "student")
        self.borrower_type_combo.addItem("Teacher", "teacher")
        self.borrower_type_combo.currentTextChanged.connect(self.on_borrower_type_changed)
        
        # Student selection - FIXED: Use surname instead of last_name
        self.student_combo = QComboBox()
        self.student_combo.setProperty("class", "form-control")
        self.student_combo.addItem("Select Student", None)
        for student in self.students:
            self.student_combo.addItem(f"{student['first_name']} {student['surname']}", student['id'])  # CHANGED
        
        # Teacher selection - FIXED: Use surname instead of last_name
        self.teacher_combo = QComboBox()
        self.teacher_combo.setProperty("class", "form-control")
        self.teacher_combo.addItem("Select Teacher", None)
        for teacher in self.teachers:
            self.teacher_combo.addItem(f"{teacher['first_name']} {teacher['surname']}", teacher['id'])
        
        # Dates
        self.borrow_date_edit = QDateEdit()
        self.borrow_date_edit.setProperty("class", "form-control")
        self.borrow_date_edit.setDate(QDate.currentDate())
        self.borrow_date_edit.setCalendarPopup(True)
        
        self.due_date_edit = QDateEdit()
        self.due_date_edit.setProperty("class", "form-control")
        self.due_date_edit.setDate(QDate.currentDate().addDays(14))  # Default 2 weeks
        self.due_date_edit.setCalendarPopup(True)
        
        form_layout.addRow("Book *:", self.book_combo)
        form_layout.addRow("Borrower Type *:", self.borrower_type_combo)
        form_layout.addRow("Student:", self.student_combo)
        form_layout.addRow("Teacher:", self.teacher_combo)
        form_layout.addRow("Borrow Date *:", self.borrow_date_edit)
        form_layout.addRow("Due Date *:", self.due_date_edit)
        
        layout.addLayout(form_layout)
        
        # Initially hide teacher combo (student is default)
        self.teacher_combo.hide()
        form_layout.labelForField(self.teacher_combo).hide()
        
        # Button box
        button_layout = QHBoxLayout()
        
        borrow_btn = QPushButton("Borrow")
        borrow_btn.setProperty("class", "success")
        borrow_btn.clicked.connect(self.accept)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setProperty("class", "secondary")
        cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(borrow_btn)
        button_layout.addWidget(cancel_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
    def on_borrower_type_changed(self, text):
        """Handle borrower type change"""
        if text == "Student":
            self.student_combo.show()
            self.teacher_combo.hide()
            form_layout = self.layout().itemAt(0).layout()
            form_layout.labelForField(self.student_combo).show()
            form_layout.labelForField(self.teacher_combo).hide()
        else:
            self.student_combo.hide()
            self.teacher_combo.show()
            form_layout = self.layout().itemAt(0).layout()
            form_layout.labelForField(self.student_combo).hide()
            form_layout.labelForField(self.teacher_combo).show()
        
    def get_borrow_data(self):
        """Get the borrowing data from the form"""
        borrower_type = self.borrower_type_combo.currentData()
        
        return {
            'book_id': self.book_combo.currentData(),
            'student_id': self.student_combo.currentData() if borrower_type == 'student' else None,
            'teacher_id': self.teacher_combo.currentData() if borrower_type == 'teacher' else None,
            'borrow_date': self.borrow_date_edit.date().toString("yyyy-MM-dd"),
            'due_date': self.due_date_edit.date().toString("yyyy-MM-dd")
        }
        
    def accept(self):
        """Validate and accept the dialog"""
        # Basic validation
        if not self.book_combo.currentData():
            QMessageBox.warning(self, "Validation Error", "Please select a book.")
            return
            
        borrower_type = self.borrower_type_combo.currentData()
        if borrower_type == 'student' and not self.student_combo.currentData():
            QMessageBox.warning(self, "Validation Error", "Please select a student.")
            return
        elif borrower_type == 'teacher' and not self.teacher_combo.currentData():
            QMessageBox.warning(self, "Validation Error", "Please select a teacher.")
            return
            
        if self.borrow_date_edit.date() > self.due_date_edit.date():
            QMessageBox.warning(self, "Validation Error", "Due date cannot be before borrow date.")
            return
            
        super().accept()