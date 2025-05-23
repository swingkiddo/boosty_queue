#!/bin/bash

docker compose exec -it bot pytest -v --cov=bot --cov-report=html --cov-report=term-missing