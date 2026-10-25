package com.example.mergefile;

import java.io.IOException;

import org.apache.hadoop.io.LongWritable;
import org.apache.hadoop.io.Text;
import org.apache.hadoop.mapreduce.InputSplit;
import org.apache.hadoop.mapreduce.Mapper;
import org.apache.hadoop.mapreduce.lib.input.FileSplit;

/**
 * MergeFile 的 Mapper。
 *
 * <p>把每个输入文件的每一行当作一条记录，键为规范化后的记录内容，值为
 * "&lt;次数&gt;\t&lt;来源文件1&gt;,&lt;来源文件2&gt;,..."。空行与只含空白字符的行被丢弃，
 * 具体规则见 apps/mergefile/README.md 与 docs/modules/mergefile/README.md。
 */
public class MergeFileMapper extends Mapper<LongWritable, Text, Text, Text> {

  private final Text outKey = new Text();
  private final Text outValue = new Text();

  @Override
  protected void map(LongWritable key, Text value, Context context)
      throws IOException, InterruptedException {
    String record = normalize(value.toString());
    if (record.isEmpty()) {
      // 规则：空行与只含空白字符的行不参与合并。
      return;
    }
    String source = sourceName(context.getInputSplit());
    outKey.set(record);
    outValue.set(MergeFileValues.encodeCount(1L, source));
    context.write(outKey, outValue);
  }

  /**
   * 记录所属的来源文件名。
   *
   * <p>作业固定使用 TextInputFormat，切片一定是 FileSplit，取文件名的最后一段作为来源标识。
   */
  static String sourceName(InputSplit split) throws IOException {
    if (!(split instanceof FileSplit)) {
      throw new IOException("期望 FileSplit，实际为: " + split.getClass().getName());
    }
    return ((FileSplit) split).getPath().getName();
  }

  /**
   * 规范化一条记录：去掉首尾空白字符（空格、制表符、回车、换行等 ASCII &lt;= U+0020）。
   * 行内空白保留，因此 "a b" 与 "a  b" 是两条不同记录。
   */
  static String normalize(String line) {
    return line == null ? "" : line.trim();
  }
}
