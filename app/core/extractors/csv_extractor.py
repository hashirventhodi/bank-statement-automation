import pandas as pd
import re
import datetime
from app.utils.logger import logger

class CSVExtractor:
    """Extracts data from CSV or Excel bank statements."""
    
    def __init__(self, template=None):
        self.template = template
    
    def extract(self, file_path, file_format="csv"):
        try:
            if file_format.lower() == "csv":
                df = pd.read_csv(file_path)
            else:
                df = pd.read_excel(file_path)
            metadata = self._extract_metadata(df, file_path)
            if self.template:
                transactions = self._extract_transactions_with_template(df)
            else:
                transactions = self._extract_transactions_auto(df)
            return {
                "metadata": metadata,
                "transactions": transactions,
                "extraction_method": "template" if self.template else "auto"
            }
        except Exception as e:
            logger.error(f"Error extracting data from {file_format.upper()}: {str(e)}")
            raise
    
    def _extract_metadata(self, df, file_path):
        metadata = {
            "account_number": None,
            "account_name": None,
            "statement_period": None,
            "opening_balance": None,
            "closing_balance": None,
            "bank_name": None
        }
        try:
            if self.template:
                import json
                template_data = self.template if isinstance(self.template, dict) else json.loads(self.template)
                header_rows = template_data.get("header_rows", 5)
                header_text = " ".join([" ".join(map(str, row)) for _, row in df.head(header_rows).iterrows()])
                for field, pattern in template_data.get("metadata_patterns", {}).items():
                    match = re.search(pattern, header_text)
                    if match and match.group(1):
                        metadata[field] = match.group(1).strip()
            else:
                header_text = " ".join([" ".join(map(str, row)) for _, row in df.head(5).iterrows()])
                account_match = re.search(r'(?:account\s*no|account\s*number|a/c\s*no)[:\s]*([0-9X]+)', 
                                         header_text, re.IGNORECASE)
                if account_match:
                    metadata["account_number"] = account_match.group(1).strip()
                date_cols = [col for col in df.columns if "date" in str(col).lower()]
                if date_cols:
                    try:
                        dates = pd.to_datetime(df[date_cols[0]], errors='coerce')
                        dates = dates.dropna()
                        if not dates.empty:
                            start_date = dates.min().strftime("%d/%m/%Y")
                            end_date = dates.max().strftime("%d/%m/%Y")
                            metadata["statement_period"] = f"{start_date} to {end_date}"
                    except:
                        pass
                for i in range(min(5, len(df))):
                    row_text = " ".join(map(str, df.iloc[i]))
                    if "opening" in row_text.lower() or "beginning" in row_text.lower():
                        amounts = re.findall(r'(\d{1,3}(?:,\d{3})*\.\d{2})', row_text)
                        if amounts:
                            metadata["opening_balance"] = float(amounts[0].replace(',', ''))
                for i in range(1, min(6, len(df) + 1)):
                    row_text = " ".join(map(str, df.iloc[-i]))
                    if "closing" in row_text.lower() or "ending" in row_text.lower():
                        amounts = re.findall(r'(\d{1,3}(?:,\d{3})*\.\d{2})', row_text)
                        if amounts:
                            metadata["closing_balance"] = float(amounts[0].replace(',', ''))
                import os
                filename = os.path.basename(file_path).lower()
                common_banks = ["hdfc", "sbi", "icici", "axis", "baroda", "pnb", "kotak", 
                                "yes", "idbi", "boi", "canara", "chase", "bofa", "wells", 
                                "citi", "hsbc"]
                for bank in common_banks:
                    if bank in filename:
                        metadata["bank_name"] = bank.upper()
                        break
        except Exception as e:
            logger.error(f"Error extracting metadata from tabular data: {str(e)}")
        return metadata
    
    def _extract_transactions_with_template(self, df):
        transactions = []
        try:
            import json
            template_data = self.template if isinstance(self.template, dict) else json.loads(self.template)
            start_row = template_data.get("transaction_start_row", 0)
            end_row = template_data.get("transaction_end_row", None)
            transaction_df = df.iloc[start_row:end_row].copy()
            transaction_df = transaction_df.dropna(how='all')
            field_mapping = template_data.get("field_mapping", {})
            for _, row in transaction_df.iterrows():
                transaction = {}
                for field, column_pattern in field_mapping.items():
                    matching_cols = [col for col in transaction_df.columns 
                                     if re.search(column_pattern, str(col), re.IGNORECASE)]
                    if matching_cols:
                        value = row[matching_cols[0]]
                        if field == "date" and pd.notna(value):
                            try:
                                date_format = template_data.get("date_format", "%d/%m/%Y")
                                if isinstance(value, (datetime.date, datetime.datetime)):
                                    value = value.strftime(date_format)
                                elif isinstance(value, str):
                                    parsed_date = pd.to_datetime(value)
                                    value = parsed_date.strftime(date_format)
                            except:
                                pass
                        if field in ["amount", "debit", "credit", "balance"] and pd.notna(value):
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
    
    def _extract_transactions_auto(self, df):
        transactions = []
        try:
            work_df = df.copy()
            work_df = work_df.dropna(how='all')
            start_row = 0
            end_row = len(work_df)
            for i, row in work_df.head(10).iterrows():
                row_text = " ".join(map(str, row)).lower()
                if "date" in row_text and ("description" in row_text or "particulars" in row_text):
                    start_row = i + 1
                    work_df.columns = work_df.iloc[i]
                    work_df = work_df.iloc[i+1:].reset_index(drop=True)
                    break
            for i in range(len(work_df) - 1, max(len(work_df) - 10, 0), -1):
                row_text = " ".join(map(str, work_df.iloc[i])).lower()
                if "total" in row_text or "balance" in row_text or "closing" in row_text:
                    end_row = i
                    break
            transaction_df = work_df.iloc[:end_row].copy()
            date_col = next((col for col in transaction_df.columns if "date" in str(col).lower()), None)
            desc_col = next((col for col in transaction_df.columns if any(term in str(col).lower() for term in 
                                                                          ["description", "particulars", "details", "narration"])), None)
            debit_col = next((col for col in transaction_df.columns if any(term in str(col).lower() for term in 
                                                                           ["debit", "withdrawal", "dr", "withdrawals"])), None)
            credit_col = next((col for col in transaction_df.columns if any(term in str(col).lower() for term in 
                                                                            ["credit", "deposit", "cr", "deposits"])), None)
            amount_col = next((col for col in transaction_df.columns if "amount" in str(col).lower()), None)
            balance_col = next((col for col in transaction_df.columns if "balance" in str(col).lower()), None)
            if date_col and (amount_col or debit_col or credit_col):
                for _, row in transaction_df.iterrows():
                    transaction = {}
                    if date_col and pd.notna(row[date_col]):
                        try:
                            date_value = row[date_col]
                            if isinstance(date_value, (datetime.date, datetime.datetime)):
                                transaction["date"] = date_value.strftime("%d/%m/%Y")
                            else:
                                parsed_date = pd.to_datetime(date_value)
                                transaction["date"] = parsed_date.strftime("%d/%m/%Y")
                        except:
                            transaction["date"] = str(row[date_col])
                    if desc_col and pd.notna(row[desc_col]):
                        transaction["description"] = str(row[desc_col])
                    if debit_col and credit_col:
                        try:
                            if pd.notna(row[debit_col]) and str(row[debit_col]).strip():
                                debit_value = float(str(row[debit_col]).replace(',', ''))
                                if debit_value > 0:
                                    transaction["amount"] = debit_value
                                    transaction["transaction_type"] = "debit"
                            if pd.notna(row[credit_col]) and str(row[credit_col]).strip():
                                credit_value = float(str(row[credit_col]).replace(',', ''))
                                if credit_value > 0:
                                    transaction["amount"] = credit_value
                                    transaction["transaction_type"] = "credit"
                        except:
                            pass
                    elif amount_col:
                        try:
                            if pd.notna(row[amount_col]) and str(row[amount_col]).strip():
                                amount_value = float(str(row[amount_col]).replace(',', ''))
                                transaction["amount"] = abs(amount_value)
                                transaction["transaction_type"] = "debit" if amount_value < 0 else "credit"
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
            logger.error(f"Error extracting transactions automatically: {str(e)}")
        return transactions
