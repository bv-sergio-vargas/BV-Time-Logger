"""
Report Generator - Generates reports for time tracking analysis
"""

import logging
import csv
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, date
from pathlib import Path

logger = logging.getLogger(__name__)


class ReportGenerator:
    """
    Generates various reports for time tracking analysis.
    Supports CSV and JSON export formats.
    """
    
    def __init__(self, output_dir: str = "reports"):
        """
        Initialize report generator.
        
        Args:
            output_dir: Directory to save generated reports
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"[REPORTS] Initialized with output directory: {self.output_dir}")
    
    def generate_daily_report(
        self,
        report_date: date,
        comparisons: List[Dict[str, Any]],
        statistics: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        Generate daily time tracking report.
        
        Args:
            report_date: Date for the report
            comparisons: List of time comparisons
            statistics: Aggregate statistics
            
        Returns:
            Dictionary with paths to generated report files
        """
        logger.info(f"[REPORTS] Generating daily report for {report_date}")
        
        report_data = {
            'report_type': 'daily',
            'report_date': report_date.isoformat(),
            'generated_at': datetime.utcnow().isoformat(),
            'summary': {
                'total_work_items': statistics.get('total_items', 0),
                'total_estimated_hours': statistics.get('total_estimated_hours', 0),
                'total_actual_hours': statistics.get('total_actual_hours', 0),
                'total_meeting_hours': statistics.get('total_meeting_hours', 0),
                'total_execution_hours': statistics.get('total_execution_hours', 0),
                'overall_variance_percentage': statistics.get('overall_variance_percentage', 0),
                'acceptable_count': statistics.get('acceptable_count', 0),
                'deviation_count': statistics.get('deviation_count', 0)
            },
            'deviations_by_level': statistics.get('by_level', {}),
            'work_items': comparisons,
            'top_deviations': statistics.get('top_deviations', [])
        }
        
        # Generate filename base
        filename_base = f"daily_report_{report_date.isoformat()}"
        
        # Export to both formats
        files = {
            'csv': self.export_to_csv(report_data, filename_base),
            'json': self.export_to_json(report_data, filename_base)
        }
        
        logger.info(f"[REPORTS] Daily report generated: {files}")
        
        return files
    
    def generate_sprint_summary(
        self,
        sprint_name: str,
        sprint_start: date,
        sprint_end: date,
        comparisons: List[Dict[str, Any]],
        statistics: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        Generate sprint summary report.
        
        Args:
            sprint_name: Name of the sprint
            sprint_start: Sprint start date
            sprint_end: Sprint end date
            comparisons: List of time comparisons
            statistics: Aggregate statistics
            
        Returns:
            Dictionary with paths to generated report files
        """
        logger.info(f"[REPORTS] Generating sprint summary for '{sprint_name}'")
        
        report_data = {
            'report_type': 'sprint_summary',
            'sprint_name': sprint_name,
            'sprint_start': sprint_start.isoformat(),
            'sprint_end': sprint_end.isoformat(),
            'generated_at': datetime.utcnow().isoformat(),
            'summary': {
                'total_work_items': statistics.get('total_items', 0),
                'total_estimated_hours': statistics.get('total_estimated_hours', 0),
                'total_actual_hours': statistics.get('total_actual_hours', 0),
                'total_meeting_hours': statistics.get('total_meeting_hours', 0),
                'total_execution_hours': statistics.get('total_execution_hours', 0),
                'overall_variance_percentage': statistics.get('overall_variance_percentage', 0),
                'overall_variance_ratio': statistics.get('overall_variance_ratio', 0),
                'acceptable_count': statistics.get('acceptable_count', 0),
                'deviation_count': statistics.get('deviation_count', 0),
                'average_estimated': statistics.get('average_estimated', 0),
                'average_actual': statistics.get('average_actual', 0)
            },
            'deviations_by_level': statistics.get('by_level', {}),
            'work_items': comparisons,
            'top_deviations': statistics.get('top_deviations', [])
        }
        
        # Generate filename base (safe sprint name)
        safe_sprint_name = sprint_name.replace(' ', '_').replace('/', '-')
        filename_base = f"sprint_summary_{safe_sprint_name}_{sprint_start.isoformat()}"
        
        # Export to both formats
        files = {
            'csv': self.export_to_csv(report_data, filename_base),
            'json': self.export_to_json(report_data, filename_base)
        }
        
        logger.info(f"[REPORTS] Sprint summary generated: {files}")
        
        return files
    
    def generate_discrepancy_report(
        self,
        discrepancies: List[Dict[str, Any]],
        min_deviation_level: str = "leve"
    ) -> Dict[str, str]:
        """
        Generate report focused on discrepancies.
        
        Args:
            discrepancies: List of work items with discrepancies
            min_deviation_level: Minimum deviation level included
            
        Returns:
            Dictionary with paths to generated report files
        """
        logger.info(f"[REPORTS] Generating discrepancy report (min level: {min_deviation_level})")
        
        report_data = {
            'report_type': 'discrepancies',
            'generated_at': datetime.utcnow().isoformat(),
            'min_deviation_level': min_deviation_level,
            'summary': {
                'total_discrepancies': len(discrepancies),
                'by_level': self._count_by_level(discrepancies)
            },
            'discrepancies': discrepancies
        }
        
        # Generate filename
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        filename_base = f"discrepancy_report_{timestamp}"
        
        # Export to both formats
        files = {
            'csv': self.export_to_csv(report_data, filename_base),
            'json': self.export_to_json(report_data, filename_base)
        }
        
        logger.info(f"[REPORTS] Discrepancy report generated: {files}")
        
        return files
    
    def export_to_csv(
        self,
        report_data: Dict[str, Any],
        filename_base: str
    ) -> str:
        """
        Export report data to CSV format.
        
        Args:
            report_data: Report data dictionary
            filename_base: Base filename (without extension)
            
        Returns:
            Path to generated CSV file
        """
        csv_path = self.output_dir / f"{filename_base}.csv"
        
        # Determine CSV structure based on report type
        report_type = report_data.get('report_type', 'generic')
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            if report_type in ['daily', 'sprint_summary', 'discrepancies']:
                # Work items CSV
                work_items = report_data.get('work_items') or report_data.get('discrepancies', [])
                
                if work_items:
                    fieldnames = [
                        'work_item_id',
                        'work_item_title',
                        'estimated_hours',
                        'actual_hours',
                        'meeting_hours',
                        'execution_hours',
                        'variance_absolute',
                        'variance_percentage',
                        'variance_ratio',
                        'deviation_level',
                        'deviation_description',
                        'recommendation'
                    ]
                    
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction='ignore')
                    writer.writeheader()
                    writer.writerows(work_items)
                    
                    logger.info(f"[REPORTS] CSV exported with {len(work_items)} rows to {csv_path}")
                else:
                    logger.warning(f"[REPORTS] No work items to export to CSV")
            else:
                # Generic CSV export
                logger.warning(f"[REPORTS] Unknown report type for CSV: {report_type}")
        
        return str(csv_path)
    
    def export_to_json(
        self,
        report_data: Dict[str, Any],
        filename_base: str
    ) -> str:
        """
        Export report data to JSON format.
        
        Args:
            report_data: Report data dictionary
            filename_base: Base filename (without extension)
            
        Returns:
            Path to generated JSON file
        """
        json_path = self.output_dir / f"{filename_base}.json"
        
        with open(json_path, 'w', encoding='utf-8') as jsonfile:
            json.dump(report_data, jsonfile, indent=2, ensure_ascii=False)
        
        logger.info(f"[REPORTS] JSON exported to {json_path}")
        
        return str(json_path)
    
    def generate_custom_report(
        self,
        report_name: str,
        data: Dict[str, Any],
        formats: Optional[List[str]] = None
    ) -> Dict[str, str]:
        """
        Generate a custom report with specified data.
        
        Args:
            report_name: Name for the report
            data: Report data
            formats: List of formats to export ('csv', 'json'), defaults to both
            
        Returns:
            Dictionary with paths to generated files
        """
        if formats is None:
            formats = ['csv', 'json']
        
        logger.info(f"[REPORTS] Generating custom report '{report_name}'")
        
        # Add metadata
        report_data = {
            'report_type': 'custom',
            'report_name': report_name,
            'generated_at': datetime.utcnow().isoformat(),
            **data
        }
        
        # Generate filename
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        safe_name = report_name.replace(' ', '_').replace('/', '-')
        filename_base = f"custom_{safe_name}_{timestamp}"
        
        # Export to requested formats
        files = {}
        if 'csv' in formats:
            files['csv'] = self.export_to_csv(report_data, filename_base)
        if 'json' in formats:
            files['json'] = self.export_to_json(report_data, filename_base)
        
        logger.info(f"[REPORTS] Custom report generated: {files}")
        
        return files
    
    def generate_summary_text(
        self,
        statistics: Dict[str, Any],
        include_recommendations: bool = True
    ) -> str:
        """
        Generate human-readable summary text in Spanish.
        
        Args:
            statistics: Statistics dictionary
            include_recommendations: Include recommendations section
            
        Returns:
            Formatted summary text
        """
        summary_lines = [
            "=" * 60,
            "RESUMEN DE SEGUIMIENTO DE TIEMPO",
            "=" * 60,
            "",
            f"Total de Work Items: {statistics.get('total_items', 0)}",
            f"Horas Estimadas: {statistics.get('total_estimated_hours', 0):.2f}h",
            f"Horas Reales: {statistics.get('total_actual_hours', 0):.2f}h",
            f"  - Reuniones: {statistics.get('total_meeting_hours', 0):.2f}h",
            f"  - Ejecución: {statistics.get('total_execution_hours', 0):.2f}h",
            "",
            f"Varianza Total: {statistics.get('overall_variance_absolute', 0):.2f}h "
            f"({statistics.get('overall_variance_percentage', 0):.1f}%)",
            "",
            "DESVIACIONES POR NIVEL:",
            f"  - Ninguna (aceptable): {statistics.get('by_level', {}).get('none', 0)}",
            f"  - Leve: {statistics.get('by_level', {}).get('leve', 0)}",
            f"  - Moderada: {statistics.get('by_level', {}).get('moderada', 0)}",
            f"  - Alta: {statistics.get('by_level', {}).get('alta', 0)}",
            ""
        ]
        
        if include_recommendations:
            deviation_count = statistics.get('deviation_count', 0)
            acceptable_count = statistics.get('acceptable_count', 0)
            
            summary_lines.extend([
                "RECOMENDACIONES:",
                ""
            ])
            
            if deviation_count > acceptable_count:
                summary_lines.append(
                    f"- Hay {deviation_count} work items con desviaciones significativas. "
                    "Revisar estimaciones y alcances."
                )
            
            overall_variance_pct = statistics.get('overall_variance_percentage', 0)
            if overall_variance_pct > 25:
                summary_lines.append(
                    f"- La varianza total ({overall_variance_pct:.1f}%) es alta. "
                    "Considerar ajustar el proceso de estimación."
                )
            elif overall_variance_pct < -25:
                summary_lines.append(
                    f"- Las tareas se completan consistentemente por debajo del estimado "
                    f"({overall_variance_pct:.1f}%). Considerar optimizar estimaciones futuras."
                )
            else:
                summary_lines.append(
                    "- Las estimaciones están generalmente alineadas con el tiempo real."
                )
            
            summary_lines.append("")
        
        summary_lines.append("=" * 60)
        
        return "\n".join(summary_lines)
    
    def _count_by_level(self, items: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Count items by deviation level.
        
        Args:
            items: List of comparison/discrepancy items
            
        Returns:
            Dictionary with counts by level
        """
        counts = {
            'none': 0,
            'leve': 0,
            'moderada': 0,
            'alta': 0
        }
        
        for item in items:
            level = item.get('deviation_level', 'none')
            counts[level] = counts.get(level, 0) + 1
        
        return counts
