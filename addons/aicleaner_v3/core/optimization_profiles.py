"""
Optimization Profiles for AICleaner Phase 3C.2
Predefined performance profiles for different use cases and hardware configurations.
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import json
import os

try:
    from core.local_model_manager import QuantizationLevel, CompressionType, OptimizationConfig
    from integrations.ollama_client import OptimizationOptions
    DEPENDENCIES_AVAILABLE = True
except ImportError:
    DEPENDENCIES_AVAILABLE = False


class ProfileCategory(Enum):
    """Categories of optimization profiles."""
    HARDWARE_BASED = "hardware_based"
    USE_CASE_BASED = "use_case_based"
    PERFORMANCE_BASED = "performance_based"
    RESOURCE_BASED = "resource_based"


class HardwareType(Enum):
    """Hardware configuration types."""
    LOW_END = "low_end"          # Limited CPU/RAM, no GPU
    MEDIUM_END = "medium_end"    # Decent CPU/RAM, optional GPU
    HIGH_END = "high_end"        # Powerful CPU/RAM, dedicated GPU
    SERVER_GRADE = "server_grade" # Server hardware with multiple GPUs


class UseCase(Enum):
    """Use case scenarios."""
    REAL_TIME = "real_time"           # Real-time analysis, low latency priority
    BATCH_PROCESSING = "batch_processing"  # Batch processing, throughput priority
    INTERACTIVE = "interactive"       # Interactive use, balanced performance
    BACKGROUND = "background"         # Background processing, resource efficiency
    DEMO = "demo"                    # Demo/presentation, reliability priority


@dataclass
class OptimizationProfile:
    """Complete optimization profile definition."""
    profile_id: str
    name: str
    description: str
    category: ProfileCategory
    target_hardware: Optional[HardwareType] = None
    target_use_case: Optional[UseCase] = None
    
    # Model optimization settings
    quantization_level: QuantizationLevel = QuantizationLevel.DYNAMIC
    compression_type: CompressionType = CompressionType.NONE
    enable_gpu_acceleration: bool = False
    memory_optimization: bool = True
    auto_optimize: bool = True
    
    # Resource limits
    max_memory_mb: int = 4096
    max_cpu_percent: int = 80
    max_gpu_memory_percent: int = 80
    
    # Performance tuning
    context_window_size: int = 2048
    batch_size: int = 1
    num_predict: int = 512
    temperature: float = 0.1
    top_p: float = 0.9
    
    # Monitoring and alerts
    enable_monitoring: bool = True
    alert_thresholds: Dict[str, float] = None
    
    # Advanced settings
    cache_enabled: bool = True
    cache_ttl_minutes: int = 5
    optimization_threshold_mb: float = 2048
    
    # Metadata
    created_by: str = "system"
    version: str = "1.0"
    tags: List[str] = None

    def __post_init__(self):
        """Initialize default values after creation."""
        if self.alert_thresholds is None:
            self.alert_thresholds = {
                "memory_usage_percent": 90,
                "cpu_usage_percent": 95,
                "response_time_seconds": 30
            }
        
        if self.tags is None:
            self.tags = []


class OptimizationProfileManager:
    """
    Manager for optimization profiles with predefined configurations.
    
    Features:
    - Predefined profiles for common scenarios
    - Hardware-specific optimizations
    - Use-case optimized configurations
    - Profile inheritance and customization
    - Dynamic profile selection
    - Profile validation and testing
    """
    
    def __init__(self, data_path: str = "/data/optimization_profiles"):
        """
        Initialize Optimization Profile Manager.
        
        Args:
            data_path: Path to store profile data
        """
        self.logger = logging.getLogger(__name__)
        self.data_path = data_path
        
        # Ensure data directory exists
        os.makedirs(data_path, exist_ok=True)
        
        # Profile storage
        self.profiles: Dict[str, OptimizationProfile] = {}
        self.active_profile_id: Optional[str] = None
        
        # Initialize predefined profiles
        self._create_predefined_profiles()
        
        # Load custom profiles
        self._load_custom_profiles()
        
        self.logger.info("Optimization Profile Manager initialized")

    def _create_predefined_profiles(self):
        """Create predefined optimization profiles."""
        
        # Hardware-based profiles
        self._create_hardware_profiles()
        
        # Use-case based profiles
        self._create_use_case_profiles()
        
        # Performance-based profiles
        self._create_performance_profiles()
        
        # Resource-based profiles
        self._create_resource_profiles()

    def _create_hardware_profiles(self):
        """Create hardware-specific optimization profiles."""
        
        # Low-end hardware profile
        self.add_profile(OptimizationProfile(
            profile_id="hardware_low_end",
            name="Low-End Hardware",
            description="Optimized for systems with limited CPU/RAM and no GPU",
            category=ProfileCategory.HARDWARE_BASED,
            target_hardware=HardwareType.LOW_END,
            quantization_level=QuantizationLevel.INT4,
            compression_type=CompressionType.GZIP,
            enable_gpu_acceleration=False,
            memory_optimization=True,
            max_memory_mb=2048,
            max_cpu_percent=70,
            context_window_size=1024,
            batch_size=1,
            num_predict=256,
            cache_enabled=True,
            cache_ttl_minutes=10,
            alert_thresholds={
                "memory_usage_percent": 85,
                "cpu_usage_percent": 80,
                "response_time_seconds": 60
            },
            tags=["low-resource", "conservative", "stable"]
        ))
        
        # Medium-end hardware profile
        self.add_profile(OptimizationProfile(
            profile_id="hardware_medium_end",
            name="Medium-End Hardware",
            description="Balanced optimization for decent CPU/RAM with optional GPU",
            category=ProfileCategory.HARDWARE_BASED,
            target_hardware=HardwareType.MEDIUM_END,
            quantization_level=QuantizationLevel.INT8,
            compression_type=CompressionType.NONE,
            enable_gpu_acceleration=True,
            memory_optimization=True,
            max_memory_mb=4096,
            max_cpu_percent=80,
            context_window_size=2048,
            batch_size=2,
            num_predict=512,
            tags=["balanced", "moderate-performance"]
        ))
        
        # High-end hardware profile
        self.add_profile(OptimizationProfile(
            profile_id="hardware_high_end",
            name="High-End Hardware",
            description="Performance-focused for powerful CPU/RAM with dedicated GPU",
            category=ProfileCategory.HARDWARE_BASED,
            target_hardware=HardwareType.HIGH_END,
            quantization_level=QuantizationLevel.FP16,
            compression_type=CompressionType.NONE,
            enable_gpu_acceleration=True,
            memory_optimization=False,
            max_memory_mb=8192,
            max_cpu_percent=90,
            max_gpu_memory_percent=90,
            context_window_size=4096,
            batch_size=4,
            num_predict=1024,
            cache_ttl_minutes=2,
            alert_thresholds={
                "memory_usage_percent": 95,
                "cpu_usage_percent": 95,
                "response_time_seconds": 15
            },
            tags=["high-performance", "gpu-accelerated", "fast"]
        ))

    def _create_use_case_profiles(self):
        """Create use-case specific optimization profiles."""
        
        # Real-time analysis profile
        self.add_profile(OptimizationProfile(
            profile_id="use_case_real_time",
            name="Real-Time Analysis",
            description="Optimized for real-time image analysis with low latency",
            category=ProfileCategory.USE_CASE_BASED,
            target_use_case=UseCase.REAL_TIME,
            quantization_level=QuantizationLevel.INT8,
            enable_gpu_acceleration=True,
            context_window_size=1024,
            batch_size=1,
            num_predict=256,
            temperature=0.05,  # Lower temperature for consistency
            cache_enabled=True,
            cache_ttl_minutes=1,  # Short cache for real-time
            alert_thresholds={
                "response_time_seconds": 5,  # Strict latency requirement
                "memory_usage_percent": 90,
                "cpu_usage_percent": 85
            },
            tags=["real-time", "low-latency", "responsive"]
        ))
        
        # Batch processing profile
        self.add_profile(OptimizationProfile(
            profile_id="use_case_batch",
            name="Batch Processing",
            description="Optimized for batch processing with high throughput",
            category=ProfileCategory.USE_CASE_BASED,
            target_use_case=UseCase.BATCH_PROCESSING,
            quantization_level=QuantizationLevel.DYNAMIC,
            enable_gpu_acceleration=True,
            context_window_size=2048,
            batch_size=8,  # Larger batch size for throughput
            num_predict=512,
            cache_enabled=False,  # Disable cache for batch processing
            alert_thresholds={
                "memory_usage_percent": 95,
                "cpu_usage_percent": 95,
                "response_time_seconds": 120  # More lenient for batch
            },
            tags=["batch", "throughput", "efficient"]
        ))
        
        # Interactive use profile
        self.add_profile(OptimizationProfile(
            profile_id="use_case_interactive",
            name="Interactive Use",
            description="Balanced optimization for interactive applications",
            category=ProfileCategory.USE_CASE_BASED,
            target_use_case=UseCase.INTERACTIVE,
            quantization_level=QuantizationLevel.DYNAMIC,
            enable_gpu_acceleration=True,
            context_window_size=2048,
            batch_size=2,
            num_predict=512,
            temperature=0.1,
            cache_enabled=True,
            cache_ttl_minutes=5,
            tags=["interactive", "balanced", "user-friendly"]
        ))

    def _create_performance_profiles(self):
        """Create performance-focused optimization profiles."""
        
        # Maximum performance profile
        self.add_profile(OptimizationProfile(
            profile_id="performance_maximum",
            name="Maximum Performance",
            description="Aggressive optimization for maximum performance",
            category=ProfileCategory.PERFORMANCE_BASED,
            quantization_level=QuantizationLevel.NONE,  # No quantization for max quality
            compression_type=CompressionType.NONE,
            enable_gpu_acceleration=True,
            memory_optimization=False,
            max_memory_mb=16384,  # Allow high memory usage
            max_cpu_percent=95,
            context_window_size=4096,
            batch_size=8,
            num_predict=1024,
            cache_enabled=True,
            cache_ttl_minutes=1,
            tags=["maximum-performance", "aggressive", "resource-intensive"]
        ))
        
        # Balanced performance profile
        self.add_profile(OptimizationProfile(
            profile_id="performance_balanced",
            name="Balanced Performance",
            description="Balanced optimization between performance and resource usage",
            category=ProfileCategory.PERFORMANCE_BASED,
            quantization_level=QuantizationLevel.DYNAMIC,
            compression_type=CompressionType.NONE,
            enable_gpu_acceleration=True,
            memory_optimization=True,
            max_memory_mb=4096,
            max_cpu_percent=80,
            context_window_size=2048,
            batch_size=2,
            num_predict=512,
            tags=["balanced", "moderate", "stable"]
        ))

    def _create_resource_profiles(self):
        """Create resource-focused optimization profiles."""
        
        # Resource efficient profile
        self.add_profile(OptimizationProfile(
            profile_id="resource_efficient",
            name="Resource Efficient",
            description="Optimized for minimal resource usage",
            category=ProfileCategory.RESOURCE_BASED,
            quantization_level=QuantizationLevel.INT4,
            compression_type=CompressionType.GZIP,
            enable_gpu_acceleration=False,
            memory_optimization=True,
            max_memory_mb=1024,
            max_cpu_percent=60,
            context_window_size=512,
            batch_size=1,
            num_predict=128,
            cache_enabled=True,
            cache_ttl_minutes=15,  # Longer cache to reduce processing
            alert_thresholds={
                "memory_usage_percent": 80,
                "cpu_usage_percent": 70,
                "response_time_seconds": 90
            },
            tags=["resource-efficient", "minimal", "conservative"]
        ))

    def add_profile(self, profile: OptimizationProfile):
        """Add a new optimization profile."""
        self.profiles[profile.profile_id] = profile
        self.logger.debug(f"Added optimization profile: {profile.name}")

    def get_profile(self, profile_id: str) -> Optional[OptimizationProfile]:
        """Get an optimization profile by ID."""
        return self.profiles.get(profile_id)

    def list_profiles(self, category: Optional[ProfileCategory] = None,
                     hardware_type: Optional[HardwareType] = None,
                     use_case: Optional[UseCase] = None) -> List[OptimizationProfile]:
        """
        List optimization profiles with optional filtering.
        
        Args:
            category: Filter by profile category
            hardware_type: Filter by target hardware type
            use_case: Filter by target use case
            
        Returns:
            List of matching profiles
        """
        profiles = list(self.profiles.values())
        
        if category:
            profiles = [p for p in profiles if p.category == category]
        
        if hardware_type:
            profiles = [p for p in profiles if p.target_hardware == hardware_type]
        
        if use_case:
            profiles = [p for p in profiles if p.target_use_case == use_case]
        
        return profiles

    def recommend_profile(self, system_info: Dict[str, Any]) -> Optional[OptimizationProfile]:
        """
        Recommend an optimization profile based on system information.
        
        Args:
            system_info: Dictionary with system information
            
        Returns:
            Recommended optimization profile
        """
        try:
            # Extract system characteristics
            memory_gb = system_info.get("memory_gb", 4)
            cpu_cores = system_info.get("cpu_cores", 4)
            has_gpu = system_info.get("has_gpu", False)
            use_case = system_info.get("use_case", "interactive")
            
            # Determine hardware category
            if memory_gb < 4 or cpu_cores < 4:
                hardware_type = HardwareType.LOW_END
            elif memory_gb < 16 or cpu_cores < 8:
                hardware_type = HardwareType.MEDIUM_END
            else:
                hardware_type = HardwareType.HIGH_END
            
            # Find matching profiles
            candidates = self.list_profiles(hardware_type=hardware_type)
            
            if not candidates:
                # Fallback to balanced profile
                return self.get_profile("performance_balanced")
            
            # Prefer use-case specific profiles if available
            use_case_matches = [p for p in candidates if p.target_use_case and p.target_use_case.value == use_case]
            
            if use_case_matches:
                return use_case_matches[0]
            
            # Return first hardware match
            return candidates[0]
            
        except Exception as e:
            self.logger.error(f"Error recommending profile: {e}")
            return self.get_profile("performance_balanced")

    def apply_profile(self, profile_id: str) -> bool:
        """
        Apply an optimization profile as the active configuration.
        
        Args:
            profile_id: ID of the profile to apply
            
        Returns:
            True if profile was applied successfully
        """
        profile = self.get_profile(profile_id)
        if not profile:
            self.logger.error(f"Profile {profile_id} not found")
            return False
        
        try:
            self.active_profile_id = profile_id
            self.logger.info(f"Applied optimization profile: {profile.name}")
            
            # In a real implementation, this would update the actual system configuration
            # For now, just log the change
            self._log_profile_application(profile)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error applying profile {profile_id}: {e}")
            return False

    def get_active_profile(self) -> Optional[OptimizationProfile]:
        """Get the currently active optimization profile."""
        if self.active_profile_id:
            return self.get_profile(self.active_profile_id)
        return None

    def create_custom_profile(self, base_profile_id: str, customizations: Dict[str, Any],
                            new_profile_id: str, name: str, description: str) -> OptimizationProfile:
        """
        Create a custom profile based on an existing profile with modifications.
        
        Args:
            base_profile_id: ID of the base profile to customize
            customizations: Dictionary of parameter overrides
            new_profile_id: ID for the new custom profile
            name: Name for the new profile
            description: Description for the new profile
            
        Returns:
            New custom optimization profile
        """
        base_profile = self.get_profile(base_profile_id)
        if not base_profile:
            raise ValueError(f"Base profile {base_profile_id} not found")
        
        # Create a copy of the base profile
        custom_profile_data = asdict(base_profile)
        
        # Apply customizations
        custom_profile_data.update(customizations)
        custom_profile_data.update({
            "profile_id": new_profile_id,
            "name": name,
            "description": description,
            "created_by": "user",
            "tags": custom_profile_data.get("tags", []) + ["custom"]
        })
        
        # Create new profile
        custom_profile = OptimizationProfile(**custom_profile_data)
        self.add_profile(custom_profile)
        
        # Save custom profile
        self._save_custom_profile(custom_profile)
        
        return custom_profile

    def _log_profile_application(self, profile: OptimizationProfile):
        """Log the application of a profile."""
        self.logger.info(f"Profile Applied: {profile.name}")
        self.logger.info(f"  Quantization: {profile.quantization_level.value}")
        self.logger.info(f"  GPU Acceleration: {profile.enable_gpu_acceleration}")
        self.logger.info(f"  Memory Limit: {profile.max_memory_mb}MB")
        self.logger.info(f"  Context Window: {profile.context_window_size}")
        self.logger.info(f"  Batch Size: {profile.batch_size}")

    def _save_custom_profile(self, profile: OptimizationProfile):
        """Save a custom profile to disk."""
        try:
            filename = f"custom_profile_{profile.profile_id}.json"
            filepath = os.path.join(self.data_path, filename)
            
            with open(filepath, 'w') as f:
                json.dump(asdict(profile), f, indent=2, default=str)
                
        except Exception as e:
            self.logger.error(f"Error saving custom profile: {e}")

    def _load_custom_profiles(self):
        """Load custom profiles from disk."""
        try:
            for filename in os.listdir(self.data_path):
                if filename.startswith("custom_profile_") and filename.endswith(".json"):
                    filepath = os.path.join(self.data_path, filename)
                    
                    with open(filepath, 'r') as f:
                        profile_data = json.load(f)
                    
                    # Convert enum strings back to enums
                    if DEPENDENCIES_AVAILABLE:
                        profile_data["quantization_level"] = QuantizationLevel(profile_data["quantization_level"])
                        profile_data["compression_type"] = CompressionType(profile_data["compression_type"])
                        profile_data["category"] = ProfileCategory(profile_data["category"])
                        
                        if profile_data.get("target_hardware"):
                            profile_data["target_hardware"] = HardwareType(profile_data["target_hardware"])
                        
                        if profile_data.get("target_use_case"):
                            profile_data["target_use_case"] = UseCase(profile_data["target_use_case"])
                    
                    profile = OptimizationProfile(**profile_data)
                    self.add_profile(profile)
                    
        except Exception as e:
            self.logger.error(f"Error loading custom profiles: {e}")

    def get_profile_summary(self) -> Dict[str, Any]:
        """Get summary of all available profiles."""
        return {
            "total_profiles": len(self.profiles),
            "active_profile": self.active_profile_id,
            "categories": {
                category.value: len([p for p in self.profiles.values() if p.category == category])
                for category in ProfileCategory
            },
            "hardware_types": {
                hw_type.value: len([p for p in self.profiles.values() if p.target_hardware == hw_type])
                for hw_type in HardwareType
            },
            "use_cases": {
                use_case.value: len([p for p in self.profiles.values() if p.target_use_case == use_case])
                for use_case in UseCase
            }
        }
