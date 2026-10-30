package com.hadooplab.wordcount;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * WordCount 固定分词规则，Mapper 与测试共用同一份实现，保证“代码、输入、预期结果”三者一致。
 *
 * <p>规则只有三条：
 * <ol>
 *   <li>一个“单词”是连续的字母或数字（Java 正则里的 \p{L} 和 \p{N}，含中文、日文等 Unicode 字母）；</li>
 *   <li>其余字符（空格、制表符、标点、引号、括号等）都是分隔符，本身不产生单词；</li>
 *   <li>所有单词统一转成小写（Locale.ROOT，避免土耳其语等地区设置影响 i/I 转换），因此不区分大小写。</li>
 * </ol>
 *
 * <p>空行、纯标点行、纯空白行不含任何字母数字，切分后得到 0 个单词，Mapper 不会输出任何键值对。
 *
 * <p>注意：不使用 String.split，因为分隔符是“连续的非字母数字串”，用正则查找更直观，
 * 也不会在同一条记录里产生空字符串碎片。
 */
public final class Tokenizer {

    /** 连续字母或数字构成一个单词。 */
    private static final Pattern WORD_PATTERN = Pattern.compile("[\\p{L}\\p{N}]+");

    private Tokenizer() {
        // 工具类，不实例化。
    }

    /**
     * 把一行文本切成单词列表。
     *
     * @param line 一行原始文本，可为 null
     * @return 小写单词列表，顺序与原文一致；没有单词时返回空列表（不是 null）
     */
    public static List<String> tokenize(String line) {
        List<String> words = new ArrayList<String>();
        if (line == null || line.isEmpty()) {
            return words;
        }
        Matcher matcher = WORD_PATTERN.matcher(line);
        while (matcher.find()) {
            words.add(matcher.group().toLowerCase(Locale.ROOT));
        }
        return words;
    }
}
