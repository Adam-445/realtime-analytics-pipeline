from confluent_kafka.admin import AdminClient, NewTopic


def create_topic():
    config = {"bootstrap.servers": "kafka1:19092"}
    admin = AdminClient(config)

    topic = NewTopic(
        "analytics_events",
        num_partitions=3,
        replication_factor=1,
        config={"retention.ms": "604800000"},  # 7 days
    )

    result = admin.create_topics([topic])
    for topic, future in result.items():
        try:
            future.result()
            print("" "Topic {} created".format(topic))
        except Exception as e:
            print("Failed to create topic {}: {}".format(topic, e))
