package com.apismith.facebooktranscript;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Command line entry point: one URL, one Run, print or persist the result. */
public final class SingleUrl {
    private SingleUrl() {
    }

    public static void main(String[] args) {
        Map<String, String> flags = new LinkedHashMap<>();
        List<String> positional = new ArrayList<>();
        for (int index = 0; index < args.length; index++) {
            String argument = args[index];
            if (argument.startsWith("--")) {
                String key = argument.substring(2);
                if (List.of("json", "require-charge-cap").contains(key)) {
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
            System.err.println("usage: single-url [--json] [--output PATH] [--resume RUN_ID] <facebook-video-url>");
            System.exit(2);
        }

        Map<String, String> dotEnv = TranscriptClient.readDotEnv(Path.of(".env"));
        TranscriptClient.Options options = new TranscriptClient.Options();
        String token = flags.getOrDefault("token", "");
        if (token.isBlank()) {
            token = dotEnv.getOrDefault("APIFY_TOKEN", "");
        }
        if (token.isBlank()) {
            token = System.getenv().getOrDefault("APIFY_TOKEN", "");
        }
        options.token = token;
        options.actorId = flags.getOrDefault("actor", ReliableActor.DEFAULT_ACTOR_ID);
        options.build = flags.getOrDefault("build", ReliableActor.APPROVED_BUILD_NUMBER);
        options.runId = flags.get("resume");
        options.requireChargeCap = "true".equals(flags.get("require-charge-cap"));
        options.maxTotalChargeUsd = flags.getOrDefault("max-total-charge-usd",
                dotEnv.getOrDefault("APIFY_MAX_TOTAL_CHARGE_USD",
                        System.getenv().getOrDefault("APIFY_MAX_TOTAL_CHARGE_USD", "")));
        if (flags.containsKey("timeout")) {
            options.timeoutSeconds = Integer.parseInt(flags.get("timeout"));
        }
        if (flags.containsKey("dataset-limit")) {
            options.datasetLimit = Integer.parseInt(flags.get("dataset-limit"));
        }
        if (flags.containsKey("output") || options.runId != null) {
            options.journal = new ReliableActor.FileJournal(
                    Path.of("sample-output", "generated", "java-run-journal.jsonl"));
        }

        try {
            TranscriptClient.Result result = TranscriptClient.getTranscript(positional.get(0), options);
            boolean wantsJson = "true".equals(flags.get("json"));
            String output = flags.get("output");

            if (wantsJson || output != null) {
                String payload = renderJson(result);
                if (output != null) {
                    Path target = Path.of(output);
                    if (target.getParent() != null) {
                        Files.createDirectories(target.getParent());
                    }
                    Files.writeString(target, payload + "\n", StandardCharsets.UTF_8);
                }
                if (wantsJson) {
                    System.out.println(payload);
                }
                return;
            }

            System.out.println("Run ID: " + nullToEmpty(result.runId()));
            System.out.println("Status: " + result.status());
            if (result.error() != null && !result.error().isBlank()) {
                System.out.println("Error: " + result.error());
            }
            if (result.succeeded()) {
                System.out.println("Segments: " + result.segments().size());
                if (result.duration() != null) {
                    System.out.println("Duration: " + result.duration() + " s");
                }
                System.out.println("Transcript:");
                System.out.println(result.text());
            } else {
                System.exit(result.exitCode());
            }
        } catch (TranscriptClient.ConfigurationException error) {
            System.err.println(error.getMessage());
            System.exit(2);
        } catch (TranscriptClient.CreationUnknownException error) {
            System.err.println(error.getMessage());
            System.exit(10);
        } catch (TranscriptClient.TransportException error) {
            System.err.println(error.getMessage());
            System.exit(8);
        } catch (TranscriptClient.ProtocolException error) {
            System.err.println(error.getMessage());
            System.exit(3);
        } catch (IOException error) {
            System.err.println("could not write the result: " + error.getMessage());
            System.exit(2);
        }
    }

    static String renderJson(TranscriptClient.Result result) {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("status", result.status());
        payload.put("text", result.text());
        payload.put("segments", result.segments());
        payload.put("items", result.items());
        payload.put("runId", result.runId());
        payload.put("datasetId", result.datasetId());
        payload.put("sourceUrl", result.sourceUrl());
        payload.put("canonicalUrl", result.canonicalUrl());
        payload.put("urlForm", result.urlForm());
        payload.put("error", nullIfBlank(result.error()));
        payload.put("datasetComplete", result.datasetComplete());
        payload.put("title", nullIfBlank(result.title()));
        payload.put("nickname", nullIfBlank(result.nickname()));
        payload.put("duration", result.duration());
        payload.put("generatedAt", Instant.now().toString());
        return Json.write(payload);
    }

    private static String nullToEmpty(String value) {
        return value == null ? "" : value;
    }

    /** Blank optional values become JSON null, matching the other three clients. */
    private static Object nullIfBlank(String value) {
        return value == null || value.isBlank() ? null : value;
    }
}
