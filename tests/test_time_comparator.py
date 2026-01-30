"""
Tests for TimeComparator
"""

import pytest
from src.core.time_comparator import TimeComparator, DeviationLevel


@pytest.fixture
def comparator():
    """Create TimeComparator instance"""
    return TimeComparator(
        acceptable_variance=0.10,  # 10%
        light_threshold=0.25,  # 25%
        moderate_threshold=0.50  # 50%
    )


class TestTimeComparator:
    """Test cases for TimeComparator"""
    
    def test_initialization(self, comparator):
        """Test comparator initialization"""
        assert comparator.acceptable_variance == 0.10
        assert comparator.light_threshold == 0.25
        assert comparator.moderate_threshold == 0.50
    
    def test_compare_times_exact_match(self, comparator):
        """Test comparison when actual equals estimated"""
        result = comparator.compare_times(
            work_item_id=123,
            estimated_hours=8.0,
            actual_hours=8.0,
            work_item_title="Test Task"
        )
        
        assert result['work_item_id'] == 123
        assert result['estimated_hours'] == 8.0
        assert result['actual_hours'] == 8.0
        assert result['variance_absolute'] == 0.0
        assert result['variance_percentage'] == 0.0
        assert result['variance_ratio'] == 1.0
        assert result['deviation_level'] == DeviationLevel.NONE.value
        assert result['is_acceptable'] is True
    
    def test_compare_times_within_acceptable(self, comparator):
        """Test comparison within acceptable range"""
        result = comparator.compare_times(
            work_item_id=123,
            estimated_hours=10.0,
            actual_hours=10.5  # 5% variance
        )
        
        assert result['variance_percentage'] == 5.0
        assert result['deviation_level'] == DeviationLevel.NONE.value
        assert result['is_acceptable'] is True
    
    def test_compare_times_light_deviation(self, comparator):
        """Test comparison with light deviation"""
        result = comparator.compare_times(
            work_item_id=123,
            estimated_hours=10.0,
            actual_hours=12.0  # 20% variance
        )
        
        assert result['variance_percentage'] == 20.0
        assert result['deviation_level'] == DeviationLevel.LEVE.value
        assert result['is_acceptable'] is False
        assert result['is_over_estimate'] is True
    
    def test_compare_times_moderate_deviation(self, comparator):
        """Test comparison with moderate deviation"""
        result = comparator.compare_times(
            work_item_id=123,
            estimated_hours=10.0,
            actual_hours=14.0  # 40% variance
        )
        
        assert result['variance_percentage'] == 40.0
        assert result['deviation_level'] == DeviationLevel.MODERADA.value
        assert result['is_acceptable'] is False
    
    def test_compare_times_high_deviation(self, comparator):
        """Test comparison with high deviation"""
        result = comparator.compare_times(
            work_item_id=123,
            estimated_hours=10.0,
            actual_hours=18.0  # 80% variance
        )
        
        assert result['variance_percentage'] == 80.0
        assert result['deviation_level'] == DeviationLevel.ALTA.value
        assert result['is_acceptable'] is False
    
    def test_compare_times_under_estimate(self, comparator):
        """Test comparison when under estimate"""
        result = comparator.compare_times(
            work_item_id=123,
            estimated_hours=10.0,
            actual_hours=6.0  # -40% variance
        )
        
        assert result['variance_percentage'] == -40.0
        assert result['variance_absolute'] == -4.0
        assert result['is_under_estimate'] is True
        assert result['is_over_estimate'] is False
        assert result['deviation_level'] == DeviationLevel.MODERADA.value
    
    def test_compare_times_with_breakdown(self, comparator):
        """Test comparison with meeting and execution hours breakdown"""
        result = comparator.compare_times(
            work_item_id=123,
            estimated_hours=10.0,
            actual_hours=12.0,
            meeting_hours=5.0,
            execution_hours=7.0
        )
        
        assert result['meeting_hours'] == 5.0
        assert result['execution_hours'] == 7.0
        assert result['actual_hours'] == 12.0  # Total
    
    def test_calculate_variance_normal(self, comparator):
        """Test variance calculation with normal values"""
        variance = comparator.calculate_variance(10.0, 12.0)
        
        assert variance['variance_absolute'] == 2.0
        assert variance['variance_percentage'] == 20.0
        assert variance['variance_ratio'] == 1.2
        assert variance['is_over_estimate'] is True
        assert variance['is_under_estimate'] is False
    
    def test_calculate_variance_zero_estimate(self, comparator):
        """Test variance calculation with zero estimate"""
        variance = comparator.calculate_variance(0.0, 5.0)
        
        assert variance['variance_absolute'] == 5.0
        assert variance['variance_percentage'] == float('inf')
        assert variance['variance_ratio'] == float('inf')
    
    def test_calculate_variance_zero_both(self, comparator):
        """Test variance calculation when both are zero"""
        variance = comparator.calculate_variance(0.0, 0.0)
        
        assert variance['variance_absolute'] == 0.0
        assert variance['variance_percentage'] == 0.0
        assert variance['variance_ratio'] == 1.0
    
    def test_categorize_deviation_none(self, comparator):
        """Test deviation categorization - none"""
        level = comparator.categorize_deviation(8.0)  # 8%
        assert level == DeviationLevel.NONE
    
    def test_categorize_deviation_leve(self, comparator):
        """Test deviation categorization - leve"""
        level = comparator.categorize_deviation(20.0)  # 20%
        assert level == DeviationLevel.LEVE
    
    def test_categorize_deviation_moderada(self, comparator):
        """Test deviation categorization - moderada"""
        level = comparator.categorize_deviation(40.0)  # 40%
        assert level == DeviationLevel.MODERADA
    
    def test_categorize_deviation_alta(self, comparator):
        """Test deviation categorization - alta"""
        level = comparator.categorize_deviation(80.0)  # 80%
        assert level == DeviationLevel.ALTA
    
    def test_categorize_deviation_negative(self, comparator):
        """Test deviation categorization with negative variance"""
        level = comparator.categorize_deviation(-35.0)  # -35%
        assert level == DeviationLevel.MODERADA
    
    def test_compare_batch(self, comparator):
        """Test batch comparison"""
        work_items = [
            {
                'work_item_id': 123,
                'title': 'Task 1',
                'estimated_hours': 8.0,
                'actual_hours': 8.5,
                'meeting_hours': 2.0,
                'execution_hours': 6.5
            },
            {
                'work_item_id': 124,
                'title': 'Task 2',
                'estimated_hours': 10.0,
                'actual_hours': 15.0,
                'meeting_hours': 5.0,
                'execution_hours': 10.0
            },
            {
                'work_item_id': 125,
                'title': 'Task 3',
                'estimated_hours': 5.0,
                'actual_hours': 4.0,
                'meeting_hours': 1.0,
                'execution_hours': 3.0
            }
        ]
        
        result = comparator.compare_batch(work_items)
        
        assert result['total'] == 3
        assert len(result['items']) == 3
        assert 'statistics' in result
    
    def test_calculate_statistics(self, comparator):
        """Test statistics calculation"""
        comparisons = [
            {
                'work_item_id': 123,
                'estimated_hours': 8.0,
                'actual_hours': 8.5,
                'meeting_hours': 2.0,
                'execution_hours': 6.5,
                'variance_percentage': 6.25,
                'deviation_level': DeviationLevel.NONE.value,
                'is_acceptable': True
            },
            {
                'work_item_id': 124,
                'estimated_hours': 10.0,
                'actual_hours': 15.0,
                'meeting_hours': 5.0,
                'execution_hours': 10.0,
                'variance_percentage': 50.0,
                'deviation_level': DeviationLevel.MODERADA.value,
                'is_acceptable': False
            }
        ]
        
        stats = comparator.calculate_statistics(comparisons)
        
        assert stats['total_items'] == 2
        assert stats['total_estimated_hours'] == 18.0
        assert stats['total_actual_hours'] == 23.5
        assert stats['total_meeting_hours'] == 7.0
        assert stats['total_execution_hours'] == 16.5
        assert stats['acceptable_count'] == 1
        assert stats['deviation_count'] == 1
        assert stats['average_estimated'] == 9.0
        assert stats['average_actual'] == 11.75
    
    def test_calculate_statistics_by_level(self, comparator):
        """Test statistics by deviation level"""
        comparisons = [
            {'estimated_hours': 10.0, 'actual_hours': 10.0, 'variance_percentage': 0.0, 
             'deviation_level': DeviationLevel.NONE.value, 'is_acceptable': True},
            {'estimated_hours': 10.0, 'actual_hours': 12.0, 'variance_percentage': 20.0, 
             'deviation_level': DeviationLevel.LEVE.value, 'is_acceptable': False},
            {'estimated_hours': 10.0, 'actual_hours': 14.0, 'variance_percentage': 40.0, 
             'deviation_level': DeviationLevel.MODERADA.value, 'is_acceptable': False},
            {'estimated_hours': 10.0, 'actual_hours': 18.0, 'variance_percentage': 80.0, 
             'deviation_level': DeviationLevel.ALTA.value, 'is_acceptable': False}
        ]
        
        stats = comparator.calculate_statistics(comparisons)
        
        assert stats['by_level'][DeviationLevel.NONE.value] == 1
        assert stats['by_level'][DeviationLevel.LEVE.value] == 1
        assert stats['by_level'][DeviationLevel.MODERADA.value] == 1
        assert stats['by_level'][DeviationLevel.ALTA.value] == 1
    
    def test_calculate_statistics_empty(self, comparator):
        """Test statistics with empty list"""
        stats = comparator.calculate_statistics([])
        
        assert stats['total_items'] == 0
        assert stats['acceptable_count'] == 0
    
    def test_get_discrepancy_report(self, comparator):
        """Test discrepancy report generation"""
        comparisons = [
            {'work_item_id': 123, 'variance_percentage': 5.0, 
             'deviation_level': DeviationLevel.NONE.value},
            {'work_item_id': 124, 'variance_percentage': 20.0, 
             'deviation_level': DeviationLevel.LEVE.value},
            {'work_item_id': 125, 'variance_percentage': 40.0, 
             'deviation_level': DeviationLevel.MODERADA.value},
            {'work_item_id': 126, 'variance_percentage': 80.0, 
             'deviation_level': DeviationLevel.ALTA.value}
        ]
        
        discrepancies = comparator.get_discrepancy_report(
            comparisons,
            min_deviation_level=DeviationLevel.LEVE
        )
        
        # Should exclude NONE level
        assert len(discrepancies) == 3
        assert discrepancies[0]['work_item_id'] == 126  # ALTA first
        assert discrepancies[-1]['work_item_id'] == 124  # LEVE last
    
    def test_get_discrepancy_report_high_only(self, comparator):
        """Test discrepancy report with high threshold"""
        comparisons = [
            {'work_item_id': 123, 'variance_percentage': 5.0, 
             'deviation_level': DeviationLevel.NONE.value},
            {'work_item_id': 124, 'variance_percentage': 20.0, 
             'deviation_level': DeviationLevel.LEVE.value},
            {'work_item_id': 125, 'variance_percentage': 40.0, 
             'deviation_level': DeviationLevel.MODERADA.value},
            {'work_item_id': 126, 'variance_percentage': 80.0, 
             'deviation_level': DeviationLevel.ALTA.value}
        ]
        
        discrepancies = comparator.get_discrepancy_report(
            comparisons,
            min_deviation_level=DeviationLevel.ALTA
        )
        
        assert len(discrepancies) == 1
        assert discrepancies[0]['work_item_id'] == 126
    
    def test_deviation_description_spanish(self, comparator):
        """Test deviation descriptions are in Spanish"""
        comparison = comparator.compare_times(123, 10.0, 12.0)
        
        description = comparison['deviation_description']
        assert description in [
            "Dentro del rango aceptable",
            "Desviación leve",
            "Desviación moderada",
            "Desviación alta"
        ]
    
    def test_recommendation_spanish(self, comparator):
        """Test recommendations are in Spanish"""
        comparison = comparator.compare_times(123, 10.0, 18.0)
        
        recommendation = comparison['recommendation']
        assert isinstance(recommendation, str)
        assert len(recommendation) > 0
        # Should contain Spanish words
        assert any(word in recommendation.lower() for word in [
            'tiempo', 'estimación', 'tarea', 'revisar', 'considerar'
        ])
    
    def test_recommendation_under_estimate(self, comparator):
        """Test recommendation for under-estimate scenario"""
        comparison = comparator.compare_times(123, 10.0, 5.0)
        
        recommendation = comparison['recommendation']
        assert 'menos tiempo' in recommendation.lower() or 'completó' in recommendation.lower()
    
    def test_recommendation_over_estimate_high(self, comparator):
        """Test recommendation for high over-estimate"""
        comparison = comparator.compare_times(123, 10.0, 18.0)
        
        recommendation = comparison['recommendation']
        assert 'excede' in recommendation.lower() or 'supera' in recommendation.lower()
    
    def test_recommendation_acceptable(self, comparator):
        """Test recommendation for acceptable variance"""
        comparison = comparator.compare_times(123, 10.0, 10.5)
        
        recommendation = comparison['recommendation']
        assert 'dentro del rango' in recommendation.lower() or 'esperado' in recommendation.lower()
