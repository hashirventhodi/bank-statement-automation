import io
import re
import json
import PyPDF2
import tabula
import pandas as pd
from pathlib import Path
from app.utils.logger import logger
from config.config import ML_CONFIG

class PDFExtractor:
    """Extracts data from PDF bank statements."""
    
    def __init__(self, template=None):
        self.template = template
        
    def extract(self, file_path):
        """
        Extract all relevant data from a PDF bank statement.
        """
        try:
            text_content = self._extract_text(file_path)
            metadata = self._extract_metadata(text_content, file_path)
            if self.template:
                transactions = self._extract_transactions_with_template(file_path)
            else:
                transactions = self._extract_transactions_from_tables(file_path)
                if not transactions:
                    transactions = self._extract_transactions_from_text(text_content)
            return {
                "metadata": metadata,
                "transactions": transactions,
                "extraction_method": "template" if self.template else "auto",
                "raw_text": text_content
            }
        except Exception as e:
            logger.error(f"Error extracting data from PDF: {str(e)}")
            raise
    
    def _extract_text(self, file_path):
        text_content = ""
        try:
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                for page in reader.pages:
                    text_content += page.extract_text()
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {str(e)}")
        return text_content
    
    def _extract_metadata(self, text_content, file_path):
        metadata = {
            "account_number": None,
            "account_name": None,
            "statement_period": None,
            "opening_balance": None,
            "closing_balance": None,
            "bank_name": None,
            "page_count": 0
        }
        try:
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                metadata["page_count"] = len(reader.pages)
            if self.template:
                template_data = self.template if isinstance(self.template, dict) else json.loads(self.template)
                for field, pattern in template_data.get("metadata_patterns", {}).items():
                    match = re.search(pattern, text_content)
                    if match and match.group(1):
                        metadata[field] = match.group(1).strip()
            else:
                account_match = re.search(r'(?:account\s*no|account\s*number|a/c\s*no)[:\s]*([0-9X]+)', 
                                         text_content, re.IGNORECASE)
                if account_match:
                    metadata["account_number"] = account_match.group(1).strip()
                period_match = re.search(r'(?:statement period|period)[:\s]*([\w\s,]+to[\w\s,]+)', 
                                        text_content, re.IGNORECASE)
                if period_match:
                    metadata["statement_period"] = period_match.group(1).strip()
                opening_match = re.search(r'(?:opening balance|begin balance)[:\s]*([\d,]+\.\d{2})', 
                                        text_content, re.IGNORECASE)
                if opening_match:
                    metadata["opening_balance"] = float(opening_match.group(1).replace(',', ''))
                closing_match = re.search(r'(?:closing balance|end balance)[:\s]*([\d,]+\.\d{2})', 
                                        text_content, re.IGNORECASE)
                if closing_match:
                    metadata["closing_balance"] = float(closing_match.group(1).replace(',', ''))
                common_banks = ["HDFC", "SBI", "ICICI", "Axis", "Bank of Baroda", "PNB", 
                                "Kotak", "Yes Bank", "IDBI", "Bank of India", "Canara Bank", "Chase", 
                                "Bank of America", "Wells Fargo", "Citibank", "HSBC"]
                for bank in common_banks:
                    if bank.lower() in text_content.lower():
                        metadata["bank_name"] = bank
                        break
        except Exception as e:
            logger.error(f"Error extracting metadata: {str(e)}")
        return metadata
    
    def _extract_transactions_with_template(self, file_path):
        transactions = []
        try:
            template_data = self.template if isinstance(self.template, dict) else json.loads(self.template)
            table_area = template_data.get("transaction_table_area")
            if table_area:
                tables = tabula.read_pdf(file_path, 
                                          pages="all", 
                                          area=[table_area.get("top", 0), 
                                                table_area.get("left", 0),
                                                table_area.get("bottom", 1000),
                                                table_area.get("right", 1000)],
                                          multiple_tables=True)
            else:
                tables = tabula.read_pdf(file_path, pages="all", multiple_tables=True)
            header_pattern = template_data.get("transaction_header_pattern", [])
            for table in tables:
                if not table.empty:
                    column_match = False
                    if set(header_pattern).issubset(set(str(col).lower() for col in table.columns)):
                        column_match = True
                    if not column_match and not table.empty:
                        first_row = table.iloc[0].astype(str)
                        if any(pattern.lower() in " ".join(first_row).lower() for pattern in header_pattern):
                            table.columns = table.iloc[0]
                            table = table.iloc[1:].reset_index(drop=True)
                            column_match = True
                    if column_match:
                        field_mapping = template_data.get("field_mapping", {})
                        for _, row in table.iterrows():
                            transaction = {}
                            for field, column_pattern in field_mapping.items():
                                matching_cols = [col for col in table.columns 
                                                 if re.search(column_pattern, str(col), re.IGNORECASE)]
                                if matching_cols:
                                    value = row[matching_cols[0]]
                                    if field in ["amount", "debit", "credit", "balance"]:
                                        if pd.notna(value):
                                            try:
                                                value = float(str(value).replace(',', ''))
                                            except:
                                                value = None
                                    transaction[field] = value
                            if "debit" in transaction and "credit" in transaction:
                                if pd.notna(transaction["debit"]) and transaction["debit"] > 0:
                                    transaction["amount"] = transaction["debit"]
                                    transaction["transaction_type"] = "debit"
                                elif pd.notna(transaction["credit"]) and transaction["credit"] > 0:
                                    transaction["amount"] = transaction["credit"]
                                    transaction["transaction_type"] = "credit"
                            if all(field in transaction and pd.notna(transaction[field]) for field in ["date", "amount"]):
                                transactions.append(transaction)
        except Exception as e:
            logger.error(f"Error extracting transactions with template: {str(e)}")
        return transactions
    
    def _extract_transactions_from_tables(self, file_path):
        transactions = []
        try:
            tables = tabula.read_pdf(file_path, pages="all", multiple_tables=True)
            for table in tables:
                if table.empty:
                    continue
                headers = set(str(col).lower() for col in table.columns)
                transaction_indicators = ["date", "description", "amount", "balance", "debit", "credit", "particulars"]
                if any(indicator in headers for indicator in transaction_indicators):
                    date_col = next((col for col in table.columns if "date" in str(col).lower()), None)
                    desc_col = next((col for col in table.columns if any(term in str(col).lower() for term in 
                                                                         ["description", "particulars", "details", "narration"])), None)
                    debit_col = next((col for col in table.columns if any(term in str(col).lower() for term in 
                                                                          ["debit", "withdrawal"])), None)
                    credit_col = next((col for col in table.columns if any(term in str(col).lower() for term in 
                                                                           ["credit", "deposit"])), None)
                    amount_col = next((col for col in table.columns if "amount" in str(col).lower()), None)
                    balance_col = next((col for col in table.columns if "balance" in str(col).lower()), None)
                    if date_col and (amount_col or debit_col or credit_col):
                        for _, row in table.iterrows():
                            transaction = {}
                            if date_col:
                                transaction["date"] = row[date_col]
                            if desc_col:
                                transaction["description"] = row[desc_col]
                            if debit_col and credit_col:
                                try:
                                    debit_value = float(str(row[debit_col]).replace(',', '')) if pd.notna(row[debit_col]) else 0
                                    credit_value = float(str(row[credit_col]).replace(',', '')) if pd.notna(row[credit_col]) else 0
                                    if debit_value > 0:
                                        transaction["amount"] = debit_value
                                        transaction["transaction_type"] = "debit"
                                    elif credit_value > 0:
                                        transaction["amount"] = credit_value
                                        transaction["transaction_type"] = "credit"
                                except:
                                    pass
                            elif amount_col:
                                try:
                                    amount_value = float(str(row[amount_col]).replace(',', '')) if pd.notna(row[amount_col]) else 0
                                    transaction["amount"] = abs(amount_value)
                                    transaction["transaction_type"] = "credit" if amount_value >= 0 else "debit"
                                except:
                                    pass
                            if balance_col:
                                try:
                                    balance_value = float(str(row[balance_col]).replace(',', '')) if pd.notna(row[balance_col]) else None
                                    transaction["balance"] = balance_value
                                except:
                                    pass
                            if "date" in transaction and "amount" in transaction:
                                transactions.append(transaction)
        except Exception as e:
            logger.error(f"Error extracting transactions from tables: {str(e)}")
        return transactions
    
    def _extract_transactions_from_text(self, text_content):
        transactions = []
        try:
            date_pattern = r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{2,4}[/-]\d{1,2}[/-]\d{1,2})'
            amount_pattern = r'(\d{1,3}(?:,\d{3})*\.\d{2})'
            transaction_pattern = f".*{date_pattern}.*{amount_pattern}.*"
            potential_transactions = re.finditer(transaction_pattern, text_content, re.MULTILINE)
            for match in potential_transactions:
                line = match.group(0)
                transaction = {}
                date_match = re.search(date_pattern, line)
                if date_match:
                    transaction["date"] = date_match.group(0)
                amounts = re.findall(amount_pattern, line)
                if len(amounts) == 1:
                    amount_value = float(amounts[0].replace(',', ''))
                    transaction["amount"] = amount_value
                    if re.search(r'dr|debit|with', line, re.IGNORECASE):
                        transaction["transaction_type"] = "debit"
                    elif re.search(r'cr|credit|dep|deposit', line, re.IGNORECASE):
                        transaction["transaction_type"] = "credit"
                    else:
                        transaction["transaction_type"] = "debit"
                elif len(amounts) == 2:
                    first_value = float(amounts[0].replace(',', ''))
                    second_value = float(amounts[1].replace(',', ''))
                    if first_value > 0 and second_value == 0:
                        transaction["amount"] = first_value
                        transaction["transaction_type"] = "debit"
                    elif first_value == 0 and second_value > 0:
                        transaction["amount"] = second_value
                        transaction["transaction_type"] = "credit"
                    else:
                        transaction["amount"] = first_value
                        transaction["balance"] = second_value
                        transaction["transaction_type"] = "debit"
                elif len(amounts) >= 3:
                    debit_value = float(amounts[0].replace(',', ''))
                    credit_value = float(amounts[1].replace(',', ''))
                    balance_value = float(amounts[2].replace(',', ''))
                    if debit_value > 0:
                        transaction["amount"] = debit_value
                        transaction["transaction_type"] = "debit"
                    elif credit_value > 0:
                        transaction["amount"] = credit_value
                        transaction["transaction_type"] = "credit"
                    transaction["balance"] = balance_value
                desc_line = line
                desc_line = re.sub(date_pattern, "", desc_line)
                for amount in amounts:
                    desc_line = desc_line.replace(amount, "")
                desc_line = re.sub(r'\s+', ' ', desc_line).strip()
                if desc_line:
                    transaction["description"] = desc_line
                if "date" in transaction and "amount" in transaction:
                    transactions.append(transaction)
        except Exception as e:
            logger.error(f"Error extracting transactions from text: {str(e)}")
        return transactions
