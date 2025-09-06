# utils/pdf_utils.py
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSpinBox,
    QMessageBox, QFileDialog, QScrollArea, QWidget, QSizePolicy,
    QGraphicsDropShadowEffect, QComboBox
)
from PySide6.QtPrintSupport import QPrinter, QPrintDialog
from PySide6.QtPdf import QPdfDocument
from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QSize, Qt
from PySide6.QtGui import QPainter, QPixmap, QPageSize, QColor, QGuiApplication, QIcon
import tempfile
import os

# Constants for better maintainability
PDF_BASE_WIDTH = 595
PDF_BASE_HEIGHT = 842
RENDER_DPI = 300  # Professional print DPI
MAX_ZOOM = 5.0
MIN_ZOOM = 0.1
ZOOM_STEP = 1.25
DEFAULT_ZOOM_LEVELS = [25, 50, 75, 100, 125, 150, 200, 300, 400, 500]


def validate_pdf_data(pdf_data):
    """Validate that the data is actually a PDF"""
    if not pdf_data:
        return False, "No PDF data provided"

    if isinstance(pdf_data, str):
        pdf_bytes = pdf_data.encode('latin1')
    else:
        pdf_bytes = bytes(pdf_data)

    if not pdf_bytes.startswith(b'%PDF-'):
        return False, "Data does not appear to be a valid PDF (missing PDF header)"
    if b'%%EOF' not in pdf_bytes[-200:]:
        return False, "PDF data appears incomplete (missing EOF marker)"

    return True, pdf_bytes


class PDFPageContainer(QWidget):
    """Container widget for a PDF page with page number and styling"""
    def __init__(self, page_number, parent=None):
        super().__init__(parent)
        self.page_number = page_number
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        # Page number label
        self.page_label = QLabel(f"Page {self.page_number + 1}")
        self.page_label.setAlignment(Qt.AlignCenter)
        self.page_label.setStyleSheet("""
            QLabel {
                color: #666666;
                font-size: 11px;
                font-weight: bold;
                padding: 3px;
                background-color: rgba(255, 255, 255, 0.8);
                border-radius: 3px;
                margin-bottom: 5px;
            }
        """)

        # Page widget
        self.page_widget = PDFPageWidget()

        layout.addWidget(self.page_label)
        layout.addWidget(self.page_widget)


