"""
Tests for the IFCore Orchestrator.

Validates that orchestrator correctly discovers and executes all checker functions.
"""

import pytest
import sys
from pathlib import Path
import ifcopenshell
import ifcopenshell.api
from orchestrator import CheckerOrchestrator, get_orchestrator, OrchestratorError


class TestOrchestratorDiscovery:
    """Tests for checker discovery."""
    
    def test_discovery_finds_checkers(self):
        """Orchestrator should discover all checker_*.py files."""
        orchestrator = CheckerOrchestrator()
        discovered = orchestrator.discover()
        
        assert isinstance(discovered, dict)
        assert len(discovered) > 0, "Should discover at least one checker"
    
    def test_discovery_finds_check_functions(self):
        """Each discovered file should have check_* functions."""
        orchestrator = CheckerOrchestrator()
        discovered = orchestrator.discover()
        
        for filename, functions in discovered.items():
            assert filename.startswith("checker_"), f"File should be named checker_*.py: {filename}"
            assert isinstance(functions, list)
            assert len(functions) > 0, f"{filename} should have at least one check_* function"
            
            for func_name in functions:
                assert func_name.startswith("check_"), f"Function should be named check_*: {func_name}"
    
    def test_discovery_excludes_template(self):
        """checker_template.py should be excluded from discovery."""
        orchestrator = CheckerOrchestrator()
        discovered = orchestrator.discover()
        
        for filename in discovered.keys():
            assert filename != "checker_template.py", "Template file should be excluded"
    
    def test_discovery_loads_modules(self):
        """Discovered modules should be loaded into memory."""
        orchestrator = CheckerOrchestrator()
        discovered = orchestrator.discover()
        
        assert len(orchestrator.loaded_modules) > 0
        for filename in discovered.keys():
            assert filename in orchestrator.loaded_modules
            assert orchestrator.loaded_modules[filename] is not None


class TestOrchestratorExecution:
    """Tests for checker execution."""
    
    @pytest.fixture
    def simple_model(self):
        """Create a simple IFC model for testing."""
        model = ifcopenshell.file(schema="IFC4")
        
        # Create basic structure
        project = ifcopenshell.api.run("root.create_entity", model, ifc_class="IfcProject", name="Test Project")
        site = ifcopenshell.api.run("root.create_entity", model, ifc_class="IfcSite", name="Test Site")
        building = ifcopenshell.api.run("root.create_entity", model, ifc_class="IfcBuilding", name="Test Building")
        
        ifcopenshell.api.run("aggregate.assign_object", model, relating_object=project, products=[site])
        ifcopenshell.api.run("aggregate.assign_object", model, relating_object=site, products=[building])
        
        return model
    
    def test_execution_returns_correct_structure(self, simple_model):
        """Orchestrator.run() should return correct result structure."""
        orchestrator = get_orchestrator()
        result = orchestrator.run(simple_model)
        
        assert isinstance(result, dict)
        assert "results" in result
        assert "summary" in result
        assert "log" in result
        
        assert isinstance(result["results"], list)
        assert isinstance(result["summary"], dict)
        assert isinstance(result["log"], str)
    
    def test_execution_validates_result_structure(self, simple_model):
        """All results should have required keys."""
        orchestrator = get_orchestrator()
        result = orchestrator.run(simple_model)
        
        required_keys = {
            "element_id", "element_type", "element_name",
            "element_name_long", "check_status", "actual_value",
            "required_value", "comment", "log"
        }
        
        for res in result["results"]:
            assert isinstance(res, dict)
            missing_keys = required_keys - set(res.keys())
            assert not missing_keys, f"Result missing keys: {missing_keys}"
    
    def test_execution_validates_model_type(self):
        """Orchestrator should reject non-IFC models."""
        orchestrator = get_orchestrator()
        
        with pytest.raises(OrchestratorError):
            orchestrator.run("not a model")
        
        with pytest.raises(OrchestratorError):
            orchestrator.run(None)
    
    def test_execution_requires_discovery(self):
        """Orchestrator should require discovery before execution."""
        orchestrator = CheckerOrchestrator()  # Don't call discover()
        model = ifcopenshell.file(schema="IFC4")
        
        with pytest.raises(OrchestratorError):
            orchestrator.run(model)


class TestOrchestratorFiltering:
    """Tests for result filtering."""
    
    @pytest.fixture
    def sample_results(self):
        """Create sample results for filtering."""
        return [
            {
                "element_id": "id1",
                "element_type": "IfcDoor",
                "element_name": "Door 1",
                "element_name_long": None,
                "check_status": "pass",
                "actual_value": "0.8m",
                "required_value": "≥ 0.8m",
                "comment": None,
                "log": None,
            },
            {
                "element_id": "id2",
                "element_type": "IfcDoor",
                "element_name": "Door 2",
                "element_name_long": None,
                "check_status": "fail",
                "actual_value": "0.7m",
                "required_value": "≥ 0.8m",
                "comment": "Too narrow",
                "log": None,
            },
            {
                "element_id": None,
                "element_type": "Summary",
                "element_name": "Door Check",
                "element_name_long": None,
                "check_status": "fail",
                "actual_value": "1 passed, 1 failed",
                "required_value": "All pass",
                "comment": None,
                "log": None,
            },
        ]
    
    def test_filter_by_status(self, sample_results):
        """Filter results by check_status."""
        orchestrator = CheckerOrchestrator()
        
        passed = orchestrator.filter_results(sample_results, status="pass")
        assert len(passed) == 1
        assert passed[0]["check_status"] == "pass"
        
        failed = orchestrator.filter_results(sample_results, status="fail")
        assert len(failed) == 2
        for result in failed:
            assert result["check_status"] == "fail"
    
    def test_filter_by_element_type(self, sample_results):
        """Filter results by element_type."""
        orchestrator = CheckerOrchestrator()
        
        doors = orchestrator.filter_results(sample_results, element_type="IfcDoor")
        assert len(doors) == 2
        for result in doors:
            assert result["element_type"] == "IfcDoor"
        
        summaries = orchestrator.filter_results(sample_results, element_type="Summary")
        assert len(summaries) == 1
        assert summaries[0]["element_type"] == "Summary"
    
    def test_filter_by_both_criteria(self, sample_results):
        """Filter by both status and element_type."""
        orchestrator = CheckerOrchestrator()
        
        result = orchestrator.filter_results(
            sample_results,
            status="pass",
            element_type="IfcDoor"
        )
        assert len(result) == 1
        assert result[0]["check_status"] == "pass"
        assert result[0]["element_type"] == "IfcDoor"


