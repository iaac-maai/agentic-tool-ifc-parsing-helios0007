"""
Stair Dimensions Checker

Verifies that stairs meet building code requirements:
- Checks tread and riser dimensions
- Validates stair accessibility and safety standards
"""

import ifcopenshell


def check_stair_dimensions(model: ifcopenshell.file, min_tread: float = 0.28, max_riser: float = 0.19, **kwargs) -> list[dict]:
    """
    Check if stairs meet building code requirements for dimensions.
    
    Args:
        model: An ifcopenshell.file object representing the IFC model
        min_tread: Minimum tread depth in meters (default: 0.28m / 11 inches)
        max_riser: Maximum riser height in meters (default: 0.19m / 7.5 inches)
        **kwargs: Additional parameters
        
    Returns:
        List of result dictionaries following the required schema
    """
    results = []
    
    # Get all stairs in the model
    stairs = model.by_type("IfcStair")
    
    if not stairs:
        results.append({
            "element_id": None,
            "element_type": "Summary",
            "element_name": "Stair Dimensions Check",
            "element_name_long": None,
            "check_status": "warning",
            "actual_value": "0",
            "required_value": ">= 1 stair",
            "comment": "No stairs found in model",
            "log": None,
        })
        return results
    
    passed = 0
    failed = 0
    unspecified = 0
    
    for stair in stairs:
        stair_id = stair.GlobalId
        stair_name = stair.Name or f"Stair #{stair.id()}"
        stair_long_name = getattr(stair, "LongName", None)
        
        tread_depth = None
        riser_height = None
        status = "log"
        comment = None
        
        # Check stair properties
        try:
            if hasattr(stair, "IsDefinedBy"):
                for rel in stair.IsDefinedBy:
                    if hasattr(rel, "RelatingPropertyDefinition"):
                        propset = rel.RelatingPropertyDefinition
                        if hasattr(propset, "HasProperties"):
                            for prop in propset.HasProperties:
                                if hasattr(prop, "Name") and hasattr(prop, "NominalValue"):
                                    prop_name = prop.Name
                                    try:
                                        value = float(prop.NominalValue.wrappedValue if hasattr(prop.NominalValue, "wrappedValue") else prop.NominalValue)
                                    except (ValueError, TypeError):
                                        continue
                                    
                                    if "Tread" in prop_name or "tread" in prop_name.lower():
                                        tread_depth = value
                                    elif "Riser" in prop_name or "riser" in prop_name.lower():
                                        riser_height = value
        except:
            pass
        
        # Evaluate stair dimensions
        tread_pass = tread_depth is None or tread_depth >= min_tread
        riser_pass = riser_height is None or riser_height <= max_riser
        
        if tread_depth is not None and riser_height is not None:
            if tread_pass and riser_pass:
                status = "pass"
                comment = f"Stair dimensions meet code: tread={tread_depth:.3f}m, riser={riser_height:.3f}m"
                passed += 1
            else:
                status = "fail"
                issues = []
                if not tread_pass:
                    issues.append(f"tread too shallow ({tread_depth:.3f}m < {min_tread:.3f}m)")
                if not riser_pass:
                    issues.append(f"riser too tall ({riser_height:.3f}m > {max_riser:.3f}m)")
                comment = f"Stair dimensions FAIL code: {', '.join(issues)}"
                failed += 1
        else:
            status = "log"
            specified = []
            if tread_depth is not None:
                specified.append(f"tread={tread_depth:.3f}m")
            if riser_height is not None:
                specified.append(f"riser={riser_height:.3f}m")
            comment = f"Stair dimensions partially specified: {', '.join(specified) if specified else 'No dimensions'}"
            unspecified += 1
        
        # Format actual/required values
        actual_val = []
        if tread_depth is not None:
            actual_val.append(f"T:{tread_depth:.3f}m")
        if riser_height is not None:
            actual_val.append(f"R:{riser_height:.3f}m")
        actual_value = ", ".join(actual_val) if actual_val else "Not specified"
        
        results.append({
            "element_id": stair_id,
            "element_type": "IfcStair",
            "element_name": stair_name,
            "element_name_long": stair_long_name,
            "check_status": status,
            "actual_value": actual_value,
            "required_value": f"Tread ≥ {min_tread:.3f}m, Riser ≤ {max_riser:.3f}m",
            "comment": comment,
            "log": None,
        })
    
    # Add summary result
    summary_status = "pass" if failed == 0 else "fail"
    results.append({
        "element_id": None,
        "element_type": "Summary",
        "element_name": "Stair Dimensions Check",
        "element_name_long": None,
        "check_status": summary_status,
        "actual_value": f"Passed: {passed}, Failed: {failed}, Unspecified: {unspecified}",
        "required_value": f"All stairs meet code dimensions",
        "comment": f"Checked {len(stairs)} stair(s). {failed} failed dimension check." if failed > 0 else f"All {len(stairs)} stair(s) meet code dimensions.",
        "log": None,
    })
    
    return results
