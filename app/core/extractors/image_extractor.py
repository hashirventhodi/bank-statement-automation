import cv2
import numpy as np
import pytesseract
from PIL import Image
from google.cloud import vision
from app.utils.logger import logger
from config.config import OCR_CONFIG, GCV_CREDENTIALS

class ImageExtractor:
    """Extracts data from scanned bank statements using OCR."""
    
    def __init__(self, use_cloud_vision=True):
        self.use_cloud_vision = use_cloud_vision and GCV_CREDENTIALS is not None
        if OCR_CONFIG.get("tesseract_cmd"):
            pytesseract.pytesseract.tesseract_cmd = OCR_CONFIG["tesseract_cmd"]
    
    def extract(self, file_path):
        try:
            preprocessed_image = self._preprocess_image(file_path)
            if self.use_cloud_vision:
                text_content = self._perform_cloud_vision_ocr(file_path)
            else:
                text_content = self._perform_tesseract_ocr(preprocessed_image)
            transactions = self._extract_transactions_from_text(text_content)
            return {
                "raw_text": text_content,
                "transactions": transactions,
                "extraction_method": "google_vision" if self.use_cloud_vision else "tesseract"
            }
        except Exception as e:
            logger.error(f"Error extracting data from image: {str(e)}")
            raise
    
    def _preprocess_image(self, file_path):
        try:
            image = cv2.imread(file_path)
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            kernel = np.ones((1, 1), np.uint8)
            opening = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=1)
            return opening
        except Exception as e:
            logger.error(f"Error preprocessing image: {str(e)}")
            return cv2.imread(file_path)
    
    def _perform_tesseract_ocr(self, image):
        try:
            pil_image = Image.fromarray(image)
            text = pytesseract.image_to_string(
                pil_image, 
                lang=OCR_CONFIG.get("lang", "eng"),
                config=OCR_CONFIG.get("config", "--psm 6")
            )
            return text
        except Exception as e:
            logger.error(f"Error performing Tesseract OCR: {str(e)}")
            return ""
    
    def _perform_cloud_vision_ocr(self, file_path):
        try:
            client = vision.ImageAnnotatorClient()
            with open(file_path, "rb") as image_file:
                content = image_file.read()
            image = vision.Image(content=content)
            response = client.text_detection(image=image)
            texts = response.text_annotations
            if texts:
                return texts[0].description
            else:
                return ""
        except Exception as e:
            logger.error(f"Error performing Google Cloud Vision OCR: {str(e)}")
            return ""
    
    def _extract_transactions_from_text(self, text_content):
        transactions = []
        import re
        date_pattern = r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{2,4}[/-]\d{1,2}[/-]\d{1,2})'
        amount_pattern = r'(\d{1,3}(?:,\d{3})*\.\d{2})'
        lines = text_content.split('\n')
        for line in lines:
            if re.search(date_pattern, line) and re.search(amount_pattern, line):
                transaction = {}
                date_match = re.search(date_pattern, line)
                if date_match:
                    transaction["date"] = date_match.group(0)
                amounts = re.findall(amount_pattern, line)
                if amounts:
                    transaction["amount"] = float(amounts[0].replace(',', ''))
                    if re.search(r'dr|debit|withd', line, re.IGNORECASE):
                        transaction["transaction_type"] = "debit"
                    elif re.search(r'cr|credit|dep', line, re.IGNORECASE):
                        transaction["transaction_type"] = "credit"
                    else:
                        transaction["transaction_type"] = "unknown"
                    if len(amounts) > 1:
                        transaction["balance"] = float(amounts[-1].replace(',', ''))
                desc_line = line
                desc_line = re.sub(date_pattern, "", desc_line)
                for amount in amounts:
                    desc_line = desc_line.replace(amount, "")
                desc_line = re.sub(r'\s+', ' ', desc_line).strip()
                if desc_line:
                    transaction["description"] = desc_line
                if "date" in transaction and "amount" in transaction:
                    transactions.append(transaction)
        return transactions
