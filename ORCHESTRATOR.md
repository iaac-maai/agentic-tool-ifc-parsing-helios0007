# IFCore Orchestrator Guide

The **IFCore Orchestrator** automatically discovers and executes all compliance checker functions on IFC models. It provides a unified interface for running multiple compliance checks and aggregating results.

---

## Quick Start

### 1. Run All Checks

```python
import ifcopenshell
from orchestrator import run_all_checks

# Load your IFC model
model = ifcopenshell.open("model.ifc")

# Run all checks
result = run_all_checks(model)

# Access results
print(f"Total results: {len(result['results'])}")
print(f"Passed: {result['summary']['successful_checkers']}")
print(f"Failed: {result['summary']['failed_checkers']}")
```

### 2. Command-Line Usage

```bash
# Run checks on an IFC file
python run_checks.py building.ifc

# Show detailed results
python run_checks.py building.ifc -o detailed

# Only run door checks
python run_checks.py building.ifc -f doors

# Verbose output with execution log
python run_checks.py building.ifc -v
```

---

## How It Works

The orchestrator follows this workflow:

```
1. DISCOVERY
   ├─ Scan tools/ directory for checker_*.py files
   ├─ Load each module dynamically
   ├─ Find all check_*() functions (must start with "check_")
   └─ Build function registry

2. EXECUTION
   ├─ Call each check_*() function with the IFC model
   ├─ Validate return value structure
   ├─ Aggregate results from all checkers
   └─ Add metadata (_checker_file, _checker_function)

3. AGGREGATION
   ├─ Collect all results
   ├─ Summarize execution (success count, error count)
   ├─ Provide filtering and analysis functions
   └─ Return structured result object
```

---

## Available Checkers

The orchestrator auto-discovers these checkers:

| Checker | Function | Purpose |
|---------|----------|---------|
| `checker_doors.py` | `check_door_accessibility()` | Verify door widths meet ADA standards (≥ 0.8128m) |
| `checker_walls.py` | `check_wall_fire_rating()` | Validate wall fire ratings (default: F60) |
| `checker_windows.py` | `check_window_thermal()` | Check window U-values (default: ≤ 2.0 W/m²·K) |
| `checker_rooms.py` | `check_room_heights()` | Verify room ceiling heights (≥ 2.4m) |
| `checker_stairs.py` | `check_stair_dimensions()` | Validate stair treads and risers |

---

## Python API

### Basic Usage

```python
from orchestrator import get_orchestrator
import ifcopenshell

# Initialize orchestrator (includes auto-discovery)
orchestrator = get_orchestrator()

# Load an IFC model
model = ifcopenshell.open("model.ifc")

# Run all checks
result = orchestrator.run(model)

# Access results
results_list = result["results"]
summary = result["summary"]
log = result["log"]
```

### Filtering Checks

```python
# Run only specific checkers
result = orchestrator.run(model, checker_filter="doors")  # Only door checks

result = orchestrator.run(model, checker_filter="walls")  # Only wall checks
```

### Passing Custom Parameters

```python
# Pass custom parameters to check functions
result = orchestrator.run(
    model,
    min_width=0.9,              # Override door width requirement
    max_u_value=1.8,            # Override window U-value requirement
    min_height=2.7              # Override room height requirement
)
```

### Filtering Results

```python
# Filter results by status
failures = orchestrator.filter_results(result["results"], status="fail")
warnings = orchestrator.filter_results(result["results"], status="warning")

# Filter by element type
doors = orchestrator.filter_results(result["results"], element_type="IfcDoor")
summaries = orchestrator.filter_results(result["results"], element_type="Summary")

# Combine filters
door_failures = orchestrator.filter_results(
    result["results"],
    status="fail",
    element_type="IfcDoor"
)
```

### Summarizing Results

```python
# Get count of results by status
status_summary = orchestrator.get_summary_by_status(result["results"])
# Returns: {"pass": 10, "fail": 2, "warning": 3}

# Pretty-print summary
orchestrator.print_summary(result)
```

---

## Result Structure

Each result dictionary contains:

```python
{
    # Required fields (from check_* function)
    "element_id": "GlobalId or None",
    "element_type": "IfcDoor | IfcWall | Summary | ...",
    "element_name": "Display name of element",
    "element_name_long": "Full name or None",
    "check_status": "pass | fail | warning | blocked | log",
    "actual_value": "What was found",
    "required_value": "What was expected",
    "comment": "Human-readable explanation or None",
    "log": "Debug info or None",
    
    # Metadata added by orchestrator
    "_checker_file": "checker_doors.py",
    "_checker_function": "check_door_accessibility"
}
```

### Valid check_status Values

- **`pass`**: Element meets requirement
- **`fail`**: Element does NOT meet requirement
- **`warning`**: Element may not meet requirement (uncertain)
- **`blocked`**: Check could not be performed (e.g., missing data)
- **`log`**: Informational result (for debugging)

