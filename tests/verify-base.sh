#!/usr/bin/env bash
# Run inside the base image. No HDFS, YARN, WordCount or MergeFile test here.
set -euo pipefail
cd /workspace
source .development
java -version 2>&1 | grep -F "\"${JDK_VERSION}\""
javac -version 2>&1 | grep -F "javac ${JDK_VERSION}"
hadoop version | grep -Fx "Hadoop ${HADOOP_VERSION}"
[[ "$JAVA_HOME" == /opt/java/openjdk && "$HADOOP_HOME" == /opt/hadoop ]]
[[ "$HADOOP_CONF_DIR" == /opt/hadoop/etc/hadoop && "$PWD" == "$WORKSPACE" ]]
test -r "$HADOOP_CONF_DIR/core-site.xml"
test -w "$HADOOP_LOG_DIR"

# Prove members can compile against Hadoop APIs and run a JVM, not just print versions.
scratch="$(mktemp -d)"
trap 'rm -rf -- "$scratch"' EXIT
cat > "$scratch/BaseProbe.java" <<'JAVA'
import org.apache.hadoop.conf.Configuration;
public class BaseProbe {
    public static void main(String[] args) {
        Configuration conf = new Configuration();
        if (!"file:///".equals(conf.get("fs.defaultFS"))) {
            throw new IllegalStateException("Base image unexpectedly targets a cluster");
        }
        System.out.println("BASE_API_PASS");
    }
}
JAVA
classpath="$(hadoop classpath --glob)"
javac -encoding UTF-8 -cp "$classpath" -d "$scratch" "$scratch/BaseProbe.java"
java -cp "$scratch:$classpath" BaseProbe | grep -Fx BASE_API_PASS
printf 'PASS: frozen Java/Hadoop versions, paths, compiler and Hadoop API loading\n'