class TestOrchestratorSummary:
    """Tests for result summarization."""
    
    @pytest.fixture
    def sample_results(self):
        """Create sample results for summarization."""
        return [
            {"check_status": "pass", "element_type": "IfcDoor", "element_id": "1", 
             "element_name": "D1", "element_name_long": None, "actual_value": "ok", 
             "required_value": "ok", "comment": None, "log": None},
            {"check_status": "pass", "element_type": "IfcDoor", "element_id": "2",
             "element_name": "D2", "element_name_long": None, "actual_value": "ok",
             "required_value": "ok", "comment": None, "log": None},
            {"check_status": "fail", "element_type": "IfcWall", "element_id": "3",
             "element_name": "W1", "element_name_long": None, "actual_value": "bad",
             "required_value": "good", "comment": None, "log": None},
            {"check_status": "warning", "element_type": "IfcWindow", "element_id": "4",
             "element_name": "W1", "element_name_long": None, "actual_value": "maybe",
             "required_value": "yes", "comment": None, "log": None},
        ]
    
    def test_summary_by_status(self, sample_results):
        """Get count of results by status."""
        orchestrator = CheckerOrchestrator()
        summary = orchestrator.get_summary_by_status(sample_results)
        
        assert summary == {
            "pass": 2,
            "fail": 1,
            "warning": 1,
        }
    
    def test_summary_by_status_empty(self):
        """Summary of empty results."""
        orchestrator = CheckerOrchestrator()
        summary = orchestrator.get_summary_by_status([])
        
        assert summary == {}


class TestGetOrchestratorHelper:
    """Tests for convenience functions."""
    
    def test_get_orchestrator_initializes(self):
        """get_orchestrator() should return initialized instance."""
        orchestrator = get_orchestrator()
        
        assert isinstance(orchestrator, CheckerOrchestrator)
        assert len(orchestrator.checkers) > 0, "Should be pre-initialized with discovery"
    
    def test_get_orchestrator_with_custom_path(self, tmp_path):
        """get_orchestrator() should accept custom tools directory."""
        # Create a minimal checker file in temp dir
        temp_checker = tmp_path / "checker_test.py"
        temp_checker.write_text("""
def check_test(model):
    return [{
        "element_id": None,
        "element_type": "Test",
        "element_name": "Test",
        "element_name_long": None,
        "check_status": "pass",
        "actual_value": "1",
        "required_value": "1",
        "comment": None,
        "log": None,
    }]
""")
        
        orchestrator = get_orchestrator(tmp_path)
        assert "checker_test.py" in orchestrator.checkers


class TestOrchestratorIntegration:
    """Integration tests with real checkers and models."""
    
    @pytest.fixture
    def sample_model(self):
        """Create a sample IFC model with various elements."""
        model = ifcopenshell.file(schema="IFC4")
        
        # Create project structure
        project = ifcopenshell.api.run("root.create_entity", model, ifc_class="IfcProject", name="Test")
        site = ifcopenshell.api.run("root.create_entity", model, ifc_class="IfcSite", name="Test Site")
        building = ifcopenshell.api.run("root.create_entity", model, ifc_class="IfcBuilding", name="Test Building")
        
        ifcopenshell.api.run("aggregate.assign_object", model, relating_object=project, products=[site])
        ifcopenshell.api.run("aggregate.assign_object", model, relating_object=site, products=[building])
        
        return model
    
    def test_full_execution_flow(self, sample_model):
        """Full workflow: discover -> run -> filter -> summarize."""
        orchestrator = CheckerOrchestrator()
        
        # Discover
        discovered = orchestrator.discover()
        assert len(discovered) > 0
        
        # Run
        result = orchestrator.run(sample_model)
        assert result["summary"]["total_checkers"] > 0
        
        # Filter
        failures = orchestrator.filter_results(result["results"], status="fail")
        assert isinstance(failures, list)
        
        # Summarize
        summary = orchestrator.get_summary_by_status(result["results"])
        assert isinstance(summary, dict)
    
    def test_execution_with_kwargs(self, sample_model):
        """Orchestrator should pass kwargs to check functions."""
        orchestrator = get_orchestrator()
        
        # Run with custom parameters
        result = orchestrator.run(sample_model, min_width=0.9, max_u_value=1.5)
        
        # Should complete without error
        assert result is not None
        assert "results" in result
        assert "summary" in result
