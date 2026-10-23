import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import org.apache.hadoop.fs.*;

/** Structured, scoped reads. Uses the original independent Java reference. */
public final class WebPlusInspect {
    public static void main(String[] args) throws Exception {
        String action=args[0];
        if (action.equals("diagnose")) {
            String mode=args[1], id=args[2]; ConsoleInspect.id(id);
            if (!mode.equals("standalone") && !mode.equals("pseudo")) throw new IllegalArgumentException("Invalid mode");
            ByteArrayOutputStream expected=new ByteArrayOutputStream();
            PrintStream previous=System.out;
            try {
                System.setOut(new PrintStream(expected,true,"UTF-8"));
                InputCounts.main(new String[]{"file:///member5-input"});
            } finally { System.setOut(previous); }
            try (FileSystem fs=FileSystem.get(ConsoleInspect.CONF)) {
                Path output=mode.equals("pseudo")?ConsoleInspect.hdfsPath("output",id):new Path("/workspace/runtime/member5/standalone/"+id+"/output");
                ConsoleInspect.safe(fs,output);
                StringBuilder actual=new StringBuilder(); int parts=0;
                if (fs.exists(output)) {
                    FileStatus[] files=fs.listStatus(output);
                    Arrays.sort(files,Comparator.comparing(f->f.getPath().getName()));
                    for (FileStatus file:files) if(file.getPath().getName().startsWith("part-r-")) {
                        ConsoleInspect.safe(fs,file.getPath());
                        if (!file.isFile()) throw new IOException("Result part is not a file");
                        parts++;
                        try (BufferedReader in=new BufferedReader(new InputStreamReader(fs.open(file.getPath()),StandardCharsets.UTF_8))) {
                            String line; while((line=in.readLine())!=null) actual.append(line).append('\n');
                        }
                    }
                }
                System.out.println(ConsoleInspect.json(ConsoleInspect.obj("expected_text",expected.toString("UTF-8"),"actual_text",actual.toString(),
                    "output_exists",fs.exists(output),"success_marker",fs.isFile(new Path(output,"_SUCCESS")),"part_count",parts,
                    "output_path",output.toString(),"fs",ConsoleInspect.CONF.get("fs.defaultFS"))));
            }
        } else if (action.equals("ls")) {
            try (FileSystem fs=FileSystem.get(ConsoleInspect.CONF)) {
                Path path=ConsoleInspect.hdfsPath(args[1],args[2]); ConsoleInspect.safe(fs,path);
                if(!fs.exists(path)) throw new FileNotFoundException(path.toString());
                List<Object> rows=new ArrayList<>();
                for(FileStatus file:fs.listStatus(path)) {
                    ConsoleInspect.safe(fs,file.getPath());
                    rows.add(ConsoleInspect.obj("name",file.getPath().getName(),"bytes",file.getLen(),"directory",file.isDirectory(),"modified_ms",file.getModificationTime()));
                }
                System.out.println(ConsoleInspect.json(ConsoleInspect.obj("files",rows,"path",path.toString(),"fs",ConsoleInspect.CONF.get("fs.defaultFS"))));
            }
        } else throw new IllegalArgumentException("Invalid action");
    }
}