---

## Execution Result Structure

```python
result = orchestrator.run(model)

result = {
    "results": [
        # List of all result dicts from all checkers
        {
            "element_id": ...,
            "element_type": ...,
            ...
        },
        ...
    ],
    
    "summary": {
        "total_checkers": 5,              # Number of checkers discovered
        "successful_checkers": 5,         # Number that ran without error
        "failed_checkers": 0,             # Number that raised exceptions
        "total_results": 25,              # Total results across all checkers
        "checker_details": [
            {
                "checker": "checker_doors.py::check_door_accessibility",
                "status": "success",      # "success" or "failed"
                "result_count": 5,        # Number of results from this checker
                "error": None             # Error message if failed
            },
            ...
        ]
    },
    
    "log": "Multi-line execution log with timestamps and details"
}
```

---

## Examples

### Example 1: Check a Model and Report Failures

```python
from orchestrator import run_all_checks
import ifcopenshell

model = ifcopenshell.open("building.ifc")
result = run_all_checks(model)

# Find all failures
failures = [r for r in result["results"] if r["check_status"] == "fail"]

if failures:
    print(f"❌ Found {len(failures)} compliance issues:\n")
    for failure in failures:
        print(f"  • {failure['element_type']}: {failure['element_name']}")
        print(f"    Required: {failure['required_value']}")
        print(f"    Actual: {failure['actual_value']}")
        print(f"    Note: {failure['comment']}\n")
else:
    print("✅ All checks passed!")
```

### Example 2: Check Specific Element Type

```python
from orchestrator import get_orchestrator
import ifcopenshell

orchestrator = get_orchestrator()
model = ifcopenshell.open("building.ifc")

result = orchestrator.run(model)

# Get only door check results
door_results = orchestrator.filter_results(result["results"], element_type="IfcDoor")

print(f"Door Check Results:")
for r in door_results:
    status_emoji = "✓" if r["check_status"] == "pass" else "✗"
    print(f"  {status_emoji} {r['element_name']}: {r['actual_value']}")
```

### Example 3: Custom Parameters

```python
from orchestrator import get_orchestrator
import ifcopenshell

orchestrator = get_orchestrator()
model = ifcopenshell.open("luxury_mansion.ifc")

# Stricter requirements for luxury building
result = orchestrator.run(
    model,
    min_width=0.95,             # Wider doors
    max_u_value=1.2,            # Better windows
    min_height=3.0              # Higher ceilings
)

orchestrator.print_summary(result)
```

### Example 4: Detailed Analysis

```python
from orchestrator import get_orchestrator
import ifcopenshell

orchestrator = get_orchestrator()
discovery = orchestrator.discover()

print("Discovered compliance checkers:")
for filename, functions in discovery.items():
    print(f"\n{filename}:")
    for func_name in functions:
        print(f"  - {func_name}()")

model = ifcopenshell.open("model.ifc")
result = orchestrator.run(model)

# Analyze by checker
print("\n\nResults by checker:")
for detail in result["summary"]["checker_details"]:
    print(f"  {detail['checker']}: {detail['result_count']} results")

# Summary by status
status_breakdown = orchestrator.get_summary_by_status(result["results"])
print("\n\nStatus breakdown:")
for status, count in status_breakdown.items():
    print(f"  {status}: {count}")
```

---

## Error Handling

```python
from orchestrator import get_orchestrator, OrchestratorError
import ifcopenshell

try:
    orchestrator = get_orchestrator()
    model = ifcopenshell.open("model.ifc")
    result = orchestrator.run(model)
    
except FileNotFoundError as e:
    print(f"IFC file not found: {e}")
    
except OrchestratorError as e:
    print(f"Orchestrator error: {e}")
    
except Exception as e:
    print(f"Unexpected error: {e}")
```

---

## Troubleshooting

### No checkers discovered

- Ensure checker files are in the `tools/` directory
- Files must be named `checker_*.py` (not `checker_template.py`)
- Functions must be named `check_*()` (case-sensitive)

### Checker execution failed

- Check the `log` field in the execution result for error messages
- Verify the IFC model is valid: `ifcopenshell.open(path)`
- Ensure the checker function has the correct signature: `def check_*(model, **kwargs)`

### Missing results

- Check that the checker function returns a list of dicts
- Verify each dict has all required keys
- Some checkers return "warning" status if elements are not found in the model

---

## See Also

- [Checker Template](tools/checker_template.py) - Starting point for creating new checkers
- [Compliance Contract](docs/AGENTS.md) - Checker function requirements
- [Orchestrator Tests](tests/test_orchestrator.py) - Detailed usage patterns
- [Command-Line Tool](run_checks.py) - CLI for IFC checking
