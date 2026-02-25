"""
IFCore Orchestrator

Discovers and executes all compliance checker functions (check_*) from checker_*.py files.
Returns aggregated results with metadata about which checkers were run.
"""

import importlib.util
import inspect
import sys
from pathlib import Path
from typing import List, Dict, Any, Callable
import ifcopenshell


class OrchestratorError(Exception):
    """Error in orchestrator discovery or execution."""
    pass


class CheckerOrchestrator:
    """
    Discovers and runs all compliance checker functions.
    
    Process:
    1. Scan tools/ directory for checker_*.py files
    2. Load each module dynamically
    3. Find all check_*() functions (must start with "check_")
    4. Execute each function with the IFC model
    5. Aggregate and return results with metadata
    """
    
    def __init__(self, tools_dir: Path = None):
        """
        Initialize the orchestrator.
        
        Args:
            tools_dir: Path to tools directory (default: ./tools)
        """
        self.tools_dir = tools_dir or Path(__file__).parent / "tools"
        self.checkers: Dict[str, Dict[str, Any]] = {}  # {filename: {function_name: function_obj}}
        self.loaded_modules: Dict[str, Any] = {}  # {filename: module_obj}
        self.execution_log: List[str] = []
    
    def discover(self) -> Dict[str, List[str]]:
        """
        Discover all checker_*.py files and their check_* functions.
        
        Returns:
            Dict mapping filename to list of function names found
            
        Raises:
            OrchestratorError: If discovery fails
        """
        if not self.tools_dir.exists():
            raise OrchestratorError(f"Tools directory not found: {self.tools_dir}")
        
        self.execution_log.append(f"Scanning tools directory: {self.tools_dir}")
        
        # Find all checker_*.py files (exclude checker_template.py)
        checker_files = sorted([
            f for f in self.tools_dir.glob("checker_*.py")
            if f.name != "checker_template.py"
        ])
        
        self.execution_log.append(f"Found {len(checker_files)} checker file(s)")
        
        for checker_file in checker_files:
            try:
                # Load the module
                module = self._load_module(checker_file)
                self.loaded_modules[checker_file.name] = module
                
                # Find all check_* functions
                check_functions = [
                    (name, obj) for name, obj in inspect.getmembers(module)
                    if name.startswith("check_") and callable(obj)
                ]
                
                if not check_functions:
                    self.execution_log.append(f"  ⚠️  {checker_file.name}: No check_* functions found")
                    continue
                
                self.checkers[checker_file.name] = {
                    name: func for name, func in check_functions
                }
                
                self.execution_log.append(
                    f"  ✓ {checker_file.name}: Found {len(check_functions)} function(s) - "
                    f"{', '.join([name for name, _ in check_functions])}"
                )
                
            except Exception as e:
                self.execution_log.append(f"  ✗ {checker_file.name}: {str(e)}")
                raise OrchestratorError(f"Failed to load {checker_file.name}: {str(e)}")
        
        return {name: list(funcs.keys()) for name, funcs in self.checkers.items()}
    
    def _load_module(self, module_path: Path) -> Any:
        """
        Dynamically load a Python module from a file path.
        
        Args:
            module_path: Path to the .py file
            
        Returns:
            Loaded module object
            
        Raises:
            ImportError: If module cannot be loaded
        """
        module_name = module_path.stem
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load module from {module_path}")
        
        # Create unique module name to avoid conflicts
        unique_name = f"_ifcore_checker_{module_name}_{id(module_path)}"
        module = importlib.util.module_from_spec(spec)
        sys.modules[unique_name] = module
        spec.loader.exec_module(module)
        
        return module
    
    def run(self, model: ifcopenshell.file, checker_filter: str = None, **kwargs) -> Dict[str, Any]:
        """
        Execute all discovered checkers on the IFC model.
        
        Args:
            model: ifcopenshell.file object to check
            checker_filter: Only run checkers matching this name (e.g., "doors", "walls")
            **kwargs: Additional arguments passed to all check functions
            
        Returns:
            Dictionary with:
            - "results": List of all result dicts from all checkers
            - "summary": Execution summary and metadata
            - "log": Execution log messages
            
        Raises:
            OrchestratorError: If execution fails
        """
        
        if not self.checkers:
            raise OrchestratorError("No checkers discovered. Call discover() first.")
        
        if not isinstance(model, ifcopenshell.file):
            raise OrchestratorError("model must be an ifcopenshell.file object")
        
        self.execution_log.append("\n" + "="*70)
        self.execution_log.append("ORCHESTRATOR EXECUTION START")
        self.execution_log.append("="*70)
        
        all_results = []
        execution_stats = {
            "total_checkers": 0,
            "successful": 0,
            "failed": 0,
            "checker_details": []
        }
        
        # Execute each checker
        for filename, functions_dict in self.checkers.items():
            for func_name, func_obj in functions_dict.items():
                
                # Apply filter if specified
                if checker_filter and checker_filter.lower() not in filename.lower():
                    continue
                
                execution_stats["total_checkers"] += 1
                full_name = f"{filename}::{func_name}"
                
                try:
                    self.execution_log.append(f"\n📋 Running: {full_name}")
                    
                    # Call the checker function with the model and kwargs
                    results = func_obj(model, **kwargs)
                    
                    # Validate results structure
                    if not isinstance(results, list):
                        raise ValueError(f"check_* function must return a list, got {type(results)}")
                    
                    if not results:
                        self.execution_log.append(f"  ⚠️  No results returned")
                    else:
                        # Validate each result dict
                        for i, result in enumerate(results):
                            if not isinstance(result, dict):
                                raise ValueError(f"Result {i} is not a dict: {type(result)}")
                            
                            # Validate required keys
                            required_keys = {
                                "element_id", "element_type", "element_name",
                                "element_name_long", "check_status", "actual_value",
                                "required_value", "comment", "log"
                            }
                            missing_keys = required_keys - set(result.keys())
                            if missing_keys:
                                raise ValueError(f"Result {i} missing keys: {missing_keys}")
                            
                            # Add metadata
                            result["_checker_file"] = filename
                            result["_checker_function"] = func_name
                            all_results.append(result)
                        
                        self.execution_log.append(f"  ✓ {len(results)} result(s)")
                    
                    execution_stats["successful"] += 1
                    execution_stats["checker_details"].append({
                        "checker": full_name,
                        "status": "success",
                        "result_count": len(results)
                    })
                    
                except Exception as e:
                    execution_stats["failed"] += 1
                    self.execution_log.append(f"  ✗ ERROR: {str(e)}")
                    execution_stats["checker_details"].append({
                        "checker": full_name,
                        "status": "failed",
                        "error": str(e)
                    })
        
        self.execution_log.append("\n" + "="*70)
        self.execution_log.append(f"ORCHESTRATOR EXECUTION COMPLETE")
        self.execution_log.append(f"  Checkers run: {execution_stats['successful']}/{execution_stats['total_checkers']}")
        self.execution_log.append(f"  Results collected: {len(all_results)}")
        self.execution_log.append("="*70)
        
        return {
            "results": all_results,
            "summary": {
                "total_checkers": execution_stats["total_checkers"],
                "successful_checkers": execution_stats["successful"],
                "failed_checkers": execution_stats["failed"],
                "total_results": len(all_results),
                "checker_details": execution_stats["checker_details"]
            },
            "log": "\n".join(self.execution_log)
        }
    
    def get_summary_by_status(self, results: List[Dict]) -> Dict[str, int]:
        """
        Count results by check_status.
        
        Args:
            results: List of result dicts
            
        Returns:
            Dict with count per status: {"pass": N, "fail": N, ...}
        """
        summary = {}
        for result in results:
            status = result.get("check_status", "unknown")
            summary[status] = summary.get(status, 0) + 1
        return summary
    
    def filter_results(self, results: List[Dict], status: str = None, element_type: str = None) -> List[Dict]:
        """
        Filter results by status or element type.
        
        Args:
            results: List of result dicts
            status: Filter by check_status (e.g., "fail", "warning")
            element_type: Filter by element_type (e.g., "IfcDoor", "Summary")
            
        Returns:
            Filtered list of results
        """
        filtered = results
        
        if status:
            filtered = [r for r in filtered if r.get("check_status") == status]
        
        if element_type:
            filtered = [r for r in filtered if r.get("element_type") == element_type]
        
        return filtered
    
    def print_summary(self, execution_result: Dict[str, Any]):
        """
        Print a human-readable summary of execution.
        
        Args:
            execution_result: Result dict from run()
        """
        summary = execution_result["summary"]
        results = execution_result["results"]
        
        print("\n" + "="*70)
        print("IFCORE ORCHESTRATOR - EXECUTION SUMMARY")
        print("="*70)
        print(f"Checkers discovered: {summary['total_checkers']}")
        print(f"Checkers successful: {summary['successful_checkers']}")
        print(f"Checkers failed: {summary['failed_checkers']}")
        print(f"Total results: {summary['total_results']}")
        print()
        
        # Status breakdown
        status_summary = self.get_summary_by_status(results)
        print("Results by status:")
        for status, count in sorted(status_summary.items()):
            print(f"  {status}: {count}")
        print()
        
        # Checker details
        print("Checker execution details:")
        for detail in summary["checker_details"]:
            if detail["status"] == "success":
                print(f"  ✓ {detail['checker']}: {detail['result_count']} result(s)")
            else:
                print(f"  ✗ {detail['checker']}: {detail['error']}")
        
        print("="*70 + "\n")


# Convenience functions
def get_orchestrator(tools_dir: Path = None) -> CheckerOrchestrator:
    """
    Create and initialize an orchestrator.
    
    Args:
        tools_dir: Path to tools directory
        
    Returns:
        Initialized CheckerOrchestrator instance
    """
    orchestrator = CheckerOrchestrator(tools_dir)
    orchestrator.discover()
    return orchestrator


def run_all_checks(model: ifcopenshell.file, tools_dir: Path = None, **kwargs) -> Dict[str, Any]:
    """
    One-shot function to discover and run all checkers.
    
    Args:
        model: ifcopenshell.file object
        tools_dir: Path to tools directory
        **kwargs: Additional arguments for check functions
        
    Returns:
        Execution result dict
    """
    orchestrator = get_orchestrator(tools_dir)
    return orchestrator.run(model, **kwargs)
