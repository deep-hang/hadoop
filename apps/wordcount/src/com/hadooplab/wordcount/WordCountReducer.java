package com.hadooplab.wordcount;

import java.io.IOException;

import org.apache.hadoop.io.IntWritable;
import org.apache.hadoop.io.Text;
import org.apache.hadoop.mapreduce.Reducer;

/**
 * Reduce 阶段：同一个单词的所有 1 累加，输出 (单词, 总次数)。
 *
 * <p>框架保证进入 reduce() 的键已经按单词排好序，值是同一个单词的所有计数。
 * 这个类同时被当作 Combiner 使用：Combiner 的输入输出类型与 Reduce 完全一致，
 * 它先在每个 Map 任务的输出上做一次局部合并，减少 Shuffle 传输的数据量，
 * 语义上要求“可结合、可交换”，累加满足该条件，所以不会改变最终结果。
 */
public class WordCountReducer extends Reducer<Text, IntWritable, Text, IntWritable> {

    private final IntWritable result = new IntWritable();

    @Override
    protected void reduce(Text key, Iterable<IntWritable> values, Context context)
            throws IOException, InterruptedException {
        int sum = 0;
        for (IntWritable value : values) {
            sum += value.get();
        }
        result.set(sum);
        context.write(key, result);
    }
}
