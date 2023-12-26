# Use the official Elasticsearch Docker image from Docker Hub
FROM docker.elastic.co/elasticsearch/elasticsearch:7.15.2

# Set environment variables for Elasticsearch
ENV ELASTICSEARCH_URL=https://localhost:9200
ENV ELASTICSEARCH_USERNAME=elastic
ENV ELASTICSEARCH_PASSWORD=1_W28jlMre-sx005bcoB

# Expose ports
EXPOSE 9200
EXPOSE 9300

# Start Elasticsearch in the container
CMD ["elasticsearch"]
