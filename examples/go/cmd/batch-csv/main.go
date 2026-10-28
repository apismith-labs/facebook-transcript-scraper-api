// Command batch-csv creates one Run per CSV row. Plan-only by default: without
// --execute it validates every row, prints a cost estimate, reads no token, and
// creates no Run.
package main

import (
	"context"
	"encoding/csv"
	"encoding/json"
	"flag"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/apismith-labs/facebook-transcript-scraper-api/examples/go/transcript"
)

type row struct {
	Line      int
	URL       string
	Seconds   float64
	HasSecs   bool
	Canonical string
	Form      string
}

type rowResult struct {
	RowID      string           `json:"rowId"`
	SourceURL  string           `json:"sourceUrl"`
	Canonical  string           `json:"canonicalUrl"`
	URLForm    string           `json:"urlForm"`
	Status     string           `json:"status"`
	RunID      string           `json:"runId,omitempty"`
	DatasetID  string           `json:"datasetId,omitempty"`
	Text       string           `json:"text,omitempty"`
	Segments   []map[string]any `json:"segments,omitempty"`
	Error      string           `json:"error,omitempty"`
	Duration   *float64         `json:"duration,omitempty"`
	RowSeconds *float64         `json:"inputDurationSeconds,omitempty"`
}

func main() {
	flags := flag.NewFlagSet("batch-csv", flag.ExitOnError)
	execute := flags.Bool("execute", false, "actually create Runs (default is plan only)")
	limit := flags.Int("limit", 0, "process only the first N rows")
	concurrency := flags.Int("max-concurrency", 3, "concurrent Runs")
	output := flags.String("output", "", "result JSON path")
	tier := flags.String("tier", "FREE", "pricing tier used for the estimate")
	capUSD := flags.String("max-total-charge-usd", "", "per-Run charge cap in USD")
	requireCap := flags.Bool("require-charge-cap", false, "fail when no charge cap is provided")
	timeout := flags.Int("timeout", transcript.DefaultTimeout, "per-Run deadline in seconds")

	_ = flags.Parse(os.Args[1:])
	if flags.NArg() != 1 {
		fmt.Fprintln(os.Stderr, "usage: batch-csv [flags] <file.csv>")
		os.Exit(transcript.ExitBatchConfigError)
	}
	csvPath := flags.Arg(0)

	rows, err := readCSV(csvPath)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(transcript.ExitBatchConfigError)
	}
	if *limit > 0 && *limit < len(rows) {
		rows = rows[:*limit]
	}
	if len(rows) == 0 {
		fmt.Fprintln(os.Stderr, "no data rows found")
		os.Exit(transcript.ExitBatchConfigError)
	}

	total := 0.0
	for index := range rows {
		canonical, form, validateErr := transcript.ValidateVideoURL(rows[index].URL)
		if validateErr != nil {
			fmt.Fprintf(os.Stderr, "line %d: %v\n", rows[index].Line, validateErr)
			os.Exit(transcript.ExitBatchConfigError)
		}
		rows[index].Canonical = canonical
		rows[index].Form = form
		seconds := 60.0
		if rows[index].HasSecs {
			seconds = rows[index].Seconds
		}
		cost, costErr := transcript.EstimateCost(1, seconds, *tier)
		if costErr != nil {
			fmt.Fprintln(os.Stderr, costErr)
			os.Exit(transcript.ExitBatchConfigError)
		}
		total += cost
	}

	fmt.Printf("rows: %d\ntier: %s\nestimated cost: %s\n", len(rows), *tier, transcript.FormatUSD(total))
	if !*execute {
		fmt.Println("plan only: no token read, no Run created. Re-run with --execute to submit.")
		return
	}

	loadDotEnv(".env")
	capValue := *capUSD
	if capValue == "" {
		capValue = os.Getenv("APIFY_MAX_TOTAL_CHARGE_USD")
	}
	if *requireCap && strings.TrimSpace(capValue) == "" {
		fmt.Fprintln(os.Stderr, "APIFY_MAX_TOTAL_CHARGE_USD is required with --require-charge-cap")
		os.Exit(transcript.ExitBatchConfigError)
	}

	journal := &transcript.FileJournal{Path: filepath.Join(filepath.Dir(csvPath), "go-run-journal.jsonl")}
	results := make([]rowResult, len(rows))
	semaphore := make(chan struct{}, maxInt(1, *concurrency))
	var waitGroup sync.WaitGroup

	for index := range rows {
		waitGroup.Add(1)
		go func(position int) {
			defer waitGroup.Done()
			semaphore <- struct{}{}
			defer func() { <-semaphore }()

			current := rows[position]
			results[position] = executeRow(current, journal, capValue, *timeout)
		}(index)
	}
	waitGroup.Wait()

	summary := map[string]int{"processed": len(results), "failed": 0}
	for _, item := range results {
		summary[item.Status]++
		if item.Status != "success" {
			summary["failed"]++
		}
	}

	payload := map[string]any{
		"generatedAt": time.Now().UTC().Format(time.RFC3339),
		"csv":         csvPath,
		"tier":        *tier,
		"estimateUsd": total,
		"summary":     summary,
		"rows":        results,
	}
	encoded, marshalErr := json.MarshalIndent(payload, "", "  ")
	if marshalErr != nil {
		fmt.Fprintln(os.Stderr, "could not encode results")
		os.Exit(transcript.ExitBatchConfigError)
	}

	target := *output
	if target == "" {
		target = uniqueResultPath(filepath.Dir(csvPath))
	}
	if writeErr := os.WriteFile(target, append(encoded, '\n'), 0o600); writeErr != nil {
		fmt.Fprintf(os.Stderr, "could not write %s: %v\n", target, writeErr)
		os.Exit(transcript.ExitBatchConfigError)
	}

	fmt.Printf("results: %s\nsuccess: %d\nfailed: %d\n", target, summary["success"], summary["failed"])
	if summary["failed"] > 0 || summary["success"] != len(results) {
		os.Exit(transcript.ExitBatchRowFailed)
	}
}

