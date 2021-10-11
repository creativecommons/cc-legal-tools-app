#!/bin/bash
# Note that docker-compose executes this with the cc-licenses as the working
# directory
while !</dev/tcp/db/5432; do
    echo 'Waiting on db service; sleeping for 1 second.'
    sleep 1
done 2>/dev/null
echo 'The db service is available.'
./manage.py runserver 0.0.0.0:8000
