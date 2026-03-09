import json
import logging
import os
from kafka import KafkaConsumer
from django.conf import settings
from django.core.management.base import BaseCommand
from service_provider.services.booking_projection import BookingProjectionService
from service_provider.services.cached_slots import AvailabilityCacheService
from datetime import datetime

logger = logging.getLogger("booking_consumer")

class Command(BaseCommand):
    help = 'Runs the Kafka consumer to project booking events into Redis cache.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting Booking Projection Consumer..."))
        self.run_booking_consumer()

    def run_booking_consumer(self):
        """
        Listens to 'booking_events' from customer_service and updates:
        1. The Booking Projection Cache
        2. Invalidates the Availability HTML/Frontend Cache
        """
        try:
            consumer = KafkaConsumer(
                'booking_events',
                bootstrap_servers=getattr(settings, 'KAFKA_BROKER_URL', 'localhost:9093'),
                auto_offset_reset='latest',
                enable_auto_commit=True,
                group_id='booking-projection-group',
                value_deserializer=lambda x: json.loads(x.decode('utf-8'))
            )
            logger.info("🎧 Booking Projection Consumer started. Listening to 'booking_events'...")
            
            for message in consumer:
                payload = message.value
                event_type = payload.get('event_type')
                data = payload.get('data', {})
                
                logger.info(f"📥 Received Booking Event: {event_type} for ID: {data.get('booking_id')}")

                employee_id = data.get('assigned_employee_id')
                if not employee_id:
                    logger.info(f"⏭ Skip event: No assigned employee.")
                    continue
                    
                selected_time_str = data.get('selected_time')
                end_time_str = data.get('end_time') # Could be missing in older event versions
                
                if not selected_time_str:
                    continue
                    
                # Parse Date
                try:
                    dt = datetime.fromisoformat(selected_time_str.replace('Z', '+00:00'))
                    date_str = dt.strftime('%Y-%m-%d')
                    time_str = dt.strftime('%H:%M')
                    
                    # Derive End time or assume 1 hour duration.
                    if end_time_str:
                        end_dt = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
                        end_time_str_fmt = end_dt.strftime('%H:%M')
                    else:
                        # In missing cases, assume 60 mins. Wait, let's grab it via datetime math
                        from datetime import timedelta
                        end_dt = dt + timedelta(minutes=60)
                        end_time_str_fmt = end_dt.strftime('%H:%M')

                    if event_type in ['BOOKING_CREATED', 'BOOKING_UPDATED']:
                        # 1. Update Interval Cache
                        BookingProjectionService.add_booking_interval(
                            employee_id=employee_id,
                            date_str=date_str,
                            start_time_str=time_str,
                            end_time_str=end_time_str_fmt
                        )
                        
                        # 2. Invalidate HTML/Slots view Cache to force recompute next time
                        AvailabilityCacheService.invalidate_employee_day(employee_id, dt.date())
                        logger.info(f"✅ Projection updated and cache invalidated for {employee_id} on {date_str}")
                        
                    elif event_type in ['BOOKING_CANCELLED', 'BOOKING_REJECTED', 'BOOKING_DELETED']:
                        # 1. Remove from Interval Cache
                        BookingProjectionService.remove_booking_interval(
                            employee_id=employee_id,
                            date_str=date_str,
                            start_time_str=time_str,
                            end_time_str=end_time_str_fmt
                        )
                        
                        # 2. Invalidate HTML/Slots view Cache to force recompute
                        AvailabilityCacheService.invalidate_employee_day(employee_id, dt.date())
                        logger.info(f"🗑 Projection removed and cache invalidated for {employee_id} on {date_str}")
                        
                except Exception as e:
                    logger.error(f"❌ Error processing event {event_type}: {e}")
                    
        except Exception as e:
            logger.error(f"❌ Booking Projection Consumer crashed: {e}")
