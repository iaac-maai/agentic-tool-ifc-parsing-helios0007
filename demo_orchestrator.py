#!/usr/bin/env python3
"""
Simple Orchestrator Demo

This script demonstrates the orchestrator in action with a test IFC model.
"""

import sys
from pathlib import Path
import ifcopenshell
import ifcopenshell.api
from orchestrator import get_orchestrator


def create_demo_model() -> ifcopenshell.file:
    """Create a simple demo IFC model with some building elements."""
    
    print("Creating demo IFC model...")
    model = ifcopenshell.file(schema="IFC4")
    
    # Create project structure
    project = ifcopenshell.api.run("root.create_entity", model, ifc_class="IfcProject", name="Demo Project")
    site = ifcopenshell.api.run("root.create_entity", model, ifc_class="IfcSite", name="Demo Site")
    building = ifcopenshell.api.run("root.create_entity", model, ifc_class="IfcBuilding", name="Demo Building")
    
    ifcopenshell.api.run("aggregate.assign_object", model, relating_object=project, products=[site])
    ifcopenshell.api.run("aggregate.assign_object", model, relating_object=site, products=[building])
    
    # Create building storey
    storey = ifcopenshell.api.run("root.create_entity", model, ifc_class="IfcBuildingStorey", name="Ground Floor")
    storey.Elevation = 0.0
    ifcopenshell.api.run("aggregate.assign_object", model, relating_object=building, products=[storey])
    
    # Create context
    context = ifcopenshell.api.run("context.add_context", model, context_type="Model")
    
    print(f"  ✓ Created project, building, storey, and context")
    return model


def main():
    """Run the demo."""
    
    print("\n" + "="*70)
    print("IFCORE ORCHESTRATOR DEMO")
    print("="*70 + "\n")
    
    try:
        # Create a demo model
        model = create_demo_model()
        
        # Initialize orchestrator and discover checkers
        print("\nDiscovering compliance checkers...")
        orchestrator = get_orchestrator()
        
        print(f"\nDiscovered checkers:")
        for filename, functions in orchestrator.checkers.items():
            for func_name in functions:
                print(f"  • {filename}::{func_name}()")
        
        # Run all checks
        print("\n" + "-"*70)
        print("Running all compliance checks...\n")
        result = orchestrator.run(model)
        
        # Display summary
        orchestrator.print_summary(result)
        
        # Show sample results
        if result["results"]:
            print("\nSample Results (first 5):\n")
            for i, res in enumerate(result["results"][:5], 1):
                print(f"{i}. [{res['check_status'].upper():7}] {res['element_type']:20} {res['element_name']}")
                print(f"   Expected: {res['required_value']}")
                print(f"   Actual:   {res['actual_value']}")
                print()
        
        # Demo: Filter by status
        print("-"*70)
        failures = orchestrator.filter_results(result["results"], status="fail")
        if failures:
            print(f"\n❌ FAILURES FOUND: {len(failures)}")
            for f in failures[:3]:  # Show first 3
                print(f"  • {f['element_name']}: {f['comment']}")
        else:
            print("\n✅ No failures found!")
        
        # Demo: Get summary by status
        status_count = orchestrator.get_summary_by_status(result["results"])
        print(f"\nStatus breakdown: {status_count}")
        
        print("\n" + "="*70)
        print("Demo complete!")
        print("="*70 + "\n")
        
    except Exception as e:
        print(f"ERROR: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
