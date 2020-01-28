#!/bin/bash

celery worker -A web.asynchro.celery --concurrency=10 -Q scheduler --purge
