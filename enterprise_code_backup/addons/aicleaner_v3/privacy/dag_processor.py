"""
DAG Processor for Privacy Pipeline
Implements configurable Directed Acyclic Graph for parallel privacy processing
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set, Callable, Tuple
from enum import Enum
import threading
import cv2
import numpy as np

from .privacy_config import PrivacyConfig, PrivacyLevel


class NodeStatus(Enum):
    """Status of processing nodes"""
    PENDING = "pending"
    RUNNING = "running" 
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class DetectionResult:
    """Result from a detection node"""
    node_type: str
    bounding_boxes: List[Tuple[int, int, int, int]]  # (x1, y1, x2, y2)
    confidences: List[float]
    labels: List[str]
    processing_time: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass 
class ProcessingContext:
    """Context shared between processing nodes"""
    original_image: np.ndarray
    image_path: str
    privacy_level: PrivacyLevel
    detection_results: Dict[str, DetectionResult] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    start_time: float = field(default_factory=time.time)


class ProcessingNode(ABC):
    """
    Abstract base class for processing nodes in the DAG
    """
    
    def __init__(self, node_id: str, config: PrivacyConfig):
        """
        Initialize processing node
        
        Args:
            node_id: Unique identifier for this node
            config: Privacy pipeline configuration
        """
        self.node_id = node_id
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{node_id}")
        
        self.status = NodeStatus.PENDING
        self.dependencies: Set[str] = set()
        self.dependents: Set[str] = set()
        self.processing_time: float = 0.0
        self.error_message: Optional[str] = None
        
        # Performance tracking
        self.execution_count = 0
        self.total_processing_time = 0.0
        self.average_processing_time = 0.0
    
    @abstractmethod
    async def process(self, context: ProcessingContext) -> Optional[DetectionResult]:
        """
        Process the context and return detection results
        
        Args:
            context: Processing context with image and metadata
            
        Returns:
            DetectionResult if successful, None if failed/skipped
        """
        pass
    
    def add_dependency(self, node_id: str):
        """Add a dependency on another node"""
        self.dependencies.add(node_id)
    
    def add_dependent(self, node_id: str):
        """Add a node that depends on this one"""
        self.dependents.add(node_id)
    
    def can_execute(self, completed_nodes: Set[str]) -> bool:
        """Check if this node can execute based on dependencies"""
        return self.dependencies.issubset(completed_nodes)
    
    def is_enabled_for_level(self, privacy_level: PrivacyLevel) -> bool:
        """Check if this node should be enabled for the given privacy level"""
        # Default implementation - override in subclasses for level-specific logic
        return True
    
    def _update_performance_stats(self, processing_time: float):
        """Update performance statistics"""
        self.execution_count += 1
        self.total_processing_time += processing_time
        self.average_processing_time = self.total_processing_time / self.execution_count
        self.processing_time = processing_time


class DAGProcessor:
    """
    Configurable DAG processor for privacy pipeline
    
    Features:
    - Parallel execution of independent nodes
    - Dependency management
    - Privacy level-based node selection
    - Performance monitoring
    - Error handling and recovery
    """
    
    def __init__(self, config: PrivacyConfig):
        """
        Initialize DAG processor
        
        Args:
            config: Privacy pipeline configuration
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Node management
        self.nodes: Dict[str, ProcessingNode] = {}
        self.execution_order: List[str] = []
        
        # Execution state
        self.completed_nodes: Set[str] = set()
        self.failed_nodes: Set[str] = set()
        self.running_nodes: Set[str] = set()
        
        # Performance tracking
        self.execution_stats = {
            'total_executions': 0,
            'successful_executions': 0,
            'failed_executions': 0,
            'average_execution_time': 0.0,
            'node_performance': {}
        }
        
        self.logger.info(f"DAG Processor initialized for {config.level.value} privacy level")
    
    def add_node(self, node: ProcessingNode):
        """
        Add a processing node to the DAG
        
        Args:
            node: ProcessingNode to add
        """
        if node.node_id in self.nodes:
            raise ValueError(f"Node {node.node_id} already exists")
        
        self.nodes[node.node_id] = node
        self.logger.debug(f"Added node: {node.node_id}")
    
    def add_dependency(self, dependent_node_id: str, dependency_node_id: str):
        """
        Add a dependency relationship between nodes
        
        Args:
            dependent_node_id: Node that depends on the other
            dependency_node_id: Node that must complete first
        """
        if dependent_node_id not in self.nodes:
            raise ValueError(f"Dependent node {dependent_node_id} not found")
        if dependency_node_id not in self.nodes:
            raise ValueError(f"Dependency node {dependency_node_id} not found")
        
        self.nodes[dependent_node_id].add_dependency(dependency_node_id)
        self.nodes[dependency_node_id].add_dependent(dependent_node_id)
        
        self.logger.debug(f"Added dependency: {dependent_node_id} depends on {dependency_node_id}")
    
    def build_execution_graph(self, privacy_level: PrivacyLevel) -> List[List[str]]:
        """
        Build execution graph based on dependencies and privacy level
        
        Args:
            privacy_level: Current privacy level
            
        Returns:
            List of execution stages, each containing nodes that can run in parallel
        """
        # Filter nodes based on privacy level
        enabled_nodes = {
            node_id: node for node_id, node in self.nodes.items()
            if node.is_enabled_for_level(privacy_level)
        }
        
        if not enabled_nodes:
            return []
        
        # Topological sort to determine execution order
        execution_stages = []
        remaining_nodes = set(enabled_nodes.keys())
        completed_deps = set()
        
        while remaining_nodes:
            # Find nodes with all dependencies satisfied
            ready_nodes = [
                node_id for node_id in remaining_nodes
                if enabled_nodes[node_id].can_execute(completed_deps)
            ]
            
            if not ready_nodes:
                # Circular dependency detected
                raise ValueError(f"Circular dependency detected in nodes: {remaining_nodes}")
            
            # Add ready nodes as parallel execution stage
            execution_stages.append(ready_nodes)
            
            # Update state
            for node_id in ready_nodes:
                remaining_nodes.remove(node_id)
                completed_deps.add(node_id)
        
        self.execution_order = [node for stage in execution_stages for node in stage]
        
        self.logger.info(f"Built execution graph with {len(execution_stages)} stages")
        self.logger.debug(f"Execution stages: {execution_stages}")
        
        return execution_stages
    
    async def process(self, image: np.ndarray, image_path: str = "") -> ProcessingContext:
        """
        Process image through the DAG
        
        Args:
            image: Input image as numpy array
            image_path: Optional path to image file
            
        Returns:
            ProcessingContext with all detection results
        """
        start_time = time.time()
        
        try:
            # Initialize processing context
            context = ProcessingContext(
                original_image=image.copy(),
                image_path=image_path,
                privacy_level=self.config.level,
                start_time=start_time
            )
            
            # Reset execution state
            self.completed_nodes.clear()
            self.failed_nodes.clear()
            self.running_nodes.clear()
            
            # Build execution graph for current privacy level
            execution_stages = self.build_execution_graph(self.config.level)
            
            if not execution_stages:
                self.logger.warning("No nodes enabled for current privacy level")
                return context
            
            # Execute stages sequentially, nodes within each stage in parallel
            for stage_idx, stage_nodes in enumerate(execution_stages):
                self.logger.debug(f"Executing stage {stage_idx + 1}/{len(execution_stages)}: {stage_nodes}")
                
                if self.config.performance.parallel_processing and len(stage_nodes) > 1:
                    # Parallel execution within stage
                    await self._execute_stage_parallel(stage_nodes, context)
                else:
                    # Sequential execution within stage
                    await self._execute_stage_sequential(stage_nodes, context)
            
            # Update performance statistics
            execution_time = time.time() - start_time
            self._update_execution_stats(execution_time, len(self.failed_nodes) == 0)
            
            context.metadata['total_processing_time'] = execution_time
            context.metadata['completed_nodes'] = list(self.completed_nodes)
            context.metadata['failed_nodes'] = list(self.failed_nodes)
            
            self.logger.info(f"DAG processing completed in {execution_time:.3f}s")
            self.logger.info(f"Nodes - Completed: {len(self.completed_nodes)}, Failed: {len(self.failed_nodes)}")
            
            return context
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"DAG processing failed after {execution_time:.3f}s: {e}")
            self._update_execution_stats(execution_time, False)
            
            # Return context with error information
            context.metadata['error'] = str(e)
            context.metadata['total_processing_time'] = execution_time
            return context
    
    async def _execute_stage_parallel(self, stage_nodes: List[str], context: ProcessingContext):
        """Execute nodes in parallel within a stage"""
        tasks = []
        
        for node_id in stage_nodes:
            if node_id in self.nodes:
                task = asyncio.create_task(self._execute_node(node_id, context))
                tasks.append(task)
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _execute_stage_sequential(self, stage_nodes: List[str], context: ProcessingContext):
        """Execute nodes sequentially within a stage"""
        for node_id in stage_nodes:
            if node_id in self.nodes:
                await self._execute_node(node_id, context)
    
    async def _execute_node(self, node_id: str, context: ProcessingContext):
        """
        Execute a single node
        
        Args:
            node_id: ID of node to execute
            context: Processing context
        """
        node = self.nodes[node_id]
        
        try:
            # Update node status
            node.status = NodeStatus.RUNNING
            self.running_nodes.add(node_id)
            
            self.logger.debug(f"Executing node: {node_id}")
            node_start_time = time.time()
            
            # Execute node processing
            result = await node.process(context)
            
            node_processing_time = time.time() - node_start_time
            node._update_performance_stats(node_processing_time)
            
            # Store result if successful
            if result is not None:
                context.detection_results[node_id] = result
                node.status = NodeStatus.COMPLETED
                self.completed_nodes.add(node_id)
                
                self.logger.debug(f"Node {node_id} completed in {node_processing_time:.3f}s")
            else:
                node.status = NodeStatus.SKIPPED
                self.logger.debug(f"Node {node_id} skipped")
            
        except Exception as e:
            # Handle node execution error
            node_processing_time = time.time() - node_start_time if 'node_start_time' in locals() else 0
            node._update_performance_stats(node_processing_time)
            
            node.status = NodeStatus.FAILED
            node.error_message = str(e)
            self.failed_nodes.add(node_id)
            
            self.logger.error(f"Node {node_id} failed after {node_processing_time:.3f}s: {e}")
            
            # Optionally continue processing other nodes or fail fast
            if not self.config.performance.async_processing:
                raise
        
        finally:
            # Clean up running state
            self.running_nodes.discard(node_id)
    
    def _update_execution_stats(self, execution_time: float, success: bool):
        """Update execution statistics"""
        self.execution_stats['total_executions'] += 1
        
        if success:
            self.execution_stats['successful_executions'] += 1
        else:
            self.execution_stats['failed_executions'] += 1
        
        # Update average execution time
        total_time = (self.execution_stats['average_execution_time'] * 
                     (self.execution_stats['total_executions'] - 1) + execution_time)
        self.execution_stats['average_execution_time'] = total_time / self.execution_stats['total_executions']
        
        # Update node performance stats
        for node_id, node in self.nodes.items():
            if node.execution_count > 0:
                self.execution_stats['node_performance'][node_id] = {
                    'executions': node.execution_count,
                    'average_time': node.average_processing_time,
                    'total_time': node.total_processing_time,
                    'last_time': node.processing_time
                }
    
    def get_performance_report(self) -> Dict[str, Any]:
        """
        Get comprehensive performance report
        
        Returns:
            Dictionary with performance metrics
        """
        return {
            'execution_stats': self.execution_stats.copy(),
            'node_count': len(self.nodes),
            'enabled_nodes': [
                node_id for node_id, node in self.nodes.items()
                if node.is_enabled_for_level(self.config.level)
            ],
            'last_execution': {
                'completed_nodes': list(self.completed_nodes),
                'failed_nodes': list(self.failed_nodes),
                'execution_order': self.execution_order
            },
            'node_details': {
                node_id: {
                    'status': node.status.value,
                    'dependencies': list(node.dependencies),
                    'dependents': list(node.dependents),
                    'execution_count': node.execution_count,
                    'average_time': node.average_processing_time,
                    'error_message': node.error_message
                }
                for node_id, node in self.nodes.items()
            }
        }
    
    def reset_statistics(self):
        """Reset all performance statistics"""
        self.execution_stats = {
            'total_executions': 0,
            'successful_executions': 0,
            'failed_executions': 0,
            'average_execution_time': 0.0,
            'node_performance': {}
        }
        
        for node in self.nodes.values():
            node.execution_count = 0
            node.total_processing_time = 0.0
            node.average_processing_time = 0.0
        
        self.logger.info("Performance statistics reset")
    
    def validate_graph(self) -> List[str]:
        """
        Validate the DAG for correctness
        
        Returns:
            List of validation errors
        """
        errors = []
        
        # Check for self-dependencies
        for node_id, node in self.nodes.items():
            if node_id in node.dependencies:
                errors.append(f"Node {node_id} has self-dependency")
        
        # Check for invalid dependencies
        for node_id, node in self.nodes.items():
            for dep_id in node.dependencies:
                if dep_id not in self.nodes:
                    errors.append(f"Node {node_id} depends on non-existent node {dep_id}")
        
        # Check for orphaned nodes (no dependencies and no dependents)
        for node_id, node in self.nodes.items():
            if not node.dependencies and not node.dependents and len(self.nodes) > 1:
                errors.append(f"Node {node_id} is orphaned (no connections)")
        
        return errors