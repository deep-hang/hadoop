package com.example.mergefile;

import java.io.IOException;
import java.util.Set;
import java.util.TreeSet;

import org.apache.hadoop.io.Text;
import org.apache.hadoop.mapreduce.Reducer;

/**
 * MergeFile 的 Combiner：在 Map 端先做一次局部合并，减少 Shuffle 数据量。
 *
 * <p>合并逻辑与 Reducer 相同（次数求和、来源集合取并集），因此结果与只用 Reducer 完全一致。
 */
public class MergeFileCombiner extends Reducer<Text, Text, Text, Text> {

  @Override
  protected void reduce(Text key, Iterable<Text> values, Context context)
      throws IOException, InterruptedException {
    long count = 0;
    Set<String> sources = new TreeSet<>();
    for (Text value : values) {
      count += MergeFileValues.decodeCount(value);
      sources.addAll(MergeFileValues.decodeSources(value));
    }
    context.write(key, MergeFileReducer.format(context, count, sources));
  }
}
