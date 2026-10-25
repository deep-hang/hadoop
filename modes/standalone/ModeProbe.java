import org.apache.hadoop.mapred.JobConf;

/** Inspect the configuration actually loaded by MapReduce, not just XML text. */
public final class ModeProbe {
    public static void main(String[] args) {
        JobConf conf = new JobConf();
        String fs = conf.get("fs.defaultFS");
        String framework = conf.get("mapreduce.framework.name");
        if (args.length != 1 || !args[0].equals(fs) || !"local".equals(framework)) {
            throw new IllegalStateException("Unexpected configuration: fs=" + fs
                    + ", framework=" + framework);
        }
        System.out.println("MODE_CONFIG_PASS fs.defaultFS=" + fs
                + " mapreduce.framework.name=" + framework);
    }
}
