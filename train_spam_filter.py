# train_spam_filter.py
from services.spam_filter import train_and_save_spam_filter
import sys

if __name__ == "__main__":
    if len(sys.argv) > 1:
        csv_file = sys.argv[1]
    else:
        csv_file = "spam_dataset.csv"  # Default filename
    
    print(f"🛡️ Training spam filter with: {csv_file}")
    success = train_and_save_spam_filter(csv_file)
    
    if success:
        print("✅ Training completed! Model saved to services/spam_filter.pkl")
    else:
        print("❌ Training failed. Check your dataset.")