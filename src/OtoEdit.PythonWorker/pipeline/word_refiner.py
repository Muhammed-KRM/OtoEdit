"""
OtoEdit Kelime Sınırı İyileştirici (Word Boundary Refiner)

Whisper/Groq kelime zaman damgalarını gerçek ses fonasyonuna (RMS zarfı) kilitler.
İki aşamalıdır:

1. Küme Kırpması (yalnızca > 0.65s kelimeler):
   Whisper, duraklama / nefes / kumanda tıkını bitişik kelimenin içine gömer
   (örn. 'bizzat' 8.1s). Kelime aralığındaki konuşma kümeleri çıkarılır ve
   cümle akışına göre gerçek kelime kümesi seçilir.

2. Kenar Koruması (tüm kelimeler, histerezis):
   Kelime sonlarındaki yumuşak sesler (-r, -s, -ş, nefesli kapanış) yüksek eşiğin
   altında kalır ve kesimin kelimeyi yutmasına sebep olur. Kelime sonu/başı,
   düşük eşiğin üzerinde kalan kesintisiz enerji boyunca komşu kelimeye
   taşmadan genişletilir. Böylece kesim asla kelime bitmeden başlamaz.

Tek kaynak: Transcriber bu modülü kullanır; Retake ve Jump-Cut motorları
iyileştirilmiş kelimelerle çalışır.
"""
from typing import List, Optional, Tuple
import numpy as np

# Kırpma yapılacak minimum kelime süresi (bunun altı tek hece/kelime kabul edilir)
LONG_WORD_SEC = 0.65
# Küme kırpması sonrası bırakılan güvenlik payı
CLUSTER_MARGIN_SEC = 0.05
# Kenar koruması: kelime sonu/başı en fazla bu kadar genişletilebilir
MAX_TAIL_EXTEND_SEC = 0.25
MAX_HEAD_EXTEND_SEC = 0.15
# Komşu kelimeye bırakılacak minimum mesafe
NEIGHBOR_GUARD_SEC = 0.01


def compute_thresholds(analysis) -> Optional[Tuple[float, float]]:
    """(yüksek_eşik, düşük_eşik) döner. Yüksek eşik konuşma çekirdeği, düşük eşik kuyruk içindir."""
    rms = getattr(analysis, "rms_envelope", None) if analysis is not None else None
    if rms is None or len(rms) == 0:
        return None

    hop_sec = getattr(analysis, "rms_hop_ms", 10.0) / 1000.0
    speech_vals = []
    for reg in getattr(analysis, "speech_regions", None) or []:
        s_i = int(reg.start / hop_sec)
        e_i = int(reg.end / hop_sec)
        if e_i > s_i:
            speech_vals.append(rms[s_i:e_i])

    med_speech = float(np.median(np.concatenate(speech_vals))) if speech_vals else 0.04
    floor_rms = float(np.percentile(rms, 10))
    high = max(0.012, floor_rms + 0.12 * (med_speech - floor_rms))
    low = max(0.004, floor_rms + 0.04 * (med_speech - floor_rms))
    return high, min(low, high * 0.6)


def _speech_clusters(w_rms: np.ndarray, thresh: float, hop_sec: float) -> List[Tuple[int, int]]:
    """Eşik üstü kesintisiz bölgeleri (60ms boşluk toleransı) indeks çiftleri olarak döner."""
    clusters: List[Tuple[int, int]] = []
    in_c = False
    c_s = 0
    dip = 0
    for idx, r in enumerate(w_rms):
        if r >= thresh:
            if not in_c:
                in_c = True
                c_s = idx
            dip = 0
        elif in_c:
            dip += 1
            if dip > 6:
                clusters.append((c_s, idx - dip))
                in_c = False
                dip = 0
    if in_c:
        clusters.append((c_s, len(w_rms) - 1))

    valid = [(cs, ce) for cs, ce in clusters if (ce - cs) * hop_sec >= 0.10]
    if not valid and clusters:
        valid = [max(clusters, key=lambda c: c[1] - c[0])]

    # Kelime içi sessiz ünsüz kapanmalarını (< 160ms) birleştir
    merged: List[Tuple[int, int]] = []
    for cs, ce in valid:
        if merged and (cs - merged[-1][1]) * hop_sec < 0.16:
            merged[-1] = (merged[-1][0], ce)
        else:
            merged.append((cs, ce))
    return merged


