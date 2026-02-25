#!/usr/bin/env python3
"""
IFCore Orchestrator Demo

Demonstrates how to use the orchestrator to run all compliance checkers on an IFC model.
"""

import argparse
import sys
from pathlib import Path
import ifcopenshell
from orchestrator import get_orchestrator, CheckerOrchestrator


def load_ifc_model(ifc_path: str) -> ifcopenshell.file:
    """
    Load an IFC file.
    
    Args:
        ifc_path: Path to the IFC file
        
    Returns:
        ifcopenshell.file object
        
    Raises:
        FileNotFoundError: If IFC file not found
        Exception: If IFC loading fails
    """
    model_path = Path(ifc_path)
    
    if not model_path.exists():
        raise FileNotFoundError(f"IFC file not found: {ifc_path}")
    
    print(f"Loading IFC model: {ifc_path}")
    model = ifcopenshell.open(ifc_path)
    
    # Print basic model info
    project = model.by_type("IfcProject")
    if project:
        print(f"  Project: {project[0].Name}")
    
    print(f"  Schema: {model.schema}")
    print(f"  Total entities: {len(model.entity_by_id)}\n")
    
    return model


def run_checks_on_model(ifc_path: str, tools_dir: str = None, verbose: bool = False, 
                       filter_checker: str = None, output_format: str = "summary"):
    """
    Run all checks on an IFC model and display results.
    
    Args:
        ifc_path: Path to IFC file
        tools_dir: Path to tools directory (default: ./tools)
        verbose: Print detailed execution log
        filter_checker: Only run checkers matching this name
        output_format: Output format - "summary", "detailed", or "json"
    """
    
    try:
        # Load the model
        model = load_ifc_model(ifc_path)
        
        # Get orchestrator and run all checks
        tools_path = Path(tools_dir) if tools_dir else None
        orchestrator = get_orchestrator(tools_path)
        
        print("Running compliance checks...\n")
        result = orchestrator.run(model, checker_filter=filter_checker)
        
        # Print execution log if verbose
        if verbose:
            print(result["log"])
            print()
        
        # Print summary
        if output_format == "summary":
            orchestrator.print_summary(result)
            
            # Show failures if any
            failures = orchestrator.filter_results(result["results"], status="fail")
            if failures:
                print("\n⚠️  FAILURES DETECTED:\n")
                for failure in failures:
                    print(f"  • {failure['element_type']}: {failure['element_name']}")
                    print(f"    Status: {failure['check_status']}")
                    print(f"    Expected: {failure['required_value']}")
                    print(f"    Actual: {failure['actual_value']}")
                    if failure['comment']:
                        print(f"    Note: {failure['comment']}")
                    print()
        
        elif output_format == "detailed":
            orchestrator.print_summary(result)
            
            print("\nDETAILED RESULTS:\n")
            for i, res in enumerate(result["results"], 1):
                print(f"{i}. [{res['check_status'].upper()}] {res['element_type']}: {res['element_name']}")
                print(f"   File: {res.get('_checker_file', 'unknown')}")
                print(f"   Function: {res.get('_checker_function', 'unknown')}")
                print(f"   Expected: {res['required_value']}")
                print(f"   Actual: {res['actual_value']}")
                if res['comment']:
                    print(f"   Comment: {res['comment']}")
                print()
        
        elif output_format == "json":
            import json
            print(json.dumps(result, indent=2, default=str))
        
        return result
        
    except Exception as e:
        print(f"ERROR: {str(e)}", file=sys.stderr)
        return None


def main():
    """Command-line interface for the orchestrator."""
    
    parser = argparse.ArgumentParser(
        description="IFCore Orchestrator - Run all compliance checks on an IFC model"
    )
    
    parser.add_argument(
        "ifc_file",
        help="Path to the IFC file to check"
    )
    
    parser.add_argument(
        "-t", "--tools-dir",
        default="./tools",
        help="Path to tools directory (default: ./tools)"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Print detailed execution log"
    )
    
    parser.add_argument(
        "-f", "--filter",
        default=None,
        help="Only run checkers matching this name (e.g., 'doors', 'walls')"
    )
    
    parser.add_argument(
        "-o", "--output",
        choices=["summary", "detailed", "json"],
        default="summary",
        help="Output format (default: summary)"
    )
    
    args = parser.parse_args()
    
    run_checks_on_model(
        args.ifc_file,
        tools_dir=args.tools_dir,
        verbose=args.verbose,
        filter_checker=args.filter,
        output_format=args.output
    )


if __name__ == "__main__":
    main()
