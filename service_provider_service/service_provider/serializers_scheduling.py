from rest_framework import serializers
from .models_scheduling import EmployeeWeeklySchedule, EmployeeLeave, EmployeeBlockTime, EmployeeDailySchedule

class EmployeeWeeklyScheduleSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)
    
    class Meta:
        model = EmployeeWeeklySchedule
        fields = [
            'id', 'employee', 'employee_name', 'day_of_week', 
            'start_time', 'end_time', 'status', 
            'approved_by_auth_id', 'rejection_reason',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'status', 'approved_by_auth_id', 'created_at', 'updated_at']

class EmployeeDailyScheduleSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)
    
    class Meta:
        model = EmployeeDailySchedule
        fields = [
            'id', 'employee', 'employee_name', 'date', 
            'start_time', 'end_time', 'reason', 'status', 
            'approved_by_auth_id', 'rejection_reason',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'status', 'approved_by_auth_id', 'created_at', 'updated_at']


class EmployeeLeaveSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeLeave
        fields = ['id', 'employee', 'date', 'reason', 'created_at']

class EmployeeBlockTimeSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeBlockTime
        fields = ['id', 'employee', 'date', 'start_time', 'end_time', 'reason', 'created_at']
