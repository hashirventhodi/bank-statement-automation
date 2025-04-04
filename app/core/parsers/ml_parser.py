from typing import Dict, List, Any, Optional
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from app.core.parsers.transaction_parser import TransactionParser
from app.utils.logger import logger

class MLParser(TransactionParser):
    """ML-enhanced transaction parser that learns from corrections."""
    
    def __init__(self, template: Optional[Dict] = None, model_path: Optional[str] = None):
        super().__init__(template)
        self.vectorizer = TfidfVectorizer(
            max_features=1000,
            ngram_range=(1, 3),
            stop_words='english'
        )
        self.classifier = RandomForestClassifier(
            n_estimators=100,
            random_state=42
        )
        self.is_trained = False
        
        if model_path:
            self.load_model(model_path)
    
    def train(self, training_data: List[Dict[str, Any]]) -> None:
        """
        Train the ML model on historical transaction data.
        
        Args:
            training_data: List of transaction dictionaries with correct categorization
        """
        try:
            # Extract features and labels
            descriptions = [tx.get("raw_description", "") for tx in training_data]
            categories = [tx.get("bank_category", "UNKNOWN") for tx in training_data]
            
            # Transform text to features
            X = self.vectorizer.fit_transform(descriptions)
            
            # Train the classifier
            self.classifier.fit(X, categories)
            
            self.is_trained = True
            logger.info("ML parser training completed successfully")
            
        except Exception as e:
            logger.error(f"Error training ML parser: {str(e)}")
            self.is_trained = False
    
    def parse(self, raw_transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Parse transactions with ML enhancement if trained.
        
        Args:
            raw_transactions: List of raw transaction dictionaries
            
        Returns:
            List of parsed transaction dictionaries
        """
        # First do basic parsing
        parsed_transactions = super().parse(raw_transactions)
        
        # Apply ML enhancements if trained
        if self.is_trained:
            try:
                # Extract descriptions
                descriptions = [tx.get("raw_description", "") for tx in parsed_transactions]
                
                # Transform text
                X = self.vectorizer.transform(descriptions)
                
                # Predict categories
                predicted_categories = self.classifier.predict(X)
                
                # Get prediction probabilities for confidence scores
                prediction_probs = self.classifier.predict_proba(X)
                confidence_scores = np.max(prediction_probs, axis=1)
                
                # Update transactions with predictions
                for tx, category, confidence in zip(parsed_transactions, predicted_categories, confidence_scores):
                    if confidence > 0.7:  # Only use predictions with high confidence
                        tx["bank_category"] = category
                        tx["confidence_score"] = float(confidence)
                
            except Exception as e:
                logger.error(f"Error applying ML enhancements: {str(e)}")
        
        return parsed_transactions
    
    def save_model(self, model_path: str) -> None:
        """Save the trained model and vectorizer."""
        if not self.is_trained:
            logger.warning("Cannot save untrained model")
            return
            
        try:
            import joblib
            
            # Save the vectorizer
            joblib.dump(self.vectorizer, f"{model_path}_vectorizer.joblib")
            
            # Save the classifier
            joblib.dump(self.classifier, f"{model_path}_classifier.joblib")
            
            logger.info("ML model saved successfully")
            
        except Exception as e:
            logger.error(f"Error saving ML model: {str(e)}")
    
    def load_model(self, model_path: str) -> None:
        """Load a trained model and vectorizer."""
        try:
            import joblib
            
            # Load the vectorizer
            self.vectorizer = joblib.load(f"{model_path}_vectorizer.joblib")
            
            # Load the classifier
            self.classifier = joblib.load(f"{model_path}_classifier.joblib")
            
            self.is_trained = True
            logger.info("ML model loaded successfully")
            
        except Exception as e:
            logger.error(f"Error loading ML model: {str(e)}")
            self.is_trained = False
    
    def update_model(self, new_data: List[Dict[str, Any]]) -> None:
        """
        Update the model with new transaction data.
        
        Args:
            new_data: List of new transaction dictionaries with correct categorization
        """
        if not self.is_trained:
            self.train(new_data)
            return
            
        try:
            # Extract features and labels from new data
            descriptions = [tx.get("raw_description", "") for tx in new_data]
            categories = [tx.get("bank_category", "UNKNOWN") for tx in new_data]
            
            # Transform text to features
            X_new = self.vectorizer.transform(descriptions)
            
            # Update the classifier with new data
            self.classifier.fit(X_new, categories)
            
            logger.info("ML model updated successfully")
            
        except Exception as e:
            logger.error(f"Error updating ML model: {str(e)}")