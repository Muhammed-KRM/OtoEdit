"""
RabbitMQ Bağlantı Koruyucu Nabız (Heartbeat) Yöneticisi
Uzun süren ağır video/AI işlemleri sırasında RabbitMQ BlockingConnection
soketinin kopmasını (StreamLostError / ConnectionReset) önlemek için arka planda
periyodik event işleyen thread yöneticisi.
"""

import threading
import time
import logging
from typing import Optional

logger = logging.getLogger("OtoEdit.HeartbeatManager")


class RabbitHeartbeatKeeper:
    """
    Uzun süren video/AI işlemlerinde RabbitMQ bağlantısının kopmasını
    engellemek için arka planda düzenli event pompalayan servis.
    """

    def __init__(self, connection, interval_sec: float = 10.0):
        self._connection = connection
        self._interval = interval_sec
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Nabız thread'ini başlatır."""
        if not self._connection or not getattr(self._connection, "is_open", False):
            logger.warning("[HeartbeatKeeper] Geçerli ve açık bir bağlantı verilmedi, başlatılamıyor.")
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="RabbitMQ-HeartbeatKeeper")
        self._thread.start()
        logger.info("💓 [HeartbeatKeeper] RabbitMQ arka plan nabız thread'i başlatıldı (Aralık: %.1f sn).", self._interval)

    def stop(self) -> None:
        """Nabız thread'ini durdurur."""
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        logger.info("🛑 [HeartbeatKeeper] RabbitMQ arka plan nabız thread'i durduruldu.")

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                if self._connection and getattr(self._connection, "is_open", False):
                    # Soket seviyesinde nabız gönder ve bekleyen frame'leri temizle
                    self._connection.process_data_events(time_limit=0)
            except Exception as ex:
                # Ağ veya soket geçici hatalarında thread'in patlamasını önle
                logger.debug("[HeartbeatKeeper] process_data_events geçici durum: %s", str(ex))

            # Belirlenen aralıkla bekle, ancak stop sinyaline anında tepki ver
            self._stop_event.wait(self._interval)
