// Command single-url runs one public Facebook video URL through the Actor and
// prints the transcript. It creates at most one billable Run.
package main

import (
	"bufio"
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"github.com/apismith-labs/facebook-transcript-scraper-api/examples/go/transcript"
)

func main() {
	flags := flag.NewFlagSet("single-url", flag.ExitOnError)
	asJSON := flags.Bool("json", false, "print the full result as JSON")
	output := flags.String("output", "", "write the result to this path")
	resume := flags.String("resume", "", "resume an existing Run ID (GET only, never creates a Run)")
	actor := flags.String("actor", "", "Actor ID override")
	build := flags.String("build", transcript.ApprovedBuildNumber, "pinned Actor Build")
	capUSD := flags.String("max-total-charge-usd", "", "per-Run charge cap in USD")
	requireCap := flags.Bool("require-charge-cap", false, "fail when no charge cap is provided")
	timeout := flags.Int("timeout", transcript.DefaultTimeout, "overall deadline in seconds")
	datasetLimit := flags.Int("dataset-limit", transcript.DefaultDatasetLimit, "Dataset page size")

	_ = flags.Parse(os.Args[1:])
	if flags.NArg() != 1 {
		fmt.Fprintln(os.Stderr, "usage: single-url [flags] <facebook-video-url>")
		os.Exit(transcript.ExitConfiguration)
	}

	loadDotEnv(".env")

	options := transcript.Options{
		ActorID:           *actor,
		Build:             *build,
		Timeout:           time.Duration(*timeout) * time.Second,
		MaxTotalChargeUSD: *capUSD,
		RequireChargeCap:  *requireCap,
		DatasetLimit:      *datasetLimit,
		RunID:             strings.TrimSpace(*resume),
	}
	if options.MaxTotalChargeUSD == "" {
		options.MaxTotalChargeUSD = os.Getenv("APIFY_MAX_TOTAL_CHARGE_USD")
	}
	if *output != "" || options.RunID != "" {
		// A journal is only needed when a result is persisted or a Run is resumed.
		options.Journal = &transcript.FileJournal{Path: journalPath()}
	}

	result, err := transcript.GetTranscript(context.Background(), flags.Arg(0), options)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(exitCodeForError(err))
	}

	if *asJSON || *output != "" {
		payload := renderJSON(result)
		if *output != "" {
			if writeErr := writePrivate(*output, payload); writeErr != nil {
				fmt.Fprintf(os.Stderr, "could not write %s: %v\n", *output, writeErr)
				os.Exit(transcript.ExitConfiguration)
			}
		}
		if *asJSON {
			fmt.Println(payload)
		}
		return
	}

	printHuman(result)
}

func printHuman(result transcript.Result) {
	fmt.Printf("Run ID: %s\n", result.RunID)
	fmt.Printf("Status: %s\n", result.Status)
	if result.Error != "" {
		fmt.Printf("Error: %s\n", result.Error)
	}
	if result.Status == "success" {
		fmt.Printf("Segments: %d\n", len(result.Segments))
		if result.HasDuration {
			fmt.Printf("Duration: %s s\n", strconv.FormatFloat(result.Duration, 'f', -1, 64))
		}
		fmt.Printf("Transcript:\n%s\n", result.Text)
	}
}

func renderJSON(result transcript.Result) string {
	payload := map[string]any{
		"status":       result.Status,
		"text":         nilIfEmpty(result.Text),
		"segments":     result.Segments,
		"items":        result.Items,
		"runId":        nilIfEmpty(result.RunID),
		"datasetId":    nilIfEmpty(result.DatasetID),
		"sourceUrl":    result.SourceURL,
		"canonicalUrl": result.CanonicalURL,
		"urlForm":      result.URLForm,
		"error":        nilIfEmpty(result.Error),
		"title":        nilIfEmpty(result.Title),
		"nickname":     nilIfEmpty(result.Nickname),
		"duration":     nilIfZero(result.Duration, result.HasDuration),
	}
	encoded, err := json.MarshalIndent(payload, "", "  ")
	if err != nil {
		return `{"status":"unknown"}`
	}
	return string(encoded)
}

func nilIfEmpty(value string) any {
	if strings.TrimSpace(value) == "" {
		return nil
	}
	return value
}

func nilIfZero(value float64, present bool) any {
	if !present {
		return nil
	}
	return value
}

func exitCodeForError(err error) int {
	switch err.(type) {
	case *transcript.ConfigurationError:
		return transcript.ExitConfiguration
	case *transcript.ProtocolError:
		return transcript.ExitProtocol
	case *transcript.CreationUnknownError:
		return transcript.ExitCodes["creation_unknown"]
	case *transcript.TransportError:
		return transcript.ExitCodes["transport_error"]
	default:
		return transcript.ExitProtocol
	}
}

func journalPath() string {
	return filepath.Join("sample-output", "generated", "go-run-journal.jsonl")
}

// loadDotEnv reads APIFY_* keys from .env without overriding the environment.
func loadDotEnv(path string) {
	file, err := os.Open(path)
	if err != nil {
		return
	}
	defer file.Close()

	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		key, value, found := strings.Cut(line, "=")
		key = strings.TrimSpace(key)
		if !found || !strings.HasPrefix(key, "APIFY_") {
			continue
		}
		if _, exists := os.LookupEnv(key); exists {
			continue
		}
		value = strings.Trim(strings.TrimSpace(value), `"'`)
		_ = os.Setenv(key, value)
	}
}

func writePrivate(path string, content string) error {
	if dir := filepath.Dir(path); dir != "." {
		if err := os.MkdirAll(dir, 0o755); err != nil {
			return err
		}
	}
	return os.WriteFile(path, []byte(content+"\n"), 0o600)
}
