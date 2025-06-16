import re
import html
from typing import Tuple
import streamlit as st

class InputValidator:
    def __init__(self):
        # Dangerous patterns to detect
        self.sql_injection_patterns = [
            r"(\bUNION\b.*\bSELECT\b)",
            r"(\bDROP\b.*\bTABLE\b)",
            r"(\bINSERT\b.*\bINTO\b)",
            r"(\bUPDATE\b.*\bSET\b)",
            r"(\bDELETE\b.*\bFROM\b)",
            r"(;\s*--)",
            r"(\bEXEC\b)",
            r"(\bXP_\w+)",
        ]
        
        self.xss_patterns = [
            r"<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>",
            r"javascript:",
            r"vbscript:",
            r"onload\s*=",
            r"onerror\s*=",
            r"onclick\s*=",
        ]
        
        self.max_lengths = {
            "question": 2000,
            "code": 10000,
            "query": 1000
        }
    
    def validate_question(self, question: str) -> Tuple[bool, str, str]:
        """Validate user question input"""
        if not question or not question.strip():
            return False, "Question cannot be empty", question
        
        # Length check
        if len(question) > self.max_lengths["question"]:
            return False, f"Question too long (max {self.max_lengths['question']} characters)", question
        
        # Basic sanitization
        cleaned_question = html.escape(question.strip())
        
        # Security checks
        security_result = self._check_security_patterns(cleaned_question)
        if not security_result[0]:
            return security_result[0], security_result[1], cleaned_question
        
        # Content validation
        if self._is_inappropriate_content(cleaned_question):
            return False, "Question contains inappropriate content", cleaned_question
        
        # Check if question is Salesforce-related
        if not self._is_salesforce_related(cleaned_question):
            # Don't block, just warn
            pass
        
        return True, "Valid", cleaned_question
    
    def validate_code_input(self, code: str) -> Tuple[bool, str, str]:
        """Validate Apex code input"""
        if not code or not code.strip():
            return False, "Code cannot be empty", code
        
        if len(code) > self.max_lengths["code"]:
            return False, f"Code too long (max {self.max_lengths['code']} characters)", code
        
        cleaned_code = code.strip()
        
        # Check for obvious non-Apex code
        if self._contains_malicious_code(cleaned_code):
            return False, "Code contains potentially malicious patterns", cleaned_code
        
        return True, "Valid", cleaned_code
    
    def validate_soql_query(self, query: str) -> Tuple[bool, str, str]:
        """Validate SOQL query input"""
        if not query or not query.strip():
            return False, "Query cannot be empty", query
        
        if len(query) > self.max_lengths["query"]:
            return False, f"Query too long (max {self.max_lengths['query']} characters)", query
        
        cleaned_query = query.strip()
        
        # Check for basic SOQL structure
        if not self._is_valid_soql_structure(cleaned_query):
            return False, "Does not appear to be a valid SOQL query", cleaned_query
        
        # Security check
        security_result = self._check_security_patterns(cleaned_query)
        if not security_result[0]:
            return security_result[0], security_result[1], cleaned_query
        
        return True, "Valid", cleaned_query
    
    def _check_security_patterns(self, text: str) -> Tuple[bool, str]:
        """Check for SQL injection and XSS patterns"""
        text_lower = text.lower()
        
        # Check SQL injection patterns
        for pattern in self.sql_injection_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return False, "Potentially malicious SQL pattern detected"
        
        # Check XSS patterns
        for pattern in self.xss_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return False, "Potentially malicious script pattern detected"
        
        return True, "Secure"
    
    def _is_inappropriate_content(self, text: str) -> bool:
        """Check for inappropriate content"""
        inappropriate_keywords = [
            "hack", "exploit", "bypass", "unauthorized", "steal", "crack"
        ]
        
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in inappropriate_keywords)
    
    def _is_salesforce_related(self, text: str) -> bool:
        """Check if question is Salesforce-related"""
        salesforce_keywords = [
            "salesforce", "apex", "soql", "sosl", "trigger", "workflow", 
            "lightning", "visualforce", "governor", "limit", "crm",
            "account", "contact", "opportunity", "lead", "case",
            "platform", "force.com", "trailhead", "metadata"
        ]
        
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in salesforce_keywords)
    
    def _contains_malicious_code(self, code: str) -> bool:
        """Check for potentially malicious code patterns"""
        malicious_patterns = [
            r"System\.exit\(",
            r"Runtime\.getRuntime\(",
            r"ProcessBuilder\(",
            r"exec\(",
            r"eval\(",
            r"import\s+os",
            r"__import__",
        ]
        
        for pattern in malicious_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                return True
        
        return False
    
    def _is_valid_soql_structure(self, query: str) -> bool:
        """Basic SOQL structure validation"""
        query_lower = query.lower().strip()
        
        # Must start with SELECT
        if not query_lower.startswith("select"):
            return False
        
        # Must contain FROM
        if " from " not in query_lower:
            return False
        
        # Basic structure check
        try:
            # Very basic parsing
            select_part = query_lower.split(" from ")[0]
            if "select" not in select_part:
                return False
            return True
        except:
            return False

# Global validator
validator = InputValidator()