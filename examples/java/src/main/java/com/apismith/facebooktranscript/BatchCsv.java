package com.apismith.facebooktranscript;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;

/**
 * Creates one Run per CSV row. Plan-only by default: without --execute it
 * validates every row, prints a cost estimate, reads no token, creates no Run.
 */
public final class BatchCsv {
    private static final DateTimeFormatter STAMP =
            DateTimeFormatter.ofPattern("yyyyMMdd'T'HHmmss'Z'").withZone(ZoneOffset.UTC);

    private BatchCsv() {
    }

    private record Row(int line, String url, Double seconds) {
    }

    public static void main(String[] args) {
        Map<String, String> flags = new LinkedHashMap<>();
        List<String> positional = new ArrayList<>();
        for (int index = 0; index < args.length; index++) {
            String argument = args[index];
            if (argument.startsWith("--")) {
                String key = argument.substring(2);
                if (List.of("execute", "require-charge-cap").contains(key)) {
                    flags.put(key, "true");
                } else if (index + 1 < args.length) {
                    flags.put(key, args[++index]);
                } else {
                    System.err.println("missing value for --" + key);
                    System.exit(2);
                }
            } else {
                positional.add(argument);
            }
        }
        if (positional.size() != 1) {
            System.err.println("usage: batch-csv [--execute] [--limit N] [--max-concurrency N] <file.csv>");
            System.exit(2);
        }

        Path csvPath = Path.of(positional.get(0));
        List<Row> rows;
        try {
            rows = readCsv(csvPath);
        } catch (IOException | IllegalArgumentException error) {
            System.err.println(error.getMessage());
            System.exit(2);
            return;
        }

        int limit = Integer.parseInt(flags.getOrDefault("limit", "0"));
        if (limit > 0 && limit < rows.size()) {
            rows = new ArrayList<>(rows.subList(0, limit));
        }
        if (rows.isEmpty()) {
            System.err.println("no data rows found");
            System.exit(2);
        }

        String tier = flags.getOrDefault("tier", "FREE").toUpperCase();
        double estimate = 0;
        List<String[]> canonical = new ArrayList<>();
        for (Row row : rows) {
            try {
                String[] validated = TranscriptClient.validateVideoUrl(row.url());
                canonical.add(validated);
                estimate += Cost.estimate(1, row.seconds() == null ? 60 : row.seconds(), tier);
            } catch (TranscriptClient.ConfigurationException error) {
                System.err.println("line " + row.line() + ": " + error.getMessage());
                System.exit(2);
            }
        }

        System.out.println("rows: " + rows.size());
        System.out.println("tier: " + tier);
        System.out.println("estimated cost: " + Cost.formatUsd(estimate));
        if (!"true".equals(flags.get("execute"))) {
            System.out.println("plan only: no token read, no Run created. Re-run with --execute to submit.");
            return;
        }

        Map<String, String> dotEnv = TranscriptClient.readDotEnv(Path.of(".env"));
        String token = dotEnv.getOrDefault("APIFY_TOKEN", System.getenv().getOrDefault("APIFY_TOKEN", ""));
        if (token.isBlank()) {
            System.err.println("APIFY_TOKEN is required with --execute");
            System.exit(2);
        }
        String cap = flags.getOrDefault("max-total-charge-usd",
                dotEnv.getOrDefault("APIFY_MAX_TOTAL_CHARGE_USD",
                        System.getenv().getOrDefault("APIFY_MAX_TOTAL_CHARGE_USD", "")));
        if ("true".equals(flags.get("require-charge-cap")) && cap.isBlank()) {
            System.err.println("APIFY_MAX_TOTAL_CHARGE_USD is required with --require-charge-cap");
            System.exit(2);
        }

        int concurrency = Math.max(1, Integer.parseInt(flags.getOrDefault("max-concurrency", "3")));
        int timeout = Integer.parseInt(flags.getOrDefault("timeout",
                String.valueOf(ReliableActor.DEFAULT_TIMEOUT_SECONDS)));
        ReliableActor.FileJournal journal = new ReliableActor.FileJournal(
                csvPath.toAbsolutePath().getParent().resolve("java-run-journal.jsonl"));

        Object[] results = new Object[rows.size()];
        final List<Row> workRows = rows;

        ExecutorService pool = Executors.newFixedThreadPool(concurrency);
        List<Future<?>> futures = new ArrayList<>();
        for (int index = 0; index < workRows.size(); index++) {
            final int position = index;
            futures.add(pool.submit(() -> {
                results[position] = executeRow(workRows.get(position), canonical.get(position),
                        token, cap, timeout, journal);
            }));
        }
        for (Future<?> future : futures) {
            try {
                future.get();
            } catch (Exception error) {
                System.err.println("row execution failed: " + error.getMessage());
            }
        }
        pool.shutdown();

        Map<String, Object> summary = new LinkedHashMap<>();
        int failed = 0;
        for (Object item : results) {
            Map<String, Object> result = item instanceof Map<?, ?> map
                    ? Json.asObject(map)
                    : Map.of("status", "unknown");
            String status = String.valueOf(result.get("status"));
            summary.merge(status, 1, (left, right) -> ((Number) left).intValue() + ((Number) right).intValue());
            if (!"success".equals(status)) {
                failed++;
            }
        }
        summary.put("processed", results.length);
        summary.put("failed", failed);

        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("generatedAt", Instant.now().toString());
        payload.put("csv", csvPath.toString());
        payload.put("tier", tier);
        payload.put("estimateUsd", estimate);
        payload.put("summary", summary);
        payload.put("rows", results);

        String output = flags.get("output");
        Path target = output != null ? Path.of(output) : uniqueResultPath(csvPath.toAbsolutePath().getParent());
        try {
            if (target.getParent() != null) {
                Files.createDirectories(target.getParent());
            }
            Files.writeString(target, Json.write(payload) + "\n", StandardCharsets.UTF_8);
        } catch (IOException error) {
            System.err.println("could not write " + target + ": " + error.getMessage());
            System.exit(2);
        }

        System.out.println("results: " + target);
        System.out.println("success: " + summary.getOrDefault("success", 0));
        System.out.println("failed: " + failed);
        if (failed > 0) {
            System.exit(1);
        }
    }

