from langchain.tools import tool
import re
import json
import html

def clean_input(code: str) -> str:
    """Clean and decode HTML entities from Streamlit input"""
    if not code:
        return code
    
    # More aggressive HTML entity cleaning
    cleaned = code
    
    # Multiple passes to handle double-encoding
    for _ in range(3):  # Up to 3 passes for nested encoding
        cleaned = html.unescape(cleaned)
    
    # Manual replacement of common HTML entities (case-insensitive)
    html_entities = {
        '&lt;': '<',
        '&LT;': '<',
        '&gt;': '>',
        '&GT;': '>',
        '&amp;': '&',
        '&AMP;': '&',
        '&#x27;': "'",
        '&#X27;': "'",
        '&#39;': "'",
        '&quot;': '"',
        '&QUOT;': '"',
        '&apos;': "'",
        '&APOS;': "'",
        '&nbsp;': ' ',
        '&NBSP;': ' ',
        '&#60;': '<',
        '&#62;': '>',
        '&#38;': '&',
        '&#34;': '"'
    }
    
    # Apply replacements multiple times in case of nested encoding
    for _ in range(2):
        for entity, replacement in html_entities.items():
            cleaned = cleaned.replace(entity, replacement)
    
    # Remove any remaining HTML tags
    cleaned = re.sub(r'<[^>]+>', '', cleaned)
    
    # Fix whitespace issues that might come from HTML formatting
    # Replace multiple spaces with single spaces but preserve indentation
    lines = cleaned.split('\n')
    fixed_lines = []
    for line in lines:
        # Only fix excessive spaces within the line content, preserve leading spaces
        if line.strip():  # Only process non-empty lines
            leading_spaces = len(line) - len(line.lstrip())
            content = line.strip()
            # Fix multiple spaces within content
            content = re.sub(r'  +', ' ', content)
            fixed_lines.append(' ' * leading_spaces + content)
        else:
            fixed_lines.append(line)
    
    return '\n'.join(fixed_lines)

def format_apex_code(code: str) -> str:
    """Format single-line Apex code into properly structured multi-line code"""
    if not code or not code.strip():
        return code
    
    # Code should already be cleaned, don't double-clean
    cleaned = code
    
    if '\n' in cleaned and len(cleaned.split('\n')) > 3:
        return cleaned
    
    formatted = cleaned.strip()
    
    formatted = re.sub(r'\{\s*', '{\n', formatted)
    
    formatted = re.sub(r'\s*\}', '\n}', formatted)
    
    formatted = re.sub(r';\s*(?![^(]*\))', ';\n', formatted)
    
    formatted = re.sub(r'\n+', '\n', formatted)
    
    lines = []
    for line in formatted.split('\n'):
        cleaned = line.strip()
        if cleaned:
            lines.append(cleaned)
    
    return '\n'.join(lines)


