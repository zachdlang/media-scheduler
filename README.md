# media-scheduler

## Gunicorn Setup
1. Set up a symlink for the service file, so Gunicorn can be automatically started & reloaded.

	`ln -s <Location>/scheduler/gu-app.service /etc/systemd/system/gu-scheduler.service`

1. Activate the service file, enable it at boot/resart, and start the app.

	```
	systemctl daemon-reload
	systemctl enable gu-scheduler
	systemctl start gu-scheduler
	```
