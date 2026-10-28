package com.example.mergefile;

import org.apache.hadoop.conf.Configuration;
import org.apache.hadoop.conf.Configured;
import org.apache.hadoop.fs.FileSystem;
import org.apache.hadoop.fs.Path;
import org.apache.hadoop.io.Text;
import org.apache.hadoop.mapreduce.Job;
import org.apache.hadoop.mapreduce.lib.input.FileInputFormat;
import org.apache.hadoop.mapreduce.lib.input.TextInputFormat;
import org.apache.hadoop.mapreduce.lib.output.FileOutputFormat;
import org.apache.hadoop.mapreduce.lib.output.TextOutputFormat;
import org.apache.hadoop.util.Tool;
import org.apache.hadoop.util.ToolRunner;

/**
 * MergeFile 的 Driver。
 *
 * <p>用法：<code>hadoop jar mergefile.jar com.example.mergefile.MergeFileDriver &lt;input&gt; &lt;output&gt;</code>。
 *
 * <p>输入是一个包含多个文本文件的目录（也可以是单个文件）；输出是一个新目录，
 * 目录已存在时作业失败（不覆盖用户数据）。作业固定使用一个 Reducer，
 * 以保证合并结果全局有序且只产生一个结果文件。
 */
public class MergeFileDriver extends Configured implements Tool {

  /** 是否在输出中保留来源文件列，默认保留。 */
  public static final String INCLUDE_SOURCES = "mergefile.output.include-sources";

  /** INCLUDE_SOURCES 的默认值。 */
  public static final boolean DEFAULT_INCLUDE_SOURCES = true;

  /** 退出码：参数错误。 */
  public static final int EXIT_USAGE = 2;

  /** 退出码：输入路径不存在。 */
  public static final int EXIT_NO_INPUT = 3;

  @Override
  public int run(String[] args) throws Exception {
    if (args.length != 2) {
      System.err.println("用法: MergeFileDriver <input> <output>");
      System.err.println("  input  包含多个文本文件的目录，或单个文本文件");
      System.err.println("  output 输出目录，必须不存在");
      return EXIT_USAGE;
    }

    Configuration conf = getConf();
    if (conf.get(INCLUDE_SOURCES) == null) {
      conf.setBoolean(INCLUDE_SOURCES, DEFAULT_INCLUDE_SOURCES);
    }

    Path input = new Path(args[0]);
    Path output = new Path(args[1]);
    if (input.equals(output)) {
      System.err.println("错误: 输入与输出路径不能相同: " + input);
      return EXIT_USAGE;
    }

    FileSystem inputFs = input.getFileSystem(conf);
    if (!inputFs.exists(input)) {
      System.err.println("错误: 输入路径不存在: " + input);
      return EXIT_NO_INPUT;
    }
    FileSystem outputFs = output.getFileSystem(conf);
    if (outputFs.exists(output)) {
      System.err.println("错误: 输出路径已存在，不覆盖已有数据: " + output);
      return EXIT_NO_INPUT;
    }

    printRules(conf);

    Job job = Job.getInstance(conf, "MergeFile");
    job.setJarByClass(MergeFileDriver.class);
    job.setInputFormatClass(TextInputFormat.class);
    job.setOutputFormatClass(TextOutputFormat.class);
    job.setMapperClass(MergeFileMapper.class);
    job.setCombinerClass(MergeFileCombiner.class);
    job.setReducerClass(MergeFileReducer.class);
    job.setOutputKeyClass(Text.class);
    job.setOutputValueClass(Text.class);
    // 全局排序要求单一 Reducer：输出只会有一个结果文件，且已按记录升序排列。
    job.setNumReduceTasks(1);

    FileInputFormat.addInputPath(job, input);
    FileOutputFormat.setOutputPath(job, output);

    boolean ok = job.waitForCompletion(true);
    if (!ok) {
      System.err.println("错误: MergeFile 作业执行失败");
    }
    return ok ? 0 : 1;
  }

  /** 打印本次作业生效的合并规则，便于在作业日志中留证。 */
  private void printRules(Configuration conf) {
    System.out.println("[MergeFile] 合并规则: 忽略空行 | 去除首尾空白 | 区分大小写 | 记录去重"
        + " | UTF-8 字节序升序 | 输出单个结果文件");
    System.out.println("[MergeFile] 来源文件列: "
        + conf.getBoolean(INCLUDE_SOURCES, DEFAULT_INCLUDE_SOURCES));
    System.out.println("[MergeFile] Reducer 数量: 1（全局排序需要）");
  }

  public static void main(String[] args) throws Exception {
    int exitCode = ToolRunner.run(new MergeFileDriver(), args);
    System.exit(exitCode);
  }
}
