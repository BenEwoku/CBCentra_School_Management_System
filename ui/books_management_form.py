#ui/books_management_form.py
import sys
import os
import traceback
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QDialog,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QMessageBox, QFileDialog, QScrollArea, QFrame, QSizePolicy,
    QGroupBox, QGridLayout, QSpacerItem, QComboBox, QFormLayout, 
    QTabWidget, QMenu, QCheckBox, QDateEdit, QTextEdit, QApplication,
    QSplitter, QListWidget, QListWidgetItem, QProgressDialog, QSpinBox
)
from PySide6.QtGui import QFont, QPalette, QIcon, QPixmap, QPainter, QAction, QColor, QTextCursor
from PySide6.QtCore import Qt, Signal, QSize, QDate, QTimer, QDateTime
import mysql.connector
from mysql.connector import Error
from ui.audit_base_form import AuditBaseForm
from models.models import get_db_connection
from ui.borrowing_form import BorrowingManagementForm
from fpdf import FPDF
import platform
import subprocess

# Import your existing database connection
from models.models import get_db_connection

class BooksManagementForm(AuditBaseForm):
    def __init__(self, parent=None, user_session=None):
        super().__init__(parent, user_session)
        print("DEBUG: BooksManagementForm initializing")
        self.user_session = user_session
        self.selected_book_id = None
        self.selected_category_id = None
        
        # Database connection
        try:
            self.db_connection = get_db_connection()
            self.cursor = self.db_connection.cursor(buffered=True)
            print("DEBUG: Database connection successful")
        except Error as e:
            print(f"DEBUG: Database connection failed: {e}")
            QMessageBox.critical(self, "Database Error", f"Failed to connect to database: {e}")
            return
        
        # Data storage
        self.books_data = []
        self.categories_data = []
        self.filtered_books_data = []
        
        self.setup_ui()
        self.load_data()
        print("DEBUG: BooksManagementForm initialized successfully")
        
    def setup_ui(self):
        """Setup the main UI components with tabbed interface"""
        self.setWindowTitle("Books Management System")
        self.setMinimumSize(1200, 800)
        
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setProperty("class", "main-tabs")
        
        # Create tabs in the EXACT desired order: Categories, Books, Borrowing, Reports
        self.create_categories_tab()    # 1st: Categories (foundation)
        self.create_books_tab()         # 2nd: Books 
        self.create_borrowing_tab()     # 3rd: Borrowing
        self.create_reports_tab()       # 4th: Reports
        
        # Add tab widget to main layout
        main_layout.addWidget(self.tab_widget)            
    
    def create_categories_tab(self):
        """Create the categories management tab - FIRST TAB"""
        categories_widget = QWidget()
        categories_layout = QVBoxLayout(categories_widget)
        categories_layout.setContentsMargins(20, 20, 20, 20)
        categories_layout.setSpacing(15)
        
        # Title
        title_label = QLabel("Book Categories Management")
        title_label.setProperty("class", "page-title")
        categories_layout.addWidget(title_label)
        
        # Action buttons
        action_layout = QHBoxLayout()
        action_layout.setSpacing(10)
        
        add_cat_btn = QPushButton("Add Category")
        add_cat_btn.setProperty("class", "success")
        add_cat_btn.setIcon(QIcon("static/icons/add.png"))
        add_cat_btn.setIconSize(QSize(16, 16))
        add_cat_btn.clicked.connect(self.add_category)
        action_layout.addWidget(add_cat_btn)
        
        edit_cat_btn = QPushButton("Edit Category")
        edit_cat_btn.setProperty("class", "primary")
        edit_cat_btn.setIcon(QIcon("static/icons/edit.png"))
        edit_cat_btn.setIconSize(QSize(16, 16))
        edit_cat_btn.clicked.connect(self.edit_category)
        action_layout.addWidget(edit_cat_btn)
        
        delete_cat_btn = QPushButton("Delete Category")
        delete_cat_btn.setProperty("class", "danger")
        delete_cat_btn.setIcon(QIcon("static/icons/delete.png"))
        delete_cat_btn.setIconSize(QSize(16, 16))
        delete_cat_btn.clicked.connect(self.delete_category)
        action_layout.addWidget(delete_cat_btn)
        
        action_layout.addStretch()
        categories_layout.addLayout(action_layout)
        
        # Categories table
        self.categories_table = QTableWidget()
        self.categories_table.setColumnCount(3)
        self.categories_table.setHorizontalHeaderLabels(["ID", "Name", "Description"])
        self.categories_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.categories_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.categories_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.categories_table.cellClicked.connect(self.on_category_row_click)
        self.categories_table.setAlternatingRowColors(True)
        self.categories_table.setProperty("class", "data-table")
        
        categories_layout.addWidget(self.categories_table)
        
        # Status info
        self.categories_info_label = QLabel("Select a category to manage")
        self.categories_info_label.setProperty("class", "info-label")
        categories_layout.addWidget(self.categories_info_label)
        
        # Add tab - POSITION 0 (FIRST)
        self.tab_widget.addTab(categories_widget, "Categories")
    
    def create_books_tab(self):
        """Create the books management tab - SECOND TAB"""
        books_widget = QWidget()
        books_layout = QVBoxLayout(books_widget)
        books_layout.setContentsMargins(20, 20, 20, 20)
        books_layout.setSpacing(15)
        
        # Title
        title_label = QLabel("Books Management")
        title_label.setProperty("class", "page-title")
        books_layout.addWidget(title_label)
        
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
        self.search_entry.setPlaceholderText("Search by title, author, or ISBN...")
        self.search_entry.textChanged.connect(self.search_books)
        search_layout.addWidget(self.search_entry)
        
        category_label = QLabel("Category:")
        category_label.setProperty("class", "field-label")
        search_layout.addWidget(category_label)
        
        self.category_filter = QComboBox()
        self.category_filter.setProperty("class", "form-control")
        self.category_filter.currentTextChanged.connect(self.filter_books_by_category)
        search_layout.addWidget(self.category_filter)
        
        status_label = QLabel("Status:")
        status_label.setProperty("class", "field-label")
        search_layout.addWidget(status_label)
        
        self.status_filter = QComboBox()
        self.status_filter.setProperty("class", "form-control")
        self.status_filter.addItems(["All", "Available", "Checked Out"])
        self.status_filter.currentTextChanged.connect(self.filter_books_by_status)
        search_layout.addWidget(self.status_filter)
        
        clear_btn = QPushButton("Clear")
        clear_btn.setProperty("class", "secondary")
        clear_btn.setIcon(QIcon("static/icons/clear.png"))
        clear_btn.setIconSize(QSize(16, 16))
        clear_btn.clicked.connect(self.clear_filters)
        search_layout.addWidget(clear_btn)
        
        books_layout.addWidget(search_group)
        
        # Action buttons
        action_layout = QHBoxLayout()
        action_layout.setSpacing(10)
        
        add_btn = QPushButton("Add Book")
        add_btn.setProperty("class", "success")
        add_btn.setIcon(QIcon("static/icons/add.png"))
        add_btn.setIconSize(QSize(16, 16))
        add_btn.clicked.connect(self.add_book)
        action_layout.addWidget(add_btn)
        
        edit_btn = QPushButton("Edit Book")
        edit_btn.setProperty("class", "primary")
        edit_btn.setIcon(QIcon("static/icons/edit.png"))
        edit_btn.setIconSize(QSize(16, 16))
        edit_btn.clicked.connect(self.edit_book)
        action_layout.addWidget(edit_btn)
        
        delete_btn = QPushButton("Delete Book")
        delete_btn.setProperty("class", "danger")
        delete_btn.setIcon(QIcon("static/icons/delete.png"))
        delete_btn.setIconSize(QSize(16, 16))
        delete_btn.clicked.connect(self.delete_book)
        action_layout.addWidget(delete_btn)
        
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setProperty("class", "info")
        refresh_btn.setIcon(QIcon("static/icons/refresh.png"))
        refresh_btn.setIconSize(QSize(16, 16))
        refresh_btn.clicked.connect(self.refresh_data)
        action_layout.addWidget(refresh_btn)
        
        action_layout.addStretch()
        books_layout.addLayout(action_layout)
        
        # Books table
        self.books_table = QTableWidget()
        self.books_table.setColumnCount(9)
        self.books_table.setHorizontalHeaderLabels([
            "ID", "Title", "Author", "ISBN", "Category", "Year", "Quantity", "Available", "Status"
        ])
        self.books_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.books_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.books_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.books_table.cellClicked.connect(self.on_book_row_click)
        self.books_table.setAlternatingRowColors(True)
        self.books_table.setProperty("class", "data-table")
        
        books_layout.addWidget(self.books_table)
        
        # Status info
        self.books_info_label = QLabel("Select a book to manage")
        self.books_info_label.setProperty("class", "info-label")
        books_layout.addWidget(self.books_info_label)
        
        # Add tab - POSITION 1 (SECOND)
        self.tab_widget.addTab(books_widget, "Books")
    
    def create_borrowing_tab(self):
        """Create the book borrowing management tab - THIRD TAB"""
        borrowing_widget = QWidget()
        borrowing_layout = QVBoxLayout(borrowing_widget)
        borrowing_layout.setContentsMargins(20, 20, 20, 20)
        borrowing_layout.setSpacing(15)
        
        # Title
        title_label = QLabel("Book Borrowing Management")
        title_label.setProperty("class", "page-title")
        borrowing_layout.addWidget(title_label)
        
        # Create borrowing form
        self.borrowing_form = BorrowingManagementForm(parent=self, user_session=self.user_session)
        borrowing_layout.addWidget(self.borrowing_form)
        
        # Add tab - POSITION 2 (THIRD)
        self.tab_widget.addTab(borrowing_widget, "Borrowing")
    
    def create_reports_tab(self):
        """Create the reports tab - FOURTH TAB"""
        reports_widget = QWidget()
        reports_layout = QVBoxLayout(reports_widget)
        reports_layout.setContentsMargins(20, 20, 20, 20)
        reports_layout.setSpacing(15)
        
        # Title
        title_label = QLabel("📊 Reports & Analytics")
        title_label.setProperty("class", "page-title")
        reports_layout.addWidget(title_label)
        
        # Report options
        reports_group = QGroupBox("Generate Reports")
        reports_group.setProperty("class", "form-section")
        reports_group_layout = QVBoxLayout(reports_group)  # Fixed variable name
        reports_group_layout.setContentsMargins(16, 20, 16, 12)
        reports_group_layout.setSpacing(12)
        
        # Book inventory report
        inventory_btn = QPushButton("📋 Book Inventory Report")
        inventory_btn.setProperty("class", "primary")
        inventory_btn.setIcon(QIcon("static/icons/report.png"))
        inventory_btn.setIconSize(QSize(16, 16))
        inventory_btn.clicked.connect(self.generate_inventory_report)
        reports_group_layout.addWidget(inventory_btn)
        
        # Category report
        category_btn = QPushButton("📊 Category Summary Report")
        category_btn.setProperty("class", "primary")
        category_btn.setIcon(QIcon("static/icons/report.png"))
        category_btn.setIconSize(QSize(16, 16))
        category_btn.clicked.connect(self.generate_category_report)
        reports_group_layout.addWidget(category_btn)
        
        # Popular books report
        popular_btn = QPushButton("🔥 Popular Books Report")
        popular_btn.setProperty("class", "primary")
        popular_btn.setIcon(QIcon("static/icons/report.png"))
        popular_btn.setIconSize(QSize(16, 16))
        popular_btn.clicked.connect(self.generate_popular_books_report)
        reports_group_layout.addWidget(popular_btn)
        
        reports_layout.addWidget(reports_group)
        
        # Add tab - POSITION 3 (FOURTH)
        self.tab_widget.addTab(reports_widget, "Reports")
        
    def load_data(self):
        """Load all data from database"""
        try:
            # Load books
            self.cursor.execute("""
                SELECT b.*, c.name as category_name 
                FROM books b 
                LEFT JOIN categories c ON b.category_id = c.id 
                ORDER BY b.title
            """)
            self.books_data = self.cursor.fetchall()
            self.filtered_books_data = self.books_data.copy()
            
            # Load categories
            self.cursor.execute("SELECT * FROM categories ORDER BY name")
            self.categories_data = self.cursor.fetchall()
            
            # Update UI
            self.update_books_table()
            self.update_categories_table()
            self.update_category_filters()
            
        except Error as e:
            QMessageBox.critical(self, "Database Error", f"Failed to load data: {e}")
            print(f"Database error: {e}")
            traceback.print_exc()
            
    def update_books_table(self):
        """Update the books table with current data"""
        self.books_table.setRowCount(0)
        
        for row, book in enumerate(self.filtered_books_data):
            self.books_table.insertRow(row)
            
            # Calculate status
            available = book['available_quantity']
            total = book['quantity']
            status = "Available" if available > 0 else "Checked Out"
            
            # Add items to table
            self.books_table.setItem(row, 0, QTableWidgetItem(str(book['id'])))
            self.books_table.setItem(row, 1, QTableWidgetItem(book['title']))
            self.books_table.setItem(row, 2, QTableWidgetItem(book['author']))
            self.books_table.setItem(row, 3, QTableWidgetItem(book['isbn']))
            self.books_table.setItem(row, 4, QTableWidgetItem(book['category_name'] or "Uncategorized"))
            self.books_table.setItem(row, 5, QTableWidgetItem(str(book['published_year'])))
            self.books_table.setItem(row, 6, QTableWidgetItem(str(book['quantity'])))
            self.books_table.setItem(row, 7, QTableWidgetItem(str(book['available_quantity'])))
            self.books_table.setItem(row, 8, QTableWidgetItem(status))
            
        self.books_info_label.setText(f"Showing {len(self.filtered_books_data)} of {len(self.books_data)} books")
        
    def update_categories_table(self):
        """Update the categories table with current data"""
        self.categories_table.setRowCount(0)
        
        for row, category in enumerate(self.categories_data):
            self.categories_table.insertRow(row)
            
            self.categories_table.setItem(row, 0, QTableWidgetItem(str(category['id'])))
            self.categories_table.setItem(row, 1, QTableWidgetItem(category['name']))
            self.categories_table.setItem(row, 2, QTableWidgetItem(category['description'] or ""))
            
        self.categories_info_label.setText(f"Showing {len(self.categories_data)} categories")
        
    def update_category_filters(self):
        """Update category filter dropdowns"""
        self.category_filter.clear()
        self.category_filter.addItem("All Categories", None)
        
        for category in self.categories_data:
            self.category_filter.addItem(category['name'], category['id'])
            
    def on_book_row_click(self, row, column):
        """Handle book row selection"""
        if row < 0 or row >= len(self.filtered_books_data):
            return
            
        book_id = self.books_table.item(row, 0).text()
        self.selected_book_id = int(book_id)
        
        book_title = self.books_table.item(row, 1).text()
        self.books_info_label.setText(f"Selected: {book_title}")
        
    def on_category_row_click(self, row, column):
        """Handle category row selection"""
        if row < 0 or row >= len(self.categories_data):
            return
            
        category_id = self.categories_table.item(row, 0).text()
        self.selected_category_id = int(category_id)
        
        category_name = self.categories_table.item(row, 1).text()
        self.categories_info_label.setText(f"Selected: {category_name}")
        
    def search_books(self):
        """Search books based on search text"""
        search_text = self.search_entry.text().lower().strip()
        
        if not search_text:
            self.filtered_books_data = self.books_data.copy()
        else:
            self.filtered_books_data = [
                book for book in self.books_data
                if (search_text in book['title'].lower() or 
                    search_text in book['author'].lower() or 
                    search_text in book['isbn'].lower())
            ]
            
        self.update_books_table()
        
    def filter_books_by_category(self):
        """Filter books by selected category"""
        category_name = self.category_filter.currentText()
        
        if category_name == "All Categories":
            self.filtered_books_data = self.books_data.copy()
        else:
            self.filtered_books_data = [
                book for book in self.books_data
                if book['category_name'] == category_name
            ]
            
        self.update_books_table()
        
    def filter_books_by_status(self):
        """Filter books by availability status"""
        status = self.status_filter.currentText()
        
        if status == "All":
            self.filtered_books_data = self.books_data.copy()
        elif status == "Available":
            self.filtered_books_data = [book for book in self.books_data if book['available_quantity'] > 0]
        elif status == "Checked Out":
            self.filtered_books_data = [book for book in self.books_data if book['available_quantity'] == 0]
            
        self.update_books_table()
        
    def clear_filters(self):
        """Clear all filters"""
        self.search_entry.clear()
        self.category_filter.setCurrentIndex(0)
        self.status_filter.setCurrentIndex(0)
        self.filtered_books_data = self.books_data.copy()
        self.update_books_table()
        
    def add_book(self):
        """Open dialog to add a new book"""
        dialog = BookDialog(self, categories=self.categories_data)
        if dialog.exec() == QDialog.Accepted:
            book_data = dialog.get_book_data()
            self.save_book(book_data)
            
    def edit_book(self):
        """Open dialog to edit selected book"""
        if not self.selected_book_id:
            QMessageBox.warning(self, "Warning", "Please select a book to edit.")
            return
            
        # Find the selected book
        selected_book = None
        for book in self.books_data:
            if book['id'] == self.selected_book_id:
                selected_book = book
                break
                
        if not selected_book:
            QMessageBox.warning(self, "Error", "Selected book not found.")
            return
            
        dialog = BookDialog(self, book=selected_book, categories=self.categories_data)
        if dialog.exec() == QDialog.Accepted:
            book_data = dialog.get_book_data()
            self.update_book(self.selected_book_id, book_data)
            
    def delete_book(self):
        """Delete selected book"""
        if not self.selected_book_id:
            QMessageBox.warning(self, "Warning", "Please select a book to delete.")
            return
            
        # Find the selected book
        selected_book = None
        for book in self.books_data:
            if book['id'] == self.selected_book_id:
                selected_book = book
                break
                
        if not selected_book:
            QMessageBox.warning(self, "Error", "Selected book not found.")
            return
            
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete '{selected_book['title']}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                self.cursor.execute("DELETE FROM books WHERE id = %s", (self.selected_book_id,))
                self.db_connection.commit()
                QMessageBox.information(self, "Success", "Book deleted successfully!")
                self.load_data()
            except Error as e:
                QMessageBox.critical(self, "Database Error", f"Failed to delete book: {e}")
                
    def save_book(self, book_data):
        """Save new book to database"""
        try:
            query = """
                INSERT INTO books (title, author, isbn, published_year, category_id, quantity, available_quantity)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            values = (
                book_data['title'],
                book_data['author'],
                book_data['isbn'],
                book_data['published_year'],
                book_data['category_id'],
                book_data['quantity'],
                book_data['available_quantity']
            )
            
            self.cursor.execute(query, values)
            self.db_connection.commit()
            
            # Show success message
            QMessageBox.information(self, "Success", "Book added successfully!")
            
            # Refresh the data to show the new book
            self.load_data()
            
        except Error as e:
            # Handle specific database errors
            error_message = f"Failed to add book: {e}"
            
            # Check for duplicate ISBN error
            if "duplicate" in str(e).lower() and "isbn" in str(e).lower():
                error_message = "Failed to add book: A book with this ISBN already exists."
            # Check for foreign key constraint error (invalid category)
            elif "foreign key constraint" in str(e).lower():
                error_message = "Failed to add book: Invalid category selected."
            
            QMessageBox.critical(self, "Database Error", error_message)
            print(f"Database error: {e}")
            
        except Exception as e:
            # Handle any other unexpected errors
            error_message = f"An unexpected error occurred: {e}"
            QMessageBox.critical(self, "Error", error_message)
            print(f"Unexpected error: {e}")

    def update_book(self, book_id, book_data):
        """Update existing book in database"""
        try:
            query = """
                UPDATE books 
                SET title = %s, author = %s, isbn = %s, published_year = %s, 
                    category_id = %s, quantity = %s, available_quantity = %s  -- Using category_id
                WHERE id = %s
            """
            values = (
                book_data['title'],
                book_data['author'],
                book_data['isbn'],
                book_data['published_year'],
                book_data['category_id'],  # Now using category ID
                book_data['quantity'],
                book_data['available_quantity'],
                book_id
            )
            
            self.cursor.execute(query, values)
            self.db_connection.commit()
            QMessageBox.information(self, "Success", "Book added successfully!")
            self.load_data()
            
        except Error as e:
            QMessageBox.critical(self, "Database Error", f"Failed to add book: {e}")
            
    def update_book(self, book_id, book_data):
        """Update existing book in database"""
        try:
            query = """
                UPDATE books 
                SET title = %s, author = %s, isbn = %s, published_year = %s, 
                    category_id = %s, quantity = %s, available_quantity = %s  -- Using category_id
                WHERE id = %s
            """
            values = (
                book_data['title'],
                book_data['author'],
                book_data['isbn'],
                book_data['published_year'],
                book_data['category_id'],  # Now using category ID
                book_data['quantity'],
                book_data['available_quantity'],
                book_id
            )
            
            self.cursor.execute(query, values)
            self.db_connection.commit()
            QMessageBox.information(self, "Success", "Book updated successfully!")
            self.load_data()
            
        except Error as e:
            QMessageBox.critical(self, "Database Error", f"Failed to update book: {e}")
            
    def add_category(self):
        """Open dialog to add a new category"""
        dialog = CategoryDialog(self)
        if dialog.exec() == QDialog.Accepted:
            category_data = dialog.get_category_data()
            self.save_category(category_data)
            
    def edit_category(self):
        """Open dialog to edit selected category"""
        if not self.selected_category_id:
            QMessageBox.warning(self, "Warning", "Please select a category to edit.")
            return
            
        # Find the selected category
        selected_category = None
        for category in self.categories_data:
            if category['id'] == self.selected_category_id:
                selected_category = category
                break
                
        if not selected_category:
            QMessageBox.warning(self, "Error", "Selected category not found.")
            return
            
        dialog = CategoryDialog(self, category=selected_category)
        if dialog.exec() == QDialog.Accepted:
            category_data = dialog.get_category_data()
            self.update_category(self.selected_category_id, category_data)
            
    def delete_category(self):
        """Delete selected category"""
        if not self.selected_category_id:
            QMessageBox.warning(self, "Warning", "Please select a category to delete.")
            return
            
        # Find the selected category
        selected_category = None
        for category in self.categories_data:
            if category['id'] == self.selected_category_id:
                selected_category = category
                break
                
        if not selected_category:
            QMessageBox.warning(self, "Error", "Selected category not found.")
            return
            
        # Check if category is used by any books
        self.cursor.execute("SELECT COUNT(*) as count FROM books WHERE category_id = %s", (self.selected_category_id,))
        result = self.cursor.fetchone()
        
        if result['count'] > 0:
            QMessageBox.warning(
                self, "Cannot Delete", 
                f"This category is used by {result['count']} books. Please reassign those books first."
            )
            return
            
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete '{selected_category['name']}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                self.cursor.execute("DELETE FROM categories WHERE id = %s", (self.selected_category_id,))
                self.db_connection.commit()
                QMessageBox.information(self, "Success", "Category deleted successfully!")
                self.load_data()
            except Error as e:
                QMessageBox.critical(self, "Database Error", f"Failed to delete category: {e}")
                
    def save_category(self, category_data):
        """Save new category to database"""
        try:
            query = "INSERT INTO categories (name, description) VALUES (%s, %s)"
            values = (category_data['name'], category_data['description'])
            
            self.cursor.execute(query, values)
            self.db_connection.commit()
            QMessageBox.information(self, "Success", "Category added successfully!")
            self.load_data()
            
        except Error as e:
            QMessageBox.critical(self, "Database Error", f"Failed to add category: {e}")
            
    def update_category(self, category_id, category_data):
        """Update existing category in database"""
        try:
            query = "UPDATE categories SET name = %s, description = %s WHERE id = %s"
            values = (category_data['name'], category_data['description'], category_id)
            
            self.cursor.execute(query, values)
            self.db_connection.commit()
            QMessageBox.information(self, "Success", "Category updated successfully!")
            self.load_data()
            
        except Error as e:
            QMessageBox.critical(self, "Database Error", f"Failed to update category: {e}")
            
    def refresh_data(self):
        """Refresh all data from database"""
        self.load_data()
        QMessageBox.information(self, "Success", "Data refreshed successfully!")
        
    def generate_inventory_report(self):
        """Generate PDF inventory report"""
        try:
            if not self.books_data:
                QMessageBox.warning(self, "Warning", "No book data to export.")
                return

            # File save dialog
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save Inventory Report As",
                f"book_inventory_report_{timestamp}.pdf",
                "PDF Files (*.pdf)"
            )
            
            if not file_path:
                return

            # Custom PDF class
            class PDF(FPDF):
                def __init__(self, *args, **kwargs):
                    super().__init__(*args, **kwargs)
                    self.school_name = "LIBRARY MANAGEMENT SYSTEM"
                    
                def footer(self):
                    self.set_y(-15)
                    self.set_font("Arial", 'I', 8)
                    self.cell(0, 10, f'{self.school_name} - Page {self.page_no()}', 0, 0, 'C')

            # Initialize PDF
            pdf = PDF(orientation='L', unit='mm', format='A4')  # Landscape for wide tables
            pdf.set_margins(15, 20, 15)
            pdf.add_page()
            pdf.set_auto_page_break(True, 25)

            # Header
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(0, 10, "BOOK INVENTORY REPORT", 0, 1, 'C')
            pdf.set_font("Arial", '', 12)
            pdf.cell(0, 8, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 0, 1, 'C')
            pdf.ln(10)
            
            # Summary
            total_books = sum(book['quantity'] for book in self.books_data)
            available_books = sum(book['available_quantity'] for book in self.books_data)
            checked_out = total_books - available_books
            
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 8, "SUMMARY", 0, 1)
            pdf.set_font("Arial", '', 10)
            pdf.cell(0, 6, f"Total Books: {total_books}", 0, 1)
            pdf.cell(0, 6, f"Available: {available_books}", 0, 1)
            pdf.cell(0, 6, f"Checked Out: {checked_out}", 0, 1)
            pdf.ln(10)
            
            # Table
            pdf.set_font("Arial", 'B', 10)
            pdf.cell(0, 8, "BOOK DETAILS", 0, 1)
            pdf.ln(3)

            # Table headers
            headers = ["ID", "Title", "Author", "ISBN", "Category", "Year", "Total", "Available", "Status"]
            col_widths = [10, 50, 40, 30, 30, 15, 15, 15, 15]
            
            pdf.set_fill_color(70, 130, 180)
            pdf.set_text_color(255, 255, 255)
            pdf.set_font("Arial", 'B', 9)
            
            for i, header in enumerate(headers):
                pdf.cell(col_widths[i], 8, header, 1, 0, 'C', True)
            pdf.ln()
            
            # Table data
            pdf.set_text_color(0, 0, 0)
            pdf.set_font("Arial", '', 8)
            row_height = 6
            
            for i, book in enumerate(self.books_data):
                if pdf.get_y() + row_height > pdf.h - 25:
                    pdf.add_page()
                    # Repeat headers
                    pdf.set_fill_color(70, 130, 180)
                    pdf.set_text_color(255, 255, 255)
                    pdf.set_font("Arial", 'B', 9)
                    for j, header in enumerate(headers):
                        pdf.cell(col_widths[j], 8, header, 1, 0, 'C', True)
                    pdf.ln()
                    pdf.set_text_color(0, 0, 0)
                    pdf.set_font("Arial", '', 8)
                
                status = "Available" if book['available_quantity'] > 0 else "Checked Out"
                
                row_data = [
                    str(book['id']),
                    book['title'][:40] + "..." if len(book['title']) > 40 else book['title'],
                    book['author'][:30] + "..." if len(book['author']) > 30 else book['author'],
                    book['isbn'],
                    book['category_name'] or "Uncategorized",
                    str(book['published_year']),
                    str(book['quantity']),
                    str(book['available_quantity']),
                    status
                ]
                
                # Alternate row colors
                if i % 2 == 0:
                    pdf.set_fill_color(248, 249, 250)
                    fill = True
                else:
                    pdf.set_fill_color(255, 255, 255)
                    fill = True
                
                for j, cell_data in enumerate(row_data):
                    align = 'C' if j in [0, 5, 6, 7, 8] else 'L'
                    pdf.cell(col_widths[j], row_height, str(cell_data), 1, 0, align, fill)
                pdf.ln()
                
            # Save PDF
            pdf.output(file_path)
            
            # Open PDF
            self._open_pdf(file_path)

            QMessageBox.information(
                self,
                "Export Successful",
                f"Inventory report exported successfully!\n\n"
                f"Total Books: {len(self.books_data)}\n"
                f"File: {os.path.basename(file_path)}"
            )

        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export PDF:\n{e}")
            traceback.print_exc()
            
    def generate_category_report(self):
        """Generate PDF category summary report"""
        # Similar implementation to inventory report but grouped by category
        pass
        
    def generate_popular_books_report(self):
        """Generate PDF popular books report"""
        # Implementation for popular books based on checkout history
        pass
        
    def _open_pdf(self, path):
        """Open PDF file with the system's default viewer"""
        try:
            system = platform.system()
            
            if system == 'Windows':
                os.startfile(path)
            elif system == 'Darwin':  # macOS
                subprocess.run(['open', path], check=True)
            else:  # Linux and others
                try:
                    subprocess.run(['xdg-open', path], check=True)
                except (subprocess.CalledProcessError, FileNotFoundError):
                    QMessageBox.information(
                        self,
                        "PDF Saved Successfully", 
                        f"PDF report has been saved successfully!\n\n"
                        f"Location: {path}\n\n"
                        f"Please open it manually from the saved location."
                    )
            
        except Exception as e:
            print(f"Failed to open PDF automatically: {e}")
            QMessageBox.information(
                self,
                "PDF Saved Successfully", 
                f"PDF report has been saved successfully!\n\n"
                f"Location: {path}\n\n"
                f"Please open it manually from the saved location."
            )
            
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


