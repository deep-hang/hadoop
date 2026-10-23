import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.OutputStreamWriter;
import java.io.PrintWriter;
import java.nio.charset.CodingErrorAction;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.StringTokenizer;
import java.util.TreeMap;
import org.apache.hadoop.fs.FileStatus;
import org.apache.hadoop.fs.FileSystem;
import org.apache.hadoop.fs.Path;
import org.apache.hadoop.io.compress.CompressionCodecFactory;
import org.apache.hadoop.mapred.JobConf;

/** Independent streaming reference for the bundled WordCount's token rules. */
public final class InputCounts {
    private static boolean visible(Path path) {
        String name = path.getName();
        return !name.startsWith(".") && !name.startsWith("_");
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 1) throw new IllegalArgumentException("Expected an input path");
        JobConf conf = new JobConf();
        Path input = new Path(args[0]);
        FileSystem fs = input.getFileSystem(conf);
        FileStatus root = fs.getFileStatus(input);
        List<Path> files = new ArrayList<>();
        if (root.isFile() && visible(input)) files.add(input);
        else if (root.isDirectory()) {
            for (FileStatus child : fs.listStatus(input)) {
                if (!visible(child.getPath())) continue;
                if (!child.isFile()) throw new IllegalArgumentException("Nested input directories are not supported");
                files.add(child.getPath());
            }
        }
        if (files.isEmpty()) throw new IllegalArgumentException("Input directory is missing or empty (no visible files)");
        CompressionCodecFactory codecs = new CompressionCodecFactory(conf);
        Map<String, Long> counts = new TreeMap<>();
        for (Path file : files) {
            if (codecs.getCodec(file) != null) throw new IllegalArgumentException("Use plain UTF-8 text, not compressed files");
            try (BufferedReader reader = new BufferedReader(new InputStreamReader(fs.open(file),
                    StandardCharsets.UTF_8.newDecoder().onMalformedInput(CodingErrorAction.REPORT)
                            .onUnmappableCharacter(CodingErrorAction.REPORT)))) {
                boolean first = true;
                String line;
                while ((line = reader.readLine()) != null) {
                    // TextInputFormat removes a UTF-8 BOM at the start of each file.
                    if (first && line.startsWith("\uFEFF")) line = line.substring(1);
                    first = false;
                    StringTokenizer tokens = new StringTokenizer(line);
                    while (tokens.hasMoreTokens()) {
                        String token = tokens.nextToken();
                        counts.put(token, counts.getOrDefault(token, 0L) + 1L);
                    }
                }
            }
        }
        PrintWriter writer = new PrintWriter(new OutputStreamWriter(System.out, StandardCharsets.UTF_8));
        for (Map.Entry<String, Long> entry : counts.entrySet()) writer.println(entry.getKey() + "\t" + entry.getValue());
        writer.flush();
    }
}
