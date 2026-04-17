from apscheduler.schedulers.background import BackgroundScheduler
from services.delivery_service import process_overdue_deliveries

scheduler = BackgroundScheduler()

def start_scheduler():
    # Run every hour
    scheduler.add_job(process_overdue_deliveries, "interval", hours=1)
    scheduler.start()

