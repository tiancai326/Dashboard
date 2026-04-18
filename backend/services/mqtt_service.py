import json
import logging
import os
from typing import Any

import paho.mqtt.client as mqtt

logger = logging.getLogger("dashboard-mqtt-ingest")


class MqttIngestService:
    def __init__(
        self,
        data_service: Any,
        valid_zones: list[str],
        topic_prefix: str,
        valve_ack_topic: str,
        broker: str,
        port: int,
    ) -> None:
        self.data_service = data_service
        self.valid_zones = valid_zones
        self.topic_prefix = topic_prefix
        self.valve_ack_topic = valve_ack_topic
        self.broker = broker
        self.port = port
        self.sub_topics = [(f"{self.topic_prefix}{zone}", 0) for zone in self.valid_zones]
        self.sub_topics += [(f"{self.topic_prefix}Zone_{i}", 0) for i in range(1, 7)]
        self.sub_topics += [(self.valve_ack_topic, 0)]
        self.client: mqtt.Client | None = None
        self.started = False

    @staticmethod
    def normalize_zone(value: str) -> str:
        return value.strip().lower().replace("-", "_")

    def resolve_zone(self, msg_topic: str, payload: dict[str, Any]) -> str | None:
        topic_zone = self.normalize_zone(msg_topic.split("/")[-1])
        payload_zone = self.normalize_zone(str(payload.get("zone_id", "")))
        if topic_zone in self.valid_zones:
            return topic_zone
        if payload_zone in self.valid_zones:
            return payload_zone
        return None

    def _on_connect(self, client: mqtt.Client, _userdata: Any, _flags: Any, rc: int) -> None:
        if rc != 0:
            logger.error("MQTT connect failed. rc=%s", rc)
            return
        client.subscribe(self.sub_topics)
        logger.info("MQTT connected and subscribed: %s", [t[0] for t in self.sub_topics])

    def _on_valve_ack_message(self, msg: mqtt.MQTTMessage) -> None:
        raw_text = msg.payload.decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw_text)
        except json.JSONDecodeError:
            payload = {"raw": raw_text}

        status = str(payload.get("status", "")).lower()
        message = str(payload.get("msg", payload.get("message", "")))
        if status == "ok":
            logger.info("Valve ACK success: topic=%s status=%s msg=%s payload=%s", msg.topic, status, message, payload)
        else:
            logger.warning("Valve ACK received: topic=%s status=%s msg=%s payload=%s", msg.topic, status, message, payload)

    def _on_message(self, _client: mqtt.Client, _userdata: Any, msg: mqtt.MQTTMessage) -> None:
        if msg.topic == self.valve_ack_topic:
            self._on_valve_ack_message(msg)
            return

        try:
            payload = json.loads(msg.payload.decode("utf-8"))
        except Exception as exc:
            logger.error("Invalid JSON from %s: %s", msg.topic, exc)
            return

        zone_id = self.resolve_zone(msg.topic, payload)
        if zone_id is None:
            logger.warning("Skip unknown zone. topic=%s payload=%s", msg.topic, payload)
            return

        try:
            self.data_service.insert_sensor_row(payload, zone_id)
            logger.info("Inserted sensor row: topic=%s zone_id=%s", msg.topic, zone_id)
        except Exception as exc:
            logger.exception("Insert failed: %s", exc)

    def start(self) -> None:
        if self.started:
            return
        self.client = mqtt.Client(client_id=f"dashboard_ingest_{os.getpid()}", protocol=mqtt.MQTTv311)
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.connect(self.broker, self.port, 60)
        self.client.loop_start()
        self.started = True

    def stop(self) -> None:
        if self.client is not None:
            self.client.loop_stop()
            self.client.disconnect()
        self.started = False
