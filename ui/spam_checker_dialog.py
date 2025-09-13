# ui/spam_checker_dialog.py
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                              QPushButton, QTextEdit, QFrame, QProgressBar,
                              QGroupBox, QApplication)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor
import pickle
import os

class SpamCheckerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Spam Content Checker")
        self.setMinimumSize(800, 600)
        self.spam_filter = None
        
        self.setup_ui()
        self.load_spam_filter()
        
    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)
        
        # Header
        header_label = QLabel("Spam Content Analyzer")
        header_label.setFont(QFont("Arial", 16, QFont.Bold))
        header_label.setStyleSheet("color: #2c3e50;")
        main_layout.addWidget(header_label)
        
        # Description
        desc_label = QLabel(
            "Paste your email content below to check if it might be flagged as spam. "
            "The analyzer will show spam probability and highlight problematic content."
        )
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #6c757d; padding: 5px;")
        main_layout.addWidget(desc_label)
        
        # Split layout for input and output
        split_layout = QHBoxLayout()
        
        # Left pane - Input
        input_group = QGroupBox("📝 Paste Your Text Here")
        input_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        input_layout = QVBoxLayout(input_group)
        
        self.input_text = QTextEdit()
        self.input_text.setPlaceholderText("Paste your email content here...\n\nExample: 'Win free prize money now!!!'")
        self.input_text.setMinimumHeight(250)
        input_layout.addWidget(self.input_text)
        
        # Test button
        test_btn = QPushButton("Test for Spam")
        test_btn.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                font-weight: bold;
                padding: 10px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)
        test_btn.clicked.connect(self.analyze_text)
        input_layout.addWidget(test_btn)
        
        split_layout.addWidget(input_group)
        
        # Right pane - Results
        results_group = QGroupBox("📊 Analysis Results")
        results_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        results_layout = QVBoxLayout(results_group)
        
        # Spam probability meter
        self.probability_label = QLabel("Spam Probability: ")
        self.probability_label.setFont(QFont("Arial", 12, QFont.Bold))
        results_layout.addWidget(self.probability_label)
        
        self.spam_meter = QProgressBar()
        self.spam_meter.setRange(0, 100)
        self.spam_meter.setFormat("Risk Level: %p%")
        self.spam_meter.setMinimumHeight(25)
        results_layout.addWidget(self.spam_meter)
        
        # Result verdict
        self.verdict_label = QLabel("Verdict: ")
        self.verdict_label.setFont(QFont("Arial", 14, QFont.Bold))
        results_layout.addWidget(self.verdict_label)
        
        # Detailed analysis
        analysis_group = QGroupBox("🔍 Detailed Analysis")
        analysis_layout = QVBoxLayout(analysis_group)
        
        self.analysis_text = QTextEdit()
        self.analysis_text.setReadOnly(True)
        self.analysis_text.setMinimumHeight(150)
        analysis_layout.addWidget(self.analysis_text)
        
        results_layout.addWidget(analysis_group)
        
        # Highlighted text
        highlight_group = QGroupBox("🎯 Processed Text (Spam Highlights)")
        highlight_layout = QVBoxLayout(highlight_group)
        
        self.highlighted_text = QTextEdit()
        self.highlighted_text.setReadOnly(True)
        self.highlighted_text.setMinimumHeight(100)
        highlight_layout.addWidget(self.highlighted_text)
        
        results_layout.addWidget(highlight_group)
        
        split_layout.addWidget(results_group)
        main_layout.addLayout(split_layout)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        copy_btn = QPushButton("Copy Safe Text")
        copy_btn.setProperty("class", "success")
        copy_btn.setIcon(QIcon("static/icons/copy.png"))
        copy_btn.setToolTip("Copy the processed text to clipboard")
        copy_btn.clicked.connect(self.copy_safe_text)
        
        close_btn = QPushButton("Close")
        close_btn.setProperty("class", "danger")
        close_btn.setIcon(QIcon("static/icons/cancel.png"))
        close_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(copy_btn)
        button_layout.addStretch()
        button_layout.addWidget(close_btn)
        
        main_layout.addLayout(button_layout)
        
    def load_spam_filter(self):
        """Load the pre-trained spam filter model from services folder"""
        try:
            model_path = "services/spam_filter.pkl"  # ← Look in services folder
            if os.path.exists(model_path):
                with open(model_path, 'rb') as f:
                    self.spam_filter = pickle.load(f)
                self.analysis_text.setPlainText("✅ Spam filter model loaded from services folder!")
            else:
                self.analysis_text.setPlainText("⚠️ No spam filter model found in services folder. Using basic pattern matching.")
                self.spam_filter = None
        except Exception as e:
            self.analysis_text.setPlainText(f"❌ Error loading spam filter: {str(e)}")
            self.spam_filter = None
    
    def analyze_text(self):
        """Analyze the text for spam content"""
        text = self.input_text.toPlainText().strip()
        
        if not text:
            self.analysis_text.setPlainText("Please enter some text to analyze.")
            return
        
        # Get spam probability
        spam_prob = self.get_spam_probability(text)
        
        # Update UI
        self.update_results(text, spam_prob)
    
    def get_spam_probability(self, text):
        """Get spam probability using the trained model or fallback"""
        if self.spam_filter and hasattr(self.spam_filter, 'predict_proba'):
            try:
                return self.spam_filter.predict_proba([text])[0][1]  # Probability of being spam
            except:
                pass
        
        # Fallback: Basic pattern matching
        return self.basic_spam_check(text)
    
    def basic_spam_check(self, text):
        """Basic spam detection fallback"""
        text_lower = text.lower()
        spam_indicators = [
            'free', 'win', 'winner', 'prize', '100%', 'guarantee',
            'cash', 'money', 'profit', 'discount', 'offer', 'limited time',
            'risk-free', 'no cost', 'special promotion', 'earn', 'extra income',
            'work from home', 'make money', 'mlm', 'multi-level marketing'
        ]
        
        # Count spam indicators
        spam_count = sum(1 for word in spam_indicators if word in text_lower)
        
        # Check for excessive punctuation
        if '!!!' in text or '???' in text:
            spam_count += 2
        
        # Check for ALL CAPS
        if any(word.isupper() and len(word) > 3 for word in text.split()):
            spam_count += 2
        
        # Convert to probability (0-1)
        return min(1.0, spam_count * 0.1)
    
    def update_results(self, text, spam_prob):
        """Update the results display"""
        # Update probability meter
        percent = int(spam_prob * 100)
        self.probability_label.setText(f"Spam Probability: {percent}%")
        self.spam_meter.setValue(percent)
        
        # Set meter color based on risk
        if percent >= 70:
            color = "#dc3545"  # Red - high risk
            verdict = "HIGH RISK - Likely Spam"
        elif percent >= 40:
            color = "#ffc107"  # Yellow - medium risk
            verdict = "MEDIUM RISK - Possibly Spam"
        else:
            color = "#28a745"  # Green - low risk
            verdict = "LOW RISK - Probably Safe"
        
        self.spam_meter.setStyleSheet(f"""
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 3px;
            }}
        """)
        
        self.verdict_label.setText(f"Verdict: {verdict}")
        self.verdict_label.setStyleSheet(f"color: {color};")
        
        # Generate detailed analysis
        analysis = self.generate_analysis(text, spam_prob)
        self.analysis_text.setPlainText(analysis)
        
        # Show highlighted text
        highlighted = self.highlight_spam_words(text)
        self.highlighted_text.setHtml(highlighted)
    
    def generate_analysis(self, text, spam_prob):
        """Generate detailed analysis report"""
        analysis = []
        
        if spam_prob >= 0.7:
            analysis.append("❌ HIGH SPAM RISK DETECTED")
            analysis.append("This content has a high chance of being flagged as spam.")
        elif spam_prob >= 0.4:
            analysis.append("⚠️ MODERATE SPAM RISK")
            analysis.append("Some spam-like patterns detected. Consider revising.")
        else:
            analysis.append("✅ LOW SPAM RISK")
            analysis.append("Content appears safe and professional.")
        
        analysis.append("\n🔍 DETECTED PATTERNS:")
        
        # Check for specific issues
        text_lower = text.lower()
        spam_words = ['free', 'win', 'winner', 'prize', '100%', 'guarantee']
        
        for word in spam_words:
            if word in text_lower:
                analysis.append(f"• Found spam-trigger word: '{word}'")
        
        if '!!!' in text or '???' in text:
            analysis.append("• Excessive punctuation detected")
        
        if any(word.isupper() and len(word) > 3 for word in text.split()):
            analysis.append("• ALL CAPS words detected")
        
        if not any(term in text_lower for term in ['school', 'student', 'teacher', 'parent', 'homework', 'assignment']):
            analysis.append("• Missing school-related terminology")
        
        analysis.append("\n💡 SUGGESTIONS:")
        if spam_prob > 0.4:
            analysis.append("- Avoid words like 'free', 'win', 'prize'")
            analysis.append("- Use professional language")
            analysis.append("- Include school-related context")
            analysis.append("- Avoid excessive punctuation")
        else:
            analysis.append("- Content looks good for school communication!")
        
        return "\n".join(analysis)
    
    def highlight_spam_words(self, text):
        """Highlight spam words in the text with HTML"""
        spam_words = ['free', 'win', 'winner', 'prize', '100%', 'guarantee', 'cash', 'money']
        
        highlighted_text = text
        for word in spam_words:
            if word in text.lower():
                # Highlight the word with red background
                highlighted_text = highlighted_text.replace(
                    word, 
                    f'<span style="background-color: #ffcccc; color: #dc3545; font-weight: bold;">{word}</span>'
                )
        
        # Also highlight ALL CAPS words
        words = highlighted_text.split()
        for i, word in enumerate(words):
            if word.isupper() and len(word) > 3 and not word.startswith('<'):
                words[i] = f'<span style="background-color: #fff3cd; color: #856404;">{word}</span>'
        
        highlighted_text = ' '.join(words)
        
        return f"""
        <div style="font-family: Arial; line-height: 1.4; padding: 10px;">
            {highlighted_text}
        </div>
        """
    
    def copy_safe_text(self):
        """Copy the original text to clipboard"""
        text = self.input_text.toPlainText()
        QApplication.clipboard().setText(text)
        self.analysis_text.append("\n✅ Text copied to clipboard!")