class BookDialog(QDialog):
    def __init__(self, parent=None, book=None, categories=None):
        super().__init__(parent)
        self.book = book
        self.categories = categories or []
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("Edit Book" if self.book else "Add New Book")
        self.setMinimumSize(500, 400)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Form
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        
        self.title_edit = QLineEdit()
        self.title_edit.setProperty("class", "form-control")
        
        self.author_edit = QLineEdit()
        self.author_edit.setProperty("class", "form-control")
        
        self.isbn_edit = QLineEdit()
        self.isbn_edit.setProperty("class", "form-control")
        
        self.year_spin = QSpinBox()
        self.year_spin.setProperty("class", "form-control")
        self.year_spin.setRange(1000, datetime.now().year)
        self.year_spin.setValue(datetime.now().year)
        
        self.category_combo = QComboBox()
        self.category_combo.setProperty("class", "form-control")
        self.category_combo.addItem("Select Category", None)
        for category in self.categories:
            self.category_combo.addItem(category['name'], category['id'])
        
        self.quantity_spin = QSpinBox()
        self.quantity_spin.setProperty("class", "form-control")
        self.quantity_spin.setRange(1, 1000)
        self.quantity_spin.setValue(1)
        
        self.available_spin = QSpinBox()
        self.available_spin.setProperty("class", "form-control")
        self.available_spin.setRange(0, 1000)
        self.available_spin.setValue(1)
    

        form_layout.addRow("Title *:", self.title_edit)
        form_layout.addRow("Author *:", self.author_edit)
        form_layout.addRow("ISBN *:", self.isbn_edit)
        form_layout.addRow("Published Year:", self.year_spin)
        form_layout.addRow("Category:", self.category_combo)
        form_layout.addRow("Total Quantity *:", self.quantity_spin)
        form_layout.addRow("Available Quantity *:", self.available_spin)
        
        layout.addLayout(form_layout)
        
        # Pre-fill data if editing
        if self.book:
            self.title_edit.setText(self.book['title'])
            self.author_edit.setText(self.book['author'])
            self.isbn_edit.setText(self.book['isbn'])
            self.year_spin.setValue(self.book['published_year'])
            
            # Set category
            index = self.category_combo.findData(self.book['category_id'])
            if index >= 0:
                self.category_combo.setCurrentIndex(index)
                
            self.quantity_spin.setValue(self.book['quantity'])
            self.available_spin.setValue(self.book['available_quantity'])
        
        # Button box
        button_layout = QHBoxLayout()
        
        save_btn = QPushButton("Save")
        save_btn.setProperty("class", "success")
        save_btn.setIcon(QIcon("static/icons/save.png"))
        save_btn.setIconSize(QSize(16, 16))
        save_btn.clicked.connect(self.accept)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setProperty("class", "secondary")
        cancel_btn.setIcon(QIcon("static/icons/cancel.png"))
        cancel_btn.setIconSize(QSize(16, 16))
        cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
    def get_book_data(self):
        """Get the book data from the form"""
        return {
            'title': self.title_edit.text().strip(),
            'author': self.author_edit.text().strip(),
            'isbn': self.isbn_edit.text().strip(),
            'published_year': self.year_spin.value(),
            'category_id': self.category_combo.currentData(),  # Get the category ID, not name
            'quantity': self.quantity_spin.value(),
            'available_quantity': self.available_spin.value()
        }
        
    def accept(self):
        """Validate and accept the dialog"""
        # Basic validation
        if not self.title_edit.text().strip():
            QMessageBox.warning(self, "Validation Error", "Title is required.")
            return
            
        if not self.author_edit.text().strip():
            QMessageBox.warning(self, "Validation Error", "Author is required.")
            return
            
        if not self.isbn_edit.text().strip():
            QMessageBox.warning(self, "Validation Error", "ISBN is required.")
            return
            
        if self.available_spin.value() > self.quantity_spin.value():
            QMessageBox.warning(self, "Validation Error", 
                               "Available quantity cannot exceed total quantity.")
            return
            
        super().accept()