func executeRow(current row, journal transcript.Journal, capValue string, timeout int) rowResult {
	rowID := strconv.Itoa(current.Line)
	result, err := transcript.GetTranscript(context.Background(), current.URL, transcript.Options{
		Timeout:           time.Duration(timeout) * time.Second,
		MaxTotalChargeUSD: capValue,
		Journal:           journal,
		RowID:             rowID,
	})
	if err != nil {
		status := "unknown"
		switch err.(type) {
		case *transcript.TransportError:
			status = "transport_error"
		case *transcript.CreationUnknownError:
			status = "creation_unknown"
		}
		entry := rowResult{
			RowID:     rowID,
			SourceURL: current.URL,
			Canonical: current.Canonical,
			URLForm:   current.Form,
			Status:    status,
			Error:     err.Error(),
		}
		if current.HasSecs {
			entry.RowSeconds = &current.Seconds
		}
		return entry
	}

	entry := rowResult{
		RowID:     rowID,
		SourceURL: result.SourceURL,
		Canonical: result.CanonicalURL,
		URLForm:   result.URLForm,
		Status:    result.Status,
		RunID:     result.RunID,
		DatasetID: result.DatasetID,
		Text:      result.Text,
		Segments:  result.Segments,
		Error:     result.Error,
	}
	if result.HasDuration {
		duration := result.Duration
		entry.Duration = &duration
	}
	if current.HasSecs {
		entry.RowSeconds = &current.Seconds
	}
	return entry
}

func readCSV(path string) ([]row, error) {
	file, err := os.Open(path)
	if err != nil {
		return nil, fmt.Errorf("could not read %s", path)
	}
	defer file.Close()

	reader := csv.NewReader(file)
	reader.FieldsPerRecord = -1
	records, err := reader.ReadAll()
	if err != nil {
		return nil, fmt.Errorf("CSV could not be parsed: %v", err)
	}
	if len(records) == 0 {
		return nil, fmt.Errorf("CSV is empty")
	}

	header := records[0]
	urlIndex, durationIndex := -1, -1
	for index, name := range header {
		switch strings.ToLower(strings.TrimSpace(strings.TrimPrefix(name, "\ufeff"))) {
		case "videourl", "url":
			urlIndex = index
		case "durationseconds", "duration":
			durationIndex = index
		}
	}
	if urlIndex < 0 {
		return nil, fmt.Errorf("CSV header must contain videoUrl or url")
	}

	var rows []row
	for position, record := range records[1:] {
		if urlIndex >= len(record) {
			continue
		}
		value := strings.TrimSpace(record[urlIndex])
		if value == "" {
			continue
		}
		entry := row{Line: position + 2, URL: value}
		if durationIndex >= 0 && durationIndex < len(record) {
			if seconds, parseErr := strconv.ParseFloat(strings.TrimSpace(record[durationIndex]), 64); parseErr == nil && seconds >= 0 {
				entry.Seconds = seconds
				entry.HasSecs = true
			}
		}
		rows = append(rows, entry)
	}
	return rows, nil
}

func uniqueResultPath(dir string) string {
	stamp := time.Now().UTC().Format("20060102T150405Z")
	base := filepath.Join(dir, "facebook-batch-results-"+stamp)
	candidate := base + ".json"
	for suffix := 1; ; suffix++ {
		if _, err := os.Stat(candidate); os.IsNotExist(err) {
			return candidate
		}
		candidate = fmt.Sprintf("%s-%d.json", base, suffix)
	}
}

func maxInt(left, right int) int {
	if left > right {
		return left
	}
	return right
}

func loadDotEnv(path string) {
	content, err := os.ReadFile(path)
	if err != nil {
		return
	}
	for _, line := range strings.Split(string(content), "\n") {
		trimmed := strings.TrimSpace(line)
		if trimmed == "" || strings.HasPrefix(trimmed, "#") {
			continue
		}
		key, value, found := strings.Cut(trimmed, "=")
		key = strings.TrimSpace(key)
		if !found || !strings.HasPrefix(key, "APIFY_") {
			continue
		}
		if _, exists := os.LookupEnv(key); exists {
			continue
		}
		_ = os.Setenv(key, strings.Trim(strings.TrimSpace(value), `"'`))
	}
}
