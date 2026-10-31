package com.hadooplab.wordcount;

import org.apache.hadoop.conf.Configuration;
import org.apache.hadoop.conf.Configured;
import org.apache.hadoop.fs.FileSystem;
import org.apache.hadoop.fs.Path;
import org.apache.hadoop.io.IntWritable;
import org.apache.hadoop.io.Text;
import org.apache.hadoop.mapreduce.Job;
import org.apache.hadoop.mapreduce.lib.input.FileInputFormat;
import org.apache.hadoop.mapreduce.lib.output.FileOutputFormat;
import org.apache.hadoop.util.Tool;
import org.apache.hadoop.util.ToolRunner;

/**
 * Driver：组装并提交 WordCount 作业。
 *
 * <p>用法：{@code WordCountDriver <输入路径> <输出路径>}
 *
 * <p>因为实现了 {@link Tool} 并用 {@link ToolRunner} 启动，命令行可以额外传 Hadoop 通用参数，
 * 例如 {@code -D mapreduce.job.reduces=2} 指定 Reduce 任务数、{@code -D mapreduce.framework.name=local}
 * 切到本地模式调试。这些 -D 参数由 ToolRunner 先解析进 Configuration，再调用 run()。
 *
 * <p>退出码约定：0 成功，1 作业失败，2 参数错误或输出目录已存在。
 */
public class WordCountDriver extends Configured implements Tool {

    /** 参数错误。 */
    public static final int EXIT_USAGE = 2;
    /** 作业执行失败。 */
    public static final int EXIT_FAILURE = 1;

    @Override
    public int run(String[] args) throws Exception {
        if (args.length != 2) {
            System.err.println("用法: WordCountDriver <输入路径> <输出路径>");
            return EXIT_USAGE;
        }

        Path inputPath = new Path(args[0]);
        Path outputPath = new Path(args[1]);
        Configuration conf = getConf();

        // 输出目录必须不存在：不默认删除已有结果，避免覆盖其他同学的演示数据。
        FileSystem outputFs = outputPath.getFileSystem(conf);
        if (outputFs.exists(outputPath)) {
            System.err.println("输出路径已存在，拒绝覆盖: " + outputPath);
            return EXIT_USAGE;
        }

        Job job = Job.getInstance(conf, "wordcount");
        job.setJarByClass(WordCountDriver.class);

        job.setMapperClass(WordCountMapper.class);
        job.setCombinerClass(WordCountReducer.class);
        job.setReducerClass(WordCountReducer.class);

        // Map 输出类型：单词作键、1 作值。
        job.setMapOutputKeyClass(Text.class);
        job.setMapOutputValueClass(IntWritable.class);
        // 最终输出类型：单词作键、总次数作值。
        job.setOutputKeyClass(Text.class);
        job.setOutputValueClass(IntWritable.class);

        FileInputFormat.addInputPath(job, inputPath);
        FileOutputFormat.setOutputPath(job, outputPath);

        boolean succeeded = job.waitForCompletion(true);
        if (!succeeded) {
            System.err.println("作业失败，未能得到结果。");
            return EXIT_FAILURE;
        }
        return 0;
    }

    public static void main(String[] args) throws Exception {
        int exitCode = ToolRunner.run(new Configuration(), new WordCountDriver(), args);
        System.exit(exitCode);
    }
}
