FROM alpine

ENV LANG C.UTF-8

RUN apk add py3-cryptography py3-paho-mqtt
COPY setup.py /tmp/build/
COPY broadlink_bridge/ /tmp/build/broadlink_bridge/
RUN pip3 install /tmp/build \
    && rm -Rf /tmp/build

RUN mkdir -p /config && touch /config/config.ini
VOLUME [ "/config" ]

USER nobody
EXPOSE 8765 8780
CMD [ "broadlink-bridge", "/config/config.ini" ]
