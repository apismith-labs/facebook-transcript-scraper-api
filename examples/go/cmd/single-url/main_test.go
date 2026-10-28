package main

import (
	"encoding/json"
	"testing"

	"github.com/apismith-labs/facebook-transcript-scraper-api/examples/go/transcript"
)

// renderJSON must keep the same documented keys as the Python, Node.js, and Java CLIs, so a
// caller can switch language without changing its parser.
func TestRenderJSONKeepsDocumentedKeys(t *testing.T) {
	result := transcript.Result{
		Status:          "success",
		Text:            "hello",
		HasText:         true,
		RunID:           "run1",
		DatasetID:       "ds1",
		SourceURL:       "https://www.facebook.com/watch/?v=1",
		CanonicalURL:    "https://www.facebook.com/watch/?v=1",
		URLForm:         "watch",
		DatasetComplete: true,
		Title:           "title",
		Nickname:        "nickname",
		Duration:        1.5,
		HasDuration:     true,
	}

	var payload map[string]any
	if err := json.Unmarshal([]byte(renderJSON(result)), &payload); err != nil {
		t.Fatalf("renderJSON returned invalid JSON: %v", err)
	}

	for _, key := range []string{
		"status", "text", "segments", "items", "runId", "datasetId", "sourceUrl",
		"canonicalUrl", "urlForm", "error", "datasetComplete", "title", "nickname", "duration",
	} {
		if _, ok := payload[key]; !ok {
			t.Fatalf("renderJSON is missing the %q key", key)
		}
	}
	if payload["datasetComplete"] != true {
		t.Fatalf("datasetComplete = %v, want true", payload["datasetComplete"])
	}
}

// Empty optional values must be null, never an empty string, so callers can branch on presence.
func TestRenderJSONNullsEmptyValues(t *testing.T) {
	var payload map[string]any
	if err := json.Unmarshal([]byte(renderJSON(transcript.Result{Status: "no_transcript"})), &payload); err != nil {
		t.Fatalf("renderJSON returned invalid JSON: %v", err)
	}
	if payload["runId"] != nil || payload["duration"] != nil || payload["text"] != nil {
		t.Fatalf("expected nulls for absent values, got %v / %v / %v", payload["runId"], payload["duration"], payload["text"])
	}
}
