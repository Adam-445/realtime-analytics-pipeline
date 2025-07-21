FROM confluentinc/cp-kafka:7.8.0

USER root

RUN mkdir -p /opt/kafka \
    && curl -fSL \
    -o /opt/kafka/jmx_prometheus_javaagent.jar \
    https://repo1.maven.org/maven2/io/prometheus/jmx/jmx_prometheus_javaagent/1.0.1/jmx_prometheus_javaagent-1.0.1.jar \
    && chmod 644 /opt/kafka/jmx_prometheus_javaagent.jar

USER appuser
