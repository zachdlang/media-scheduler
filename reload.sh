#!/bin/bash

cd /var/www/scheduler && sudo -u zach git pull
cd

echo 'Reloading scheduler...'
sudo systemctl restart gu-scheduler
sudo systemctl restart celery-scheduler