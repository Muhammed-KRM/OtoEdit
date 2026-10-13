"""
OtoEdit STT Hız Sınırlayıcı ve Anahtar Rotasyon Yöneticisi
- Birden fazla API anahtarı arasında rotasyon yapar.
- Dakika başına istek sınırını (RPM) takip eder.
- 429 kota aşımlarında retryDelay süresince anahtarı soğumaya alır.
- Eğer tüm anahtarlar meşgulse ve bekleme süresi sınırı aşıyorsa sonraki motora devredilmesini sağlar.
"""

import time
import threading
from typing import List, Optional
from config import Config
from utils.logger import get_logger

logger = get_logger("STT.RateLimiter")


class KeyState:
    def __init__(self, key: str, max_rpm: int = 3):
        self.key = key
        self.max_rpm = max_rpm
        self.request_timestamps: List[float] = []
        self.cool_down_until: float = 0.0
        self.lock = threading.Lock()

    def is_cooling_down(self, now: float) -> bool:
        return now < self.cool_down_until

    def available_in_sec(self, now: float) -> float:
        """Bu anahtarın kullanıma hazır olmasına kaç saniye kaldığını döner (0 ise hazır)."""
        with self.lock:
            # 1. Soğuma kontrolü (429'dan kaynaklı)
            if now < self.cool_down_until:
                return self.cool_down_until - now

            # 2. RPM kayan pencere kontrolü (son 60 sn)
            cutoff = now - 60.0
            self.request_timestamps = [t for t in self.request_timestamps if t > cutoff]

            if len(self.request_timestamps) < self.max_rpm:
                return 0.0

            # En eski isteğin 60 saniyeyi doldurmasını bekle
            oldest = self.request_timestamps[0]
            wait = max(0.0, (oldest + 60.0) - now)
            return wait

    def record_request(self, now: float):
        with self.lock:
            self.request_timestamps.append(now)

    def mark_rate_limited(self, now: float, retry_delay_sec: float = 20.0):
        with self.lock:
            self.cool_down_until = now + retry_delay_sec
            logger.warning(
                f"⏳ Anahtar {self.key[:6]}... kota aşımı (429) nedeniyle "
                f"{retry_delay_sec:.1f} sn soğumaya alındı."
            )


class GeminiKeyRotator:
    """Gemini API anahtarları arasında rotasyon ve RPM kontrolü yapan yönetici."""

    def __init__(self, api_keys: List[str], max_rpm: int = 3, max_wait_sec: float = None):
        self.keys = [k.strip() for k in api_keys if k.strip()]
        self.max_rpm = max_rpm
        self.max_wait_sec = max_wait_sec if max_wait_sec is not None else getattr(Config, "GEMINI_TRANSCRIBE_MAX_WAIT_SEC", 180.0)
        self.states = [KeyState(k, max_rpm=max_rpm) for k in self.keys]
        self._current_idx = 0
        self._lock = threading.Lock()

    def get_available_key(self, wait_if_needed: bool = True) -> Optional[str]:
        """
        Kullanıma uygun bir anahtar bulur ve döner.
        Eğer tüm anahtarlar sınıra takıldıysa ve bekleme süresi max_wait_sec altındaysa bekler.
        Aksi takdirde None döner (sonraki motora geçilmesi için).
        """
        if not self.states:
            return None

        start_time = time.time()
        while True:
            now = time.time()
            elapsed = now - start_time
            if elapsed > self.max_wait_sec:
                logger.warning(f"⚠️ Maksimum bekleme süresi ({self.max_wait_sec}s) aşıldı, sonraki motora devrediliyor.")
                return None

            with self._lock:
                # Round-robin sırayla anahtarları tara
                best_wait = float("inf")
                best_state: Optional[KeyState] = None

                for i in range(len(self.states)):
                    idx = (self._current_idx + i) % len(self.states)
                    st = self.states[idx]
                    wait = st.available_in_sec(now)
                    if wait == 0.0:
                        self._current_idx = (idx + 1) % len(self.states)
                        st.record_request(now)
                        return st.key
                    if wait < best_wait:
                        best_wait = wait
                        best_state = st

            if not wait_if_needed:
                return None

            remaining_budget = self.max_wait_sec - elapsed
            if best_wait > remaining_budget:
                logger.info(f"⏳ En erken anahtar {best_wait:.1f} sn sonra hazır ancak kalan bekleme bütçesi ({remaining_budget:.1f}s) yetersiz. Sonraki motora geçiliyor.")
                return None

            sleep_duration = min(best_wait + 0.1, 5.0)
            logger.info(f"⏳ Gemini kota soğuması/beklemesi: {best_wait:.1f} sn kaldı (bu adımda {sleep_duration:.1f} sn bekleniyor)...")
            time.sleep(sleep_duration)

    def report_429(self, key: str, retry_delay_sec: float = 20.0):
        now = time.time()
        for st in self.states:
            if st.key == key:
                st.mark_rate_limited(now, retry_delay_sec)
                break
