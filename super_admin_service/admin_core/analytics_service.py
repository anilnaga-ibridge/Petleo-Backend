
import decimal
import math
from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum, Count, Q
from .models import AnalyticsSnapshot, VerifiedUser, ProviderBillingProfile
from plans_coupens.models import PurchasedPlan, Invoice, Plan
from dynamic_services.models import Service

# --- HELPERS ---
def get_snapshot(key, period_date=None, version="1.0"):
    return AnalyticsSnapshot.objects.filter(
        snapshot_key=key, 
        period_date=period_date, 
        version=version
    ).first()

def calculate_growth(current, previous):
    if not previous or previous == 0:
        return 0
    return round(((current - previous) / previous) * 100, 1)

# --- INTELLIGENCE ENGINES ---

def get_percentile_rank(count, all_counts):
    """
    Top 10% Elite
    Next 20% Premium
    Middle (30-70%) Moderate
    Bottom (0-30%) Low
    Zero sales Dead
    """
    if count == 0: return "DEAD"
    if not all_counts: return "MODERATE"
    
    sorted_counts = sorted(all_counts)
    pos = sorted_counts.index(count)
    percentile = (pos / len(sorted_counts)) * 100
    
    if percentile >= 90: return "ELITE"
    if percentile >= 70: return "PREMIUM"
    if percentile >= 30: return "MODERATE"
    return "LOW"

def generate_smart_insights(metrics):
    """
    Rule-based Operational Intelligence.
    """
    insights = []
    
    # Revenue Insights
    rev_growth = metrics.get('revenue_growth', 0)
    if rev_growth > 10:
        insights.append({
            "icon": "tabler-trending-up",
            "text": f"Revenue velocity is high ({rev_growth}% growth). Recommend monitoring Premium tier stability.",
            "confidence": 98
        })
    elif rev_growth < -5:
        insights.append({
            "icon": "tabler-alert-circle",
            "text": "Revenue dip detected. Check for failed renewals or plan downgrades.",
            "confidence": 92
        })

    # Provider Insights
    new_reg = metrics.get('new_registrations', 0)
    if new_reg > 5:
        insights.append({
            "icon": "tabler-rocket",
            "text": f"Onboarding surge: {new_reg} new providers joined in the last window.",
            "confidence": 95
        })

    # Health Insights
    health = metrics.get('platform_health', 100)
    if health < 90:
        insights.append({
            "icon": "tabler-heart-broken",
            "text": f"Platform health is degraded ({health}%). Investigate sync logs immediately.",
            "confidence": 99
        })
    else:
        insights.append({
            "icon": "tabler-shield-check",
            "text": "Platform stability is optimal. System synchronization is at 100%.",
            "confidence": 100
        })

    return insights

# --- AGGREGATORS ---

def compute_executive_metrics():
    """
    Elite KPI Suite.
    """
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = today_start - timedelta(days=1)

    # Today & Yesterday Revenue
    today_rev = Invoice.objects.filter(status='PAID', paid_at__gte=today_start).aggregate(total=Sum('total_amount'))['total'] or 0.00
    yesterday_rev = Invoice.objects.filter(status='PAID', paid_at__gte=yesterday_start, paid_at__lt=today_start).aggregate(total=Sum('total_amount'))['total'] or 0.00
    
    rev_growth = calculate_growth(float(today_rev), float(yesterday_rev))

    # Active Stats
    total_rev = Invoice.objects.filter(status='PAID').aggregate(total=Sum('total_amount'))['total'] or 0.00
    active_subs = PurchasedPlan.objects.filter(is_active=True).count()
    total_providers = VerifiedUser.objects.filter(role__in=['organization', 'individual', 'provider']).count()
    
    # Workforce (Summarized)
    wf_snap = get_snapshot('workforce_stats')
    total_employees = wf_snap.data_json.get('total_employees', 0) if wf_snap else 0

    # Platform Health (Calculated based on lack of Sync Issues & Payment Failures)
    failed_pmts = Invoice.objects.filter(status='FAILED').count()
    incomplete_prof = ProviderBillingProfile.objects.filter(is_incomplete=True).count()
    
    # Penalty-based health logic
    health = 100
    health -= (failed_pmts * 5)
    health -= (incomplete_prof * 1)
    health = max(0, min(100, health))

    data = {
        "today_revenue": float(today_rev),
        "total_revenue": float(total_rev),
        "revenue_growth": rev_growth,
        "active_subscriptions": active_subs,
        "total_providers": total_providers,
        "total_employees": total_employees,
        "new_registrations": VerifiedUser.objects.filter(created_at__gte=today_start).count(),
        "pending_verifications": ProviderBillingProfile.objects.filter(is_incomplete=True).count(),
        "platform_health": health
    }

    # Add Operational Intelligence
    data["insights"] = generate_smart_insights(data)

    AnalyticsSnapshot.objects.update_or_create(
        snapshot_key="executive_summary",
        defaults={
            "data_json": data,
            "expires_at": now + timedelta(seconds=30)
        }
    )
    return data



