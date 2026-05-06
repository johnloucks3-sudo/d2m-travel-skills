"""
Skill Builder Configuration — Constraints, Templates, Domain Rules

Defines what skills CAN and CANNOT do in Thunderbird.
"""

from typing import Set, List
from dataclasses import dataclass


@dataclass
class SkillConstraints:
    """Safety constraints for generated skills"""

    # Functions that skills CANNOT call
    FORBIDDEN_MODULES: Set[str] = None
    FORBIDDEN_FUNCTIONS: Set[str] = None

    # Keywords that indicate constraint violations
    FORBIDDEN_KEYWORDS: Set[str] = None

    # Operations that require WF-17 approval (client-facing)
    REQUIRES_APPROVAL_KEYWORDS: Set[str] = None

    def __post_init__(self):
        if self.FORBIDDEN_MODULES is None:
            self.FORBIDDEN_MODULES = {
                "subprocess",
                "os.system",
                "os.popen",
                "shlex",
                "pty",
                "tty",
            }

        if self.FORBIDDEN_FUNCTIONS is None:
            self.FORBIDDEN_FUNCTIONS = {
                "exec",
                "eval",
                "compile",
                "__import__",
                "open(..., 'w')",  # File write
                "os.remove",
                "os.rmdir",
                "shutil.rmtree",
            }

        if self.FORBIDDEN_KEYWORDS is None:
            self.FORBIDDEN_KEYWORDS = {
                "subprocess",
                "shell=True",
                "exec(",
                "eval(",
                "compile(",
                "__import__",
                "rmtree",
                "os.remove",
                "__file__",
                "__builtins__",
            }

        if self.REQUIRES_APPROVAL_KEYWORDS is None:
            self.REQUIRES_APPROVAL_KEYWORDS = {
                "send email",
                "send sms",
                "send whatsapp",
                "send telegram",
                "notify client",
                "contact customer",
                "email to",
                "text to",
                "message to",
            }


# Default constraints instance
DEFAULT_CONSTRAINTS = SkillConstraints()


@dataclass
class SkillTemplate:
    """Template for different skill types"""

    name: str
    domain: str
    description: str
    example_requirement: str
    example_function_signature: str


SKILL_TEMPLATES: List[SkillTemplate] = [
    SkillTemplate(
        name="Hotel Price Checker",
        domain="travel",
        description="Look up hotel prices for a city and format as D2M quote",
        example_requirement="Check 4-5 star hotels in any city, return prices with Queen/Double and King/Grand",
        example_function_signature="def check_hotels_d2m(city: str, star_rating: int = 4) -> dict:"
    ),
    SkillTemplate(
        name="Price Monitor",
        domain="finance",
        description="Monitor prices for a product/service and alert on changes",
        example_requirement="Track Silversea cruise prices for Panama Canal and alert if price drops >5%",
        example_function_signature="def monitor_cruise_prices(ship_name: str, threshold_pct: float = 5.0) -> dict:"
    ),
    SkillTemplate(
        name="Data Formatter",
        domain="ops",
        description="Convert data between formats (CSV, JSON, HTML, etc.)",
        example_requirement="Convert client list to formatted CSV with name, email, booking status",
        example_function_signature="def format_client_csv(clients: list) -> str:"
    ),
    SkillTemplate(
        name="Intel Aggregator",
        domain="intel",
        description="Aggregate data from multiple sources and summarize",
        example_requirement="Scan cruise line news and summarize new ship announcements",
        example_function_signature="def aggregate_cruise_news(days_back: int = 7) -> dict:"
    ),
    SkillTemplate(
        name="Validation Checker",
        domain="ops",
        description="Validate data against rules (email, phone, booking ref, etc.)",
        example_requirement="Validate email addresses and flag invalid formats",
        example_function_signature="def validate_emails(emails: list) -> dict:"
    ),
]


# Domain-specific import allowlists
DOMAIN_ALLOWED_IMPORTS = {
    "travel": ["requests", "json", "datetime", "re"],
    "finance": ["json", "datetime", "re", "csv"],
    "intel": ["json", "datetime", "re", "collections"],
    "ops": ["json", "datetime", "re", "csv", "pathlib"],
    "email": ["json", "datetime", "re"],
    "generic": ["json", "datetime", "re"],
}


# Skill naming rules
SKILL_NAME_RULES = {
    "max_length": 50,
    "min_length": 3,
    "allowed_chars": "abcdefghijklmnopqrstuvwxyz0123456789_",
    "must_start_with": "a-z",
    "cannot_start_with": "_",
}


def validate_skill_constraint(code: str, constraints: SkillConstraints = DEFAULT_CONSTRAINTS) -> tuple[bool, str]:
    """
    Validate generated skill code against safety constraints

    Args:
        code: Generated Python code
        constraints: SkillConstraints to check against

    Returns:
        (is_valid: bool, error_message: str)
    """
    code_lower = code.lower()

    # Check for forbidden keywords
    for keyword in constraints.FORBIDDEN_KEYWORDS:
        if keyword.lower() in code_lower:
            return False, f"Forbidden keyword detected: '{keyword}'"

    # Check for forbidden modules
    for module in constraints.FORBIDDEN_MODULES:
        if f"import {module}" in code_lower or f"from {module}" in code_lower:
            return False, f"Forbidden module import: '{module}'"

    # Check for forbidden function calls
    for func in constraints.FORBIDDEN_FUNCTIONS:
        if func.lower() in code_lower:
            return False, f"Forbidden function call: '{func}'"

    return True, ""


def validate_skill_name(skill_name: str) -> tuple[bool, str]:
    """
    Validate skill name follows naming rules

    Args:
        skill_name: Proposed skill name

    Returns:
        (is_valid: bool, error_message: str)
    """
    rules = SKILL_NAME_RULES

    if len(skill_name) < rules["min_length"]:
        return False, f"Skill name too short (min {rules['min_length']} chars)"

    if len(skill_name) > rules["max_length"]:
        return False, f"Skill name too long (max {rules['max_length']} chars)"

    if not skill_name[0] in rules["must_start_with"]:
        return False, f"Skill name must start with lowercase letter"

    for char in skill_name:
        if char not in rules["allowed_chars"]:
            return False, f"Invalid character in skill name: '{char}'"

    return True, ""


# Logging configuration for skill builder
SKILL_BUILDER_LOG_CONFIG = {
    "log_file": "logs/skill_builder.log",
    "log_level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
}
