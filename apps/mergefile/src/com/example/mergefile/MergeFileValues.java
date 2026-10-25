package com.example.mergefile;

import java.util.Set;
import java.util.TreeSet;

import org.apache.hadoop.io.Text;

/**
 * 输出值的编码与解码。
 *
 * <p>编码格式：<code>&lt;次数&gt;\t&lt;来源文件1&gt;,&lt;来源文件2&gt;,...</code>。
 * 来源文件名按字典序排列并去重，输入文件名不应包含制表符或逗号。
 */
final class MergeFileValues {

  /** 次数与来源列表之间的分隔符。 */
  static final char FIELD_SEPARATOR = '\t';

  /** 来源文件列表内部的分隔符。 */
  static final char SOURCE_SEPARATOR = ',';

  private MergeFileValues() {
  }

  /** 只含一个来源文件时使用。 */
  static Text encodeCount(long count, String source) {
    Set<String> sources = new TreeSet<>();
    sources.add(source);
    return encode(count, sources);
  }

  /** 次数与已排序的来源集合。 */
  static Text encode(long count, Set<String> sources) {
    StringBuilder builder = new StringBuilder();
    builder.append(count).append(FIELD_SEPARATOR);
    boolean first = true;
    for (String source : sources) {
      if (!first) {
        builder.append(SOURCE_SEPARATOR);
      }
      builder.append(source);
      first = false;
    }
    return new Text(builder.toString());
  }

  /** 只输出次数时使用（mergefile.output.include-sources=false）。 */
  static Text encodeCountOnly(long count) {
    return new Text(Long.toString(count));
  }

  /** 解析次数；缺少分隔符时整个值都是次数。 */
  static long decodeCount(Text value) {
    String text = value.toString();
    int index = text.indexOf(FIELD_SEPARATOR);
    String head = index < 0 ? text : text.substring(0, index);
    try {
      return Long.parseLong(head.trim());
    } catch (NumberFormatException e) {
      throw new IllegalArgumentException("无法解析次数: " + text, e);
    }
  }

  /** 解析来源文件列表。 */
  static Set<String> decodeSources(Text value) {
    Set<String> sources = new TreeSet<>();
    String text = value.toString();
    int index = text.indexOf(FIELD_SEPARATOR);
    if (index < 0) {
      return sources;
    }
    String list = text.substring(index + 1).trim();
    if (list.isEmpty()) {
      return sources;
    }
    for (String source : list.split(String.valueOf(SOURCE_SEPARATOR))) {
      String trimmed = source.trim();
      if (!trimmed.isEmpty()) {
        sources.add(trimmed);
      }
    }
    return sources;
  }
}
