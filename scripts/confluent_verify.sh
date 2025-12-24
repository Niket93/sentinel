set -euo pipefail

echo "=== Confluent Cloud Verification ==="

if ! command -v ccloud >/dev/null 2>&1; then
  echo "ERROR: ccloud CLI not found. Install it first."
  echo "Docs: https://docs.confluent.io/confluent-cli/current/overview.html"
  exit 1
fi

if [[ -z "${TOPIC_OBSERVATIONS:-}" ]]; then
  echo "NOTE: TOPIC_OBSERVATIONS not set. Defaulting to 'video.observations'."
  export TOPIC_OBSERVATIONS="video.observations"
fi

echo
echo "Kafka clusters:"
ccloud kafka cluster list || true

echo
echo "Kafka topics:"
ccloud kafka topic list || true

echo
echo "Schema Registry subjects:"
ccloud schema-registry subject list || true

echo
echo "Sample Observation events (first 3 records):"
echo "Consuming from: $TOPIC_OBSERVATIONS"
ccloud kafka topic consume "$TOPIC_OBSERVATIONS" \
  --from-beginning \
  --value-format json | head -n 3

echo
echo "Done."