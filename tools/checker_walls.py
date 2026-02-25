"""
Wall Fire Rating Checker

Verifies that walls have proper fire rating classifications:
- Supports fire resistance classifications (e.g., F60, F90, F120)
- Checks fire rating property sets
"""

import ifcopenshell


def check_wall_fire_rating(model: ifcopenshell.file, required_rating: str = "F60", **kwargs) -> list[dict]:
    """
    Check if walls have proper fire rating specifications.
    
    Args:
        model: An ifcopenshell.file object representing the IFC model
        required_rating: Required fire rating (default: "F60")
        **kwargs: Additional parameters
        
    Returns:
        List of result dictionaries following the required schema
    """
    results = []
    
    # Get all walls in the model
    walls = model.by_type("IfcWall")
    
    if not walls:
        results.append({
            "element_id": None,
            "element_type": "Summary",
            "element_name": "Wall Fire Rating Check",
            "element_name_long": None,
            "check_status": "warning",
            "actual_value": "0",
            "required_value": ">= 1 wall",
            "comment": "No walls found in model",
            "log": None,
        })
        return results
    
    passed = 0
    failed = 0
    unspecified = 0
    
    for wall in walls:
        wall_id = wall.GlobalId
        wall_name = wall.Name or f"Wall #{wall.id()}"
        wall_long_name = getattr(wall, "LongName", None)
        
        fire_rating = None
        status = "log"
        comment = None
        
        # Check wall properties for fire rating
        try:
            if hasattr(wall, "IsDefinedBy"):
                for rel in wall.IsDefinedBy:
                    if hasattr(rel, "RelatingPropertyDefinition"):
                        propset = rel.RelatingPropertyDefinition
                        if hasattr(propset, "Name") and "Fire" in propset.Name:
                            if hasattr(propset, "HasProperties"):
                                for prop in propset.HasProperties:
                                    if hasattr(prop, "Name") and hasattr(prop, "NominalValue"):
                                        if "Rating" in prop.Name or "Class" in prop.Name:
                                            fire_rating = prop.NominalValue.wrappedValue if hasattr(prop.NominalValue, "wrappedValue") else str(prop.NominalValue)
        except:
            pass
        
        if fire_rating:
            if fire_rating == required_rating or (isinstance(fire_rating, str) and required_rating in fire_rating):
                status = "pass"
                comment = f"Wall has required fire rating: {fire_rating}"
                passed += 1
            else:
                status = "fail"
                comment = f"Wall fire rating {fire_rating} does NOT meet requirement of {required_rating}"
                failed += 1
        else:
            status = "warning"
            comment = "Fire rating not specified in model"
            unspecified += 1
        
        results.append({
            "element_id": wall_id,
            "element_type": "IfcWall",
            "element_name": wall_name,
            "element_name_long": wall_long_name,
            "check_status": status,
            "actual_value": fire_rating or "Not specified",
            "required_value": required_rating,
            "comment": comment,
            "log": None,
        })
    
    # Add summary result
    summary_status = "pass" if failed == 0 and unspecified == 0 else ("warning" if failed == 0 else "fail")
    results.append({
        "element_id": None,
        "element_type": "Summary",
        "element_name": "Wall Fire Rating Check",
        "element_name_long": None,
        "check_status": summary_status,
        "actual_value": f"Passed: {passed}, Failed: {failed}, Unspecified: {unspecified}",
        "required_value": f"All walls rated {required_rating}",
        "comment": f"Checked {len(walls)} wall(s). {failed} failed, {unspecified} unspecified." if (failed > 0 or unspecified > 0) else f"All {len(walls)} wall(s) have fire rating specified.",
        "log": None,
    })
    
    return results