class CategoryDialog(QDialog):
    def __init__(self, parent=None, category=None):
        super().__init__(parent)
        self.category = category
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("Edit Category" if self.category else "Add New Category")
        self.setMinimumSize(400, 300)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Form
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        
        self.name_edit = QLineEdit()
        self.name_edit.setProperty("class", "form-control")
        
        self.desc_edit = QTextEdit()
        self.desc_edit.setProperty("class", "form-control")
        self.desc_edit.setMaximumHeight(100)
        
        form_layout.addRow("Name *:", self.name_edit)
        form_layout.addRow("Description:", self.desc_edit)
        
        layout.addLayout(form_layout)
        
        # Pre-fill data if editing
        if self.category:
            self.name_edit.setText(self.category['name'])
            self.desc_edit.setText(self.category['description'] or "")
        
        # Button box
        button_layout = QHBoxLayout()
        
        save_btn = QPushButton("Save")
        save_btn.setProperty("class", "success")
        save_btn.setIcon(QIcon("static/icons/save.png"))
        save_btn.setIconSize(QSize(16, 16))
        save_btn.clicked.connect(self.accept)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setProperty("class", "secondary")
        cancel_btn.setIcon(QIcon("static/icons/cancel.png"))
        cancel_btn.setIconSize(QSize(16, 16))
        cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
    def get_category_data(self):
        """Get the category data from the form"""
        return {
            'name': self.name_edit.text().strip(),
            'description': self.desc_edit.toPlainText().strip()
        }
        
    def accept(self):
        """Validate and accept the dialog"""
        # Basic validation
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Validation Error", "Category name is required.")
            return
            
        super().accept()