@tool
def apex_code_reviewer(code: str) -> str:
    """
    Review Apex code for best practices, governor limits compliance, and potential issues.
    
    Args:
        code: The Apex code to review
        
    Returns:
        A detailed review with recommendations and best practices
    """
    
    if not code or not code.strip():
        return "Please provide Apex code to review."
    
    # FIRST: Clean HTML entities immediately
    cleaned_code = clean_input(code)
    
    # Enhanced debug logging with LangSmith tracing
    debug_info = {
        "original_code": repr(code),
        "cleaned_code": repr(cleaned_code),
        "code_length": len(code),
        "cleaned_length": len(cleaned_code),
        "code_type": str(type(code)),
        "execution_context": "streamlit" if hasattr(__builtins__, '__IPYTHON__') or 'streamlit' in str(globals()) else "local",
        "has_html_entities": "&lt;" in code or "&#x27;" in code or "&gt;" in code
    }

    # Use cleaned code for formatting instead of original
    formatted_code = format_apex_code(cleaned_code)
    
    formatting_debug = {
        "formatted_code": repr(formatted_code),
        "formatted_length": len(formatted_code),
        "lines_count": len(formatted_code.split('\n')),
        "formatting_changed": code != formatted_code
    }
    
    issues = []
    recommendations = []
    lines = formatted_code.split('\n')
    
    soql_patterns = [
        r'\[[\s\S]*?SELECT[\s\S]*?\]',
        r'Database\.query\s*\(',
        r'Database\.queryWithBinds\s*\(',
        r'Database\.getQueryLocator\s*\(',
        r'\.query\s*\('
    ]
    
    dml_patterns = [
        r'\binsert\s+',
        r'\bupdate\s+', 
        r'\bdelete\s+',
        r'\bupsert\s+',
        r'Database\.insert\s*\(',
        r'Database\.update\s*\(',
        r'Database\.delete\s*\(',
        r'Database\.upsert\s*\('
    ]
    
    loop_patterns = [
        (r'\bfor\s*\([^:)]*;[^;)]*;[^)]*\)', 'for'), 
        (r'\bfor\s*\([^)]*:\s*[^)]*\)', 'for'),
        (r'\bwhile\s*\([^)]*\)', 'while'),
        (r'\bdo\s*\{', 'do-while')
    ]
    
    loop_stack = []
    current_brace_level = 0
    
    for i, line in enumerate(lines, 1):
        line_clean = line.strip()
        line_lower = line_clean.lower()
        
        open_braces = line_clean.count('{')
        braces_closed = line_clean.count('}')
                
        for loop_pattern, loop_type in loop_patterns:
            if re.search(loop_pattern, line_lower):
                print(f"DEBUG - Found {loop_type} loop at line {i}: {line_clean}")
                if '{' in line_clean:
                    loop_stack.append((i, loop_type, current_brace_level + open_braces))
                elif ';' in line_clean:
                    print(f"DEBUG - Single-line {loop_type} loop detected at line {i}")
                    for soql_pattern in soql_patterns:
                        if re.search(soql_pattern, line, re.IGNORECASE):
                            print(f"DEBUG - SOQL pattern matched in single-line loop: {soql_pattern}")
                            issues.append(f"Line {i}: SOQL in single-line {loop_type} loop - Governor limit violation!")
                            recommendations.append("Move SOQL queries outside loops and use bulk operations with collections")
                    for dml_pattern in dml_patterns:
                        if re.search(dml_pattern, line_lower):
                            print(f"DEBUG - DML pattern matched in single-line loop: {dml_pattern}")
                            issues.append(f"Line {i}: DML in single-line {loop_type} loop - Governor limit violation!")
                            recommendations.append("Collect records in collections and perform bulk DML operations outside loops")
                else:
                    loop_stack.append((i, loop_type, current_brace_level + 1))
                break
            
        current_brace_level += open_braces
        
        # Only check for SOQL/DML inside loops if we're actually inside a loop AND not on a closing brace line
        if loop_stack and braces_closed == 0:
            # Check SOQL in loop
            for soql_pattern in soql_patterns:
                if re.search(soql_pattern, line, re.IGNORECASE):
                    loop_line, loop_type, _ = loop_stack[-1]
                    issues.append(f"Line {i}: SOQL query in {loop_type} loop (started at line {loop_line}) - Governor limit violation!")
                    recommendations.append("Move SOQL queries outside loops and use bulk operations with collections")
                    break
            
            # Check DML in loop
            for dml_pattern in dml_patterns:
                if re.search(dml_pattern, line_lower):
                    loop_line, loop_type, _ = loop_stack[-1]
                    issues.append(f"Line {i}: DML operation in {loop_type} loop (started at line {loop_line}) - Governor limit violation!")
                    recommendations.append("Collect records in collections and perform bulk DML operations outside loops")
                    break
        
        # Update brace level first
        current_brace_level -= braces_closed
        
        # Then check if we've closed any loops
        if braces_closed > 0 and loop_stack:
            loop_stack = [(line_num, loop_type, brace_level) 
                        for line_num, loop_type, brace_level in loop_stack 
                        if brace_level > current_brace_level]
            
    code_lower = cleaned_code.lower()
    
    hardcoded_id_patterns = [
        r"Id\s*=\s*['\"][0-9a-zA-Z]{15,18}['\"]",
        r"WHERE\s+Id\s*=\s*['\"][0-9a-zA-Z]{15,18}['\"]",
        r"['\"][0-9a-zA-Z]{15}[A-Z0-9]{3}['\"]",
        r"['\"][0-9a-zA-Z]{15}['\"]"
    ]

    for pattern in hardcoded_id_patterns:
        if re.search(pattern, cleaned_code, re.IGNORECASE):
            issues.append("Hardcoded Salesforce IDs detected")
            recommendations.append("Replace hardcoded IDs with Custom Settings, Custom Metadata, or SOQL queries")
            break
    
    # Check for System.debug statements
    if 'system.debug' in code_lower:
        recommendations.append("Remove System.debug statements before deploying to production")
    
    # Check for try without catch
    if 'try' in code_lower and 'catch' not in code_lower:
        issues.append("Try block without catch - Add proper exception handling")
        recommendations.append("Always include catch blocks with specific exception types (e.g., DmlException, QueryException)")
    
    # Check for trigger best practices
    if 'trigger' in code_lower and 'trigger.new' in code_lower:
        if not any(bulk_keyword in code_lower for bulk_keyword in ['list<', 'set<', 'map<']):
            recommendations.append("Use collections (List, Set, Map) for bulk processing in triggers")
        
        # Check for trigger context usage
        if 'trigger.new' in code_lower and 'trigger.isinsert' not in code_lower and 'trigger.isupdate' not in code_lower:
            recommendations.append("Use Trigger context variables (isInsert, isUpdate, isBefore, isAfter) for conditional logic")
    
    # Check for test class best practices
    if '@istest' in code_lower or 'testmethod' in code_lower:
        if 'test.starttest()' not in code_lower:
            recommendations.append("Use Test.startTest() and Test.stopTest() in test methods to reset governor limits")
        if 'system.assert' not in code_lower:
            recommendations.append("Include assertions in test methods to validate expected behavior")
    
    # Check for sharing and security
    if 'without sharing' in code_lower:
        recommendations.append("Consider security implications of 'without sharing' - use 'with sharing' when possible")
    
    # Generate review report
    review_report = "🔍 **APEX CODE REVIEW REPORT**\n\n"
    
    if issues:
        review_report += "❌ **CRITICAL ISSUES FOUND:**\n"
        for issue in issues:
            review_report += f"• {issue}\n"
        review_report += "\n"
    else:
        review_report += "✅ **NO CRITICAL ISSUES FOUND**\n\n"
    
    if recommendations:
        review_report += "💡 **RECOMMENDATIONS:**\n"
        for rec in recommendations:
            review_report += f"• {rec}\n"
        review_report += "\n"
    
    review_report += "📚 **APEX BEST PRACTICES CHECKLIST:**\n"
    review_report += "• Always bulkify your code for large data volumes\n"
    review_report += "• Avoid SOQL/DML operations inside loops\n"
    review_report += "• Use proper exception handling with specific exception types\n"
    review_report += "• Implement trigger patterns (One Trigger Per Object)\n"
    review_report += "• Use Test.startTest()/stopTest() in unit tests\n"
    review_report += "• Follow naming conventions (CamelCase for classes, camelCase for variables)\n"
    review_report += "• Use 'with sharing' for security enforcement\n"
    review_report += "• Avoid hardcoded IDs and values\n"
    
    # Log final results for comparison
    results_debug = {
        "issues_found": len(issues),
        "recommendations_count": len(recommendations),
        "issues_list": issues,
        "recommendations_list": recommendations,
        "report_length": len(review_report),
        "execution_context": debug_info['execution_context']
    }

    return review_report

