"""
Time Comparator - Compares actual time vs estimated time
"""

import logging
from typing import Dict, Any, List, Optional
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class DeviationLevel(Enum):
    """
    Categorization of time deviation severity.
    """
    NONE = "none"  # Within acceptable range (0-10%)
    LEVE = "leve"  # Light deviation (10-25%)
    MODERADA = "moderada"  # Moderate deviation (25-50%)
    ALTA = "alta"  # High deviation (>50%)


class TimeComparator:
    """
    Compares actual time worked vs estimated time.
    Calculates metrics and categorizes deviations.
    """
    
    def __init__(
        self,
        acceptable_variance: float = 0.10,  # 10%
        light_threshold: float = 0.25,  # 25%
        moderate_threshold: float = 0.50  # 50%
    ):
        """
        Initialize time comparator.
        
        Args:
            acceptable_variance: Variance within this threshold is considered acceptable
            light_threshold: Threshold for light deviation
            moderate_threshold: Threshold for moderate deviation
        """
        self.acceptable_variance = acceptable_variance
        self.light_threshold = light_threshold
        self.moderate_threshold = moderate_threshold
        
        logger.info(
            f"[COMPARATOR] Initialized (acceptable={acceptable_variance*100}%, "
            f"light={light_threshold*100}%, moderate={moderate_threshold*100}%)"
        )
    
    def compare_times(
        self,
        work_item_id: int,
        estimated_hours: float,
        actual_hours: float,
        meeting_hours: Optional[float] = None,
        execution_hours: Optional[float] = None,
        work_item_title: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Compare actual time vs estimated time for a work item.
        
        Args:
            work_item_id: Work item ID
            estimated_hours: Originally estimated hours
            actual_hours: Total actual hours worked
            meeting_hours: Hours spent in meetings (optional breakdown)
            execution_hours: Hours spent on execution (optional breakdown)
            work_item_title: Work item title for reporting
            
        Returns:
            Dictionary with comparison results
        """
        logger.info(f"[COMPARATOR] Comparing times for work item #{work_item_id}")
        
        comparison = {
            'work_item_id': work_item_id,
            'work_item_title': work_item_title or f"Work Item #{work_item_id}",
            'estimated_hours': estimated_hours,
            'actual_hours': actual_hours,
            'meeting_hours': meeting_hours,
            'execution_hours': execution_hours,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Calculate variance
        variance_result = self.calculate_variance(estimated_hours, actual_hours)
        comparison.update(variance_result)
        
        # Categorize deviation
        deviation = self.categorize_deviation(variance_result['variance_percentage'])
        comparison['deviation_level'] = deviation.value
        comparison['deviation_description'] = self._get_deviation_description(deviation)
        
        # Determine if within acceptable range
        comparison['is_acceptable'] = deviation == DeviationLevel.NONE
        
        # Add recommendations
        comparison['recommendation'] = self._get_recommendation(comparison)
        
        logger.debug(
            f"[COMPARATOR] #{work_item_id}: {estimated_hours}h estimated vs {actual_hours}h actual "
            f"({variance_result['variance_percentage']:.1f}% variance, {deviation.value})"
        )
        
        return comparison
    
    def calculate_variance(
        self,
        estimated: float,
        actual: float
    ) -> Dict[str, float]:
        """
        Calculate variance metrics between estimated and actual time.
        
        Args:
            estimated: Estimated hours
            actual: Actual hours
            
        Returns:
            Dictionary with variance calculations
        """
        if estimated == 0:
            # Handle zero estimate case
            if actual == 0:
                variance_percentage = 0.0
                variance_ratio = 1.0
            else:
                # Can't calculate percentage, mark as infinite
                variance_percentage = float('inf')
                variance_ratio = float('inf')
        else:
            variance_ratio = actual / estimated
            variance_percentage = ((actual - estimated) / estimated) * 100
        
        variance_absolute = actual - estimated
        
        return {
            'variance_absolute': variance_absolute,  # Absolute difference in hours
            'variance_percentage': variance_percentage,  # Percentage difference
            'variance_ratio': variance_ratio,  # Ratio of actual/estimated
            'is_over_estimate': actual > estimated,
            'is_under_estimate': actual < estimated
        }
    
    def categorize_deviation(
        self,
        variance_percentage: float
    ) -> DeviationLevel:
        """
        Categorize the deviation level based on variance percentage.
        
        Args:
            variance_percentage: Variance as percentage
            
        Returns:
            DeviationLevel enum
        """
        # Use absolute value for categorization
        abs_variance = abs(variance_percentage) / 100
        
        if abs_variance <= self.acceptable_variance:
            return DeviationLevel.NONE
        elif abs_variance <= self.light_threshold:
            return DeviationLevel.LEVE
        elif abs_variance <= self.moderate_threshold:
            return DeviationLevel.MODERADA
        else:
            return DeviationLevel.ALTA
    
    def compare_batch(
        self,
        work_items: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Compare times for multiple work items in batch.
        
        Args:
            work_items: List of dicts with work item comparison data
            
        Returns:
            Summary of batch comparison results
        """
        logger.info(f"[COMPARATOR] Comparing {len(work_items)} work items in batch")
        
        results = {
            'total': len(work_items),
            'items': [],
            'statistics': {}
        }
        
        # Process each work item
        for item in work_items:
            comparison = self.compare_times(
                work_item_id=item['work_item_id'],
                estimated_hours=item.get('estimated_hours', 0),
                actual_hours=item.get('actual_hours', 0),
                meeting_hours=item.get('meeting_hours'),
                execution_hours=item.get('execution_hours'),
                work_item_title=item.get('title')
            )
            results['items'].append(comparison)
        
        # Calculate statistics
        results['statistics'] = self.calculate_statistics(results['items'])
        
        logger.info(
            f"[COMPARATOR] Batch comparison complete: "
            f"{results['statistics']['acceptable_count']} acceptable, "
            f"{results['statistics']['deviation_count']} with deviations"
        )
        
        return results
    
    def calculate_statistics(
        self,
        comparisons: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate aggregate statistics from a list of comparisons.
        
        Args:
            comparisons: List of comparison results
            
        Returns:
            Dictionary with aggregate statistics
        """
        if not comparisons:
            return {
                'total_items': 0,
                'acceptable_count': 0,
                'deviation_count': 0,
                'by_level': {}
            }
        
        total_estimated = sum(c['estimated_hours'] for c in comparisons)
        total_actual = sum(c['actual_hours'] for c in comparisons)
        total_meeting = sum(c.get('meeting_hours', 0) or 0 for c in comparisons)
        total_execution = sum(c.get('execution_hours', 0) or 0 for c in comparisons)
        
        acceptable_count = sum(1 for c in comparisons if c['is_acceptable'])
        deviation_count = len(comparisons) - acceptable_count
        
        # Count by deviation level
        level_counts = {
            DeviationLevel.NONE.value: 0,
            DeviationLevel.LEVE.value: 0,
            DeviationLevel.MODERADA.value: 0,
            DeviationLevel.ALTA.value: 0
        }
        
        for comp in comparisons:
            level = comp['deviation_level']
            level_counts[level] = level_counts.get(level, 0) + 1
        
        # Calculate overall variance
        overall_variance = self.calculate_variance(total_estimated, total_actual)
        
        # Find items with highest/lowest variance
        sorted_by_variance = sorted(
            comparisons,
            key=lambda x: abs(x['variance_percentage']),
            reverse=True
        )
        
        statistics = {
            'total_items': len(comparisons),
            'total_estimated_hours': total_estimated,
            'total_actual_hours': total_actual,
            'total_meeting_hours': total_meeting,
            'total_execution_hours': total_execution,
            'overall_variance_absolute': overall_variance['variance_absolute'],
            'overall_variance_percentage': overall_variance['variance_percentage'],
            'overall_variance_ratio': overall_variance['variance_ratio'],
            'acceptable_count': acceptable_count,
            'deviation_count': deviation_count,
            'by_level': level_counts,
            'top_deviations': sorted_by_variance[:5],  # Top 5 deviations
            'average_estimated': total_estimated / len(comparisons),
            'average_actual': total_actual / len(comparisons)
        }
        
        return statistics
    
    def get_discrepancy_report(
        self,
        comparisons: List[Dict[str, Any]],
        min_deviation_level: Optional[DeviationLevel] = DeviationLevel.LEVE
    ) -> List[Dict[str, Any]]:
        """
        Get list of work items with discrepancies.
        
        Args:
            comparisons: List of comparison results
            min_deviation_level: Minimum deviation level to include
            
        Returns:
            List of work items with discrepancies
        """
        level_order = {
            DeviationLevel.NONE: 0,
            DeviationLevel.LEVE: 1,
            DeviationLevel.MODERADA: 2,
            DeviationLevel.ALTA: 3
        }
        
        min_level_value = level_order.get(min_deviation_level, 1)
        
        discrepancies = [
            comp for comp in comparisons
            if level_order.get(DeviationLevel(comp['deviation_level']), 0) >= min_level_value
        ]
        
        # Sort by severity (highest first)
        discrepancies.sort(
            key=lambda x: (
                level_order.get(DeviationLevel(x['deviation_level']), 0),
                abs(x['variance_percentage'])
            ),
            reverse=True
        )
        
        logger.info(
            f"[COMPARATOR] Found {len(discrepancies)} discrepancies "
            f"with minimum level: {min_deviation_level.value}"
        )
        
        return discrepancies
    
    def _get_deviation_description(self, deviation: DeviationLevel) -> str:
        """
        Get human-readable description for deviation level.
        
        Args:
            deviation: DeviationLevel enum
            
        Returns:
            Description string in Spanish
        """
        descriptions = {
            DeviationLevel.NONE: "Dentro del rango aceptable",
            DeviationLevel.LEVE: "Desviación leve",
            DeviationLevel.MODERADA: "Desviación moderada",
            DeviationLevel.ALTA: "Desviación alta"
        }
        
        return descriptions.get(deviation, "Desconocido")
    
    def _get_recommendation(self, comparison: Dict[str, Any]) -> str:
        """
        Get recommendation based on comparison results.
        
        Args:
            comparison: Comparison result dictionary
            
        Returns:
            Recommendation string in Spanish
        """
        deviation = DeviationLevel(comparison['deviation_level'])
        is_over = comparison['is_over_estimate']
        
        if deviation == DeviationLevel.NONE:
            return "El tiempo registrado está dentro del rango esperado."
        
        if is_over:
            if deviation == DeviationLevel.ALTA:
                return "El tiempo real excede significativamente la estimación. Revisar el alcance de la tarea."
            elif deviation == DeviationLevel.MODERADA:
                return "El tiempo real supera moderadamente la estimación. Considerar ajustar futuras estimaciones."
            else:
                return "El tiempo real supera ligeramente la estimación."
        else:
            if deviation == DeviationLevel.ALTA:
                return "La tarea se completó en mucho menos tiempo del estimado. Considerar optimizar estimaciones futuras."
            elif deviation == DeviationLevel.MODERADA:
                return "La tarea se completó en menos tiempo del estimado."
            else:
                return "El tiempo real es ligeramente menor a la estimación."
