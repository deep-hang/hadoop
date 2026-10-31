package com.hadooplab.wordcount;

import java.io.IOException;
import java.util.List;

import org.apache.hadoop.io.IntWritable;
import org.apache.hadoop.io.LongWritable;
import org.apache.hadoop.io.Text;
import org.apache.hadoop.mapreduce.Mapper;

/**
 * Map 阶段：把一行文本切成单词，每个单词输出一次 (单词, 1)。
 *
 * <p>输入：Hadoop 按行读入的文本分片，键是行在文件中的字节偏移（用不到），值是这一行的内容。
 * 输出：以 Text 作键、IntWritable(1) 作值，交给 Combiner / Shuffle 汇总。
 *
 * <p>复用同一个 Text 对象写输出是 MapReduce 的常规做法：框架会把键值序列化后立刻写出，
 * 不会保留对象引用，因此不需要每行都新建对象。
 */
public class WordCountMapper extends Mapper<LongWritable, Text, Text, IntWritable> {

    private static final IntWritable ONE = new IntWritable(1);

    private final Text outputKey = new Text();

    @Override
    protected void map(LongWritable key, Text value, Context context)
            throws IOException, InterruptedException {
        // 分词规则见 Tokenizer：按非字母数字切分、统一小写、空行不产生输出。
        List<String> words = Tokenizer.tokenize(value.toString());
        for (String word : words) {
            outputKey.set(word);
            context.write(outputKey, ONE);
        }
    }
}
