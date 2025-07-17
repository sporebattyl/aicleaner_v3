# Privacy Config Manager for integration tests
from .privacy_config import PrivacyLevel

# Create simple config class for testing
class SimplePrivacyConfig:
    def __init__(self, level: PrivacyLevel):
        self.level = level
        self.enabled = True

class PrivacyConfigManager:
    """Simple config manager for privacy pipeline"""
    
    def __init__(self):
        self.configs = {
            "speed": SimplePrivacyConfig(PrivacyLevel.SPEED),
            "balanced": SimplePrivacyConfig(PrivacyLevel.BALANCED), 
            "paranoid": SimplePrivacyConfig(PrivacyLevel.PARANOID)
        }
    
    def get_config(self, level_name: str):
        """Get config for specified privacy level"""
        return self.configs.get(level_name, self.configs["balanced"])