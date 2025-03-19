FROM alpine:latest

RUN apk add --no-cache bash docker-cli

COPY update_node_labels.sh /usr/local/bin/update_node_labels.sh
RUN chmod +x /usr/local/bin/update_node_labels.sh

CMD ["/bin/bash", "/usr/local/bin/update_node_labels.sh"]
