"""
Window Thermal Performance Checker

Verifies that windows meet thermal performance standards:
- Checks U-values (thermal transmittance)
- Validates against energy efficiency codes
"""

import ifcopenshell


def check_window_thermal(model: ifcopenshell.file, max_u_value: float = 2.0, **kwargs) -> list[dict]:
    """
    Check if windows meet thermal performance standards (U-value).
    
    Args:
        model: An ifcopenshell.file object representing the IFC model
        max_u_value: Maximum allowed U-value in W/(m²·K) (default: 2.0)
        **kwargs: Additional parameters
        
    Returns:
        List of result dictionaries following the required schema
    """
    results = []
    
    # Get all windows in the model
    windows = model.by_type("IfcWindow")
    
    if not windows:
        results.append({
            "element_id": None,
            "element_type": "Summary",
            "element_name": "Window Thermal Check",
            "element_name_long": None,
            "check_status": "warning",
            "actual_value": "0",
            "required_value": ">= 1 window",
            "comment": "No windows found in model",
            "log": None,
        })
        return results
    
    passed = 0
    failed = 0
    unspecified = 0
    
    for window in windows:
        window_id = window.GlobalId
        window_name = window.Name or f"Window #{window.id()}"
        window_long_name = getattr(window, "LongName", None)
        
        u_value = None
        status = "log"
        comment = None
        
        # Check window properties for U-value
        try:
            if hasattr(window, "IsDefinedBy"):
                for rel in window.IsDefinedBy:
                    if hasattr(rel, "RelatingPropertyDefinition"):
                        propset = rel.RelatingPropertyDefinition
                        if hasattr(propset, "HasProperties"):
                            for prop in propset.HasProperties:
                                if hasattr(prop, "Name") and hasattr(prop, "NominalValue"):
                                    if "U-value" in prop.Name or "Uvalue" in prop.Name or "ThermalTransmittance" in prop.Name:
                                        try:
                                            u_value = float(prop.NominalValue.wrappedValue if hasattr(prop.NominalValue, "wrappedValue") else prop.NominalValue)
                                        except (ValueError, TypeError):
                                            pass
        except:
            pass
        
        if u_value is not None:
            if u_value <= max_u_value:
                status = "pass"
                comment = f"Window U-value {u_value:.2f} W/(m²·K) meets thermal standard (≤ {max_u_value:.2f})"
                passed += 1
            else:
                status = "fail"
                comment = f"Window U-value {u_value:.2f} W/(m²·K) EXCEEDS thermal standard (≤ {max_u_value:.2f})"
                failed += 1
        else:
            status = "log"
            comment = "Window U-value not specified in model"
            unspecified += 1
        
        results.append({
            "element_id": window_id,
            "element_type": "IfcWindow",
            "element_name": window_name,
            "element_name_long": window_long_name,
            "check_status": status,
            "actual_value": f"{u_value:.2f} W/(m²·K)" if u_value is not None else "Not specified",
            "required_value": f"≤ {max_u_value:.2f} W/(m²·K)",
            "comment": comment,
            "log": None,
        })
    
    # Add summary result
    summary_status = "pass" if failed == 0 else "fail"
    results.append({
        "element_id": None,
        "element_type": "Summary",
        "element_name": "Window Thermal Check",
        "element_name_long": None,
        "check_status": summary_status,
        "actual_value": f"Passed: {passed}, Failed: {failed}, Unspecified: {unspecified}",
        "required_value": f"All windows U-value ≤ {max_u_value:.2f} W/(m²·K)",
        "comment": f"Checked {len(windows)} window(s). {failed} failed thermal check." if failed > 0 else f"All {len(windows)} window(s) meet thermal standard.",
        "log": None,
    })
    
    return results
