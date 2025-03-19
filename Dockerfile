FROM alpine:latest

RUN apk add --no-cache docker-cli bash

COPY update_node_labels.sh /usr/local/bin/update_node_labels.sh
RUN chmod +x /usr/local/bin/update_node_labels.sh

CMD ["/usr/local/bin/update_node_labels.sh"]
