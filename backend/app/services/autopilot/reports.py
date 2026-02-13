"""
AutoPilot Reports Service

Phase 4: Generate P&L reports, tax summaries, and downloadable files.
"""
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any
from uuid import UUID
import os
import csv
import io
from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.autopilot import AutoPilotReport, AutoPilotTradeJournal


class ReportService:
    """Service for generating and managing reports."""

    @staticmethod
    async def list_reports(
        db: AsyncSession,
        user_id: UUID,
        report_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """List user's reports."""
        conditions = [AutoPilotReport.user_id == user_id]

        if report_type:
            conditions.append(AutoPilotReport.report_type == report_type)

        # Count total
        count_query = select(func.count(AutoPilotReport.id)).where(and_(*conditions))
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Fetch reports
        query = select(AutoPilotReport).where(and_(*conditions))
        query = query.order_by(desc(AutoPilotReport.created_at))
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await db.execute(query)
        reports = result.scalars().all()

        return {
            "reports": reports,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }

    @staticmethod
    async def get_report(
        db: AsyncSession,
        report_id: int,
        user_id: UUID
    ) -> Optional[AutoPilotReport]:
        """Get a report by ID."""
        query = select(AutoPilotReport).where(
            AutoPilotReport.id == report_id,
            AutoPilotReport.user_id == user_id
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def generate_report(
        db: AsyncSession,
        user_id: UUID,
        request: Any
    ) -> AutoPilotReport:
        """Generate a new report."""

        # Generate report name
        name = request.name or f"{request.report_type.value.title()} Report - {request.start_date} to {request.end_date}"

        # Create report record (initially not ready)
        report = AutoPilotReport(
            user_id=user_id,
            report_type=request.report_type.value,
            name=name,
            description=request.description,
            start_date=request.start_date,
            end_date=request.end_date,
            strategy_id=request.strategy_id,
            format=request.format.value,
            is_ready=False,
            report_data={}
        )

        db.add(report)
        await db.commit()
        await db.refresh(report)

        # Generate report data
        try:
            report_data = await ReportService._generate_report_data(
                db, user_id, request.start_date, request.end_date,
                request.report_type.value, request.strategy_id
            )

            report.report_data = report_data
            report.is_ready = True
            report.generated_at = datetime.utcnow()

            # Generate file if needed
            if request.format.value in ["csv", "excel"]:
                file_path = await ReportService._generate_file(
                    report_data, report.id, request.format.value
                )
                report.file_path = file_path
                if file_path and os.path.exists(file_path):
                    report.file_size_bytes = os.path.getsize(file_path)

            await db.commit()
            await db.refresh(report)

        except Exception as e:
            report.error_message = str(e)
            report.is_ready = False
            await db.commit()

        return report

    @staticmethod
    async def _generate_report_data(
        db: AsyncSession,
        user_id: UUID,
        start_date: date,
        end_date: date,
        report_type: str,
        strategy_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Generate report data based on type."""

        conditions = [
            AutoPilotTradeJournal.user_id == user_id,
            AutoPilotTradeJournal.is_open == False,
            AutoPilotTradeJournal.entry_time >= datetime.combine(start_date, datetime.min.time()),
            AutoPilotTradeJournal.entry_time <= datetime.combine(end_date, datetime.max.time())
        ]

        if strategy_id:
            conditions.append(AutoPilotTradeJournal.strategy_id == strategy_id)

        # Get all trades
        query = select(AutoPilotTradeJournal).where(and_(*conditions)).order_by(AutoPilotTradeJournal.entry_time)
        result = await db.execute(query)
        trades = result.scalars().all()

        # Calculate summary
        total_trades = len(trades)
        winning_trades = sum(1 for t in trades if t.net_pnl and t.net_pnl > 0)
        losing_trades = total_trades - winning_trades
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

        gross_pnl = sum(t.gross_pnl or Decimal("0") for t in trades)
        net_pnl = sum(t.net_pnl or Decimal("0") for t in trades)
        total_brokerage = sum(t.brokerage or Decimal("0") for t in trades)
        total_taxes = sum(t.taxes or Decimal("0") for t in trades)

        # Build trades list for report
        trades_data = []
        for trade in trades:
            trades_data.append({
                "id": trade.id,
                "strategy_name": trade.strategy_name,
                "underlying": trade.underlying,
                "position_type": trade.position_type,
                "entry_time": trade.entry_time.isoformat() if trade.entry_time else None,
                "exit_time": trade.exit_time.isoformat() if trade.exit_time else None,
                "holding_duration_minutes": trade.holding_duration_minutes,
                "lots": trade.lots,
                "entry_premium": float(trade.entry_premium) if trade.entry_premium else None,
                "exit_premium": float(trade.exit_premium) if trade.exit_premium else None,
                "gross_pnl": float(trade.gross_pnl) if trade.gross_pnl else None,
                "brokerage": float(trade.brokerage) if trade.brokerage else None,
                "taxes": float(trade.taxes) if trade.taxes else None,
                "net_pnl": float(trade.net_pnl) if trade.net_pnl else None,
                "pnl_percentage": float(trade.pnl_percentage) if trade.pnl_percentage else None,
                "exit_reason": trade.exit_reason
            })

        return {
            "summary": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "total_trades": total_trades,
                "winning_trades": winning_trades,
                "losing_trades": losing_trades,
                "win_rate": round(win_rate, 2),
                "gross_pnl": float(gross_pnl),
                "net_pnl": float(net_pnl),
                "total_brokerage": float(total_brokerage),
                "total_taxes": float(total_taxes)
            },
            "trades": trades_data
        }

    @staticmethod
    async def _generate_file(
        report_data: Dict[str, Any],
        report_id: int,
        format_type: str
    ) -> Optional[str]:
        """Generate downloadable file."""

        # Create reports directory
        reports_dir = os.path.join(os.path.dirname(__file__), "..", "..", "reports")
        os.makedirs(reports_dir, exist_ok=True)

        if format_type == "csv":
            file_path = os.path.join(reports_dir, f"report_{report_id}.csv")

            with open(file_path, 'w', newline='') as f:
                writer = csv.writer(f)

                # Header
                writer.writerow([
                    "ID", "Strategy", "Underlying", "Position Type",
                    "Entry Time", "Exit Time", "Duration (min)",
                    "Lots", "Entry Premium", "Exit Premium",
                    "Gross P&L", "Brokerage", "Taxes", "Net P&L", "P&L %",
                    "Exit Reason"
                ])

                # Data
                for trade in report_data.get("trades", []):
                    writer.writerow([
                        trade.get("id"),
                        trade.get("strategy_name"),
                        trade.get("underlying"),
                        trade.get("position_type"),
                        trade.get("entry_time"),
                        trade.get("exit_time"),
                        trade.get("holding_duration_minutes"),
                        trade.get("lots"),
                        trade.get("entry_premium"),
                        trade.get("exit_premium"),
                        trade.get("gross_pnl"),
                        trade.get("brokerage"),
                        trade.get("taxes"),
                        trade.get("net_pnl"),
                        trade.get("pnl_percentage"),
                        trade.get("exit_reason")
                    ])

            return file_path

        return None

    @staticmethod
    async def delete_report(
        db: AsyncSession,
        report_id: int,
        user_id: UUID
    ) -> bool:
        """Delete a report."""
        query = select(AutoPilotReport).where(
            AutoPilotReport.id == report_id,
            AutoPilotReport.user_id == user_id
        )
        result = await db.execute(query)
        report = result.scalar_one_or_none()

        if not report:
            return False

        # Delete file if exists
        if report.file_path and os.path.exists(report.file_path):
            os.remove(report.file_path)

        await db.delete(report)
        await db.commit()

        return True

    @staticmethod
    async def get_tax_summary(
        db: AsyncSession,
        user_id: UUID,
        financial_year: str
    ) -> Dict[str, Any]:
        """Get tax summary for a financial year."""

        # Parse financial year (e.g., '2024-25' -> Apr 1, 2024 to Mar 31, 2025)
        start_year = int(financial_year.split('-')[0])
        start_date = date(start_year, 4, 1)
        end_date = date(start_year + 1, 3, 31)

        conditions = [
            AutoPilotTradeJournal.user_id == user_id,
            AutoPilotTradeJournal.is_open == False,
            AutoPilotTradeJournal.exit_time >= datetime.combine(start_date, datetime.min.time()),
            AutoPilotTradeJournal.exit_time <= datetime.combine(end_date, datetime.max.time())
        ]

        # Get all trades
        query = select(AutoPilotTradeJournal).where(and_(*conditions))
        result = await db.execute(query)
        trades = result.scalars().all()

        # Calculate totals
        # F&O trades are non-speculative business income
        fo_turnover = Decimal("0")
        fo_pnl = Decimal("0")
        total_brokerage = Decimal("0")
        total_taxes = Decimal("0")

        for trade in trades:
            # Turnover for F&O = absolute value of P&L + option premium received
            if trade.gross_pnl:
                fo_turnover += abs(trade.gross_pnl)
            if trade.net_pnl:
                fo_pnl += trade.net_pnl
            if trade.brokerage:
                total_brokerage += trade.brokerage
            if trade.taxes:
                total_taxes += trade.taxes

        # Calculate if tax audit required (turnover > 6 crore, or > 2 crore if opt-out of presumptive)
        audit_threshold = Decimal("60000000")  # 6 crore
        audit_required = fo_turnover > audit_threshold

        return {
            "financial_year": financial_year,
            "total_turnover": fo_turnover,
            "speculative_pnl": Decimal("0"),  # No speculative trading in this system
            "non_speculative_pnl": fo_pnl,  # F&O is non-speculative
            "total_brokerage": total_brokerage,
            "total_taxes_paid": total_taxes,  # STT, GST, etc.
            "net_taxable_income": fo_pnl,  # Simplified - actual would consider expenses
            "audit_required": audit_required,
            "trade_count": len(trades),
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        }
