# utils/printing.py
from PySide6.QtWidgets import QMessageBox
from fpdf import FPDF
from docx import Document
import tempfile
import os

class PDFGenerator:
    """Helper class for generating PDF documents"""
    
    @staticmethod
    def generate_teacher_pdf(teacher_data):
        """Generate a teacher profile PDF"""
        try:
            pdf = FPDF()
            pdf.add_page()
            
            # Add content to PDF using teacher_data
            pdf.set_font("Arial", size=12)
            pdf.cell(200, 10, txt=f"Teacher Profile: {teacher_data['name']}", ln=1)
            # Add more content as needed...
            
            # Return PDF as bytes
            return pdf.output(dest='S').encode('latin1')
            
        except Exception as e:
            raise ValueError(f"PDF generation failed: {str(e)}")


def generate_pdf(document_type, data):
    """
    Generate PDF for different document types
    Args:
        document_type: 'teacher', 'report', etc.
        data: Data needed for the document
    """
    try:
        if document_type == 'teacher':
            return PDFGenerator.generate_teacher_pdf(data)
        # Add other document types as needed...
        else:
            raise ValueError(f"Unknown document type: {document_type}")
            
    except Exception as e:
        raise ValueError(f"Document generation error: {str(e)}")