@tool
def soql_query_optimizer(query: str) -> str:
    """
    Analyze and optimize SOQL queries for performance and best practices.
    
    Args:
        query: The SOQL query to analyze and optimize
        
    Returns:
        Analysis and optimization recommendations for the SOQL query
    """
    if not query or not query.strip():
        return "Please provide a SOQL query to analyze."
    
    query = query.strip()
    query_lower = query.lower()
    
    issues = []
    optimizations = []
    
    # Check for SELECT *
    if 'select *' in query_lower:
        issues.append("Using SELECT * - This is not supported in SOQL")
        optimizations.append("Specify exact fields needed: SELECT Id, Name, Email FROM Account")
    
    # Check for missing WHERE clause on large objects
    large_objects = ['account', 'contact', 'opportunity', 'lead', 'case']
    for obj in large_objects:
        if f'from {obj}' in query_lower and 'where' not in query_lower and 'limit' not in query_lower:
            issues.append(f"Query on {obj.title()} without WHERE clause or LIMIT - May hit governor limits")
            optimizations.append(f"Add WHERE clause or LIMIT to queries on {obj.title()}")
    
    # Check for inefficient WHERE clauses
    if 'where' in query_lower:
        where_clause = query_lower.split('where')[1].split('order by')[0] if 'order by' in query_lower else query_lower.split('where')[1]
        
        # Check for functions in WHERE clause
        if any(func in where_clause for func in ['day(', 'month(', 'year(', 'hour(']):
            issues.append("Date functions in WHERE clause can prevent index usage")
            optimizations.append("Use date literals instead of date functions when possible")
        
        # Check for LIKE with leading wildcards - FIXED RECOMMENDATION
        if re.search(r"like\s+['\"]%", where_clause):
            issues.append("LIKE with leading wildcard (%) prevents index usage")
            optimizations.append("Avoid leading wildcards in LIKE clauses. Consider:")
            optimizations.append("  • Use SOSL with FIND for full-text search across multiple fields")
            optimizations.append("  • Use exact match or trailing wildcards: Name LIKE 'test%'")
            optimizations.append("  • Create custom indexed fields for common search patterns")
    
    # Check for missing LIMIT on queries that should have it
    if 'limit' not in query_lower and 'count()' not in query_lower:
        optimizations.append("Consider adding LIMIT clause to prevent large result sets")
    
    # Check for unnecessary fields
    if 'select' in query_lower:
        select_clause = query_lower.split('from')[0].replace('select', '').strip()
        if 'id,' in select_clause and select_clause.count(',') > 10:
            optimizations.append("Consider if all selected fields are necessary - fewer fields = better performance")
    
    # Check for relationship queries depth
    dot_count = query.count('.')
    if dot_count > 5:
        issues.append("Deep relationship queries detected - May impact performance")
        optimizations.append("Consider separate queries or reducing relationship depth")
    
    # Check for subqueries
    if 'select' in query_lower and query_lower.count('select') > 1:
        optimizations.append("Subqueries detected - Ensure they're necessary and optimized")
    
    # Check for proper filtering on large objects
    if any(obj in query_lower for obj in large_objects):
        if 'where' in query_lower and not any(indexed_field in where_clause for indexed_field in ['id', 'name', 'email', 'createddate', 'lastmodifieddate']):
            optimizations.append("Consider using indexed fields in WHERE clause (Id, Name, Email, CreatedDate, LastModifiedDate)")
    
    # Generate optimization report
    report = "🔍 **SOQL QUERY ANALYSIS REPORT**\n\n"
    report += f"**Query:** `{query}`\n\n"
    
    if issues:
        report += "❌ **PERFORMANCE ISSUES:**\n"
        for issue in issues:
            report += f"• {issue}\n"
        report += "\n"
    else:
        report += "✅ **NO MAJOR ISSUES DETECTED**\n\n"
    
    if optimizations:
        report += "⚡ **OPTIMIZATION SUGGESTIONS:**\n"
        for opt in optimizations:
            report += f"• {opt}\n"
        report += "\n"
    
    # FIXED: Accurate SOQL best practices
    report += "📈 **SOQL BEST PRACTICES:**\n"
    report += "• Use selective WHERE clauses with indexed fields\n"
    report += "• Avoid leading wildcards in LIKE (use trailing: 'test%')\n"
    report += "• For full-text search, use SOSL instead of SOQL\n"
    report += "• Use LIMIT to control result set size\n"
    report += "• Avoid functions in WHERE clauses when possible\n"
    report += "• Query only the fields you need\n"
    report += "• Use relationship queries efficiently (limit depth)\n"
    report += "• Consider using WITH SECURITY_ENFORCED for user context\n"
    
    # Add SOSL recommendation for text search
    if 'like' in query_lower and '%' in query_lower:
        report += "\n💡 **ALTERNATIVE APPROACH:**\n"
        report += "For text searching, consider using SOSL instead:\n"
        report += "```\n"
        report += "FIND {search term} IN ALL FIELDS\n"
        report += "RETURNING Account(Id, Name), Contact(Id, Name)\n"
        report += "```\n"
    
    return report