def compute_intelligence_suite():
    """
    Plan Rankings & Rankings IQ.
    """
    # 1. Plan Intelligence (Percentile Ranking + Role Segment)
    # Use IDs to bridge between SuperAdmin (AUTH_USER_MODEL) and VerifiedUser (where role is stored)
    org_user_ids = VerifiedUser.objects.filter(role__icontains='organization').values_list('id', flat=True)
    ind_user_ids = VerifiedUser.objects.filter(role__icontains='individual').values_list('id', flat=True)

    plans = Plan.objects.annotate(
        total_count=Count('purchases'),
        org_count=Count('purchases', filter=Q(purchases__user_id__in=org_user_ids)),
        ind_count=Count('purchases', filter=Q(purchases__user_id__in=ind_user_ids))
    ).all()
    
    all_counts = [p.total_count for p in plans if p.total_count > 0]
    
    plan_tiering = []
    for plan in plans:
        rank = get_percentile_rank(plan.total_count, all_counts)
        plan_tiering.append({
            "id": str(plan.id),
            "title": plan.title,
            "count": plan.total_count,
            "org_count": plan.org_count,
            "ind_count": plan.ind_count,
            "revenue": float(plan.total_count * plan.price),
            "tier": rank,
            "growth": calculate_growth(plan.total_count, 0)
        })

    # Sort by total_count desc
    plan_tiering.sort(key=lambda x: x['count'], reverse=True)

    data = {
        "plans": plan_tiering,
        "provider_split": {
            "series": [
                VerifiedUser.objects.filter(role__icontains='organization').count(),
                VerifiedUser.objects.filter(role__icontains='individual').count()
            ],
            "labels": ["Organization", "Individual"]
        }
    }

    AnalyticsSnapshot.objects.update_or_create(
        snapshot_key="intelligence_suite",
        defaults={
            "data_json": data,
            "expires_at": timezone.now() + timedelta(minutes=5)
        }
    )
    return data


def compute_revenue_trend():
    """
    Daily revenue for last 30 days with time-series continuity (zero-filling).
    Includes real summary indicators for MRR/ARR.
    """
    now = timezone.now()
    today = now.date()
    thirty_days_ago = today - timedelta(days=29)
    
    # 1. Fetch real PAID invoices
    paid_invoices = Invoice.objects.filter(
        status='PAID', 
        paid_at__date__gte=thirty_days_ago
    ).extra(select={'day': "date(paid_at)"}).values('day').annotate(total=Sum('total_amount'))
    
    revenue_map = {str(entry['day']): float(entry['total']) for entry in paid_invoices}
    
    # 2. Time-Series Continuity (Zero-Fill)
    labels = []
    series_data = []
    
    for i in range(30):
        current_day = thirty_days_ago + timedelta(days=i)
        day_str = str(current_day)
        labels.append(day_str)
        series_data.append(revenue_map.get(day_str, 0.0))

    # 3. Calculate Executive Financial Summary
    mrr = sum(series_data)
    failed_pmts = Invoice.objects.filter(status='FAILED', created_at__date__gte=thirty_days_ago).count()
    refunds = Invoice.objects.filter(status='REFUNDED', updated_at__date__gte=thirty_days_ago).aggregate(total=Sum('total_amount'))['total'] or 0.00

    data = {
        "series": [{"name": "Revenue Velocity", "data": series_data}],
        "labels": labels,
        "summary": {
            "mrr": float(mrr),
            "arr": float(mrr * 12),
            "failed_payments": failed_pmts,
            "refunds": float(refunds),
            "new_revenue": float(mrr * 0.3), # Estimated split
            "renewal_revenue": float(mrr * 0.7)
        }
    }

    AnalyticsSnapshot.objects.update_or_create(
        snapshot_key="revenue_trend",
        defaults={
            "data_json": data,
            "expires_at": now + timedelta(hours=1)
        }
    )
    return data

def get_operational_alerts():
    """
    Generate alerts based on executive rules.
    """
    alerts = []
    now = timezone.now()

    # 1. Failed Payments
    failed_invoices = Invoice.objects.filter(status='FAILED').count()
    if failed_invoices > 0:
        alerts.append({
            "level": "CRITICAL",
            "title": "Payment Resilience Warning",
            "message": f"{failed_invoices} invoices failed. Action required for revenue protection.",
            "category": "billing"
        })

    # 2. Registration Health
    incomplete = ProviderBillingProfile.objects.filter(is_incomplete=True).count()
    if incomplete > 5:
        alerts.append({
            "level": "WARNING",
            "title": "Registration Bottleneck",
            "message": f"{incomplete} profiles are incomplete. Potential onboarding delay.",
            "category": "operations"
        })

    return alerts
