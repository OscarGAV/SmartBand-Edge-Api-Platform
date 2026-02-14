from datetime import datetime, UTC
from typing import List
from uuid import UUID, uuid4
from core_context.domain.events.abnormal_heart_rate_detected_event import AbnormalHeartRateDetectedEvent
from core_context.domain.events.domain_event import DomainEvent
from core_context.domain.events.heart_rate_recorded_event import HeartRateRecordedEvent
from core_context.domain.model.value_objects.heart_rate_status import HeartRateStatus


class HeartRateReading:
    """Domain Entity - Aggregate Root"""

    def __init__(
            self,
            heart_rate_id: UUID,
            smart_band_id: int,
            pulse: int,
            timestamp: datetime,
            status: HeartRateStatus
    ):
        self.id = heart_rate_id
        self.smart_band_id = smart_band_id
        self.pulse = pulse
        self.timestamp = timestamp
        self.status = status
        self._domain_events: List['DomainEvent'] = []

    @staticmethod
    def create(smart_band_id: int, pulse: int) -> 'HeartRateReading':
        """Factory method with business rules"""
        heart_rate_id = uuid4()
        timestamp = datetime.now(UTC)
        status = HeartRateReading._determine_status(pulse)

        reading = HeartRateReading(heart_rate_id, smart_band_id, pulse, timestamp, status)

        # Raise domain events
        reading._add_domain_event(HeartRateRecordedEvent(
            reading_id=heart_rate_id,
            smart_band_id=smart_band_id,
            pulse=pulse,
            status=status,
            timestamp=timestamp
        ))

        if status in [HeartRateStatus.LOW, HeartRateStatus.HIGH, HeartRateStatus.CRITICAL]:
            reading._add_domain_event(AbnormalHeartRateDetectedEvent(
                reading_id=heart_rate_id,
                smart_band_id=smart_band_id,
                pulse=pulse,
                status=status
            ))

        return reading

    @staticmethod
    def _determine_status(pulse: int) -> HeartRateStatus:
        """Business rule: Determine heart rate status"""
        if pulse < 40:
            return HeartRateStatus.CRITICAL
        elif pulse < 60:
            return HeartRateStatus.LOW
        elif pulse <= 140:
            return HeartRateStatus.NORMAL
        elif pulse > 140:
            return HeartRateStatus.HIGH
        else:
            return HeartRateStatus.CRITICAL

    def _add_domain_event(self, event: 'DomainEvent'):
        self._domain_events.append(event)

    def get_domain_events(self) -> List['DomainEvent']:
        return self._domain_events.copy()

    def clear_domain_events(self):
        self._domain_events.clear()