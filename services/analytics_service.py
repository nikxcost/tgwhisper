"""
Analytics Service for TGWhisper Bot

Provides metrics calculation and export functionality for product analytics:
- DAU/MAU (Daily/Monthly Active Users)
- Conversion rate
- Retention rate
- Profile popularity
- Performance metrics
- Error rates
- Usage patterns by time
"""

import csv
import json
from io import BytesIO, StringIO
from zipfile import ZipFile
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional

from sqlalchemy import func, distinct, desc, and_
from sqlalchemy.orm import Session

from database.models import User, Profile, UsageLog


class AnalyticsService:
    """Service for calculating analytics metrics and generating exports"""

    def __init__(self, session: Session):
        self.session = session

    # ==================== Core Metrics ====================

    def get_dau(self, target_date: date = None) -> int:
        """
        Get Daily Active Users count for a specific date.
        Uses users.last_activity timestamp.
        """
        if target_date is None:
            target_date = date.today()

        count = self.session.query(func.count(distinct(User.id))).filter(
            func.date(User.last_activity) == target_date
        ).scalar()

        return count or 0

    def get_mau(self, days: int = 30) -> int:
        """
        Get Monthly Active Users count for the last N days.
        """
        cutoff = datetime.utcnow() - timedelta(days=days)

        count = self.session.query(func.count(distinct(User.id))).filter(
            User.last_activity >= cutoff
        ).scalar()

        return count or 0

    def get_total_users(self) -> int:
        """Get total registered users count"""
        return self.session.query(func.count(User.id)).scalar() or 0

    def get_conversion_rate(self, days: int = None) -> float:
        """
        Calculate conversion rate: users with successful processing / total users.
        Returns percentage (0-100).
        """
        if days:
            cutoff = datetime.utcnow() - timedelta(days=days)
            total_users = self.session.query(func.count(User.id)).filter(
                User.created_at >= cutoff
            ).scalar() or 0

            converted_users = self.session.query(
                func.count(distinct(UsageLog.user_id))
            ).filter(
                UsageLog.created_at >= cutoff,
                UsageLog.success == True
            ).scalar() or 0
        else:
            total_users = self.get_total_users()
            converted_users = self.session.query(
                func.count(distinct(UsageLog.user_id))
            ).filter(
                UsageLog.success == True
            ).scalar() or 0

        if total_users == 0:
            return 0.0

        return round((converted_users / total_users) * 100, 2)

    def get_retention_rate(self, cohort_days: int = 30, return_days: int = 7) -> float:
        """
        Calculate retention rate: percentage of users who return after N days.

        Args:
            cohort_days: Look at users registered in the last N days
            return_days: Check if they were active at least N days after registration

        Returns:
            Retention rate as percentage (0-100)
        """
        cohort_cutoff = datetime.utcnow() - timedelta(days=cohort_days)

        # Get users in cohort (registered in last cohort_days)
        cohort_users = self.session.query(User.id, User.created_at).filter(
            User.created_at >= cohort_cutoff,
            User.created_at <= datetime.utcnow() - timedelta(days=return_days)
        ).all()

        if not cohort_users:
            return 0.0

        retained_count = 0
        for user_id, created_at in cohort_users:
            # Check if user had activity at least return_days after registration
            return_cutoff = created_at + timedelta(days=return_days)

            later_activity = self.session.query(UsageLog.id).filter(
                UsageLog.user_id == user_id,
                UsageLog.created_at >= return_cutoff
            ).first()

            if later_activity:
                retained_count += 1

        return round((retained_count / len(cohort_users)) * 100, 2)

    # ==================== Profile Analytics ====================

    def get_profile_popularity(self, days: int = None) -> List[Dict]:
        """
        Get profile usage statistics.

        Returns list of dicts:
        [
            {
                'profile_id': 1,
                'profile_name': 'Деловая переписка',
                'is_default': True,
                'usage_count': 150,
                'usage_percentage': 43.9
            }, ...
        ]
        """
        query = self.session.query(
            Profile.id,
            Profile.name,
            Profile.is_default,
            func.count(UsageLog.id).label('usage_count')
        ).outerjoin(UsageLog, and_(
            Profile.id == UsageLog.profile_id,
            UsageLog.success == True
        ))

        if days:
            cutoff = datetime.utcnow() - timedelta(days=days)
            query = query.filter(
                (UsageLog.created_at >= cutoff) | (UsageLog.id == None)
            )

        results = query.group_by(Profile.id).order_by(desc('usage_count')).all()

        total = sum(r.usage_count for r in results)

        return [{
            'profile_id': r.id,
            'profile_name': r.name,
            'is_default': r.is_default,
            'usage_count': r.usage_count,
            'usage_percentage': round(r.usage_count / total * 100, 2) if total > 0 else 0.0
        } for r in results]

    # ==================== Performance Metrics ====================

    def get_performance_metrics(self, days: int = None) -> Dict:
        """
        Get performance statistics.

        Returns:
        {
            'avg_processing_seconds': 5.2,
            'max_processing_seconds': 25,
            'min_processing_seconds': 1,
            'avg_audio_duration_seconds': 11.3,
            'efficiency_ratio': 0.46,
            'total_processed': 342
        }
        """
        query = self.session.query(
            func.avg(UsageLog.processing_time_seconds).label('avg_processing'),
            func.max(UsageLog.processing_time_seconds).label('max_processing'),
            func.min(UsageLog.processing_time_seconds).label('min_processing'),
            func.avg(UsageLog.audio_duration_seconds).label('avg_audio'),
            func.count(UsageLog.id).label('total')
        ).filter(UsageLog.success == True)

        if days:
            cutoff = datetime.utcnow() - timedelta(days=days)
            query = query.filter(UsageLog.created_at >= cutoff)

        result = query.first()

        avg_processing = result.avg_processing or 0
        avg_audio = result.avg_audio or 0
        efficiency = round(avg_processing / avg_audio, 2) if avg_audio > 0 else 0

        return {
            'avg_processing_seconds': round(avg_processing, 2),
            'max_processing_seconds': result.max_processing or 0,
            'min_processing_seconds': result.min_processing or 0,
            'avg_audio_duration_seconds': round(avg_audio, 2),
            'efficiency_ratio': efficiency,
            'total_processed': result.total or 0
        }

    def identify_bottlenecks(self, days: int = None) -> Dict:
        """
        Identify performance bottlenecks.

        Returns:
        {
            'slowest_profiles': [{'name': '...', 'avg_seconds': 5.2}],
            'outlier_count': 5,
            'outlier_threshold_seconds': 10.4
        }
        """
        base_filter = [UsageLog.success == True]
        if days:
            cutoff = datetime.utcnow() - timedelta(days=days)
            base_filter.append(UsageLog.created_at >= cutoff)

        # Processing time by profile
        by_profile = self.session.query(
            Profile.name,
            func.avg(UsageLog.processing_time_seconds).label('avg_time')
        ).join(UsageLog, Profile.id == UsageLog.profile_id).filter(
            *base_filter
        ).group_by(Profile.id).order_by(desc('avg_time')).limit(5).all()

        # Calculate average for outlier detection
        avg_time = self.session.query(
            func.avg(UsageLog.processing_time_seconds)
        ).filter(*base_filter).scalar() or 0

        threshold = avg_time * 2

        # Count outliers
        outlier_filter = base_filter + [UsageLog.processing_time_seconds > threshold]
        outlier_count = self.session.query(
            func.count(UsageLog.id)
        ).filter(*outlier_filter).scalar() or 0

        return {
            'slowest_profiles': [
                {'name': r.name, 'avg_seconds': round(r.avg_time, 2)}
                for r in by_profile
            ],
            'outlier_count': outlier_count,
            'outlier_threshold_seconds': round(threshold, 2)
        }

    # ==================== Error Tracking ====================

    def get_error_rates(self, days: int = None) -> Dict:
        """
        Get error statistics.

        Returns:
        {
            'total_requests': 350,
            'failed_requests': 8,
            'success_rate': 97.7,
            'error_rate': 2.3,
            'common_errors': [{'message': '...', 'count': 5}]
        }
        """
        base_filter = []
        if days:
            cutoff = datetime.utcnow() - timedelta(days=days)
            base_filter.append(UsageLog.created_at >= cutoff)

        total = self.session.query(func.count(UsageLog.id)).filter(
            *base_filter
        ).scalar() or 0

        failed = self.session.query(func.count(UsageLog.id)).filter(
            *base_filter,
            UsageLog.success == False
        ).scalar() or 0

        # Get common errors
        error_query = self.session.query(
            UsageLog.error_message,
            func.count(UsageLog.id).label('count')
        ).filter(
            *base_filter,
            UsageLog.success == False,
            UsageLog.error_message != None
        ).group_by(UsageLog.error_message).order_by(desc('count')).limit(5)

        common_errors = [
            {'message': r.error_message[:100] if r.error_message else 'Unknown', 'count': r.count}
            for r in error_query.all()
        ]

        success_rate = round((total - failed) / total * 100, 2) if total > 0 else 100.0
        error_rate = round(failed / total * 100, 2) if total > 0 else 0.0

        return {
            'total_requests': total,
            'failed_requests': failed,
            'success_rate': success_rate,
            'error_rate': error_rate,
            'common_errors': common_errors
        }

    # ==================== Usage Patterns ====================

    def get_usage_by_hour(self, days: int = None) -> Dict[int, int]:
        """
        Get usage distribution by hour of day.

        Returns: {0: 5, 1: 2, ..., 23: 10}
        """
        base_filter = [UsageLog.success == True]
        if days:
            cutoff = datetime.utcnow() - timedelta(days=days)
            base_filter.append(UsageLog.created_at >= cutoff)

        # SQLite uses strftime for hour extraction
        results = self.session.query(
            func.strftime('%H', UsageLog.created_at).label('hour'),
            func.count(UsageLog.id).label('count')
        ).filter(*base_filter).group_by('hour').order_by('hour').all()

        # Initialize all hours with 0
        hourly = {h: 0 for h in range(24)}
        for r in results:
            if r.hour is not None:
                hourly[int(r.hour)] = r.count

        return hourly

    def get_usage_by_weekday(self, days: int = None) -> Dict[str, int]:
        """
        Get usage distribution by day of week.

        Returns: {'Monday': 45, 'Tuesday': 52, ...}
        """
        base_filter = [UsageLog.success == True]
        if days:
            cutoff = datetime.utcnow() - timedelta(days=days)
            base_filter.append(UsageLog.created_at >= cutoff)

        # SQLite strftime %w: 0=Sunday, 6=Saturday
        results = self.session.query(
            func.strftime('%w', UsageLog.created_at).label('weekday'),
            func.count(UsageLog.id).label('count')
        ).filter(*base_filter).group_by('weekday').order_by('weekday').all()

        weekday_names = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']

        # Initialize all days with 0
        weekly = {name: 0 for name in weekday_names}
        for r in results:
            if r.weekday is not None:
                weekly[weekday_names[int(r.weekday)]] = r.count

        return weekly

    # ==================== Export Functions ====================

    def get_full_report(self, days: int = None) -> Dict:
        """
        Generate complete analytics report as dictionary.
        """
        today = date.today()

        return {
            'export_date': datetime.utcnow().isoformat() + 'Z',
            'period_days': days or 'all_time',
            'summary': {
                'dau_today': self.get_dau(today),
                'mau': self.get_mau(days) if days else self.get_mau(30),
                'total_users': self.get_total_users(),
                'conversion_rate': self.get_conversion_rate(days),
                'retention_rate_7d': self.get_retention_rate(days or 30, 7),
            },
            'profile_popularity': self.get_profile_popularity(days),
            'performance': self.get_performance_metrics(days),
            'bottlenecks': self.identify_bottlenecks(days),
            'error_rates': self.get_error_rates(days),
            'usage_patterns': {
                'by_hour': self.get_usage_by_hour(days),
                'by_weekday': self.get_usage_by_weekday(days)
            }
        }

    def export_to_json(self, days: int = None) -> bytes:
        """
        Export analytics to JSON format.

        Returns: UTF-8 encoded JSON bytes
        """
        report = self.get_full_report(days)
        return json.dumps(report, indent=2, ensure_ascii=False).encode('utf-8')

    def export_to_csv(self, days: int = None) -> BytesIO:
        """
        Export analytics to CSV format (multiple files in ZIP archive).

        Returns: BytesIO containing ZIP file
        """
        report = self.get_full_report(days)
        period_str = f"Last {days} days" if days else "All time"

        zip_buffer = BytesIO()

        with ZipFile(zip_buffer, 'w') as zipf:
            # 1. Summary CSV
            summary_buffer = StringIO()
            writer = csv.writer(summary_buffer)
            writer.writerow(['Metric', 'Value', 'Period'])
            writer.writerow(['DAU (Today)', report['summary']['dau_today'], date.today().isoformat()])
            writer.writerow(['MAU', report['summary']['mau'], period_str])
            writer.writerow(['Total Users', report['summary']['total_users'], 'All time'])
            writer.writerow(['Conversion Rate (%)', report['summary']['conversion_rate'], period_str])
            writer.writerow(['Retention Rate 7d (%)', report['summary']['retention_rate_7d'], period_str])
            writer.writerow(['Total Processed', report['performance']['total_processed'], period_str])
            writer.writerow(['Success Rate (%)', report['error_rates']['success_rate'], period_str])
            zipf.writestr('summary.csv', summary_buffer.getvalue())

            # 2. Profile Stats CSV
            profile_buffer = StringIO()
            writer = csv.writer(profile_buffer)
            writer.writerow(['Profile Name', 'Usage Count', 'Percentage (%)', 'Is Default'])
            for p in report['profile_popularity']:
                writer.writerow([
                    p['profile_name'],
                    p['usage_count'],
                    p['usage_percentage'],
                    'Yes' if p['is_default'] else 'No'
                ])
            zipf.writestr('profile_stats.csv', profile_buffer.getvalue())

            # 3. Performance CSV
            perf_buffer = StringIO()
            writer = csv.writer(perf_buffer)
            writer.writerow(['Metric', 'Value'])
            perf = report['performance']
            writer.writerow(['Average Processing (seconds)', perf['avg_processing_seconds']])
            writer.writerow(['Max Processing (seconds)', perf['max_processing_seconds']])
            writer.writerow(['Min Processing (seconds)', perf['min_processing_seconds']])
            writer.writerow(['Average Audio Duration (seconds)', perf['avg_audio_duration_seconds']])
            writer.writerow(['Efficiency Ratio', perf['efficiency_ratio']])

            # Bottlenecks
            writer.writerow([])
            writer.writerow(['Bottlenecks', ''])
            writer.writerow(['Outlier Count', report['bottlenecks']['outlier_count']])
            writer.writerow(['Outlier Threshold (seconds)', report['bottlenecks']['outlier_threshold_seconds']])
            writer.writerow([])
            writer.writerow(['Slowest Profiles', 'Avg Processing (seconds)'])
            for sp in report['bottlenecks']['slowest_profiles']:
                writer.writerow([sp['name'], sp['avg_seconds']])
            zipf.writestr('performance.csv', perf_buffer.getvalue())

            # 4. Errors CSV
            error_buffer = StringIO()
            writer = csv.writer(error_buffer)
            writer.writerow(['Metric', 'Value'])
            errors = report['error_rates']
            writer.writerow(['Total Requests', errors['total_requests']])
            writer.writerow(['Failed Requests', errors['failed_requests']])
            writer.writerow(['Success Rate (%)', errors['success_rate']])
            writer.writerow(['Error Rate (%)', errors['error_rate']])
            writer.writerow([])
            writer.writerow(['Common Errors', 'Count'])
            for e in errors['common_errors']:
                writer.writerow([e['message'], e['count']])
            zipf.writestr('errors.csv', error_buffer.getvalue())

            # 5. Usage Patterns CSV
            patterns_buffer = StringIO()
            writer = csv.writer(patterns_buffer)

            # Hourly
            writer.writerow(['Usage by Hour', ''])
            writer.writerow(['Hour', 'Count'])
            for hour, count in sorted(report['usage_patterns']['by_hour'].items()):
                writer.writerow([f"{hour:02d}:00", count])

            writer.writerow([])

            # Weekly
            writer.writerow(['Usage by Weekday', ''])
            writer.writerow(['Day', 'Count'])
            weekday_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            for day in weekday_order:
                writer.writerow([day, report['usage_patterns']['by_weekday'].get(day, 0)])

            zipf.writestr('usage_patterns.csv', patterns_buffer.getvalue())

        zip_buffer.seek(0)
        return zip_buffer
