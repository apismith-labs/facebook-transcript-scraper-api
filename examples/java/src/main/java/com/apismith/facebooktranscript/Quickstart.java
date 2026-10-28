package com.apismith.facebooktranscript;

/** Smallest possible call: one URL, one Run, transcript on stdout. */
public final class Quickstart {
    private Quickstart() {
    }

    public static void main(String[] args) {
        if (args.length != 1) {
            System.err.println("usage: quickstart <facebook-video-url>");
            System.exit(2);
        }

        TranscriptClient.Options options = new TranscriptClient.Options();
        options.token = TranscriptClient.readDotEnv(java.nio.file.Path.of(".env"))
                .getOrDefault("APIFY_TOKEN", System.getenv().getOrDefault("APIFY_TOKEN", ""));

        try {
            TranscriptClient.Result result = TranscriptClient.getTranscript(args[0], options);
            if (result.succeeded()) {
                System.out.println(result.text());
                System.err.printf("%d segments, run %s%n", result.segments().size(), result.runId());
                return;
            }
            System.err.printf("status=%s error=%s run=%s%n", result.status(), result.error(), result.runId());
            System.exit(result.exitCode());
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
        }
    }
}
