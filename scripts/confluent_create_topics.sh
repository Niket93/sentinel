set -euo pipefail

echo "=== Create Confluent Cloud topics ==="

if ! command -v ccloud >/dev/null 2>&1; then
  echo "ERROR: ccloud CLI not found. Install it first."
  exit 1
fi

TOPIC_CLIPS="${TOPIC_CLIPS:-video.clips}"
TOPIC_OBSERVATIONS="${TOPIC_OBSERVATIONS:-video.observations}"
TOPIC_SESSIONS="${TOPIC_SESSIONS:-station.sessions}"
TOPIC_DECISIONS="${TOPIC_DECISIONS:-sop.decisions}"
TOPIC_ACTIONS="${TOPIC_ACTIONS:-workflow.actions}"
TOPIC_AUDIT="${TOPIC_AUDIT:-audit.events}"

topics=(
  "$TOPIC_CLIPS"
  "$TOPIC_OBSERVATIONS"
  "$TOPIC_SESSIONS"
  "$TOPIC_DECISIONS"
  "$TOPIC_ACTIONS"
  "$TOPIC_AUDIT"
)

PARTITIONS="${PARTITIONS:-3}"

echo "Using partitions=$PARTITIONS"
echo "Topics:"
printf ' - %s\n' "${topics[@]}"

echo
for t in "${topics[@]}"; do
  echo "Creating topic: $t"
  ccloud kafka topic create "$t" --partitions "$PARTITIONS" || true
done

echo
echo "Done."