class PDFPageWidget(QLabel):
    """Widget to display a single PDF page with professional styling"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.original_pixmap = None
        self.zoom_factor = 1.0

        # Professional styling with shadow
        self.setStyleSheet("""
            QLabel {
                background-color: white;
                border: 2px solid #d5d5d5;
                border-radius: 8px;
                padding: 2px;
            }
            QLabel:hover {
                border-color: #a0a0a0;
            }
        """)

        # Add drop shadow effect
        self.add_drop_shadow()

    def add_drop_shadow(self):
        """Add professional drop shadow effect"""
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(12)
        shadow.setColor(QColor(0, 0, 0, 60))  # Semi-transparent black
        shadow.setOffset(3, 3)
        self.setGraphicsEffect(shadow)

    def set_page_image(self, image):
        """Set the page image with high quality"""
        if not image.isNull():
            self.original_pixmap = QPixmap.fromImage(image)
            self.update_display()

    def update_display(self):
        """Update display with current zoom factor using high-quality scaling"""
        if self.original_pixmap:
            target_size = self.original_pixmap.size() * self.zoom_factor

            # Use high-quality transformation for crisp scaling
            if self.zoom_factor >= 1.0:
                scaled_pixmap = self.original_pixmap.scaled(
                    target_size,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
            else:
                scaled_pixmap = self.original_pixmap.scaled(
                    target_size,
                    Qt.KeepAspectRatio,
                    Qt.FastTransformation
                )

            self.setPixmap(scaled_pixmap)
            self.resize(scaled_pixmap.size())

    def set_zoom(self, zoom_factor):
        """Set zoom factor and update display"""
        self.zoom_factor = zoom_factor
        self.update_display()


class EnhancedPDFViewerDialog(QDialog):
    """Enhanced PDF viewer with professional appearance and functionality"""
    def __init__(self, pdf_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PDF Viewer - CBCentra SMS")
        self.resize(1100, 800)  # Larger default size

        is_valid, result = validate_pdf_data(pdf_data)
        if not is_valid:
            QMessageBox.critical(parent, "Invalid PDF", f"PDF validation failed: {result}")
            self.reject()
            return

        self.pdf_data = result
        self.pdf_document = QPdfDocument(self)
        self.buffer = QBuffer(self)
        self.temp_file_path = None
        self.current_page = 0
        self.zoom_factor = 1.0
        self.page_containers = []
        self.high_quality_cache = {}

        # Get system DPI for high-quality rendering
        self.dpi_ratio = QGuiApplication.primaryScreen().devicePixelRatio()

        self.setup_ui()
        if not self.load_pdf():
            self.reject()

    def load_icon(self, filename):
        """
        Load an icon from static/icons/{filename}
        Returns QIcon or None if not found
        """
        icon_path = os.path.join("static", "icons", filename)
        if os.path.exists(icon_path):
            return QIcon(icon_path)
        else:
            print(f"Icon not found: {icon_path}")
            return QIcon()  # Return empty icon to avoid crash

    def get_gray_button_style(self):
        """Minimal gray button style – no border, just soft hover"""
        return """
            QPushButton {
                background-color: rgba(200, 200, 200, 0.0);
                border-radius: 6px;
                min-width: 36px;
                min-height: 36px;
                padding: 0;
            }
            QPushButton:hover {
                background-color: rgba(180, 180, 180, 0.3);
            }
            QPushButton:pressed {
                background-color: rgba(160, 160, 160, 0.4);
            }
        """

    def get_action_button_style(self):
        """Get minimal, flat button style for Print and Save – matches toolbar"""
        return """
            QPushButton {
                background-color: rgba(200, 200, 200, 0.0);
                border-radius: 6px;
                padding: 8px 12px;
                color: #333333;
                font-weight: normal;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: rgba(180, 180, 180, 0.3);
                color: #000000;
            }
            QPushButton:pressed {
                background-color: rgba(160, 160, 160, 0.4);
            }
        """

    def darken_color(self, color, factor=0.8):
        """Utility to darken a color"""
        if color.startswith('#'):
            r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
            r, g, b = int(r * factor), int(g * factor), int(b * factor)
            return f"#{r:02x}{g:02x}{b:02x}"
        return color

    def setup_ui(self):
        """Setup the user interface with professional styling and named icons"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # Toolbar with enhanced controls
        toolbar_layout = QHBoxLayout()

        # --- Navigation: Page X of Y ---
        self.page_label = QLabel("Page:")
        toolbar_layout.addWidget(self.page_label)

        self.page_spinbox = QSpinBox()
        self.page_spinbox.setMinimum(1)
        self.page_spinbox.setStyleSheet("QSpinBox { min-width: 60px; }")
        self.page_spinbox.valueChanged.connect(self.go_to_page)
        toolbar_layout.addWidget(self.page_spinbox)

        self.total_pages_label = QLabel("of 0")
        toolbar_layout.addWidget(self.total_pages_label)

        self.add_separator(toolbar_layout)

        # --- Previous Button ---
        self.prev_btn = QPushButton()
        self.prev_btn.setIcon(self.load_icon("previous.png"))
        self.prev_btn.setToolTip("Previous Page")
        self.prev_btn.setStyleSheet(self.get_gray_button_style())
        self.prev_btn.setFixedSize(36, 36)
        self.prev_btn.setIconSize(QSize(24, 24))
        self.prev_btn.clicked.connect(self.previous_page)
        toolbar_layout.addWidget(self.prev_btn)

        # --- Next Button ---
        self.next_btn = QPushButton()
        self.next_btn.setIcon(self.load_icon("next.png"))
        self.next_btn.setToolTip("Next Page")
        self.next_btn.setStyleSheet(self.get_gray_button_style())
        self.next_btn.setFixedSize(36, 36)
        self.next_btn.setIconSize(QSize(24, 24))
        self.next_btn.clicked.connect(self.next_page)
        toolbar_layout.addWidget(self.next_btn)

        self.add_separator(toolbar_layout)

        # --- Zoom Out ---
        self.zoom_out_btn = QPushButton()
        self.zoom_out_btn.setIcon(self.load_icon("zoom-out.png"))
        self.zoom_out_btn.setToolTip("Zoom Out")
        self.zoom_out_btn.setStyleSheet(self.get_gray_button_style())
        self.zoom_out_btn.setFixedSize(36, 36)
        self.zoom_out_btn.setIconSize(QSize(24, 24))
        self.zoom_out_btn.clicked.connect(self.zoom_out)
        toolbar_layout.addWidget(self.zoom_out_btn)

        # --- Zoom Combo ---
        self.zoom_combo = QComboBox()
        self.zoom_combo.setEditable(True)
        self.zoom_combo.setFixedWidth(80)
        for zoom_level in DEFAULT_ZOOM_LEVELS:
            self.zoom_combo.addItem(f"{zoom_level}%")
        self.zoom_combo.setCurrentText("100%")
        self.zoom_combo.currentTextChanged.connect(self.on_zoom_combo_changed)
        toolbar_layout.addWidget(self.zoom_combo)

        # --- Zoom In ---
        self.zoom_in_btn = QPushButton()
        self.zoom_in_btn.setIcon(self.load_icon("zoom-in.png"))
        self.zoom_in_btn.setToolTip("Zoom In")
        self.zoom_in_btn.setStyleSheet(self.get_gray_button_style())
        self.zoom_in_btn.setFixedSize(36, 36)
        self.zoom_in_btn.setIconSize(QSize(24, 24))
        self.zoom_in_btn.clicked.connect(self.zoom_in)
        toolbar_layout.addWidget(self.zoom_in_btn)

        self.add_separator(toolbar_layout)

        # --- Fit Width ---
        self.fit_width_btn = QPushButton()
        self.fit_width_btn.setIcon(self.load_icon("fit-width.png"))
        self.fit_width_btn.setToolTip("Fit Width")
        self.fit_width_btn.setStyleSheet(self.get_gray_button_style())
        self.fit_width_btn.setFixedSize(36, 36)
        self.fit_width_btn.setIconSize(QSize(24, 24))
        self.fit_width_btn.clicked.connect(self.fit_width)
        toolbar_layout.addWidget(self.fit_width_btn)

        # --- Fit Page ---
        self.fit_page_btn = QPushButton()
        self.fit_page_btn.setIcon(self.load_icon("fit-page.png"))
        self.fit_page_btn.setToolTip("Fit Page")
        self.fit_page_btn.setStyleSheet(self.get_gray_button_style())
        self.fit_page_btn.setFixedSize(36, 36)
        self.fit_page_btn.setIconSize(QSize(24, 24))
        self.fit_page_btn.clicked.connect(self.fit_page)
        toolbar_layout.addWidget(self.fit_page_btn)

        self.add_separator(toolbar_layout)

        # --- Print Button ---
        self.print_btn = QPushButton(" Print")
        self.print_btn.setIcon(self.load_icon("print.png"))
        self.print_btn.setIconSize(QSize(24, 24))
        self.print_btn.setToolTip("Print Document (CTRL+P")
        self.print_btn.setStyleSheet(self.get_action_button_style())
        self.print_btn.clicked.connect(self.print_document)
        toolbar_layout.addWidget(self.print_btn)
        
        # --- Save Button ---
        self.save_btn = QPushButton(" Save PDF")
        self.save_btn.setIcon(self.load_icon("save.png"))
        self.print_btn.setIconSize(QSize(24, 24))
        self.save_btn.setToolTip("Save PDF File (Ctrl+S)")
        self.save_btn.setStyleSheet(self.get_action_button_style())
        self.save_btn.clicked.connect(self.save_pdf)
        toolbar_layout.addWidget(self.save_btn)

        main_layout.addLayout(toolbar_layout)

        # --- Scroll Area ---
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setAlignment(Qt.AlignCenter)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: #e8e8e8;
                border: 1px solid #cccccc;
                border-radius: 5px;
            }
            QScrollArea > QWidget > QWidget {
                background-color: #e8e8e8;
            }
        """)

        # Pages container
        self.pages_container = QWidget()
        self.pages_layout = QVBoxLayout(self.pages_container)
        self.pages_layout.setAlignment(Qt.AlignCenter)
        self.pages_layout.setSpacing(25)
        self.pages_layout.setContentsMargins(30, 30, 30, 30)

        self.scroll_area.setWidget(self.pages_container)
        main_layout.addWidget(self.scroll_area)

    def add_separator(self, layout):
        """Add visual separator to toolbar"""
        separator = QLabel("|")
        separator.setStyleSheet("color: #cccccc; margin: 0 8px;")
        layout.addWidget(separator)

    def load_pdf(self):
        """Load PDF document with error handling"""
        try:
            self.pdf_document.close()
            self.buffer.setData(QByteArray(self.pdf_data))
            if self.buffer.open(QIODevice.ReadOnly):
                _ = self.pdf_document.load(self.buffer)
                if self.pdf_document.error() == QPdfDocument.Error.None_:
                    self.setup_pages()
                    return True

            # Fallback to temporary file
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp.write(self.pdf_data)
                self.temp_file_path = tmp.name

            if self.buffer.isOpen():
                self.buffer.close()

            self.pdf_document.close()
            _ = self.pdf_document.load(self.temp_file_path)
            if self.pdf_document.error() == QPdfDocument.Error.None_:
                self.setup_pages()
                return True

            error_messages = {
                QPdfDocument.Error.Unknown: "Unknown error while loading PDF.",
                QPdfDocument.Error.DataNotYetAvailable: "PDF data not yet available (still loading).",
                QPdfDocument.Error.FileNotFound: "PDF file not found.",
                QPdfDocument.Error.InvalidFileFormat: "Invalid or corrupted PDF file.",
                QPdfDocument.Error.IncorrectPassword: "PDF is password-protected.",
                QPdfDocument.Error.UnsupportedSecurityScheme: "Unsupported PDF security scheme.",
            }
            msg = error_messages.get(self.pdf_document.error(), f"Unknown PDF loading error: {self.pdf_document.error()}")
            raise RuntimeError(msg)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load PDF:\n{e}")
            return False

    def setup_pages(self):
        """Set up page containers and render pages with ultra-high quality"""
        page_count = self.pdf_document.pageCount()
        if page_count == 0:
            return

        self.page_spinbox.setMaximum(page_count)
        self.page_spinbox.setValue(1)
        self.total_pages_label.setText(f"of {page_count}")

        # Clear existing containers
        for container in self.page_containers:
            container.deleteLater()
        self.page_containers.clear()
        self.high_quality_cache.clear()

        # Calculate ultra-high-quality rendering size using DPI
        scale_factor = RENDER_DPI / 72.0
        base_width = int(PDF_BASE_WIDTH * scale_factor)
        base_height = int(PDF_BASE_HEIGHT * scale_factor)
        target_width = int(base_width * self.dpi_ratio)
        target_height = int(base_height * self.dpi_ratio)

        # Create page containers with ultra-high-quality rendering
        for page_num in range(page_count):
            container = PDFPageContainer(page_num)
            self.page_containers.append(container)
            self.pages_layout.addWidget(container)

            image = self.pdf_document.render(page_num, QSize(target_width, target_height))

            if not image.isNull():
                pixmap = QPixmap.fromImage(image)
                self.high_quality_cache[page_num] = pixmap
                container.page_widget.set_page_image(image)
                container.page_widget.set_zoom(1.0)

        self.update_navigation_buttons()

    def on_zoom_combo_changed(self, text):
        """Handle zoom combo box changes"""
        try:
            zoom_text = text.replace('%', '').strip()
            zoom_percentage = float(zoom_text)
            self.zoom_factor = zoom_percentage / 100.0
            self.zoom_factor = max(MIN_ZOOM, min(MAX_ZOOM, self.zoom_factor))
            self.apply_zoom()
        except ValueError:
            self.zoom_combo.setCurrentText(f"{int(self.zoom_factor * 100)}%")

    def go_to_page(self, page_num):
        """Navigate to specific page"""
        self.current_page = page_num - 1
        self.update_navigation_buttons()
        if self.current_page < len(self.page_containers):
            self.scroll_area.ensureWidgetVisible(self.page_containers[self.current_page])

    def previous_page(self):
        """Go to previous page"""
        if self.current_page > 0:
            self.page_spinbox.setValue(self.current_page + 1)

    def next_page(self):
        """Go to next page"""
        if self.current_page < self.pdf_document.pageCount() - 1:
            self.page_spinbox.setValue(self.current_page + 2)

    def update_navigation_buttons(self):
        """Update navigation button states"""
        self.prev_btn.setEnabled(self.current_page > 0)
        self.next_btn.setEnabled(self.current_page < self.pdf_document.pageCount() - 1)

    def zoom_in(self):
        """Increase zoom level"""
        self.zoom_factor = min(self.zoom_factor * ZOOM_STEP, MAX_ZOOM)
        self.apply_zoom()

    def zoom_out(self):
        """Decrease zoom level"""
        self.zoom_factor = max(self.zoom_factor / ZOOM_STEP, MIN_ZOOM)
        self.apply_zoom()

    def fit_width(self):
        """Fit page width to window"""
        if self.page_containers and self.page_containers[0].page_widget.original_pixmap:
            available_width = self.scroll_area.viewport().width() - 60
            original_width = self.page_containers[0].page_widget.original_pixmap.width()
            self.zoom_factor = available_width / original_width
            self.apply_zoom()

    def fit_page(self):
        """Fit entire page to window"""
        if self.page_containers and self.page_containers[0].page_widget.original_pixmap:
            available_width = self.scroll_area.viewport().width() - 60
            available_height = self.scroll_area.viewport().height() - 60
            original_size = self.page_containers[0].page_widget.original_pixmap.size()
            width_scale = available_width / original_size.width()
            height_scale = available_height / original_size.height()
            self.zoom_factor = min(width_scale, height_scale)
            self.apply_zoom()

    def apply_zoom(self):
        """Apply zoom using re-rendering for maximum clarity"""
        if hasattr(self, 'zoom_factor') and (self.zoom_factor > 1.5 or self.zoom_factor < 0.8):
            self.render_at_zoom_level()
        else:
            for container in self.page_containers:
                container.page_widget.set_zoom(self.zoom_factor)

        self.zoom_combo.setCurrentText(f"{int(self.zoom_factor * 100)}%")

    def render_at_zoom_level(self):
        """Re-render pages at current zoom level for maximum sharpness"""
        page_count = self.pdf_document.pageCount()

        scale_factor = (RENDER_DPI / 72.0) * self.zoom_factor
        target_width = int(PDF_BASE_WIDTH * scale_factor * self.dpi_ratio)
        target_height = int(PDF_BASE_HEIGHT * scale_factor * self.dpi_ratio)

        max_dimension = 8000
        if target_width > max_dimension or target_height > max_dimension:
            scale = max_dimension / max(target_width, target_height)
            target_width = int(target_width * scale)
            target_height = int(target_height * scale)

        for page_num in range(min(page_count, len(self.page_containers))):
            container = self.page_containers[page_num]
            image = self.pdf_document.render(page_num, QSize(target_width, target_height))
            if not image.isNull():
                container.page_widget.set_page_image(image)
                container.page_widget.set_zoom(1.0)

    def render_pdf_for_print(self, printer):
        """Render PDF for printing with high quality"""
        try:
            if self.pdf_document.pageCount() == 0:
                raise RuntimeError("PDF document has no pages")

            painter = QPainter(printer)
            for page in range(self.pdf_document.pageCount()):
                if page > 0:
                    printer.newPage()
                printer_rect = printer.pageRect(QPrinter.DevicePixel)
                target_size = QSize(printer_rect.width(), printer_rect.height())
                image = self.pdf_document.render(page, target_size)
                if not image.isNull():
                    painter.drawPixmap(0, 0, QPixmap.fromImage(image))
            painter.end()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to render PDF for printing:\n{e}")

    def print_document(self):
        """Print the PDF document"""
        try:
            printer = QPrinter(QPrinter.HighResolution)
            printer.setPageSize(QPageSize(QPageSize.A4))
            print_dialog = QPrintDialog(printer, self)
            if print_dialog.exec() == QPrintDialog.Accepted:
                self.render_pdf_for_print(printer)
                QMessageBox.information(self, "Success", "Document sent to printer")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to print:\n{e}")

    def save_pdf(self):
        """Save PDF to file"""
        try:
            path, _ = QFileDialog.getSaveFileName(
                self, "Save PDF", "document.pdf", "PDF Files (*.pdf)"
            )
            if path:
                with open(path, 'wb') as f:
                    f.write(self.pdf_data)
                QMessageBox.information(self, "Success", f"PDF saved to:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save PDF:\n{e}")

    def keyPressEvent(self, event):
        """Handle keyboard shortcuts"""
        if event.key() in (Qt.Key_Plus, Qt.Key_Equal):
            self.zoom_in()
        elif event.key() == Qt.Key_Minus:
            self.zoom_out()
        elif event.key() == Qt.Key_PageUp:
            self.previous_page()
        elif event.key() == Qt.Key_PageDown:
            self.next_page()
        elif event.key() == Qt.Key_Home:
            self.page_spinbox.setValue(1)
        elif event.key() == Qt.Key_End:
            self.page_spinbox.setValue(self.pdf_document.pageCount())
        elif event.modifiers() == Qt.ControlModifier:
            if event.key() == Qt.Key_P:
                self.print_document()
            elif event.key() == Qt.Key_S:
                self.save_pdf()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        """Clean up resources on close"""
        try:
            if self.pdf_document:
                self.pdf_document.close()
            if self.buffer and self.buffer.isOpen():
                self.buffer.close()
            if self.temp_file_path and os.path.exists(self.temp_file_path):
                os.unlink(self.temp_file_path)
        except Exception as e:
            print(f"Cleanup error: {e}")
        super().closeEvent(event)


# Utility functions
def view_pdf(pdf_data, parent=None):
    """View PDF in enhanced viewer"""
    try:
        viewer = EnhancedPDFViewerDialog(pdf_data, parent)
        viewer.exec()
    except Exception as e:
        QMessageBox.critical(parent, "Error", f"Could not view PDF:\n{e}")


def print_pdf_enhanced(pdf_data, parent=None):
    """Print PDF using enhanced viewer"""
    try:
        viewer = EnhancedPDFViewerDialog(pdf_data, parent)
        if viewer.result() != QDialog.Rejected:
            viewer.print_document()
        viewer.close()
    except Exception as e:
        QMessageBox.critical(parent, "Error", f"Could not print PDF:\n{e}")


def print_pdf(pdf_data, parent=None):
    """Print PDF (backward compatibility)"""
    print_pdf_enhanced(pdf_data, parent)