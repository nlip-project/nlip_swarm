#!/bin/bash
# Load environment variables from models.ini and run Docker Compose

# Read models.ini and export environment variables
eval "$(python3 scripts/load_models_ini.py | sed 's/^/export /')"

if [ $? -ne 0 ]; then
    echo "Failed to load models.ini" >&2
    exit 1
fi

echo "Environment variables set from models.ini:"
echo "  LLM_MODEL=$LLM_MODEL"
echo "  TRANSLATION_MODEL=$TRANSLATION_MODEL"

# Run docker compose with all arguments passed to this script
echo -e "\nStarting Docker Compose..."
docker compose "$@"