    private static Map<String, Object> executeRow(Row row, String[] validated, String token, String cap,
                                                  int timeout, ReliableActor.Journal journal) {
        Map<String, Object> entry = new LinkedHashMap<>();
        entry.put("rowId", String.valueOf(row.line()));
        entry.put("sourceUrl", row.url());
        entry.put("canonicalUrl", validated[0]);
        entry.put("urlForm", validated[1]);
        if (row.seconds() != null) {
            entry.put("inputDurationSeconds", row.seconds());
        }

        TranscriptClient.Options options = new TranscriptClient.Options();
        options.token = token;
        options.maxTotalChargeUsd = cap;
        options.timeoutSeconds = timeout;
        options.rowId = String.valueOf(row.line());
        options.journal = journal;

        try {
            TranscriptClient.Result result = TranscriptClient.getTranscript(row.url(), options);
            entry.put("status", result.status());
            entry.put("runId", result.runId());
            entry.put("datasetId", result.datasetId());
            entry.put("text", result.text());
            entry.put("segments", result.segments());
            entry.put("error", result.error());
            entry.put("duration", result.duration());
        } catch (TranscriptClient.TransportException error) {
            entry.put("status", "transport_error");
            entry.put("error", error.getMessage());
        } catch (TranscriptClient.CreationUnknownException error) {
            entry.put("status", "creation_unknown");
            entry.put("error", error.getMessage());
        } catch (Exception error) {
            entry.put("status", "unknown");
            entry.put("error", error.getMessage());
        }
        return entry;
    }

    private static List<Row> readCsv(Path path) throws IOException {
        List<String> lines = Files.readAllLines(path, StandardCharsets.UTF_8);
        if (lines.isEmpty()) {
            throw new IllegalArgumentException("CSV is empty");
        }
        List<String> header = splitLine(lines.get(0).replace("\uFEFF", ""));
        int urlIndex = -1;
        int durationIndex = -1;
        for (int index = 0; index < header.size(); index++) {
            String name = header.get(index).trim().toLowerCase();
            if ("videourl".equals(name) || "url".equals(name)) {
                urlIndex = index;
            } else if ("durationseconds".equals(name) || "duration".equals(name)) {
                durationIndex = index;
            }
        }
        if (urlIndex < 0) {
            throw new IllegalArgumentException("CSV header must contain videoUrl or url");
        }

        List<Row> rows = new ArrayList<>();
        for (int index = 1; index < lines.size(); index++) {
            if (lines.get(index).isBlank()) {
                continue;
            }
            List<String> fields = splitLine(lines.get(index));
            if (urlIndex >= fields.size()) {
                continue;
            }
            String url = fields.get(urlIndex).trim();
            if (url.isEmpty()) {
                continue;
            }
            Double seconds = null;
            if (durationIndex >= 0 && durationIndex < fields.size() && !fields.get(durationIndex).isBlank()) {
                try {
                    double parsed = Double.parseDouble(fields.get(durationIndex).trim());
                    if (parsed >= 0) {
                        seconds = parsed;
                    }
                } catch (NumberFormatException ignored) {
                    // An unparsable duration only weakens the estimate.
                }
            }
            rows.add(new Row(index + 1, url, seconds));
        }
        return rows;
    }

    private static List<String> splitLine(String line) {
        List<String> fields = new ArrayList<>();
        StringBuilder current = new StringBuilder();
        boolean quoted = false;
        for (int index = 0; index < line.length(); index++) {
            char character = line.charAt(index);
            if (character == '"') {
                if (quoted && index + 1 < line.length() && line.charAt(index + 1) == '"') {
                    current.append('"');
                    index++;
                } else {
                    quoted = !quoted;
                }
            } else if (character == ',' && !quoted) {
                fields.add(current.toString());
                current.setLength(0);
            } else {
                current.append(character);
            }
        }
        fields.add(current.toString());
        return fields;
    }

    private static Path uniqueResultPath(Path directory) {
        String base = "facebook-batch-results-" + STAMP.format(Instant.now());
        Path candidate = directory.resolve(base + ".json");
        int suffix = 1;
        while (Files.exists(candidate)) {
            candidate = directory.resolve(base + "-" + suffix + ".json");
            suffix++;
        }
        return candidate;
    }
}
