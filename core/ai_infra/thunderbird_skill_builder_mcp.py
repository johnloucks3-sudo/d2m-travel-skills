"""
Thunderbird Skill Builder MCP Tools — OpenClaw Pattern Adaptation
Registers skill builder tools with the MCP server for natural language skill creation.

Tools:
  build_skill_from_description — Commander describes a skill, Sonnet generates it
  list_available_skills — List all skills in the registry
  validate_skill_safety — Check if generated code passes safety constraints
  get_skill_metadata — Get metadata for a specific skill
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)

THUNDERBIRD_ROOT = Path.home() / "Thunderbird"
SKILLS_REGISTRY = THUNDERBIRD_ROOT / "config" / "skills_registry.json"


def _get_skill_builder():
    """Lazy import to avoid circular dependencies."""
    from ai_infra.thunderbird_skill_builder import ThunderbirdSkillBuilder
    return ThunderbirdSkillBuilder()


def _get_skill_constraints():
    """Lazy import for constraint validation."""
    from ai_infra.skill_builder_config import (
        validate_skill_constraint,
        validate_skill_name,
        DEFAULT_CONSTRAINTS,
    )
    return validate_skill_constraint, validate_skill_name, DEFAULT_CONSTRAINTS


def build_skill_from_description(requirement: str, commander_id: str = "7554895206") -> Dict[str, Any]:
    """
    Build a Python skill from natural language description.

    Args:
        requirement: Natural language description of the desired skill
        commander_id: Telegram user ID of the Commander

    Returns:
        dict with skill_name, file_path, invocation_example, success status
    """
    try:
        builder = _get_skill_builder()
        result = builder.build_skill(requirement, commander_id)

        if result.success:
            return {
                "success": True,
                "skill_name": result.skill_name,
                "file_path": str(result.file_path),
                "test_file_path": str(result.test_file_path),
                "invocation_example": result.invocation_example,
                "generated_code_preview": result.generated_code[:500] + "..." if len(result.generated_code) > 500 else result.generated_code,
                "message": f"Skill '{result.skill_name}' created successfully. Use: {result.invocation_example}",
            }
        else:
            return {
                "success": False,
                "error": result.error_message,
                "message": f"Skill generation failed: {result.error_message}",
            }
    except Exception as e:
        logger.error(f"build_skill_from_description failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"Skill generation error: {str(e)}",
        }


def list_available_skills(domain: str = "") -> Dict[str, Any]:
    """
    List all available skills, optionally filtered by domain.

    Args:
        domain: Filter by domain (travel, intel, ops, email, finance, generic)

    Returns:
        dict with list of skills and their metadata
    """
    try:
        from ai_infra.skill_builder_config import SKILL_TEMPLATES

        skills = []

        # Built-in templates
        for template in SKILL_TEMPLATES:
            if domain and template.domain != domain:
                continue
            skills.append({
                "name": template.name,
                "domain": template.domain,
                "description": template.description,
                "signature": template.example_function_signature,
                "source": "template",
            })

        # Registry skills
        if SKILLS_REGISTRY.exists():
            registry = json.loads(SKILLS_REGISTRY.read_text())
            for skill_id, skill_meta in registry.get("skills", {}).items():
                if domain and skill_meta.get("domain") != domain:
                    continue
                skills.append({
                    "name": skill_id,
                    "domain": skill_meta.get("domain", "unknown"),
                    "description": skill_meta.get("description", ""),
                    "source": "registry",
                    "uploaded": skill_meta.get("uploaded", ""),
                })

        # Scan core/ for existing skill modules
        core_dir = THUNDERBIRD_ROOT / "core"
        for domain_dir in core_dir.iterdir():
            if not domain_dir.is_dir():
                continue
            if domain and domain_dir.name != domain:
                continue
            for py_file in domain_dir.glob("thunderbird_*.py"):
                if py_file.name == "__init__.py":
                    continue
                skills.append({
                    "name": py_file.stem.replace("thunderbird_", ""),
                    "domain": domain_dir.name,
                    "source": "core_module",
                    "path": str(py_file),
                })

        return {
            "success": True,
            "count": len(skills),
            "skills": skills,
        }
    except Exception as e:
        logger.error(f"list_available_skills failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "skills": [],
        }


def validate_skill_safety(code: str) -> Dict[str, Any]:
    """
    Validate skill code against safety constraints.

    Args:
        code: Python code to validate

    Returns:
        dict with is_valid and any error messages
    """
    try:
        validate_fn, name_fn, constraints = _get_skill_constraints()

        is_valid, error_msg = validate_fn(code, constraints)

        result = {
            "success": True,
            "is_valid": is_valid,
        }

        if not is_valid:
            result["error"] = error_msg

        # Additional checks
        if "subprocess" in code:
            result["is_valid"] = False
            result["error"] = "subprocess module not allowed in skills"

        if "os.system" in code:
            result["is_valid"] = False
            result["error"] = "os.system not allowed in skills"

        if "eval(" in code or "exec(" in code:
            result["is_valid"] = False
            result["error"] = "eval/exec not allowed in skills"

        return result
    except Exception as e:
        logger.error(f"validate_skill_safety failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "is_valid": False,
        }


def get_skill_metadata(skill_name: str) -> Dict[str, Any]:
    """
    Get metadata for a specific skill.

    Args:
        skill_name: Name of the skill

    Returns:
        dict with skill metadata
    """
    try:
        # Search in core/ directories
        core_dir = THUNDERBIRD_ROOT / "core"
        for domain_dir in core_dir.iterdir():
            if not domain_dir.is_dir():
                continue
            # Try exact match
            skill_file = domain_dir / f"{skill_name}.py"
            if skill_file.exists():
                meta_file = skill_file.with_suffix(".json")
                if meta_file.exists():
                    return {
                        "success": True,
                        "skill_name": skill_name,
                        "file_path": str(skill_file),
                        "metadata": json.loads(meta_file.read_text()),
                    }
                return {
                    "success": True,
                    "skill_name": skill_name,
                    "file_path": str(skill_file),
                    "metadata": {"note": "No metadata file found"},
                }

        # Search in registry
        if SKILLS_REGISTRY.exists():
            registry = json.loads(SKILLS_REGISTRY.read_text())
            if skill_name in registry.get("skills", {}):
                return {
                    "success": True,
                    "skill_name": skill_name,
                    "metadata": registry["skills"][skill_name],
                    "source": "registry",
                }

        return {
            "success": False,
            "error": f"Skill '{skill_name}' not found",
        }
    except Exception as e:
        logger.error(f"get_skill_metadata failed: {e}")
        return {
            "success": False,
            "error": str(e),
        }


def register_skill_builder_tools(mcp) -> None:
    """Register skill builder tools with the MCP server."""

    @mcp.tool()
    def build_skill_from_description_tool(requirement: str, commander_id: str = "7554895206") -> Dict[str, Any]:
        """Build a Python skill from natural language description.

        Args:
            requirement: Natural language description of the desired skill functionality
            commander_id: Telegram user ID of the Commander (default: 7554895206)

        Returns:
            dict with skill details including file paths, invocation example, and success status
        """
        return build_skill_from_description(requirement, commander_id)

    @mcp.tool()
    def list_available_skills_tool(domain: str = "") -> Dict[str, Any]:
        """List all available skills, optionally filtered by domain.

        Args:
            domain: Filter by domain (travel, intel, ops, email, finance, generic)

        Returns:
            dict with count and list of available skills
        """
        return list_available_skills(domain)

    @mcp.tool()
    def validate_skill_safety_tool(code: str) -> Dict[str, Any]:
        """Validate skill code against safety constraints before deployment.

        Args:
            code: Python code to validate for safety

        Returns:
            dict with is_valid status and any error messages
        """
        return validate_skill_safety(code)

    @mcp.tool()
    def get_skill_metadata_tool(skill_name: str) -> Dict[str, Any]:
        """Get metadata for a specific skill by name.

        Args:
            skill_name: Name of the skill to look up

        Returns:
            dict with skill metadata including file path and creation info
        """
        return get_skill_metadata(skill_name)

    logger.info("Registered 4 skill builder tools with MCP server")
