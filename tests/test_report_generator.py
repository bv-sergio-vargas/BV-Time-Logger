"""
Tests for ReportGenerator
"""

import pytest
import json
import csv
from pathlib import Path
from datetime import date
from src.reports.report_generator import ReportGenerator
from src.core.time_comparator import DeviationLevel


@pytest.fixture
def temp_output_dir():
    """Create temporary output directory"""
    return "test_reports"


@pytest.fixture
def generator(temp_output_dir):
    """Create ReportGenerator instance"""
    gen = ReportGenerator(output_dir=temp_output_dir)
    yield gen
    # Cleanup
    import shutil
    if Path(temp_output_dir).exists():
        shutil.rmtree(temp_output_dir)


@pytest.fixture
def sample_comparisons():
    """Sample comparison data"""
    return [
        {
            'work_item_id': 123,
            'work_item_title': 'Implement feature A',
            'estimated_hours': 8.0,
            'actual_hours': 8.5,
            'meeting_hours': 2.0,
            'execution_hours': 6.5,
            'variance_absolute': 0.5,
            'variance_percentage': 6.25,
            'variance_ratio': 1.0625,
            'deviation_level': DeviationLevel.NONE.value,
            'deviation_description': 'Dentro del rango aceptable',
            'is_acceptable': True,
            'recommendation': 'El tiempo registrado está dentro del rango esperado.'
        },
        {
            'work_item_id': 124,
            'work_item_title': 'Fix bug B',
            'estimated_hours': 10.0,
            'actual_hours': 15.0,
            'meeting_hours': 5.0,
            'execution_hours': 10.0,
            'variance_absolute': 5.0,
            'variance_percentage': 50.0,
            'variance_ratio': 1.5,
            'deviation_level': DeviationLevel.MODERADA.value,
            'deviation_description': 'Desviación moderada',
            'is_acceptable': False,
            'recommendation': 'El tiempo real supera moderadamente la estimación.'
        }
    ]


@pytest.fixture
def sample_statistics():
    """Sample statistics data"""
    return {
        'total_items': 2,
        'total_estimated_hours': 18.0,
        'total_actual_hours': 23.5,
        'total_meeting_hours': 7.0,
        'total_execution_hours': 16.5,
        'overall_variance_percentage': 30.56,
        'overall_variance_ratio': 1.306,
        'acceptable_count': 1,
        'deviation_count': 1,
        'by_level': {
            'none': 1,
            'leve': 0,
            'moderada': 1,
            'alta': 0
        },
        'top_deviations': [],
        'average_estimated': 9.0,
        'average_actual': 11.75
    }


