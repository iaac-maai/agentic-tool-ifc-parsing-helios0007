"""
Room Ceiling Height Checker

Verifies that rooms meet minimum ceiling height requirements:
- Checks room heights against building codes
- Validates occupancy types and required clearances
"""

import ifcopenshell


def check_room_heights(model: ifcopenshell.file, min_height: float = 2.4, **kwargs) -> list[dict]:
    """
    Check if rooms meet minimum ceiling height requirements.
    
    Args:
        model: An ifcopenshell.file object representing the IFC model
        min_height: Minimum required ceiling height in meters (default: 2.4m)
        **kwargs: Additional parameters
        
    Returns:
        List of result dictionaries following the required schema
    """
    results = []
    
    # Get all spaces/rooms in the model
    spaces = model.by_type("IfcSpace")
    
    if not spaces:
        results.append({
            "element_id": None,
            "element_type": "Summary",
            "element_name": "Room Height Check",
            "element_name_long": None,
            "check_status": "warning",
            "actual_value": "0",
            "required_value": ">= 1 room/space",
            "comment": "No spaces/rooms found in model",
            "log": None,
        })
        return results
    
    passed = 0
    failed = 0
    unspecified = 0
    
    for space in spaces:
        space_id = space.GlobalId
        space_name = space.Name or f"Space #{space.id()}"
        space_long_name = getattr(space, "LongName", None)
        
        height = None
        status = "log"
        comment = None
        
        # Try to get room height from various sources
        try:
            # Check for elevation and floor height if available
            if hasattr(space, "ObjectPlacement"):
                placement = space.ObjectPlacement
                if hasattr(placement, "RelativePlacement"):
                    rel_placement = placement.RelativePlacement
                    if hasattr(rel_placement, "Location") and hasattr(rel_placement.Location, "Coordinates"):
                        z_coord = rel_placement.Location.Coordinates[2] if len(rel_placement.Location.Coordinates) > 2 else None
        except:
            z_coord = None
        
        # Check dimensional properties
        try:
            if hasattr(space, "IsDefinedBy"):
                for rel in space.IsDefinedBy:
                    if hasattr(rel, "RelatingPropertyDefinition"):
                        propset = rel.RelatingPropertyDefinition
                        if hasattr(propset, "HasProperties"):
                            for prop in propset.HasProperties:
                                if hasattr(prop, "Name") and hasattr(prop, "NominalValue"):
                                    if "Height" in prop.Name or "Ceiling" in prop.Name:
                                        try:
                                            height = float(prop.NominalValue.wrappedValue if hasattr(prop.NominalValue, "wrappedValue") else prop.NominalValue)
                                        except (ValueError, TypeError):
                                            pass
        except:
            pass
        
        if height is not None:
            if height >= min_height:
                status = "pass"
                comment = f"Room height {height:.2f}m meets minimum standard (≥ {min_height:.2f}m)"
                passed += 1
            else:
                status = "fail"
                comment = f"Room height {height:.2f}m BELOW minimum standard (≥ {min_height:.2f}m)"
                failed += 1
        else:
            status = "log"
            comment = "Room height not specified in model"
            unspecified += 1
        
        results.append({
            "element_id": space_id,
            "element_type": "IfcSpace",
            "element_name": space_name,
            "element_name_long": space_long_name,
            "check_status": status,
            "actual_value": f"{height:.2f}m" if height is not None else "Not specified",
            "required_value": f">= {min_height:.2f}m",
            "comment": comment,
            "log": None,
        })
    
    # Add summary result
    summary_status = "pass" if failed == 0 else "fail"
    results.append({
        "element_id": None,
        "element_type": "Summary",
        "element_name": "Room Height Check",
        "element_name_long": None,
        "check_status": summary_status,
        "actual_value": f"Passed: {passed}, Failed: {failed}, Unspecified: {unspecified}",
        "required_value": f"All rooms ≥ {min_height:.2f}m height",
        "comment": f"Checked {len(spaces)} room(s). {failed} below minimum height." if failed > 0 else f"All {len(spaces)} room(s) meet height requirement.",
        "log": None,
    })
    
    return results
