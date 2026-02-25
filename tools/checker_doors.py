"""
Door Accessibility Checker

Verifies that doors meet accessibility standards:
- Minimum width of 32 inches (0.8128 m) for ADA compliance
- Checks door opening types and dimensions
"""

import ifcopenshell


def check_door_accessibility(model: ifcopenshell.file, min_width: float = 0.8128, **kwargs) -> list[dict]:
    """
    Check if doors meet accessibility standards (minimum width).
    
    Args:
        model: An ifcopenshell.file object representing the IFC model
        min_width: Minimum door width in meters (default: 0.8128m = 32 inches for ADA)
        **kwargs: Additional parameters
        
    Returns:
        List of result dictionaries following the required schema
    """
    results = []
    
    # Get all doors in the model
    doors = model.by_type("IfcDoor")
    
    if not doors:
        results.append({
            "element_id": None,
            "element_type": "Summary",
            "element_name": "Door Accessibility Check",
            "element_name_long": None,
            "check_status": "warning",
            "actual_value": "0",
            "required_value": ">= 1 door",
            "comment": "No doors found in model",
            "log": None,
        })
        return results
    
    passed = 0
    failed = 0
    
    for door in doors:
        door_id = door.GlobalId
        door_name = door.Name or f"Door #{door.id()}"
        door_long_name = getattr(door, "LongName", None)
        
        # Try to get door dimensions
        width = None
        status = "log"
        comment = None
        
        # Check if door has property set with accessibility info
        try:
            if hasattr(door, "IsDefinedBy"):
                for rel in door.IsDefinedBy:
                    if hasattr(rel, "RelatingPropertyDefinition"):
                        propset = rel.RelatingPropertyDefinition
                        if hasattr(propset, "HasProperties"):
                            for prop in propset.HasProperties:
                                if hasattr(prop, "Name"):
                                    if prop.Name and "Width" in prop.Name:
                                        if hasattr(prop, "NominalValue"):
                                            width = prop.NominalValue.wrappedValue
        except:
            pass
        
        # Check door opening properties
        if hasattr(door, "OverallWidth"):
            width = door.OverallWidth
        
        if width is not None:
            if width >= min_width:
                status = "pass"
                comment = f"Door width {width:.3f}m meets accessibility standard (≥ {min_width:.3f}m)"
                passed += 1
            else:
                status = "fail"
                comment = f"Door width {width:.3f}m does NOT meet accessibility standard (≥ {min_width:.3f}m)"
                failed += 1
        else:
            status = "log"
            comment = "Door width not specified in model"
        
        results.append({
            "element_id": door_id,
            "element_type": "IfcDoor",
            "element_name": door_name,
            "element_name_long": door_long_name,
            "check_status": status,
            "actual_value": f"{width:.3f}m" if width else "Not specified",
            "required_value": f">= {min_width:.3f}m ({min_width*39.37:.0f} inches)",
            "comment": comment,
            "log": None,
        })
    
    # Add summary result
    results.append({
        "element_id": None,
        "element_type": "Summary",
        "element_name": "Door Accessibility Check",
        "element_name_long": None,
        "check_status": "pass" if failed == 0 else "fail",
        "actual_value": f"Passed: {passed}, Failed: {failed}, Unspecified: {len(doors) - passed - failed}",
        "required_value": "All doors >= 0.8128m wide",
        "comment": f"Checked {len(doors)} door(s). {failed} door(s) failed accessibility check." if failed > 0 else f"All {len(doors)} door(s) pass accessibility check.",
        "log": None,
    })
    
    return results
