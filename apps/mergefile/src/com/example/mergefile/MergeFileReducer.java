package com.example.mergefile;

import java.io.IOException;
import java.util.Set;
import java.util.TreeSet;

import org.apache.hadoop.io.Text;
import org.apache.hadoop.mapreduce.Reducer;

/**
 * MergeFile 的 Reducer。
 *
 * <p>把同一个记录的全部出现合并为一行：键是记录本身，值是 "&lt;次数&gt;\t&lt;来源文件列表&gt;"。
 * 由于作业固定使用一个 Reducer，输出天然按记录的 UTF-8 字节序升序排列。
 */
public class MergeFileReducer extends Reducer<Text, Text, Text, Text> {

  @Override
  protected void reduce(Text key, Iterable<Text> values, Context context)
      throws IOException, InterruptedException {
    long count = 0;
    Set<String> sources = new TreeSet<>();
    for (Text value : values) {
      count += MergeFileValues.decodeCount(value);
      sources.addAll(MergeFileValues.decodeSources(value));
    }
    context.write(key, format(context, count, sources));
  }

  /** 按配置决定输出是否带来源文件列。 */
  static Text format(Context context, long count, Set<String> sources) {
    boolean withSources = context.getConfiguration()
        .getBoolean(MergeFileDriver.INCLUDE_SOURCES, MergeFileDriver.DEFAULT_INCLUDE_SOURCES);
    if (!withSources) {
      return MergeFileValues.encodeCountOnly(count);
    }
    return MergeFileValues.encode(count, sources);
  }
}
