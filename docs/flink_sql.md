# Confluent Flink SQL (Illustrative)

This document shows Flink SQL queries that can be used on Confluent Cloud to compute
streaming KPIs and alerts from the same event streams used by Sentinel.

> These queries are illustrative.

---

## Windowed safety violations per minute (walkway violations)

```sql
SELECT
  camera_id,
  TUMBLE_START(ts, INTERVAL '1' MINUTE) AS window_start,
  COUNT(*) AS violations
FROM video_observations
WHERE JSON_VALUE(signals, '$.walkway_violation') = 'yes'
GROUP BY camera_id, TUMBLE(ts, INTERVAL '1' MINUTE);

---

## Stop line actions per hour

SELECT
  camera_id,
  TUMBLE_START(ts, INTERVAL '1' HOUR) AS hour_start,
  COUNT(*) AS stop_line_actions
FROM workflow_actions
WHERE JSON_VALUE(action, '$.type') = 'stop_line'
GROUP BY camera_id, TUMBLE(ts, INTERVAL '1' HOUR);

## Join observations → decisions by trace_id (stream correlation)

SELECT
  o.camera_id,
  d.assessment->>'severity' AS severity,
  COUNT(*) AS decision_count
FROM video_observations o
JOIN sop_decisions d
ON o.trace_id = d.trace_id
GROUP BY o.camera_id, d.assessment->>'severity';