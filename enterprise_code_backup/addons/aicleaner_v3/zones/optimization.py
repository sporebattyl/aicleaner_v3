"""
Phase 3B: Zone Optimization Engine
ML-based optimization for zone performance and energy efficiency.
"""

import logging
import asyncio
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass

from .models import Zone, Device, Rule, DeviceType, PollingFrequency
from .logger import setup_logger
from .utils import calculate_weighted_average, exponential_moving_average, normalize_score


@dataclass
class OptimizationResult:
    """Optimization result container."""
    zone_id: str
    optimization_type: str
    improvements: Dict[str, Any]
    score_before: float
    score_after: float
    recommendations: List[str]
    execution_time_ms: float


class ZoneOptimizationEngine:
    """
    ML-based optimization engine for zone performance and efficiency.
    
    Provides intelligent optimization of device configurations, automation rules,
    and energy consumption patterns using machine learning algorithms.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize optimization engine.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.logger = setup_logger(__name__)
        
        # Optimization parameters
        self.optimization_weights = {
            'energy_efficiency': 0.3,
            'performance': 0.3,
            'reliability': 0.2,
            'user_satisfaction': 0.2
        }
        
        # Historical data for learning
        self.performance_history: Dict[str, List[float]] = {}
        self.energy_history: Dict[str, List[float]] = {}
        self.usage_patterns: Dict[str, Dict[str, Any]] = {}
        
        # Optimization thresholds
        self.min_improvement_threshold = 0.05  # 5% minimum improvement
        self.optimization_cooldown_hours = 6   # Minimum time between optimizations
        
        self.logger.info("Zone Optimization Engine initialized")
    
    async def optimize(self, zone: Zone) -> Optional[Zone]:
        """
        Perform comprehensive zone optimization.
        
        Args:
            zone: Zone to optimize
            
        Returns:
            Optimized zone or None if optimization failed
        """
        start_time = datetime.now()
        initial_score = self._calculate_zone_score(zone)
        
        try:
            self.logger.info(f"Starting optimization for zone '{zone.name}' (score: {initial_score:.3f})")
            
            # Check optimization cooldown
            if not self._can_optimize(zone):
                self.logger.info(f"Zone '{zone.name}' is in optimization cooldown")
                return None
            
            # Create optimized zone copy
            optimized_zone = Zone(**zone.dict())
            
            # Apply different optimization strategies
            optimization_results = []
            
            # 1. Device polling optimization
            device_result = await self._optimize_device_polling(optimized_zone)
            if device_result:
                optimization_results.append(device_result)
            
            # 2. Energy consumption optimization
            energy_result = await self._optimize_energy_consumption(optimized_zone)
            if energy_result:
                optimization_results.append(energy_result)
            
            # 3. Automation rule optimization
            rule_result = await self._optimize_automation_rules(optimized_zone)
            if rule_result:
                optimization_results.append(rule_result)
            
            # 4. Device placement optimization
            placement_result = await self._optimize_device_placement(optimized_zone)
            if placement_result:
                optimization_results.append(placement_result)
            
            # Calculate final score
            final_score = self._calculate_zone_score(optimized_zone)
            improvement = final_score - initial_score
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            if improvement >= self.min_improvement_threshold:
                # Update zone metrics
                optimized_zone.performance_metrics.optimization_score = final_score
                optimized_zone.performance_metrics.last_optimization = datetime.now()
                optimized_zone.last_modified = datetime.now()
                
                # Log optimization success
                self.logger.info(
                    f"Zone '{zone.name}' optimized successfully. "
                    f"Score improved from {initial_score:.3f} to {final_score:.3f} "
                    f"({improvement:.3f} improvement) in {execution_time:.1f}ms"
                )
                
                # Store optimization history
                self._record_optimization_result(zone.id, initial_score, final_score, optimization_results)
                
                return optimized_zone
            else:
                self.logger.info(
                    f"Zone '{zone.name}' optimization yielded minimal improvement "
                    f"({improvement:.3f} < {self.min_improvement_threshold})"
                )
                return None
        
        except Exception as e:
            self.logger.error(f"Optimization failed for zone '{zone.name}': {e}")
            return None
    
    async def _optimize_device_polling(self, zone: Zone) -> Optional[OptimizationResult]:
        """Optimize device polling frequencies for better performance."""
        improvements = {}
        recommendations = []
        
        try:
            for device in zone.devices:
                if not device.is_active:
                    continue
                
                # Analyze device usage patterns
                usage_score = self._get_device_usage_score(device)
                current_frequency = device.polling_frequency
                
                # Recommend optimal polling frequency
                optimal_frequency = self._calculate_optimal_polling(device, usage_score)
                
                if optimal_frequency != current_frequency:
                    device.polling_frequency = optimal_frequency
                    improvements[device.id] = {
                        'from': current_frequency,
                        'to': optimal_frequency,
                        'reason': f'Usage score: {usage_score:.2f}'
                    }
                    recommendations.append(
                        f"Device '{device.name}': {current_frequency} → {optimal_frequency}"
                    )
            
            if improvements:
                return OptimizationResult(
                    zone_id=zone.id,
                    optimization_type='device_polling',
                    improvements=improvements,
                    score_before=0.0,  # Would calculate specific metric
                    score_after=0.0,   # Would calculate specific metric
                    recommendations=recommendations,
                    execution_time_ms=0.0
                )
        
        except Exception as e:
            self.logger.error(f"Device polling optimization error: {e}")
        
        return None
    
    async def _optimize_energy_consumption(self, zone: Zone) -> Optional[OptimizationResult]:
        """Optimize energy consumption patterns."""
        improvements = {}
        recommendations = []
        
        try:
            # Analyze current energy consumption
            total_consumption = zone.calculate_energy_consumption()
            high_consumption_devices = []
            
            for device in zone.devices:
                if device.power_consumption and device.power_consumption > 50:  # > 50W
                    high_consumption_devices.append(device)
            
            # Optimize high-consumption devices
            for device in high_consumption_devices:
                # Check if device can be optimized
                if device.type in [DeviceType.LIGHT, DeviceType.CLIMATE]:
                    # Suggest dimming for lights during low activity periods
                    if device.type == DeviceType.LIGHT:
                        current_brightness = device.current_state.get('brightness', 255)
                        if current_brightness > 200:  # Very bright
                            optimal_brightness = min(current_brightness, 180)
                            improvements[device.id] = {
                                'optimization': 'brightness_reduction',
                                'from': current_brightness,
                                'to': optimal_brightness,
                                'energy_savings_watts': device.power_consumption * 0.2
                            }
                            recommendations.append(
                                f"Reduce '{device.name}' brightness to save ~{device.power_consumption * 0.2:.1f}W"
                            )
                    
                    # Temperature optimization for climate devices
                    elif device.type == DeviceType.CLIMATE:
                        current_temp = device.current_state.get('target_temperature', 21)
                        # Suggest 1-2 degree adjustment for energy savings
                        optimal_temp = current_temp - 1 if current_temp > 20 else current_temp + 1
                        improvements[device.id] = {
                            'optimization': 'temperature_adjustment',
                            'from': current_temp,
                            'to': optimal_temp,
                            'energy_savings_watts': device.power_consumption * 0.15
                        }
                        recommendations.append(
                            f"Adjust '{device.name}' temperature by 1°C to save ~{device.power_consumption * 0.15:.1f}W"
                        )
            
            if improvements:
                return OptimizationResult(
                    zone_id=zone.id,
                    optimization_type='energy_consumption',
                    improvements=improvements,
                    score_before=total_consumption,
                    score_after=total_consumption * 0.85,  # Estimated 15% reduction
                    recommendations=recommendations,
                    execution_time_ms=0.0
                )
        
        except Exception as e:
            self.logger.error(f"Energy optimization error: {e}")
        
        return None
    
    async def _optimize_automation_rules(self, zone: Zone) -> Optional[OptimizationResult]:
        """Optimize automation rules for better performance."""
        improvements = {}
        recommendations = []
        
        try:
            # Analyze rule performance
            for rule in zone.rules:
                if not rule.enabled:
                    continue
                
                # Check for rules with low success rates
                if rule.success_rate < 0.8 and rule.execution_count > 5:
                    # Suggest rule improvements
                    if rule.average_execution_time_ms > 1000:  # Slow rule
                        improvements[rule.id] = {
                            'issue': 'slow_execution',
                            'avg_time_ms': rule.average_execution_time_ms,
                            'recommendation': 'Add timeout or simplify condition'
                        }
                        recommendations.append(
                            f"Rule '{rule.name}' is slow ({rule.average_execution_time_ms:.1f}ms avg)"
                        )
                    
                    if rule.success_rate < 0.5:  # Very unreliable
                        improvements[rule.id] = {
                            'issue': 'low_reliability',
                            'success_rate': rule.success_rate,
                            'recommendation': 'Review condition logic or disable'
                        }
                        recommendations.append(
                            f"Rule '{rule.name}' has low success rate ({rule.success_rate:.1%})"
                        )
                
                # Check for conflicting rules
                for other_rule in zone.rules:
                    if (other_rule.id != rule.id and other_rule.enabled and 
                        self._rules_conflict(rule, other_rule)):
                        improvements[f"{rule.id}_conflict"] = {
                            'issue': 'rule_conflict',
                            'conflicting_with': other_rule.id,
                            'recommendation': 'Adjust priority or conditions'
                        }
                        recommendations.append(
                            f"Rules '{rule.name}' and '{other_rule.name}' may conflict"
                        )
            
            # Suggest rule consolidation
            if len(zone.rules) > 10:
                similar_rules = self._find_similar_rules(zone.rules)
                if similar_rules:
                    improvements['rule_consolidation'] = {
                        'similar_rules': similar_rules,
                        'recommendation': 'Consider consolidating similar rules'
                    }
                    recommendations.append(f"Found {len(similar_rules)} rule groups that could be consolidated")
            
            if improvements:
                return OptimizationResult(
                    zone_id=zone.id,
                    optimization_type='automation_rules',
                    improvements=improvements,
                    score_before=0.0,
                    score_after=0.0,
                    recommendations=recommendations,
                    execution_time_ms=0.0
                )
        
        except Exception as e:
            self.logger.error(f"Rule optimization error: {e}")
        
        return None
    
    async def _optimize_device_placement(self, zone: Zone) -> Optional[OptimizationResult]:
        """Optimize logical device placement and grouping."""
        improvements = {}
        recommendations = []
        
        try:
            # Group devices by type and usage patterns
            device_groups = self._analyze_device_relationships(zone.devices)
            
            # Suggest optimal groupings
            for group_type, devices in device_groups.items():
                if len(devices) > 1:
                    # Check if devices in group have similar configurations
                    inconsistencies = self._find_configuration_inconsistencies(devices)
                    if inconsistencies:
                        improvements[f"{group_type}_consistency"] = {
                            'devices': [d.id for d in devices],
                            'inconsistencies': inconsistencies,
                            'recommendation': 'Standardize configuration across similar devices'
                        }
                        recommendations.append(
                            f"Standardize {group_type} device configurations ({len(devices)} devices)"
                        )
            
            # Suggest device role assignments
            unassigned_devices = [d for d in zone.devices if not d.zone_role]
            if unassigned_devices:
                for device in unassigned_devices:
                    suggested_role = self._suggest_device_role(device, zone)
                    if suggested_role:
                        device.zone_role = suggested_role
                        improvements[device.id] = {
                            'optimization': 'role_assignment',
                            'assigned_role': suggested_role
                        }
                        recommendations.append(
                            f"Assigned role '{suggested_role}' to device '{device.name}'"
                        )
            
            if improvements:
                return OptimizationResult(
                    zone_id=zone.id,
                    optimization_type='device_placement',
                    improvements=improvements,
                    score_before=0.0,
                    score_after=0.0,
                    recommendations=recommendations,
                    execution_time_ms=0.0
                )
        
        except Exception as e:
            self.logger.error(f"Device placement optimization error: {e}")
        
        return None
    
    def _calculate_zone_score(self, zone: Zone) -> float:
        """Calculate overall zone optimization score."""
        try:
            # Performance metrics
            device_health = len(zone.get_active_devices()) / max(len(zone.devices), 1)
            rule_health = sum(r.success_rate for r in zone.rules) / max(len(zone.rules), 1)
            
            # Energy efficiency
            total_consumption = zone.calculate_energy_consumption()
            energy_efficiency = 1.0 / (1.0 + total_consumption / 1000)  # Normalize
            
            # Reliability
            avg_device_reliability = sum(d.reliability_score for d in zone.devices) / max(len(zone.devices), 1)
            
            # Response time (inverse for scoring)
            active_devices = zone.get_active_devices()
            if active_devices:
                avg_response_time = sum(d.response_time_ms or 100 for d in active_devices) / len(active_devices)
                response_score = 1.0 / (1.0 + avg_response_time / 1000)
            else:
                response_score = 1.0
            
            # Weighted score
            score = (
                device_health * self.optimization_weights['performance'] +
                energy_efficiency * self.optimization_weights['energy_efficiency'] +
                avg_device_reliability * self.optimization_weights['reliability'] +
                response_score * self.optimization_weights['user_satisfaction']
            )
            
            return normalize_score(score, 0.0, 1.0)
        
        except Exception as e:
            self.logger.error(f"Zone score calculation error: {e}")
            return 0.0
    
    def _can_optimize(self, zone: Zone) -> bool:
        """Check if zone can be optimized (cooldown check)."""
        if not zone.performance_metrics.last_optimization:
            return True
        
        time_since_last = datetime.now() - zone.performance_metrics.last_optimization
        return time_since_last.total_seconds() >= self.optimization_cooldown_hours * 3600
    
    def _get_device_usage_score(self, device: Device) -> float:
        """Calculate device usage score for optimization decisions."""
        # Simplified usage scoring - in production would use historical data
        base_score = 0.5
        
        # Factor in device type
        if device.type in [DeviceType.SENSOR, DeviceType.CAMERA]:
            base_score += 0.3  # Sensors need more frequent updates
        elif device.type in [DeviceType.LIGHT, DeviceType.SWITCH]:
            base_score += 0.1  # Lights change less frequently
        
        # Factor in reliability
        base_score += device.reliability_score * 0.2
        
        # Factor in last seen time
        if device.last_seen:
            hours_since_seen = (datetime.now() - device.last_seen).total_seconds() / 3600
            if hours_since_seen < 1:
                base_score += 0.2  # Recently active
        
        return normalize_score(base_score, 0.0, 1.0)
    
    def _calculate_optimal_polling(self, device: Device, usage_score: float) -> PollingFrequency:
        """Calculate optimal polling frequency for device."""
        if usage_score > 0.8:
            return PollingFrequency.HIGH
        elif usage_score > 0.6:
            return PollingFrequency.NORMAL
        elif usage_score > 0.3:
            return PollingFrequency.LOW
        else:
            return PollingFrequency.LOW
    
    def _rules_conflict(self, rule1: Rule, rule2: Rule) -> bool:
        """Check if two rules potentially conflict."""
        # Simplified conflict detection
        return (rule1.action == rule2.action and 
                rule1.parameters.get('device_id') == rule2.parameters.get('device_id'))
    
    def _find_similar_rules(self, rules: List[Rule]) -> List[List[str]]:
        """Find groups of similar rules that could be consolidated."""
        similar_groups = []
        
        # Group by action type
        action_groups = {}
        for rule in rules:
            action_type = rule.action.split('.')[0] if '.' in rule.action else rule.action
            if action_type not in action_groups:
                action_groups[action_type] = []
            action_groups[action_type].append(rule.id)
        
        # Find groups with multiple rules
        for action_type, rule_ids in action_groups.items():
            if len(rule_ids) > 2:
                similar_groups.append(rule_ids)
        
        return similar_groups
    
    def _analyze_device_relationships(self, devices: List[Device]) -> Dict[str, List[Device]]:
        """Analyze relationships between devices for optimization."""
        groups = {}
        
        for device in devices:
            device_type = device.type.value
            if device_type not in groups:
                groups[device_type] = []
            groups[device_type].append(device)
        
        return groups
    
    def _find_configuration_inconsistencies(self, devices: List[Device]) -> List[str]:
        """Find configuration inconsistencies among similar devices."""
        inconsistencies = []
        
        if len(devices) < 2:
            return inconsistencies
        
        # Check polling frequency consistency
        frequencies = [d.polling_frequency for d in devices]
        if len(set(frequencies)) > 1:
            inconsistencies.append("Inconsistent polling frequencies")
        
        # Check automation enablement
        auto_enabled = [d.automation_enabled for d in devices]
        if len(set(auto_enabled)) > 1:
            inconsistencies.append("Inconsistent automation enablement")
        
        return inconsistencies
    
    def _suggest_device_role(self, device: Device, zone: Zone) -> Optional[str]:
        """Suggest appropriate role for device within zone."""
        if device.type == DeviceType.LIGHT:
            # Check if it's the main light
            if 'main' in device.name.lower() or 'ceiling' in device.name.lower():
                return 'primary_lighting'
            else:
                return 'ambient_lighting'
        elif device.type == DeviceType.SENSOR:
            if 'temperature' in device.name.lower():
                return 'temperature_monitoring'
            elif 'motion' in device.name.lower():
                return 'presence_detection'
            else:
                return 'environmental_monitoring'
        elif device.type == DeviceType.CLIMATE:
            return 'climate_control'
        
        return None
    
    def _record_optimization_result(self, zone_id: str, score_before: float, 
                                  score_after: float, results: List[OptimizationResult]) -> None:
        """Record optimization result for learning."""
        if zone_id not in self.performance_history:
            self.performance_history[zone_id] = []
        
        self.performance_history[zone_id].append(score_after)
        
        # Keep only recent history
        if len(self.performance_history[zone_id]) > 100:
            self.performance_history[zone_id] = self.performance_history[zone_id][-50:]
    
    def get_optimization_recommendations(self, zone: Zone) -> List[str]:
        """Get optimization recommendations without applying changes."""
        recommendations = []
        
        try:
            # Analyze current state
            score = self._calculate_zone_score(zone)
            
            if score < 0.6:
                recommendations.append("Zone performance is below optimal - consider optimization")
            
            # Check device-specific recommendations
            inactive_devices = [d for d in zone.devices if not d.is_active]
            if inactive_devices:
                recommendations.append(f"{len(inactive_devices)} devices are inactive - check connectivity")
            
            # Check rule performance
            failed_rules = [r for r in zone.rules if r.success_rate < 0.8 and r.execution_count > 3]
            if failed_rules:
                recommendations.append(f"{len(failed_rules)} rules have low success rates - review configuration")
            
            # Energy recommendations
            high_consumption = zone.calculate_energy_consumption()
            if high_consumption > 500:  # >500W
                recommendations.append("High energy consumption detected - consider energy optimization")
            
        except Exception as e:
            self.logger.error(f"Error generating recommendations: {e}")
        
        return recommendations


# Example usage and testing
if __name__ == "__main__":
    import asyncio
    from .models import Zone, Device, Rule, DeviceType
    
    async def test_optimization_engine():
        """Test optimization engine functionality."""
        
        config = {}
        engine = ZoneOptimizationEngine(config)
        
        # Create test zone
        zone = Zone(
            id='test_zone',
            name='Test Zone',
            devices=[
                Device(
                    id='light1',
                    name='Main Light',
                    type=DeviceType.LIGHT,
                    power_consumption=60.0,
                    polling_frequency=PollingFrequency.HIGH,
                    reliability_score=0.9
                ),
                Device(
                    id='sensor1',
                    name='Temperature Sensor',
                    type=DeviceType.SENSOR,
                    polling_frequency=PollingFrequency.REALTIME,
                    reliability_score=0.95
                )
            ],
            rules=[
                Rule(
                    id='rule1',
                    name='Test Rule',
                    condition='time.is_after("18:00")',
                    action='device.turn_on',
                    success_rate=0.6,
                    execution_count=10
                )
            ]
        )
        
        # Test optimization
        print(f"Initial zone score: {engine._calculate_zone_score(zone):.3f}")
        
        optimized_zone = await engine.optimize(zone)
        if optimized_zone:
            print(f"Optimized zone score: {engine._calculate_zone_score(optimized_zone):.3f}")
        else:
            print("No optimization applied")
        
        # Test recommendations
        recommendations = engine.get_optimization_recommendations(zone)
        print(f"Recommendations: {recommendations}")
        
        print("Optimization engine test completed!")
    
    # Run test
    asyncio.run(test_optimization_engine())