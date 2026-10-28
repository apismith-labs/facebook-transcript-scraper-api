#!/usr/bin/env bash
# Transcribe one public Facebook video with the Apify API. Creates one billable Run.
#
# Usage:
#   export APIFY_TOKEN='...'
#   ./examples/curl/single-url-sync.sh 'https://www.facebook.com/watch/?v=1234567890'
#
# Optional: APIFY_MAX_TOTAL_CHARGE_USD=0.10
# Requires: curl, jq, bash 4+
set -euo pipefail

url="${1:-}"
if [ -z "$url" ]; then
  echo "Usage: $0 '<public Facebook video URL>'" >&2
  exit 2
fi
: "${APIFY_TOKEN:?Set APIFY_TOKEN in your environment first}"

api='https://api.apify.com/v2'
actor='apple_yang~facebook-transcript-scraper-api'
build='0.0.18'
query="build=${build}&restartOnError=false"
if [ -n "${APIFY_MAX_TOTAL_CHARGE_USD:-}" ]; then
  query="${query}&maxTotalChargeUsd=${APIFY_MAX_TOTAL_CHARGE_USD}"
fi
input=$(jq -cn --arg u "$url" '{videoUrl:$u}')

# Only create POST in this script. Any failure here is ambiguous: do not re-run blindly.
created=$(curl --fail --silent --show-error \
  -X POST "${api}/acts/${actor}/runs?${query}" \
  -H "Authorization: Bearer ${APIFY_TOKEN}" \
  -H 'Content-Type: application/json' \
  --data "$input") || {
  echo 'Run creation failed or is uncertain. Reconcile the existing Run in Apify before retrying.' >&2
  exit 8
}

run_id=$(jq -er '.data.id | strings | select(length > 0)' <<<"$created") || {
  echo 'Create response is ambiguous (no Run ID). Reconcile in Apify; do not retry.' >&2
  exit 10
}
dataset_id=$(jq -er '.data.defaultDatasetId | strings | select(length > 0)' <<<"$created") || {
  echo 'Create response is missing a Dataset ID. Reconcile the Run in Apify.' >&2
  exit 8
}
echo "Run ID: ${run_id}"

status=''
for _ in $(seq 1 300); do
  if ! run=$(curl --fail --silent --show-error -H "Authorization: Bearer ${APIFY_TOKEN}" "${api}/actor-runs/${run_id}"); then
    echo "Run ${run_id} could not be polled. Re-poll this same Run; do not create another." >&2
    exit 8
  fi
  status=$(jq -er '.data.status' <<<"$run")
  case "$status" in
    SUCCEEDED|FAILED|ABORTED|TIMED-OUT) break ;;
  esac
  sleep 1
done

case "$status" in
  SUCCEEDED) ;;
  FAILED|ABORTED|TIMED-OUT)
    echo "Run ${run_id} ended with ${status}. Do not create a replacement Run." >&2
    exit 9
    ;;
  *)
    echo "Polling ceiling reached for Run ${run_id} (status=${status}). Continue polling the same Run." >&2
    exit 8
    ;;
esac

items=$(curl --fail --silent --show-error \
  -H "Authorization: Bearer ${APIFY_TOKEN}" \
  "${api}/datasets/${dataset_id}/items?format=json")

jq -er '
  if length == 0 then error("Dataset is empty")
  else .[0] end
  | if ((.errMsg // "") != "") then error("Actor item reported errMsg: \(.errMsg)")
    elif (.text == null) or ((.text | type) != "string") or (.text | length) == 0
      then error("No transcript text in the first item")
    else
      "Status: success\nSegments: \(.segments | if type == "array" then length else 0 end)\nTranscript:\n\(.text)"
    end
' <<<"$items" || exit 6
