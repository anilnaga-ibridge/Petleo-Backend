import uuid
from django.db import models
from django.utils import timezone
from django.utils import timezone

class EmployeeWeeklySchedule(models.Model):
    """
    Weekly schedule for an employee (e.g., Monday 09:00 - 14:00).
    Requires provider approval before becoming active.
    """
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]

    DAY_CHOICES = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey('service_provider.OrganizationEmployee', on_delete=models.CASCADE, related_name='weekly_schedules')
    
    day_of_week = models.IntegerField(choices=DAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    approved_by_auth_id = models.UUIDField(null=True, blank=True)
    rejection_reason = models.TextField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # Prevent duplicate schedule entries for the same day (unless they have different statuses)
        # but usually, we only care about the latest approved one.
        indexes = [
            models.Index(fields=['employee', 'day_of_week', 'status']),
        ]

    def __str__(self):
        return f"{self.employee.full_name} - Day {self.day_of_week} ({self.status})"


class EmployeeLeave(models.Model):
    """
    Specific dates when an employee is unavailable (Leaves).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey('service_provider.OrganizationEmployee', on_delete=models.CASCADE, related_name='leaves')
    
    date = models.DateField()
    reason = models.CharField(max_length=255, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('employee', 'date')
        indexes = [
            models.Index(fields=['employee', 'date']),
        ]

    def __str__(self):
        return f"{self.employee.full_name} Off on {self.date}"


class EmployeeBlockTime(models.Model):
    """
    Emergency or temporary blocks for specific time ranges on a date.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey('service_provider.OrganizationEmployee', on_delete=models.CASCADE, related_name='blocked_times')
    
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    reason = models.CharField(max_length=255, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['employee', 'date']),
        ]

    def __str__(self):
        return f"{self.employee.full_name} Blocked on {self.date} {self.start_time}-{self.end_time}"


class EmployeeDailySchedule(models.Model):
    """
    Date-specific availability for an employee (e.g., 2024-05-20 09:00 - 18:00).
    Allows for dynamic scheduling with specific reasons.
    """
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey('service_provider.OrganizationEmployee', on_delete=models.CASCADE, related_name='daily_schedules')
    
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    reason = models.TextField(null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    approved_by_auth_id = models.UUIDField(null=True, blank=True)
    rejection_reason = models.TextField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('employee', 'date')
        indexes = [
            models.Index(fields=['employee', 'date', 'status']),
        ]

    def __str__(self):
        return f"{self.employee.full_name} - {self.date} ({self.status})"
