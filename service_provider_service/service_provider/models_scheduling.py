import uuid
from django.db import models
from django.utils import timezone
from django.utils import timezone

class EmployeeWorkingHours(models.Model):
    """
    Weekly working hours template for an employee.
    Used for dynamic slot generation.
    """
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
    employee = models.ForeignKey('service_provider.OrganizationEmployee', on_delete=models.CASCADE, related_name='working_hours')
    
    day_of_week = models.IntegerField(choices=DAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    
    break_start = models.TimeField(null=True, blank=True)
    break_end = models.TimeField(null=True, blank=True)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('employee', 'day_of_week')
        indexes = [
            models.Index(fields=['employee', 'day_of_week', 'is_active']),
        ]

    def __str__(self):
        return f"{self.employee.full_name} - {self.get_day_of_week_display()} ({self.start_time}-{self.end_time})"


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
    Specific dates or time ranges when an employee is unavailable (Leaves).
    """
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey('service_provider.OrganizationEmployee', on_delete=models.CASCADE, related_name='leaves')
    
    date = models.DateField()
    start_time = models.TimeField(null=True, blank=True, help_text="Null means full day leave")
    end_time = models.TimeField(null=True, blank=True, help_text="Null means full day leave")
    reason = models.CharField(max_length=255, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    approved_by_auth_id = models.UUIDField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('employee', 'date', 'start_time', 'end_time')
        indexes = [
            models.Index(fields=['employee', 'date', 'status']),
        ]

    def __str__(self):
        times = f" {self.start_time}-{self.end_time}" if self.start_time else " Full Day"
        return f"{self.employee.full_name} Off on {self.date}{times} ({self.status})"


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

class ProviderResource(models.Model):
    """
    Physical resources like Rooms or Equipment belonging to a provider.
    """
    RESOURCE_TYPE_CHOICES = [
        ('ROOM', 'Room'),
        ('EQUIPMENT', 'Equipment'),
        ('OTHER', 'Other'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.ForeignKey('service_provider.ServiceProvider', on_delete=models.CASCADE, related_name='resources')
    
    name = models.CharField(max_length=100, help_text="e.g. 'Operating Room 1', 'X-Ray Machine'")
    resource_type = models.CharField(max_length=20, choices=RESOURCE_TYPE_CHOICES, default='ROOM')
    capacity = models.PositiveIntegerField(default=1, help_text="Number of concurrent bookings this resource can handle")
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('provider', 'name')

    def __str__(self):
        return f"{self.name} ({self.resource_type})"


class FacilityResourceConstraint(models.Model):
    """
    Links a Facility (e.g. 'Surgery') to a specific Resource (e.g. 'Operating Room').
    This ensures that when a service is booked, the resource is also blocked.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    facility = models.ForeignKey('provider_dynamic_fields.ProviderTemplateFacility', on_delete=models.CASCADE, related_name='resource_constraints')
    resource = models.ForeignKey(ProviderResource, on_delete=models.CASCADE, related_name='facility_links')
    
    is_required = models.BooleanField(default=True)

    class Meta:
        unique_together = ('facility', 'resource')

    def __str__(self):
        return f"{self.facility.name} needs {self.resource.name}"
