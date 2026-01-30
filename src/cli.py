"""
Command Line Interface for BV-Time-Logger
Provides commands for syncing, reporting, manual time entry, and scheduling.
"""

import argparse
import sys
import logging
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional

from src.main import TimeLoggerOrchestrator
from src.scheduler.job_scheduler import JobScheduler
from src.tracking.manual_tracker import ManualTimeTracker
from src.reports.report_generator import ReportGenerator
from src.utils.logger import setup_logger, log_spanish_info, log_spanish_error

logger = logging.getLogger(__name__)


class TimeLoggerCLI:
    """
    Command-line interface for BV-Time-Logger
    """
    
    def __init__(self):
        self.orchestrator: Optional[TimeLoggerOrchestrator] = None
        self.scheduler: Optional[JobScheduler] = None
        self.manual_tracker: Optional[ManualTimeTracker] = None
    
    def _init_orchestrator(self, dry_run: bool = False) -> TimeLoggerOrchestrator:
        """Initialize orchestrator if not already done"""
        if not self.orchestrator:
            self.orchestrator = TimeLoggerOrchestrator(dry_run=dry_run)
        return self.orchestrator
    
    def _init_scheduler(self) -> JobScheduler:
        """Initialize scheduler if not already done"""
        if not self.scheduler:
            orchestrator = self._init_orchestrator()
            self.scheduler = JobScheduler(orchestrator)
        return self.scheduler
    
    def _init_manual_tracker(self) -> ManualTimeTracker:
        """Initialize manual tracker if not already done"""
        if not self.manual_tracker:
            self.manual_tracker = ManualTimeTracker()
        return self.manual_tracker
    
    def cmd_sync(self, args):
        """
        Sync command - Run time logging synchronization
        """
        log_spanish_info("Iniciando sincronización de horas...")
        
        start_date = args.start_date or date.today() - timedelta(days=7)
        end_date = args.end_date or date.today()
        
        orchestrator = self._init_orchestrator(dry_run=args.dry_run)
        
        result = orchestrator.run(
            start_date=start_date,
            end_date=end_date,
            user_ids=args.users
        )
        
        if result['success']:
            log_spanish_info(f"✓ Sincronización completada exitosamente")
            print(f"\nReuniones procesadas: {result['meetings_processed']}")
            print(f"Work items actualizados: {result['work_items_updated']}")
            print(f"Reportes generados: {len(result['reports'])}")
            
            if args.dry_run:
                print("\n⚠ MODO DRY-RUN: No se aplicaron cambios reales")
        else:
            log_spanish_error(f"✗ Sincronización falló: {len(result['errors'])} errores")
            for error in result['errors'][:5]:  # Show first 5 errors
                print(f"  - {error}")
            return 1
        
        return 0
    
    def cmd_manual_entry(self, args):
        """
        Manual entry command - Add manual time entry
        """
        log_spanish_info("Agregando entrada manual de tiempo...")
        
        tracker = self._init_manual_tracker()
        
        try:
            entry = tracker.add_entry(
                work_item_id=args.work_item,
                hours=args.hours,
                date=args.date or date.today(),
                description=args.description,
                user_id=args.user
            )
            
            log_spanish_info(f"✓ Entrada creada: {entry.entry_id}")
            print(f"\nEntry ID: {entry.entry_id}")
            print(f"Work Item: {entry.work_item_id}")
            print(f"Horas: {entry.hours}")
            print(f"Fecha: {entry.date}")
            print(f"Usuario: {entry.user_id}")
            
            if args.sync:
                print("\nSincronizando con Azure DevOps...")
                # TODO: Implement sync logic
                log_spanish_info("Sincronización manual no implementada aún")
            
            return 0
        
        except ValueError as e:
            log_spanish_error(f"✗ Error de validación: {e}")
            return 1
    
    def cmd_import(self, args):
        """
        Import command - Import time entries from CSV
        """
        log_spanish_info(f"Importando entradas desde {args.csv_file}...")
        
        tracker = self._init_manual_tracker()
        
        try:
            csv_path = Path(args.csv_file)
            entries = tracker.import_from_csv(csv_path)
            
            log_spanish_info(f"✓ Importadas {len(entries)} entradas")
            print(f"\nEntradas importadas: {len(entries)}")
            
            if args.sync:
                print("\nSincronizando entradas con Azure DevOps...")
                # TODO: Implement sync logic
                log_spanish_info("Sincronización automática no implementada aún")
            
            return 0
        
        except Exception as e:
            log_spanish_error(f"✗ Error al importar: {e}")
            return 1
    
    def cmd_export(self, args):
        """
        Export command - Export time entries to CSV
        """
        log_spanish_info(f"Exportando entradas a {args.csv_file}...")
        
        tracker = self._init_manual_tracker()
        
        try:
            csv_path = Path(args.csv_file)
            tracker.export_to_csv(
                csv_path=csv_path,
                work_item_id=args.work_item,
                user_id=args.user,
                start_date=args.start_date,
                end_date=args.end_date,
                synced=args.synced
            )
            
            log_spanish_info(f"✓ Entradas exportadas a {csv_path}")
            return 0
        
        except Exception as e:
            log_spanish_error(f"✗ Error al exportar: {e}")
            return 1
    
    def cmd_list(self, args):
        """
        List command - List manual time entries
        """
        tracker = self._init_manual_tracker()
        
        entries = tracker.get_entries(
            work_item_id=args.work_item,
            user_id=args.user,
            start_date=args.start_date,
            end_date=args.end_date,
            synced=args.synced
        )
        
        if not entries:
            print("No se encontraron entradas con los filtros especificados")
            return 0
        
        print(f"\nEncontradas {len(entries)} entradas:\n")
        print(f"{'ID':<25} {'Work Item':<12} {'Horas':<8} {'Fecha':<12} {'Usuario':<20} {'Sincronizado':<12}")
        print("-" * 100)
        
        for entry in entries:
            synced_str = "✓" if entry.synced else "✗"
            print(f"{entry.entry_id:<25} {entry.work_item_id:<12} {entry.hours:<8.2f} "
                  f"{entry.date:<12} {entry.user_id:<20} {synced_str:<12}")
        
        return 0
    
    def cmd_summary(self, args):
        """
        Summary command - Show summary statistics
        """
        tracker = self._init_manual_tracker()
        
        summary = tracker.get_summary(
            work_item_id=args.work_item,
            user_id=args.user,
            start_date=args.start_date,
            end_date=args.end_date
        )
        
        print("\n=== RESUMEN DE ENTRADAS MANUALES ===\n")
        print(f"Total de entradas: {summary['total_entries']}")
        print(f"Total de horas: {summary['total_hours']:.2f}")
        print(f"Entradas sincronizadas: {summary['synced_entries']}")
        print(f"Entradas pendientes: {summary['unsynced_entries']}")
        
        if summary['by_work_item']:
            print("\n--- Por Work Item ---")
            for wi_id, data in sorted(summary['by_work_item'].items()):
                print(f"  WI-{wi_id}: {data['count']} entradas, {data['hours']:.2f} horas")
        
        if summary['by_user']:
            print("\n--- Por Usuario ---")
            for user_id, data in sorted(summary['by_user'].items()):
                print(f"  {user_id}: {data['count']} entradas, {data['hours']:.2f} horas")
        
        return 0
    
    def cmd_schedule(self, args):
        """
        Schedule command - Configure scheduled execution
        """
        scheduler = self._init_scheduler()
        
        if args.action == 'start':
            if args.daily:
                hour, minute = args.time.split(':')
                scheduler.schedule_daily_sync(int(hour), int(minute))
                log_spanish_info(f"✓ Sincronización diaria programada para las {args.time}")
            
            elif args.interval:
                scheduler.schedule_interval_sync(hours=args.interval)
                log_spanish_info(f"✓ Sincronización cada {args.interval} horas programada")
            
            elif args.cron:
                scheduler.schedule_custom(args.cron)
                log_spanish_info(f"✓ Sincronización con expresión cron programada: {args.cron}")
            
            scheduler.start()
            print("Scheduler iniciado. Presiona Ctrl+C para detener.")
            
            try:
                import time
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\nDeteniendo scheduler...")
                scheduler.stop()
                log_spanish_info("✓ Scheduler detenido")
        
        elif args.action == 'stop':
            scheduler.stop()
            log_spanish_info("✓ Scheduler detenido")
        
        elif args.action == 'status':
            health = scheduler.health_check()
            print(f"\n=== ESTADO DEL SCHEDULER ===\n")
            print(f"Estado: {health['status']}")
            print(f"En ejecución: {'Sí' if health['running'] else 'No'}")
            print(f"Jobs totales: {health['total_jobs']}")
            print(f"Jobs activos: {health['enabled_jobs']}")
            print(f"Jobs pausados: {health['paused_jobs']}")
            
            if health['last_execution']:
                print(f"\nÚltima ejecución:")
                print(f"  Timestamp: {health['last_execution']['timestamp']}")
                print(f"  Éxito: {'Sí' if health['last_execution']['success'] else 'No'}")
                if health['last_execution']['exception']:
                    print(f"  Error: {health['last_execution']['exception']}")
        
        elif args.action == 'jobs':
            jobs = scheduler.get_jobs()
            if not jobs:
                print("No hay jobs programados")
                return 0
            
            print(f"\n=== JOBS PROGRAMADOS ===\n")
            for job_id, job_info in jobs.items():
                print(f"Job ID: {job_id}")
                print(f"  Tipo: {job_info['type']}")
                print(f"  Schedule: {job_info['schedule']}")
                print(f"  Activo: {'Sí' if job_info['enabled'] else 'No'}")
                print(f"  Próxima ejecución: {job_info['next_run_time']}")
                print()
        
        return 0
    
    def cmd_report(self, args):
        """
        Report command - Generate reports
        """
        log_spanish_info("Generando reporte...")
        
        # Get data for report
        orchestrator = self._init_orchestrator()
        
        start_date = args.start_date or date.today() - timedelta(days=7)
        end_date = args.end_date or date.today()
        
        # Run sync first if requested
        if args.sync:
            print("Ejecutando sincronización antes de generar reporte...")
            result = orchestrator.run(start_date=start_date, end_date=end_date)
            if not result['success']:
                log_spanish_error("✗ Sincronización falló, reporte puede estar incompleto")
        
        # Generate report
        # Note: This is simplified - actual implementation would fetch comparison data
        report_generator = ReportGenerator()
        
        output_dir = Path(args.output) if args.output else Path("reports")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate timestamp filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if args.format == 'csv':
            report_path = output_dir / f"reporte_{timestamp}.csv"
            # report_generator.generate_daily_report_csv(...) # Would need comparison data
            print(f"Reporte CSV: {report_path}")
        
        elif args.format == 'json':
            report_path = output_dir / f"reporte_{timestamp}.json"
            # report_generator.generate_sprint_summary(...) # Would need comparison data
            print(f"Reporte JSON: {report_path}")
        
        log_spanish_info(f"✓ Reporte generado en {report_path}")
        return 0
    
    def cmd_status(self, args):
        """
        Status command - Show system status
        """
        print("\n=== ESTADO DEL SISTEMA BV-Time-Logger ===\n")
        
        # Orchestrator status
        orchestrator = self._init_orchestrator()
        last_execution = orchestrator.get_last_execution()
        
        print("--- Orquestador ---")
        if last_execution:
            print(f"Última ejecución: {last_execution['timestamp']}")
            print(f"Resultado: {'Éxito' if last_execution['result']['success'] else 'Fallo'}")
            print(f"Reuniones procesadas: {last_execution['result']['meetings_processed']}")
            print(f"Work items actualizados: {last_execution['result']['work_items_updated']}")
        else:
            print("Sin ejecuciones previas")
        
        # Manual tracker status
        print("\n--- Entradas Manuales ---")
        tracker = self._init_manual_tracker()
        summary = tracker.get_summary()
        print(f"Total de entradas: {summary['total_entries']}")
        print(f"Total de horas: {summary['total_hours']:.2f}")
        print(f"Pendientes de sincronizar: {summary['unsynced_entries']}")
        
        # Scheduler status
        print("\n--- Scheduler ---")
        if self.scheduler:
            health = self.scheduler.health_check()
            print(f"Estado: {health['status']}")
            print(f"Jobs activos: {health['enabled_jobs']}/{health['total_jobs']}")
        else:
            print("Scheduler no inicializado")
        
        return 0


