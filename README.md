# media-scheduler

## Service Setup
1. Copy the service files, so Gunicorn & Celery can be automatically started & reloaded.
	
	```
	cp <Location>/scheduler/gu-app.service /etc/systemd/system/gu-scheduler.service
	cp <Location>/scheduler/celery-app.service /etc/systemd/system/celery-scheduler.service
	```

1. Activate the service file, enable it at boot/resart, and start the app.

	```
	systemctl daemon-reload
	systemctl enable gu-scheduler
	systemctl start gu-scheduler
	systemctl enable celery-scheduler
	systemctl start celery-scheduler
	```
