"""
Rule management components for the AI Cleaner addon.

This package contains rule-related functionality including:
- Ignore rules manager
- Rule matching
- Rule persistence
- Rule validation
"""

from .ignore_rules_manager import IgnoreRulesManager
from .rule_matcher import RuleMatcher
from .rule_persistence import RulePersistence
from .rule_validator import RuleValidator

__all__ = [
    'IgnoreRulesManager',
    'RuleMatcher',
    'RulePersistence',
    'RuleValidator'
]