// Command quickstart is the smallest possible call: one URL, one Run, the
// transcript on stdout. No journal, no .env loading.
package main

import (
	"context"
	"fmt"
	"os"

	"github.com/apismith-labs/facebook-transcript-scraper-api/examples/go/transcript"
)

func main() {
	if len(os.Args) != 2 {
		fmt.Fprintln(os.Stderr, "usage: quickstart <facebook-video-url>")
		os.Exit(2)
	}

	result, err := transcript.GetTranscript(context.Background(), os.Args[1], transcript.Options{})
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(2)
	}

	if result.Succeeded() {
		fmt.Println(result.Text)
		fmt.Fprintf(os.Stderr, "%d segments, run %s\n", len(result.Segments), result.RunID)
		return
	}
	fmt.Fprintf(os.Stderr, "status=%s error=%s run=%s\n", result.Status, result.Error, result.RunID)
	os.Exit(result.ExitCode())
}
