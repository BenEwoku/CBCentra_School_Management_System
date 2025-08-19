# utils/pdf_utils.py
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QPushButton, QHBoxLayout, 
                              QMessageBox, QFileDialog)
from PySide6.QtPrintSupport import QPrinter, QPrintDialog, QPrintPreviewWidget
from PySide6.QtPdf import QPdfDocument
from PySide6.QtCore import QBuffer, QByteArray, QIODevice
from PySide6.QtGui import QPainter

class PDFViewerDialog(QDialog):
    """A complete PDF viewer dialog with print and save functionality"""
    
    def __init__(self, pdf_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PDF Viewer")
        self.resize(1000, 700)
        
        self.pdf_data = pdf_data
        self.pdf_document = QPdfDocument(self)
        self.buffer = QBuffer(self)
        
        self.setup_ui()
        self.load_pdf()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # PDF Preview Widget
        self.preview_widget = QPrintPreviewWidget()
        self.preview_widget.paintRequested.connect(self.render_pdf)
        layout.addWidget(self.preview_widget)
        
        # Button Layout - using QHBoxLayout
        btn_layout = QHBoxLayout()
        
        self.print_btn = QPushButton("Print")
        self.print_btn.clicked.connect(self.print_document)
        btn_layout.addWidget(self.print_btn)
        
        self.save_btn = QPushButton("Save PDF")
        self.save_btn.clicked.connect(self.save_pdf)
        btn_layout.addWidget(self.save_btn)
        
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.close)
        btn_layout.addWidget(self.close_btn)
        
        layout.addLayout(btn_layout)
        
    def load_pdf(self):
        """Load and validate PDF data"""
        try:
            if not self.pdf_data:
                raise ValueError("No PDF data provided")
                
            if isinstance(self.pdf_data, str):
                pdf_bytes = self.pdf_data.encode('latin1')
            else:
                pdf_bytes = bytes(self.pdf_data)
                
            self.buffer.setData(QByteArray(pdf_bytes))
            if not self.buffer.open(QIODevice.ReadOnly):
                raise RuntimeError("Could not open PDF buffer")
                
            if not self.pdf_document.load(self.buffer):
                raise RuntimeError("Failed to load PDF document")
                
            self.preview_widget.updatePreview()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load PDF:\n{str(e)}")
            self.close()
            
    def render_pdf(self, printer):
        """Render PDF with proper scaling"""
        try:
            painter = QPainter(printer)
            
            for page in range(self.pdf_document.pageCount()):
                if page > 0:
                    printer.newPage()
                
                page_size = self.pdf_document.pagePointSize(page)
                printer_rect = printer.pageRect(QPrinter.DevicePixel)
                
                # Calculate scale to fit page
                x_scale = printer_rect.width() / page_size.width()
                y_scale = printer_rect.height() / page_size.height()
                scale = min(x_scale, y_scale)
                
                painter.save()
                painter.scale(scale, scale)
                self.pdf_document.render(painter, page, page_size)
                painter.restore()
                
            painter.end()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to render PDF:\n{str(e)}")
            
    def print_document(self):
        """Print the document with dialog"""
        try:
            printer = QPrinter(QPrinter.HighResolution)
            print_dialog = QPrintDialog(printer, self)
            
            if print_dialog.exec() == QPrintDialog.Accepted:
                self.render_pdf(printer)
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to print:\n{str(e)}")
            
    def save_pdf(self):
        """Save PDF to file"""
        try:
            path, _ = QFileDialog.getSaveFileName(
                self, "Save PDF", "document.pdf", "PDF Files (*.pdf)"
            )
            
            if path:
                with open(path, 'wb') as f:
                    if isinstance(self.pdf_data, str):
                        f.write(self.pdf_data.encode('latin1'))
                    else:
                        f.write(bytes(self.pdf_data))
                QMessageBox.information(self, "Success", f"Saved to:\n{path}")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save:\n{str(e)}")
            
    def closeEvent(self, event):
        """Clean up resources"""
        if self.pdf_document:
            self.pdf_document.close()
        if self.buffer and self.buffer.isOpen():
            self.buffer.close()
        super().closeEvent(event)
        
def view_pdf(pdf_data, parent=None):
    """
    Open a PDF viewer dialog
    Args:
        pdf_data: Bytes, bytearray, or str of PDF content
        parent: Parent widget
    """
    try:
        if not pdf_data:
            raise ValueError("No PDF data provided")
            
        viewer = PDFViewerDialog(pdf_data, parent)
        viewer.exec()
        
    except Exception as e:
        QMessageBox.critical(parent, "Error", f"Could not view PDF:\n{str(e)}")


def print_pdf(pdf_data, parent=None):
    """
    Directly print a PDF document
    Args:
        pdf_data: Bytes, bytearray, or str of PDF content
        parent: Parent widget
    """
    try:
        if not pdf_data:
            raise ValueError("No PDF data provided")
            
        viewer = PDFViewerDialog(pdf_data, parent)
        viewer.print_document()
        viewer.close()
        
    except Exception as e:
        QMessageBox.critical(parent, "Error", f"Could not print PDF:\n{str(e)}")