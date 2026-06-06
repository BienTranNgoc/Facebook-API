#!/usr/bin/env bash
set -euo pipefail

BOOTSTRAP_SERVER="${1:-localhost:9092}"
TOPICS=(raw_events reply_commands send_retry send_failed dead_letter)

for topic in "${TOPICS[@]}"; do
    docker exec fb_api-kafka kafka-topics         --bootstrap-server "$BOOTSTRAP_SERVER"         --create         --if-not-exists         --topic "$topic"         --partitions 1         --replication-factor 1
done
