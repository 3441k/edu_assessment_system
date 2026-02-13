"""Safe code execution service for evaluating student code submissions."""

import subprocess
import sys
import os
import psutil
import json
import tempfile
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv

load_dotenv()

CODE_TIMEOUT = int(os.getenv("CODE_EXECUTION_TIMEOUT", 5))
CODE_MEMORY_LIMIT = int(os.getenv("CODE_EXECUTION_MEMORY_LIMIT", 128))  # MB


class CodeExecutionResult:
    """Result of code execution."""
    def __init__(self, success: bool, output: str = "", error: str = "", execution_time: float = 0.0):
        self.success = success
        self.output = output
        self.error = error
        self.execution_time = execution_time
    
    def to_dict(self) -> Dict:
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "execution_time": self.execution_time
        }


def execute_code(code: str, test_cases: Optional[List[Dict]] = None, timeout: int = CODE_TIMEOUT) -> Dict:
    """
    Execute Python code safely with test cases.
    
    Args:
        code: Python code to execute
        test_cases: List of test cases with 'input' and 'output' keys
        timeout: Execution timeout in seconds
    
    Returns:
        Dictionary with execution results
    """
    if not test_cases:
        # Just execute the code and return output
        return _execute_single(code, timeout)
    
    # Execute with test cases
    results = []
    all_passed = True
    
    for idx, test_case in enumerate(test_cases):
        test_input = test_case.get('input', '')
        expected_output = test_case.get('output', '')
        
        # Prepare code with test input
        test_code = _prepare_test_code(code, test_input)
        
        # Execute
        result = _execute_single(test_code, timeout)
        
        # Compare output
        actual_output = result['output'].strip() if result['success'] else ''
        expected_output_str = str(expected_output).strip()
        
        passed = actual_output == expected_output_str
        all_passed = all_passed and passed
        
        results.append({
            "test_case": idx + 1,
            "input": test_input,
            "expected_output": expected_output_str,
            "actual_output": actual_output,
            "passed": passed,
            "error": result.get('error', '')
        })
    
    return {
        "success": all_passed,
        "all_passed": all_passed,
        "passed_count": sum(1 for r in results if r['passed']),
        "total_count": len(results),
        "test_results": results
    }


def _prepare_test_code(code: str, test_input: str) -> str:
    """Prepare code with test input."""
    # If test_input is provided, try to inject it
    # This is a simple approach - for more complex cases, we might need to parse the code
    if test_input:
        # Try to handle input() calls
        # Replace input() with the test input
        lines = code.split('\n')
        prepared_lines = []
        input_used = False
        
        for line in lines:
            if 'input()' in line and not input_used:
                # Replace with test input
                line = line.replace('input()', repr(test_input))
                input_used = True
            prepared_lines.append(line)
        
        code = '\n'.join(prepared_lines)
    
    return code


def _execute_single(code: str, timeout: int) -> Dict:
    """Execute code once and return result."""
    try:
        # Create temporary file for code
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_file = f.name
        
        try:
            # Execute with timeout and resource limits
            process = subprocess.Popen(
                [sys.executable, temp_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=tempfile.gettempdir()
            )
            
            # Monitor memory usage
            try:
                p = psutil.Process(process.pid)
                memory_mb = p.memory_info().rss / 1024 / 1024
                
                if memory_mb > CODE_MEMORY_LIMIT:
                    process.terminate()
                    return {
                        "success": False,
                        "output": "",
                        "error": f"Memory limit exceeded ({memory_mb:.1f}MB > {CODE_MEMORY_LIMIT}MB)",
                        "execution_time": 0.0
                    }
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass  # Process might have finished already
            
            # Wait for completion with timeout
            try:
                stdout, stderr = process.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate()
                return {
                    "success": False,
                    "output": "",
                    "error": f"Execution timeout ({timeout}s)",
                    "execution_time": timeout
                }
            
            # Check return code
            if process.returncode != 0:
                return {
                    "success": False,
                    "output": stdout,
                    "error": stderr,
                    "execution_time": 0.0
                }
            
            return {
                "success": True,
                "output": stdout,
                "error": "",
                "execution_time": 0.0
            }
            
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_file)
            except:
                pass
                
    except Exception as e:
        return {
            "success": False,
            "output": "",
            "error": f"Execution error: {str(e)}",
            "execution_time": 0.0
        }


def validate_code_syntax(code: str) -> Tuple[bool, Optional[str]]:
    """
    Validate Python code syntax.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        compile(code, '<string>', 'exec')
        return True, None
    except SyntaxError as e:
        return False, f"Syntax error: {e.msg} at line {e.lineno}"


def grade_code_submission(code: str, test_cases: List[Dict], points: float) -> Dict:
    """
    Grade a code submission based on test cases.
    
    Args:
        code: Student's code
        test_cases: List of test cases
        points: Maximum points for this question
    
    Returns:
        Dictionary with grade information
    """
    # First check syntax
    is_valid, syntax_error = validate_code_syntax(code)
    if not is_valid:
        return {
            "score": 0.0,
            "max_score": points,
            "feedback": syntax_error,
            "test_results": []
        }
    
    # Execute with test cases
    result = execute_code(code, test_cases)
    
    if result.get('success', False) and result.get('all_passed', False):
        # All tests passed
        score = points
        feedback = f"All {result['passed_count']} test cases passed!"
    else:
        # Calculate partial credit
        passed = result.get('passed_count', 0)
        total = result.get('total_count', 1)
        score = (passed / total) * points if total > 0 else 0.0
        feedback = f"Passed {passed} out of {total} test cases."
        
        # Add details about failed tests
        failed_tests = [r for r in result.get('test_results', []) if not r.get('passed', False)]
        if failed_tests:
            feedback += "\n\nFailed test cases:"
            for test in failed_tests[:3]:  # Show first 3 failures
                feedback += f"\n- Test {test['test_case']}: Expected '{test['expected_output']}', got '{test['actual_output']}'"
    
    return {
        "score": round(score, 2),
        "max_score": points,
        "feedback": feedback,
        "test_results": result.get('test_results', [])
    }

