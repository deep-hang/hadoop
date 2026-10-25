import java.io.*;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.*;
import org.apache.hadoop.fs.*;
import org.apache.hadoop.mapred.JobConf;
import org.apache.hadoop.hdfs.DistributedFileSystem;
import org.apache.hadoop.hdfs.protocol.HdfsConstants;

/** Read-only, structured evidence. Compiled against the existing Hadoop image. */
public final class ConsoleInspect {
    static final JobConf CONF = new JobConf();
    static Map<String,Object> obj(Object... values) {
        Map<String,Object> out = new LinkedHashMap<>();
        for (int i=0; i<values.length; i+=2) out.put((String)values[i], values[i+1]);
        return out;
    }
    static String json(Object value) {
        if (value == null) return "null";
        if (value instanceof Number || value instanceof Boolean) return value.toString();
        if (value instanceof Map) {
            List<String> items = new ArrayList<>();
            for (Object raw : ((Map<?,?>)value).entrySet()) {
                Map.Entry<?,?> e = (Map.Entry<?,?>)raw;
                items.add(json(e.getKey().toString()) + ":" + json(e.getValue()));
            }
            return "{" + String.join(",", items) + "}";
        }
        if (value instanceof Iterable) {
            List<String> items = new ArrayList<>();
            for (Object item : (Iterable<?>)value) items.add(json(item));
            return "[" + String.join(",", items) + "]";
        }
        StringBuilder out = new StringBuilder("\"");
        for (char c : value.toString().toCharArray()) {
            if (c == '"' || c == '\\') out.append('\\').append(c);
            else if (c < 32) out.append(String.format("\\u%04x", (int)c));
            else out.append(c);
        }
        return out.append('"').toString();
    }
    static void id(String id) {
        if (!id.matches("[A-Za-z0-9_-]+")) throw new IllegalArgumentException("Invalid run ID");
    }
    static void safe(FileSystem fs, Path path) throws IOException {
        for (Path p=path; p!=null; p=p.getParent()) {
            if (fs.exists(p) && fs.getFileLinkStatus(p).isSymlink())
                throw new IOException("Symbolic links are not allowed: " + p);
        }
    }
    static boolean visible(Path path) {
        return !path.getName().startsWith(".") && !path.getName().startsWith("_");
    }
    static List<Object> listing(FileSystem fs, Path path, boolean hashes) throws Exception {
        safe(fs,path);
        if (!fs.exists(path)) throw new FileNotFoundException(path.toString());
        List<Object> rows = new ArrayList<>();
        FileStatus[] entries = fs.listStatus(path);
        Arrays.sort(entries, Comparator.comparing(s -> s.getPath().getName()));
        for (FileStatus entry : entries) {
            Path p=entry.getPath();
            if (hashes && !visible(p)) continue;
            safe(fs,p);
            Map<String,Object> row = obj("name",p.getName(),"bytes",entry.getLen(),"directory",entry.isDirectory());
            if (hashes) {
                if (!entry.isFile()) throw new IOException("Nested input directory: " + p);
                MessageDigest digest=MessageDigest.getInstance("SHA-256");
                try (InputStream in=fs.open(p)) {
                    byte[] buffer=new byte[65536]; int n;
                    while ((n=in.read(buffer))!=-1) digest.update(buffer,0,n);
                }
                StringBuilder hex=new StringBuilder();
                for (byte b:digest.digest()) hex.append(String.format("%02x", b & 255));
                row.remove("directory"); row.put("sha256",hex.toString());
            }
            rows.add(row);
        }
        return rows;
    }
    static Path hdfsPath(String area, String id) {
        if (!area.equals("input") && !area.equals("output")) throw new IllegalArgumentException("Invalid area");
        if (!id.isEmpty()) id(id);
        return new Path("/project/" + area + "/member5" + (id.isEmpty()? "" : "/"+id));
    }
    public static void main(String[] args) throws Exception {
        String action=args[0];
        try (FileSystem fs=FileSystem.get(CONF)) {
            Map<String,Object> result=obj("fs",CONF.get("fs.defaultFS"),"framework",CONF.get("mapreduce.framework.name"));
            List<String> processes=new ArrayList<>();
            Process jps=new ProcessBuilder("jps").start();
            try (BufferedReader reader=new BufferedReader(new InputStreamReader(jps.getInputStream(),StandardCharsets.UTF_8))) {
                String line; while ((line=reader.readLine())!=null) processes.add(line);
            }
            if (jps.waitFor()!=0) throw new IOException("Cannot inspect Java processes");
            result.put("java_processes",processes);
            if (fs instanceof DistributedFileSystem) {
                DistributedFileSystem dfs=(DistributedFileSystem)fs;
                result.put("live_datanodes",dfs.getDataNodeStats(HdfsConstants.DatanodeReportType.LIVE).length);
                result.put("safe_mode",dfs.setSafeMode(HdfsConstants.SafeModeAction.SAFEMODE_GET));
            }
            if (action.equals("inspect")) {
                String mode=args[1], run=args[2]; id(run);
                if (!mode.equals("standalone") && !mode.equals("pseudo")) throw new IllegalArgumentException("Invalid mode");
                String base="/workspace/runtime/member5/standalone/"+run;
                Path input=mode.equals("pseudo")?hdfsPath("input",run):new Path(base+"/input");
                Path output=mode.equals("pseudo")?hdfsPath("output",run):new Path(base+"/output");
                safe(fs,input); safe(fs,output);
                result.put("input_path",input.toString()); result.put("output_path",output.toString());
                result.put("input_exists",fs.exists(input)); result.put("output_exists",fs.exists(output));
                result.put("success_marker",fs.isFile(new Path(output,"_SUCCESS")));
                if (fs.exists(input)) result.put("manifest",listing(fs,input,true));
                StringBuilder contents=new StringBuilder();
                if (fs.exists(output)) for (FileStatus part:fs.listStatus(output)) {
                    if (!part.getPath().getName().startsWith("part-r-")) continue;
                    safe(fs,part.getPath());
                    try (BufferedReader reader=new BufferedReader(new InputStreamReader(fs.open(part.getPath()),StandardCharsets.UTF_8))) {
                        String line; while ((line=reader.readLine())!=null) contents.append(line).append('\n');
                    }
                }
                result.put("output_text",contents.toString());
            } else if (action.equals("ls")) {
                result.put("files",listing(fs,hdfsPath(args[1],args.length>2?args[2]:""),false));
            } else if (action.equals("preview")) {
                String name=args[3];
                if (name.isEmpty() || name.equals(".") || name.equals("..") || name.contains("/") || name.contains("\\") || name.contains(":"))
                    throw new IllegalArgumentException("Only a filename inside this run is allowed");
                Path path=new Path(hdfsPath(args[1],args[2]),name); safe(fs,path);
                if (!fs.isFile(path)) throw new FileNotFoundException(path.toString());
                ByteArrayOutputStream bytes=new ByteArrayOutputStream();
                try (InputStream in=fs.open(path)) {
                    byte[] buffer=new byte[4096]; int n;
                    while (bytes.size()<65536 && (n=in.read(buffer,0,Math.min(buffer.length,65536-bytes.size())))!=-1) bytes.write(buffer,0,n);
                }
                String text=new String(bytes.toByteArray(),StandardCharsets.UTF_8);
                String[] lines=text.split("\n",-1);
                boolean truncated=fs.getFileStatus(path).getLen()>65536 || lines.length>200;
                result.put("text",String.join("\n",Arrays.copyOf(lines,Math.min(lines.length,200))));
                result.put("truncated",truncated); result.put("bytes_read",bytes.size());
            } else if (!action.equals("probe")) throw new IllegalArgumentException("Invalid inspection action");
            System.out.println(json(result));
        }
    }
}