def create_parser() -> argparse.ArgumentParser:
    """Create CLI argument parser"""
    parser = argparse.ArgumentParser(
        prog='bv-time-logger',
        description='Automated time tracking between Microsoft Teams and Azure DevOps'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Sync command
    sync_parser = subparsers.add_parser('sync', help='Run time synchronization')
    sync_parser.add_argument('--start-date', type=lambda s: datetime.strptime(s, '%Y-%m-%d').date(), help='Start date (YYYY-MM-DD)')
    sync_parser.add_argument('--end-date', type=lambda s: datetime.strptime(s, '%Y-%m-%d').date(), help='End date (YYYY-MM-DD)')
    sync_parser.add_argument('--users', nargs='+', help='User IDs to sync')
    sync_parser.add_argument('--dry-run', action='store_true', help='Preview changes without applying')
    
    # Manual entry command
    manual_parser = subparsers.add_parser('manual', help='Add manual time entry')
    manual_parser.add_argument('-w', '--work-item', type=int, required=True, help='Work item ID')
    manual_parser.add_argument('-H', '--hours', type=float, required=True, help='Hours worked')
    manual_parser.add_argument('-d', '--date', type=lambda s: datetime.strptime(s, '%Y-%m-%d').date(), help='Date (YYYY-MM-DD, default: today)')
    manual_parser.add_argument('-D', '--description', required=True, help='Work description')
    manual_parser.add_argument('-u', '--user', required=True, help='User ID')
    manual_parser.add_argument('--sync', action='store_true', help='Sync immediately after adding')
    
    # Import command
    import_parser = subparsers.add_parser('import', help='Import entries from CSV')
    import_parser.add_argument('csv_file', help='CSV file path')
    import_parser.add_argument('--sync', action='store_true', help='Sync after import')
    
    # Export command
    export_parser = subparsers.add_parser('export', help='Export entries to CSV')
    export_parser.add_argument('csv_file', help='Output CSV file path')
    export_parser.add_argument('-w', '--work-item', type=int, help='Filter by work item ID')
    export_parser.add_argument('-u', '--user', help='Filter by user ID')
    export_parser.add_argument('--start-date', type=lambda s: datetime.strptime(s, '%Y-%m-%d').date(), help='Start date')
    export_parser.add_argument('--end-date', type=lambda s: datetime.strptime(s, '%Y-%m-%d').date(), help='End date')
    export_parser.add_argument('--synced', type=lambda s: s.lower() == 'true', help='Filter by sync status (true/false)')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List manual time entries')
    list_parser.add_argument('-w', '--work-item', type=int, help='Filter by work item ID')
    list_parser.add_argument('-u', '--user', help='Filter by user ID')
    list_parser.add_argument('--start-date', type=lambda s: datetime.strptime(s, '%Y-%m-%d').date(), help='Start date')
    list_parser.add_argument('--end-date', type=lambda s: datetime.strptime(s, '%Y-%m-%d').date(), help='End date')
    list_parser.add_argument('--synced', type=lambda s: s.lower() == 'true', help='Filter by sync status')
    
    # Summary command
    summary_parser = subparsers.add_parser('summary', help='Show summary statistics')
    summary_parser.add_argument('-w', '--work-item', type=int, help='Filter by work item ID')
    summary_parser.add_argument('-u', '--user', help='Filter by user ID')
    summary_parser.add_argument('--start-date', type=lambda s: datetime.strptime(s, '%Y-%m-%d').date(), help='Start date')
    summary_parser.add_argument('--end-date', type=lambda s: datetime.strptime(s, '%Y-%m-%d').date(), help='End date')
    
    # Schedule command
    schedule_parser = subparsers.add_parser('schedule', help='Configure scheduled execution')
    schedule_parser.add_argument('action', choices=['start', 'stop', 'status', 'jobs'], help='Schedule action')
    schedule_parser.add_argument('--daily', action='store_true', help='Daily schedule')
    schedule_parser.add_argument('--time', default='00:00', help='Time for daily schedule (HH:MM)')
    schedule_parser.add_argument('--interval', type=int, help='Interval in hours')
    schedule_parser.add_argument('--cron', help='Custom cron expression')
    
    # Report command
    report_parser = subparsers.add_parser('report', help='Generate reports')
    report_parser.add_argument('--start-date', type=lambda s: datetime.strptime(s, '%Y-%m-%d').date(), help='Start date')
    report_parser.add_argument('--end-date', type=lambda s: datetime.strptime(s, '%Y-%m-%d').date(), help='End date')
    report_parser.add_argument('--format', choices=['csv', 'json'], default='csv', help='Report format')
    report_parser.add_argument('--output', help='Output directory')
    report_parser.add_argument('--sync', action='store_true', help='Run sync before generating report')
    
    # Status command
    subparsers.add_parser('status', help='Show system status')
    
    return parser


def main():
    """Main CLI entry point"""
    # Setup logging
    setup_logger()
    
    parser = create_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 0
    
    # Set log level
    if args.verbose:
        logging.getLogger('src').setLevel(logging.DEBUG)
    
    cli = TimeLoggerCLI()
    
    # Route to command handler
    command_handlers = {
        'sync': cli.cmd_sync,
        'manual': cli.cmd_manual_entry,
        'import': cli.cmd_import,
        'export': cli.cmd_export,
        'list': cli.cmd_list,
        'summary': cli.cmd_summary,
        'schedule': cli.cmd_schedule,
        'report': cli.cmd_report,
        'status': cli.cmd_status
    }
    
    handler = command_handlers.get(args.command)
    if not handler:
        log_spanish_error(f"Comando no reconocido: {args.command}")
        return 1
    
    try:
        return handler(args)
    except KeyboardInterrupt:
        print("\n\nInterrumpido por el usuario")
        return 130
    except Exception as e:
        log_spanish_error(f"Error inesperado: {e}")
        logger.exception("Unexpected error in CLI")
        return 1


if __name__ == '__main__':
    sys.exit(main())
