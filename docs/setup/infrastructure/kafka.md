# Kafka & Zookeeper

Managed by Compose (`infrastructure/compose/docker-compose.yml`). Provides the backbone for event transport.

- Zookeeper: `confluentinc/cp-zookeeper:7.8.0`
- Kafka: custom image built from `infrastructure/compose/kafka/Dockerfile`

## Listeners and Ports

- Internal: 19092 (broker intercommunication)
- External: 9092 (host access)
- Docker: 29092 (container-to-container via host.docker.internal)
- JMX: 9999 with Prometheus Java agent on 7071

See `KAFKA_ADVERTISED_LISTENERS` and related env vars in compose.

## Topics

Topic names are centralized in `shared/constants/topics.py`. Topic creation may be handled by services on startup.

## Monitoring

JMX metrics exported via `jmx_prometheus_javaagent.jar` configured by `monitoring/jmx/kafka-jmx-exporter.yml`.