class TestReportGenerator:
    """Test cases for ReportGenerator"""
    
    def test_initialization(self, generator, temp_output_dir):
        """Test generator initialization"""
        assert generator.output_dir == Path(temp_output_dir)
        assert generator.output_dir.exists()
    
    def test_generate_daily_report(self, generator, sample_comparisons, sample_statistics):
        """Test daily report generation"""
        report_date = date(2026, 1, 29)
        
        files = generator.generate_daily_report(
            report_date=report_date,
            comparisons=sample_comparisons,
            statistics=sample_statistics
        )
        
        assert 'csv' in files
        assert 'json' in files
        assert Path(files['csv']).exists()
        assert Path(files['json']).exists()
        assert '2026-01-29' in files['csv']
        assert '2026-01-29' in files['json']
    
    def test_generate_sprint_summary(self, generator, sample_comparisons, sample_statistics):
        """Test sprint summary generation"""
        sprint_name = "Sprint 1"
        sprint_start = date(2026, 1, 20)
        sprint_end = date(2026, 2, 2)
        
        files = generator.generate_sprint_summary(
            sprint_name=sprint_name,
            sprint_start=sprint_start,
            sprint_end=sprint_end,
            comparisons=sample_comparisons,
            statistics=sample_statistics
        )
        
        assert 'csv' in files
        assert 'json' in files
        assert Path(files['csv']).exists()
        assert Path(files['json']).exists()
        assert 'Sprint_1' in files['csv']
    
    def test_generate_discrepancy_report(self, generator, sample_comparisons):
        """Test discrepancy report generation"""
        # Filter to only discrepancies
        discrepancies = [c for c in sample_comparisons if not c['is_acceptable']]
        
        files = generator.generate_discrepancy_report(
            discrepancies=discrepancies,
            min_deviation_level='leve'
        )
        
        assert 'csv' in files
        assert 'json' in files
        assert Path(files['csv']).exists()
        assert Path(files['json']).exists()
        assert 'discrepancy_report' in files['csv']
    
    def test_export_to_csv_content(self, generator, sample_comparisons, sample_statistics):
        """Test CSV export content"""
        report_data = {
            'report_type': 'daily',
            'report_date': '2026-01-29',
            'work_items': sample_comparisons
        }
        
        csv_path = generator.export_to_csv(report_data, 'test_report')
        
        # Read and verify CSV content
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        assert len(rows) == 2
        assert rows[0]['work_item_id'] == '123'
        assert rows[0]['work_item_title'] == 'Implement feature A'
        assert rows[1]['work_item_id'] == '124'
    
    def test_export_to_json_content(self, generator, sample_comparisons, sample_statistics):
        """Test JSON export content"""
        report_data = {
            'report_type': 'daily',
            'report_date': '2026-01-29',
            'summary': sample_statistics,
            'work_items': sample_comparisons
        }
        
        json_path = generator.export_to_json(report_data, 'test_report')
        
        # Read and verify JSON content
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        assert data['report_type'] == 'daily'
        assert data['report_date'] == '2026-01-29'
        assert len(data['work_items']) == 2
        assert data['summary']['total_items'] == 2
    
    def test_export_to_json_spanish_encoding(self, generator):
        """Test JSON export handles Spanish characters correctly"""
        report_data = {
            'report_type': 'test',
            'message': 'Desviación moderada - revisión necesaria'
        }
        
        json_path = generator.export_to_json(report_data, 'test_spanish')
        
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        assert 'Desviación' in data['message']
        assert 'revisión' in data['message']
    
    def test_generate_custom_report(self, generator):
        """Test custom report generation"""
        custom_data = {
            'items': [
                {'id': 1, 'value': 'Test 1'},
                {'id': 2, 'value': 'Test 2'}
            ],
            'summary': 'Custom report summary'
        }
        
        files = generator.generate_custom_report(
            report_name='My Custom Report',
            data=custom_data,
            formats=['json']
        )
        
        assert 'json' in files
        assert 'csv' not in files  # Only JSON requested
        assert Path(files['json']).exists()
        assert 'custom_My_Custom_Report' in files['json']
    
    def test_generate_custom_report_both_formats(self, generator):
        """Test custom report with both formats"""
        custom_data = {
            'work_items': [
                {
                    'work_item_id': 100,
                    'work_item_title': 'Custom task',
                    'estimated_hours': 5.0,
                    'actual_hours': 6.0,
                    'variance_absolute': 1.0,
                    'variance_percentage': 20.0
                }
            ]
        }
        
        files = generator.generate_custom_report(
            report_name='Full Report',
            data=custom_data
        )
        
        assert 'csv' in files
        assert 'json' in files
    
    def test_generate_summary_text(self, generator, sample_statistics):
        """Test summary text generation"""
        summary_text = generator.generate_summary_text(sample_statistics)
        
        assert isinstance(summary_text, str)
        assert len(summary_text) > 0
        assert 'RESUMEN DE SEGUIMIENTO DE TIEMPO' in summary_text
        assert 'Total de Work Items: 2' in summary_text
        assert 'Horas Estimadas: 18.00h' in summary_text
        assert 'Horas Reales: 23.50h' in summary_text
    
    def test_generate_summary_text_recommendations(self, generator, sample_statistics):
        """Test summary text includes recommendations"""
        summary_text = generator.generate_summary_text(
            sample_statistics,
            include_recommendations=True
        )
        
        assert 'RECOMENDACIONES:' in summary_text
    
    def test_generate_summary_text_no_recommendations(self, generator, sample_statistics):
        """Test summary text without recommendations"""
        summary_text = generator.generate_summary_text(
            sample_statistics,
            include_recommendations=False
        )
        
        assert 'RECOMENDACIONES:' not in summary_text
    
    def test_generate_summary_text_high_variance(self, generator):
        """Test summary with high variance recommendation"""
        stats = {
            'total_items': 10,
            'total_estimated_hours': 100.0,
            'total_actual_hours': 140.0,
            'total_meeting_hours': 40.0,
            'total_execution_hours': 100.0,
            'overall_variance_percentage': 40.0,
            'acceptable_count': 3,
            'deviation_count': 7,
            'by_level': {
                'none': 3,
                'leve': 2,
                'moderada': 3,
                'alta': 2
            }
        }
        
        summary_text = generator.generate_summary_text(stats, include_recommendations=True)
        
        assert 'varianza total' in summary_text.lower()
        assert 'proceso de estimación' in summary_text.lower()
    
    def test_generate_summary_text_low_variance(self, generator):
        """Test summary with low (negative) variance"""
        stats = {
            'total_items': 10,
            'total_estimated_hours': 100.0,
            'total_actual_hours': 70.0,
            'total_meeting_hours': 20.0,
            'total_execution_hours': 50.0,
            'overall_variance_percentage': -30.0,
            'acceptable_count': 8,
            'deviation_count': 2,
            'by_level': {
                'none': 8,
                'leve': 1,
                'moderada': 1,
                'alta': 0
            }
        }
        
        summary_text = generator.generate_summary_text(stats, include_recommendations=True)
        
        assert 'por debajo del estimado' in summary_text.lower()
    
    def test_count_by_level(self, generator, sample_comparisons):
        """Test counting items by deviation level"""
        counts = generator._count_by_level(sample_comparisons)
        
        assert counts['none'] == 1
        assert counts['moderada'] == 1
        assert counts['leve'] == 0
        assert counts['alta'] == 0
    
    def test_daily_report_structure(self, generator, sample_comparisons, sample_statistics):
        """Test daily report has correct structure"""
        report_date = date(2026, 1, 29)
        
        files = generator.generate_daily_report(
            report_date=report_date,
            comparisons=sample_comparisons,
            statistics=sample_statistics
        )
        
        # Read JSON to verify structure
        with open(files['json'], 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        assert data['report_type'] == 'daily'
        assert 'report_date' in data
        assert 'generated_at' in data
        assert 'summary' in data
        assert 'work_items' in data
        assert 'deviations_by_level' in data
        assert 'top_deviations' in data
    
    def test_sprint_summary_structure(self, generator, sample_comparisons, sample_statistics):
        """Test sprint summary has correct structure"""
        files = generator.generate_sprint_summary(
            sprint_name="Sprint 1",
            sprint_start=date(2026, 1, 20),
            sprint_end=date(2026, 2, 2),
            comparisons=sample_comparisons,
            statistics=sample_statistics
        )
        
        # Read JSON to verify structure
        with open(files['json'], 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        assert data['report_type'] == 'sprint_summary'
        assert data['sprint_name'] == 'Sprint 1'
        assert 'sprint_start' in data
        assert 'sprint_end' in data
        assert 'summary' in data
        assert 'overall_variance_ratio' in data['summary']
    
    def test_output_directory_creation(self):
        """Test output directory is created if it doesn't exist"""
        import shutil
        new_dir = "test_reports_new"
        
        generator = ReportGenerator(output_dir=new_dir)
        
        assert Path(new_dir).exists()
        
        # Cleanup
        if Path(new_dir).exists():
            shutil.rmtree(new_dir)
    
    def test_safe_filename_generation(self, generator, sample_comparisons, sample_statistics):
        """Test sprint name with special characters is safely converted"""
        files = generator.generate_sprint_summary(
            sprint_name="Sprint 2024/Q1 - Special",
            sprint_start=date(2026, 1, 1),
            sprint_end=date(2026, 1, 31),
            comparisons=sample_comparisons,
            statistics=sample_statistics
        )
        
        # Should replace / with - and spaces with _
        assert '-' in Path(files['csv']).name
        assert '/' not in Path(files['csv']).name