def refine_word_boundaries(
    spans: List[Tuple[float, float]],
    analysis,
    duration: Optional[float] = None,
    texts: Optional[List[str]] = None
) -> List[Tuple[float, float]]:
    """
    spans: kronolojik sıralı (start, end) listesi.
    texts: (opsiyonel) kelime metinleri; küme seçiminde beklenen süre sağlaması için.
    Aynı uzunlukta, iyileştirilmiş (start, end) listesi döner.
    """
    thresholds = compute_thresholds(analysis)
    if thresholds is None or not spans:
        return list(spans)

    expected_lens: Optional[List[float]] = None
    if texts is not None and len(texts) == len(spans):
        expected_lens = [max(0.25, 0.06 * sum(ch.isalpha() for ch in (t or ""))) for t in texts]

    high, low = thresholds
    rms = analysis.rms_envelope
    hop_sec = getattr(analysis, "rms_hop_ms", 10.0) / 1000.0
    total = float(duration if duration is not None else getattr(analysis, "duration", spans[-1][1]))
    n = len(spans)

    # --- Aşama 1: Uzun kelimelerde küme kırpması ---
    stage1: List[Tuple[float, float]] = []
    for i, (ws, we) in enumerate(spans):
        if (we - ws) <= LONG_WORD_SEC:
            stage1.append((ws, we))
            continue

        s_idx = max(0, int(ws / hop_sec))
        e_idx = min(len(rms), int(we / hop_sec))
        w_rms = rms[s_idx:e_idx]
        merged = _speech_clusters(w_rms, high, hop_sec) if len(w_rms) else []
        if not merged:
            stage1.append((ws, we))
            continue

        if len(merged) == 1:
            best_s, best_e = merged[0]
        else:
            prev_end = spans[i - 1][1] if i > 0 else 0.0
            next_start = spans[i + 1][0] if i < n - 1 else total
            dist_prev = abs(ws - prev_end)
            dist_next = abs(next_start - we)
            c0_dur = (merged[0][1] - merged[0][0]) * hop_sec
            cl_dur = (merged[-1][1] - merged[-1][0]) * hop_sec

            if dist_prev <= 0.15 and c0_dur >= 0.15:
                best_s, best_e = merged[0]
            elif dist_next <= 0.15 and cl_dur >= 0.15:
                best_s, best_e = merged[-1]
            elif c0_dur < 0.14 and (merged[1][0] - merged[0][1]) * hop_sec >= 0.30:
                best_s, best_e = merged[-1]
            elif cl_dur < 0.22 and (merged[-1][0] - merged[-2][1]) * hop_sec >= 0.35:
                best_s, best_e = merged[0]
            else:
                best_s, best_e = max(merged, key=lambda c: c[1] - c[0])

            # Uzunluk sağlaması: seçilen küme kelime için çok kısaysa (örn. önceki kelimenin
            # kuyruğu), kelime uzunluğuna uyan kümeyi tercih et. ~60ms/harf kaba Türkçe hızı.
            if expected_lens is not None:
                expected = expected_lens[i]
                picked_dur = (best_e - best_s) * hop_sec
                if picked_dur < 0.4 * expected:
                    fitting = [c for c in merged if (c[1] - c[0]) * hop_sec >= 0.6 * expected]
                    if fitting:
                        best_s, best_e = min(fitting, key=lambda c: abs((c[1] - c[0]) * hop_sec - expected))

        new_ws = max(ws, ws + best_s * hop_sec - CLUSTER_MARGIN_SEC)
        new_we = min(we, ws + (best_e + 1) * hop_sec + CLUSTER_MARGIN_SEC)
        stage1.append((new_ws, new_we) if new_we > new_ws else (ws, we))

    # --- Aşama 2: Kenar koruması (histerezis ile kuyruk/atak genişletme) ---
    def above_low(idx: int) -> bool:
        return 0 <= idx < len(rms) and rms[idx] >= low

    result: List[Tuple[float, float]] = []
    for i, (ws, we) in enumerate(stage1):
        next_start = stage1[i + 1][0] if i < n - 1 else total
        prev_end = result[-1][1] if result else 0.0

        # Kuyruk: kelime sonundan ileri doğru düşük eşik üstü kesintisiz enerji
        tail_limit = min(we + MAX_TAIL_EXTEND_SEC, next_start - NEIGHBOR_GUARD_SEC, total)
        idx = int(we / hop_sec)
        max_idx = int(tail_limit / hop_sec)
        dips = 0
        new_we = we
        while idx < max_idx:
            if above_low(idx):
                dips = 0
                new_we = (idx + 1) * hop_sec
            else:
                dips += 1
                if dips > 2:  # 30ms sessizlik kuyruğu bitirir
                    break
            idx += 1

        # Atak: kelime başından geri doğru
        head_limit = max(ws - MAX_HEAD_EXTEND_SEC, prev_end + NEIGHBOR_GUARD_SEC, 0.0)
        idx = int(ws / hop_sec) - 1
        min_idx = int(np.ceil(head_limit / hop_sec))
        dips = 0
        new_ws = ws
        while idx >= min_idx:
            if above_low(idx):
                dips = 0
                new_ws = idx * hop_sec
            else:
                dips += 1
                if dips > 2:
                    break
            idx -= 1

        new_ws = min(new_ws, ws)
        new_we = max(new_we, we)
        result.append((round(new_ws, 3), round(new_we, 3)))

    return result
