#!/bin/bash
#
# Helper script for docker-compose app service. Ensures db services is actually
# available before executing runserver command.
#
while !</dev/tcp/db/5432; do
    echo 'Waiting on db service; sleeping for 1 second.'
    sleep 1
done 2>/dev/null
echo 'The db service is available.'
./manage.py runserver 0.0.0.0:8000
