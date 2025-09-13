# services/spam_filter.py
import pickle
import os
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

class SpamFilter:
    def __init__(self):
        self.model = None
        self.vectorizer = None
        self.accuracy = 0.0
        self.is_trained = False
        self.load_model()
    
    def load_model(self):
        """Load pre-trained spam filter from services folder"""
        try:
            model_path = "services/spam_filter.pkl"
            if os.path.exists(model_path):
                with open(model_path, 'rb') as f:
                    saved_objects = pickle.load(f)
                
                self.model = saved_objects['model']
                self.vectorizer = saved_objects['vectorizer']
                self.accuracy = saved_objects.get('accuracy', 0.0)
                self.is_trained = saved_objects.get('is_trained', False)
                
                print(f"✅ Spam filter loaded (Accuracy: {self.accuracy:.4f})")
            else:
                print("⚠️ No spam filter model found. Train with train_spam_filter.py")
                self.model = None
                self.vectorizer = None
                self.is_trained = False
        except Exception as e:
            print(f"❌ Error loading spam filter: {e}")
            self.model = None
            self.vectorizer = None
            self.is_trained = False
    
    def train_from_dataframe(self, df, text_column='text', spam_column='spam'):
        """Train spam filter from DataFrame"""
        try:
            print("🤖 Training spam filter from DataFrame...")
            
            # Prepare data
            X = df[text_column].astype(str)
            y = df[spam_column]
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y
            )
            
            # Feature extraction
            self.vectorizer = TfidfVectorizer(
                min_df=1,
                stop_words='english',
                lowercase=True,
                max_features=5000
            )
            
            X_train_features = self.vectorizer.fit_transform(X_train)
            X_test_features = self.vectorizer.transform(X_test)
            
            # Train model
            self.model = LogisticRegression(
                random_state=42,
                max_iter=1000,
                class_weight='balanced'
            )
            
            self.model.fit(X_train_features, y_train)
            
            # Evaluate
            train_pred = self.model.predict(X_train_features)
            test_pred = self.model.predict(X_test_features)
            
            train_accuracy = accuracy_score(y_train, train_pred)
            test_accuracy = accuracy_score(y_test, test_pred)
            self.accuracy = test_accuracy
            self.is_trained = True
            
            print(f"✅ Training complete! Accuracy: {test_accuracy:.4f}")
            return True
            
        except Exception as e:
            print(f"❌ Training failed: {e}")
            return False
    
    def save_model(self):
        """Save the trained model to disk"""
        if self.model is None or self.vectorizer is None:
            print("❌ No model to save")
            return False
        
        try:
            save_objects = {
                'model': self.model,
                'vectorizer': self.vectorizer,
                'accuracy': self.accuracy,
                'is_trained': self.is_trained
            }
            
            os.makedirs("services", exist_ok=True)
            with open("services/spam_filter.pkl", 'wb') as f:
                pickle.dump(save_objects, f)
            
            print("💾 Model saved to services/spam_filter.pkl")
            return True
            
        except Exception as e:
            print(f"❌ Error saving model: {e}")
            return False
    
    def is_spam(self, text, threshold=0.5):
        """Check if text is spam using pre-trained model"""
        if self.model is None or self.vectorizer is None:
            spam_detected = self.basic_spam_check(text)
            return spam_detected, 1.0 if spam_detected else 0.0
        
        try:
            features = self.vectorizer.transform([text])
            probability = self.model.predict_proba(features)[0][1]
            return probability > threshold, probability
        except Exception as e:
            print(f"❌ Prediction error: {e}")
            spam_detected = self.basic_spam_check(text)
            return spam_detected, 1.0 if spam_detected else 0.0
    
    def basic_spam_check(self, text):
        """Basic fallback spam detection"""
        spam_keywords = [
            'free', 'win', 'prize', 'viagra', 'casino', 'lottery',
            'money', 'cash', 'profit', 'discount', 'offer', '100%',
            'guarantee', 'risk-free', 'special promotion', 'earn',
            'extra income', 'work from home', 'make money',
            'click here', 'limited time', 'congratulations', 'winner'
        ]
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in spam_keywords)
    
    def get_spam_probability(self, text):
        """Get spam probability score (0-1)"""
        if self.model is None or self.vectorizer is None:
            return 1.0 if self.basic_spam_check(text) else 0.0
        
        try:
            features = self.vectorizer.transform([text])
            return self.model.predict_proba(features)[0][1]
        except:
            return 1.0 if self.basic_spam_check(text) else 0.0

# Example usage and training function
def train_and_save_spam_filter(csv_path):
    """Complete training function for your dataset"""
    try:
        # Load your dataset
        print(f"📊 Loading dataset from {csv_path}...")
        df = pd.read_csv(csv_path)
        
        # Check required columns
        if 'text' not in df.columns or 'spam' not in df.columns:
            print("❌ Dataset must contain 'text' and 'spam' columns")
            return False
        
        print(f"✅ Dataset loaded: {df.shape}")
        print(f"📈 Spam distribution:\n{df['spam'].value_counts()}")
        
        # Create and train spam filter
        spam_filter = SpamFilter()
        success = spam_filter.train_from_dataframe(df, 'text', 'spam')
        
        if success:
            # Save the model
            spam_filter.save_model()
            print("🎉 Spam filter training completed successfully!")
            return True
        else:
            print("❌ Spam filter training failed")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    # Example: Train from your CSV file
    csv_file = "spam_dataset.csv"  # Change to your file path
    if os.path.exists(csv_file):
        train_and_save_spam_filter(csv_file)
    else:
        print("ℹ️ Usage: python -c 'from services.spam_filter import train_and_save_spam_filter; train_and_save_spam_filter(\"your_dataset.csv\")'")