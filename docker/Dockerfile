# Frozen Ubuntu 22.04 + Temurin JDK 8u442-b06, verified registry manifest.
FROM eclipse-temurin:8u442-b06-jdk-jammy@sha256:5150f98fd1f01d469d3d4073d73f3144e1e56304c131a17228c75de32cb76107

ENV HADOOP_VERSION=3.3.6 \
    HADOOP_HOME=/opt/hadoop \
    HADOOP_CONF_DIR=/opt/hadoop/etc/hadoop \
    HADOOP_LOG_DIR=/opt/hadoop/logs \
    WORKSPACE=/workspace
ENV PATH="${HADOOP_HOME}/bin:${HADOOP_HOME}/sbin:${PATH}"

# No apt upgrade: all OS tools come from the immutable parent image.
# The SHA512 is the official Apache release checksum, not a build-time lookup.
RUN --mount=type=bind,source=docker/cache,target=/cache \
    set -eux; \
    if [ -f "/cache/hadoop-${HADOOP_VERSION}.tar.gz" ]; then \
      cp "/cache/hadoop-${HADOOP_VERSION}.tar.gz" /tmp/hadoop.tar.gz; \
    else \
      curl -fL --retry 3 --connect-timeout 30 \
      "https://archive.apache.org/dist/hadoop/common/hadoop-${HADOOP_VERSION}/hadoop-${HADOOP_VERSION}.tar.gz" \
      -o /tmp/hadoop.tar.gz; \
    fi; \
    echo 'de3eaca2e0517e4b569a88b63c89fae19cb8ac6c01ff990f1ff8f0cc0f3128c8e8a23db01577ca562a0e0bb1b4a3889f8c74384e609cd55e537aada3dcaa9f8a  /tmp/hadoop.tar.gz' | sha512sum -c -; \
    tar -xzf /tmp/hadoop.tar.gz -C /opt; \
    mv "/opt/hadoop-${HADOOP_VERSION}" "$HADOOP_HOME"; \
    rm /tmp/hadoop.tar.gz; \
    useradd --create-home --uid 1000 --shell /bin/bash hadoop; \
    mkdir -p /workspace /var/lib/hadoop /opt/hadoop/logs; \
    chown -R hadoop:hadoop /workspace /var/lib/hadoop /opt/hadoop

COPY config/common/ /opt/hadoop/etc/hadoop/
COPY docker/entrypoint.sh /usr/local/bin/hadoop-entrypoint
RUN chmod 755 /usr/local/bin/hadoop-entrypoint
USER hadoop
WORKDIR /workspace
ENTRYPOINT ["/usr/local/bin/hadoop-entrypoint"]
CMD ["bash"]
