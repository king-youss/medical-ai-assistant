from datetime import datetime, timedelta

def find_available_slot(existing, duration):
    start = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
    end = datetime.now().replace(hour=18, minute=0, second=0, microsecond=0)

    slot = start

    while slot + timedelta(minutes=duration) <= end:
        conflict = False

        for existing_start, existing_duration in existing:
            existing_start = datetime.fromisoformat(existing_start)
            existing_end = existing_start + timedelta(minutes=existing_duration)

            if not (slot + timedelta(minutes=duration) <= existing_start or slot >= existing_end):
                conflict = True
                break

        if not conflict:
            return slot.isoformat()

        slot += timedelta(minutes=15)

    return None