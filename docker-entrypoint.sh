#!/bin/bash

# Script de entrada para el contenedor Docker

echo "Starting Time It Right API..."

# Iniciar el servidor FastAPI con Uvicorn
#poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload 
poetry run start