"""
src/OtoEdit.PythonWorker/services/pipeline_logger.py
Kopmayan, Hata Fırlatmayan (Fail-Safe) 3 Katmanlı Pipeline Log Servisi
"""

import json
import logging
import requests
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from config import Config
from services.rabbitmq_publisher import RabbitMQPublisher
from utils.logger import get_logger

logger = get_logger("OtoEdit.PipelineLogger")


class PipelineLogger:
    """
    Pipeline aşama loglarını 3 katmanda yöneten fail-safe loglama servisi:
    Katman 1: Yerel Yapılandırılmış Konsol / Dosya Logu
    Katman 2: RabbitMQ Event Yayınlama (.NET MassTransit Consumer için)
    Katman 3: Doğrudan .NET REST API Çağrısı (DB kalıcılığı ve SignalR için)
    """

    def __init__(self,
                 api_base_url: Optional[str] = None,
                 api_key: Optional[str] = None,
                 publisher: Optional[RabbitMQPublisher] = None):
        base_url = (api_base_url or Config.API_BASE_URL).rstrip('/')
        self.api_url = f"{base_url}/api/internal/logs/pipeline"
        self.api_key = api_key or Config.INTERNAL_API_KEY
        self.publisher = publisher or RabbitMQPublisher()
        self.headers = {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key
        }

    def log_progress(self,
                     project_id: str,
                     video_id: str,
                     stage_name: str,
                     progress_pct: int,
                     status: str = "InProgress",
                     message: str = "",
                     details: Optional[Dict[str, Any]] = None,
                     error_message: Optional[str] = None) -> None:
        """
        Aşama ilerlemesini 3 katmanda kaydeder.
        Herhangi bir katmanda hata çıksa dahi ana video analizi ASLA durmaz.
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        
        # 1. KATMAN: Konsol ve Yerel Log
        if error_message or status == "Failed":
            logger.error(
                f"[PIPELINE-LOG][%s][%s] %%%d - Durum: %s, Hata: %s, Mesaj: %s",
                project_id, stage_name, progress_pct, status, error_message, message
            )
        else:
            logger.info(
                f"[PIPELINE-LOG][%s][%s] %%%d - Durum: %s, Mesaj: %s",
                project_id, stage_name, progress_pct, status, message
            )

        # 2. KATMAN: RabbitMQ Event Dağıtımı
        try:
            if status == "Failed" or error_message:
                self.publisher.publish_pipeline_error(
                    project_id=project_id,
                    video_id=video_id,
                    asama=stage_name,
                    hata_mesaji=error_message or message
                )
            else:
                self.publisher.publish_stage_changed(
                    project_id=project_id,
                    video_id=video_id,
                    asama=stage_name,
                    yuzde=progress_pct,
                    mesaj=message
                )
        except Exception as ex:
            logger.warning(f"RabbitMQ log yayını sırasında hata (ihmal edildi): {ex}")

        # 3. KATMAN: Doğrudan .NET REST API & DB Kalıcılığı (Fail-Safe HTTP POST)
        try:
            payload = {
                "projectId": project_id,
                "videoId": video_id,
                "stage": stage_name,
                "progressPercentage": progress_pct,
                "status": status,
                "message": message,
                "detailsJson": json.dumps(details or {}, ensure_ascii=False) if details else None,
                "errorMessage": error_message,
                "timestampUtc": now_iso
            }
            # 2 saniye sıkı zaman aşımı: Ağ yavaşsa veya API ayakta değilse pipeline'ı bloke etmez
            requests.post(self.api_url, json=payload, headers=self.headers, timeout=2.0)
        except Exception as ex:
            # Kritik kural: Log servisi çökse dahi video işleme devam eder!
            logger.debug(f"Merkezi API log endpoint'ine erişilemedi (İşlem devam ediyor): {ex}")