@tool
def governor_limits_calculator(operations: str) -> str:
    """
    Calculate governor limits usage for given operations and provide guidance.
    
    Args:
        operations: JSON string or description of operations (e.g., '{"soql_queries": 50, "dml_statements": 150, "heap_size_mb": 5}')
        
    Returns:
        Governor limits analysis and recommendations
    """
    
    if not operations or not operations.strip():
        return "Please provide operations data to analyze governor limits."
    
    sync_limits = {
        'soql_queries': 100,
        'dml_statements': 150,
        'dml_records': 10000,
        'heap_size_mb': 6,
        'cpu_time_ms': 10000,
        'callouts': 100,
        'email_invocations': 10,
        'future_calls': 50,
        'queueable_jobs': 50
    }
    
    try:
        if operations.startswith('{'):
            ops_data = json.loads(operations)
        else:
            # Try to extract numbers from description
            ops_data = {}
            if 'soql' in operations.lower():
                soql_match = re.search(r'(\d+)\s*soql', operations.lower())
                if soql_match:
                    ops_data['soql_queries'] = int(soql_match.group(1))
            
            if 'dml' in operations.lower():
                dml_match = re.search(r'(\d+)\s*dml', operations.lower())
                if dml_match:
                    ops_data['dml_statements'] = int(dml_match.group(1))
            
            if not ops_data:
                return """
                        Please provide operations in JSON format or clear description. 
                        Example: {"soql_queries": 50, "dml_statements": 75, "heap_size_mb": 3}
                        Or describe like: "50 SOQL queries and 75 DML statements"
                        """
    except json.JSONDecodeError:
        return "Invalid JSON format. Please provide valid JSON or description of operations."
    
    # Calculate usage percentages and warnings
    report = "📊 **GOVERNOR LIMITS ANALYSIS**\n\n"
    
    warnings = []
    critical_issues = []
    
    for operation, used in ops_data.items():
        if operation in sync_limits:
            limit = sync_limits[operation]
            percentage = (used / limit) * 100
            
            status = "🟢"
            if percentage > 80:
                status = "🔴"
                critical_issues.append(f"{operation}: {used}/{limit} ({percentage:.1f}%)")
            elif percentage > 60:
                status = "🟡"
                warnings.append(f"{operation}: {used}/{limit} ({percentage:.1f}%)")
            
            report += f"{status} **{operation.replace('_', ' ').title()}:** {used}/{limit} ({percentage:.1f}%)\n"
    
    report += "\n"
    
    if critical_issues:
        report += "🚨 **CRITICAL - NEAR LIMITS:**\n"
        for issue in critical_issues:
            report += f"• {issue}\n"
        report += "\n"
    
    if warnings:
        report += "⚠️ **WARNINGS:**\n"
        for warning in warnings:
            report += f"• {warning}\n"
        report += "\n"
    
    # Provide specific recommendations
    report += "💡 **RECOMMENDATIONS:**\n"
    
    if 'soql_queries' in ops_data and ops_data['soql_queries'] > 50:
        report += "• High SOQL usage - Consider query optimization and caching\n"
    
    if 'dml_statements' in ops_data and ops_data['dml_statements'] > 100:
        report += "• High DML usage - Implement bulk operations and reduce individual DML calls\n"
    
    if 'heap_size_mb' in ops_data and ops_data['heap_size_mb'] > 4:
        report += "• High heap usage - Optimize data structures and consider processing in batches\n"
    
    report += "• Always test with large data volumes\n"
    report += "• Implement proper error handling for limit exceptions\n"
    report += "• Consider asynchronous processing for large operations\n"
    
    report += "\n📚 **GOVERNOR LIMITS REFERENCE:**\n"
    report += "• SOQL Queries: 100 (sync) / 200 (async)\n"
    report += "• DML Statements: 150 (sync) / 150 (async)\n"
    report += "• DML Records: 10,000 per transaction\n"
    report += "• Heap Size: 6 MB (sync) / 12 MB (async)\n"
    report += "• CPU Time: 10s (sync) / 60s (async)\n"
    
    return report

# List of all tools for easy import
salesforce_tools = [apex_code_reviewer, soql_query_optimizer, governor_limits_calculator]