"""
OtoEdit Kayıp Kelime ve Tekrar Baskılama Kurtarıcısı (Gap Filler V2 - Interleaved Batch Mode)
- Silero VAD konuşma bölgeleri referans alınarak transkriptte atlanmış konuşmalar tespit edilir.
- Yalnızca tamamen boş (EMPTY) konuşma adalarını değil, aynı zamanda Whisper'ın uzun parçalarda
  "Tekrar Baskılama" (Repetition Suppression / Self-Deduplication) hatası yüzünden cümle başlarını
  veya sonlarını yuttuğu KISMİ BOŞLUKLARI (Intra-Region Partial Sub-Gaps >= 0.65s) ve
  birden fazla kelimeyi tek kelime damgasına sıkıştırdığı UZATILMIŞ KELİMELERİ (>= 1.45s) tespit eder.
- Çok sayıda boşluk bulunduğunda (örn. 70 dk videoda 120+ ada), API RPM kotasına (20 istek/dk) takılmamak
  ve ardışık tekrarların aynı ses paketinde tekrar baskılanmasını önlemek için adaları
  "Serpiştirilmiş Paketler" (Interleaved Batches: i % B) halinde 1.2sn sessizlik ayraçlarıyla birleştirerek
  yalnızca 6-8 API çağrısında saniyeler içinde kurtarır.
"""

import os
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
import numpy as np
from config import Config
from pipeline.audio_analysis import AudioAnalysis
from pipeline.stt.base import Word
from pipeline.stt.chunker import AudioChunk
from pipeline.stt.engine_chain import STTEngineChain
from utils.logger import get_logger

logger = get_logger("STT.GapFiller")


class GapFiller:
    """Atlanan konuşma bölgelerini ve Whisper tekrar baskılaması kayıplarını tespit edip kurtaran motor."""

    SAMPLE_RATE = 16000
    SILENCE_SEP_SEC = 1.25
    VERBATIM_DISFLUENCY_PROMPT = (
        "Konuşmacının tekrar ettiği kelimeleri, yarım bıraktığı heceleri ve "
        "dil sürçmelerini silmeden duyduğun gibi kelimesi kelimesine yaz."
    )

    def __init__(
        self,
        min_gap_sec: float = 0.42,
        intra_subgap_sec: float = 0.60,
        micro_island_subgap_sec: float = 0.28,
        stretched_word_sec: float = 1.40,
        max_gaps: int = 160,
    ):
        self.min_gap_sec = min_gap_sec
        self.intra_subgap_sec = intra_subgap_sec
        self.micro_island_subgap_sec = micro_island_subgap_sec
        self.stretched_word_sec = stretched_word_sec
        self.max_gaps = max_gaps

    @staticmethod
    def _is_phonetically_stretched(word_obj: Word, stretched_limit: float) -> bool:
        """
        Kelimenin akustik süresini harf sayısına göre beklenen maksimum normal konuşma süresiyle
        karşılaştırır (örn. 7 harfli 'Nefsani' için beklenen <= 1.19s iken 1.55s ise içinde yutulmuş 'haf' vardır).
        """
        dur = float(word_obj.end) - float(word_obj.start)
        if dur >= stretched_limit:
            return True
        clean = word_obj.word.strip().strip(".,!?;:\"'…")
        char_len = max(1, len(clean))
        expected_max = max(0.72, char_len * 0.115 + 0.36)
        return dur >= expected_max and dur >= 0.95

    def find_untranscribed_gaps_with_priority(
        self,
        analysis: AudioAnalysis,
        words: List[Word],
    ) -> List[Tuple[float, float, int]]:
        """
        VAD konuşma bölgelerini tarayarak (start, end, priority_tier) listesi döner:
        - Tier 3 (En Yüksek): Önünde/arkasında >= 1.2s sessizlik bulunan <= 3 kelimelik tereddüt
          mikro-adaları veya fonetik süresi şişmiş kısa adalar (örn. 591.20s 'nefsani haf' ve 596.36s 'nefsani sefalete').
        - Tier 2 (Yüksek): İçinde hiç kelime bulunmayan (EMPTY) konuşma adaları.
        - Tier 1 (Normal): Uzun konuşma adaları içindeki kısmi alt-boşluklar.
        """
        prioritized: List[Tuple[float, float, int]] = []
        regions = analysis.speech_regions
        num_reg = len(regions)

        for r_idx, region in enumerate(regions):
            if region.duration < self.min_gap_sec:
                continue

            prev_silence = (region.start - regions[r_idx - 1].end) if r_idx > 0 else region.start
            next_silence = (regions[r_idx + 1].start - region.end) if (r_idx + 1) < num_reg else 5.0
            is_hesitation_bounded = (prev_silence >= 1.15 or next_silence >= 1.15)

            reg_words = [
                w for w in words
                if float(w.end) > region.start + 0.04 and float(w.start) < region.end - 0.04
            ]

            if not reg_words:
                tier = 3 if (is_hesitation_bounded and region.duration <= 4.5) else 2
                prioritized.append((round(region.start, 3), round(region.end, 3), tier))
                continue

            is_micro_island = (len(reg_words) <= 3 and region.duration <= 5.5)
            effective_subgap = (
                self.micro_island_subgap_sec
                if (is_micro_island and is_hesitation_bounded)
                else self.intra_subgap_sec
            )

            has_stretched_word = any(
                self._is_phonetically_stretched(w, self.stretched_word_sec)
                for w in reg_words
            )

            spans = sorted(
                (max(region.start, float(w.start) - 0.03), min(region.end, float(w.end) + 0.03))
                for w in reg_words
            )
            cur = region.start
            uncovered_subgaps: List[Tuple[float, float]] = []
            for s, e in spans:
                if s - cur >= effective_subgap:
                    uncovered_subgaps.append((cur, s))
                cur = max(cur, e)
            if region.end - cur >= effective_subgap:
                uncovered_subgaps.append((cur, region.end))

            if has_stretched_word or uncovered_subgaps:
                tier = 3 if (is_micro_island and is_hesitation_bounded) else 1
                if region.duration <= 14.0:
                    prioritized.append((round(region.start, 3), round(region.end, 3), tier))
                else:
                    for sub_s, sub_e in uncovered_subgaps:
                        prioritized.append((
                            round(max(region.start, sub_s - 0.25), 3),
                            round(min(region.end, sub_e + 0.25), 3),
                            tier,
                        ))

        return prioritized

    def find_untranscribed_gaps(
        self,
        analysis: AudioAnalysis,
        words: List[Word],
    ) -> List[Tuple[float, float]]:
        """Geriye dönük uyumluluk için (start, end) çiftleri döner."""
        return [(s, e) for s, e, _ in self.find_untranscribed_gaps_with_priority(analysis, words)]

    def _decode_full_pcm(self, media_path: str) -> Optional[np.ndarray]:
        """Medya dosyasını tek seferde 16kHz mono int16 PCM dizisine çözer."""
        try:
            cmd = [
                "ffmpeg", "-v", "error",
                "-i", media_path,
                "-vn", "-ac", "1",
                "-ar", str(self.SAMPLE_RATE),
                "-f", "s16le", "pipe:1",
            ]
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=True)
            return np.frombuffer(proc.stdout, dtype=np.int16)
        except Exception as ex:
            logger.warning(f"⚠️ Tek seferlik PCM çözme başarısız oldu, doğrudan kesit moduna geçiliyor: {ex}")
            return None

    def fill_gaps(
        self,
        media_path: str,
        analysis: AudioAnalysis,
        words: List[Word],
        chain: STTEngineChain,
        temp_dir: Optional[Path] = None,
        raw_words: Optional[List[Word]] = None,
    ) -> List[Word]:
        """Tespit edilen boş veya kısmi konuşma adalarını serpiştirilmiş paketlerle yeniden transkribe eder."""
        prioritized_gaps = self.find_untranscribed_gaps_with_priority(analysis, words)
        if not prioritized_gaps:
            logger.info("✨ Şüpheli transkript boşluğu bulunamadı, tüm konuşmalar kapsandı.")
            return words

        if len(prioritized_gaps) > self.max_gaps:
            tier3_cnt = sum(1 for _, _, t in prioritized_gaps if t == 3)
            logger.info(
                f"🔍 {len(prioritized_gaps)} adet boş/kısmi konuşma adası tespit edildi "
                f"({tier3_cnt} yüksek öncelikli tereddüt mikro-adası). "
                f"Öncelik sırasına göre en kritik {self.max_gaps} bölge inceleniyor..."
            )
            # Önce priority_tier (3 > 2 > 1), sonra süre büyüklüğü
            selected = sorted(
                prioritized_gaps,
                key=lambda g: (g[2], (g[1] - g[0])),
                reverse=True,
            )[: self.max_gaps]
            gaps = [(s, e) for s, e, _ in sorted(selected, key=lambda g: g[0])]
        else:
            gaps = [(s, e) for s, e, _ in prioritized_gaps]
            logger.info(f"🔍 {len(gaps)} adet boş/kısmi konuşma adası tespit edildi. Kurtarma başlıyor...")

        work_dir = temp_dir or Config.TEMP_DIR
        os.makedirs(work_dir, exist_ok=True)

        if getattr(analysis, "pcm_samples", None) is not None and len(analysis.pcm_samples) > 0:
            pcm = np.clip(analysis.pcm_samples * 32768.0, -32768, 32767).astype(np.int16)
        else:
            pcm = self._decode_full_pcm(media_path)
        results: List[Dict[str, Any]] = []

        if pcm is not None and len(pcm) > 0:
            # Serpiştirilmiş Paketleme (Interleaved Batching):
            # Ardışık tekrar adalarının (örn. 30.5s, 32.4s, 36.2s, 42.8s) aynı ses paketine düşüp
            # Whisper tarafından tekrar baskılanmasını (Repetition Suppression) %100 engellemek için
            # adalar i % num_batches ile farklı paketlere dağıtılır!
            num_batches = min(8, max(1, min(len(gaps), (len(gaps) + 15) // 16)))
            if len(gaps) >= 2 and num_batches < 4:
                num_batches = min(len(gaps), 4)

            batches: List[List[Tuple[int, Tuple[float, float]]]] = [[] for _ in range(num_batches)]
            for idx, g in enumerate(gaps):
                batches[idx % num_batches].append((idx + 1, g))

            silence_samples = np.zeros(int(self.SILENCE_SEP_SEC * self.SAMPLE_RATE), dtype=np.int16)

            def _run_batch(b_idx: int, batch_items: List[Tuple[int, Tuple[float, float]]]) -> List[Dict[str, Any]]:
                if not batch_items:
                    return []
                batch_pcm_parts: List[np.ndarray] = []
                # (batch_start_sec, batch_end_sec, clip_start_sec, clip_end_sec, g_start, g_end, item_idx)
                meta_table: List[Tuple[float, float, float, float, float, float, int]] = []
                cur_samples = 0

                for item_idx, (g_start, g_end) in batch_items:
                    clip_start = max(0.0, g_start - 0.35)
                    clip_end = min(analysis.duration, g_end + 0.35)
                    s_i = max(0, int(clip_start * self.SAMPLE_RATE))
                    e_i = min(len(pcm), int(clip_end * self.SAMPLE_RATE))
                    if e_i <= s_i:
                        continue
                    seg_pcm = pcm[s_i:e_i]
                    b_start_sec = cur_samples / float(self.SAMPLE_RATE)
                    cur_samples += len(seg_pcm)
                    b_end_sec = cur_samples / float(self.SAMPLE_RATE)

                    meta_table.append((b_start_sec, b_end_sec, clip_start, clip_end, g_start, g_end, item_idx))
                    batch_pcm_parts.append(seg_pcm)
                    batch_pcm_parts.append(silence_samples)
                    cur_samples += len(silence_samples)

                if not batch_pcm_parts or not meta_table:
                    return []

                full_batch_pcm = np.concatenate(batch_pcm_parts)
                total_batch_sec = len(full_batch_pcm) / float(self.SAMPLE_RATE)
                batch_mp3 = str(work_dir / f"gap_batch_{b_idx}_{os.getpid()}.mp3")

                try:
                    cmd = [
                        "ffmpeg", "-y", "-v", "error",
                        "-f", "s16le", "-ar", str(self.SAMPLE_RATE), "-ac", "1",
                        "-i", "pipe:0",
                        "-acodec", "libmp3lame", "-b:a", "48k",
                        batch_mp3,
                    ]
                    subprocess.run(
                        cmd,
                        input=full_batch_pcm.tobytes(),
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        check=True,
                    )

                    chunk = AudioChunk(
                        index=900 + b_idx,
                        start_sec=0.0,
                        end_sec=total_batch_sec,
                        audio_path=batch_mp3,
                        has_speech=True,
                        prompt=self.VERBATIM_DISFLUENCY_PROMPT,
                    )
                    batch_words, engine_used = chain.transcribe_chunk(chunk)

                    per_gap_words: Dict[int, List[Word]] = {m[6]: [] for m in meta_table}
                    for bw in batch_words:
                        w_txt = bw.word.strip()
                        if w_txt.lower().replace(".", "") in ("altyazı", "mk", "mısır", "diber"):
                            continue
                        w_mid = (float(bw.start) + float(bw.end)) / 2.0
                        for b_s, b_e, c_s, c_e, g_s, g_e, item_idx in meta_table:
                            if (b_s - 0.25) <= w_mid <= (b_e + 0.25):
                                rel_s = max(0.0, float(bw.start) - b_s)
                                rel_e = max(rel_s + 0.04, min(b_e - b_s, float(bw.end) - b_s))
                                real_s = round(c_s + rel_s, 3)
                                real_e = round(min(c_e, c_s + rel_e), 3)
                                if real_e >= g_s - 0.15 and real_s <= g_e + 0.15:
                                    per_gap_words[item_idx].append(
                                        Word(word=w_txt, start=real_s, end=real_e, confidence=bw.confidence)
                                    )
                                break

                    batch_out: List[Dict[str, Any]] = []
                    for b_s, b_e, c_s, c_e, g_s, g_e, item_idx in meta_table:
                        vw = per_gap_words.get(item_idx, [])
                        if vw:
                            batch_out.append({
                                "idx": item_idx,
                                "g_start": g_s,
                                "g_end": g_e,
                                "valid_words": vw,
                                "engine": engine_used,
                            })
                    return batch_out
                except Exception as ex:
                    logger.warning(f"⚠️ GapFiller paket {b_idx} kurtarma hatası: {ex}")
                    return []
                finally:
                    if os.path.exists(batch_mp3):
                        try:
                            os.remove(batch_mp3)
                        except Exception:
                            pass

            with ThreadPoolExecutor(max_workers=2) as executor:
                futs = [
                    executor.submit(_run_batch, b_idx, b_items)
                    for b_idx, b_items in enumerate(batches, start=1)
                    if b_items
                ]
                for fut in as_completed(futs):
                    results.extend(fut.result())

        if not results:
            return words

        results.sort(key=lambda r: r["g_start"])
        updated_words: List[Word] = list(words)
        total_added = 0

        for res in results:
            g_start = res["g_start"]
            g_end = res["g_end"]
            valid_words: List[Word] = res["valid_words"]
            engine_used = res["engine"]

            # Sınır komşusu kelimelerle (g_start / g_end kenarında) zaman örtüşmesi olan kelimeleri filtrele:
            # Aksi halde 0.25s sınır payı yüzünden aynı kelime ikinci kez eklenip sahte retake kesimine yol açar!
            def _overlaps_existing(cand: Word, pool: List[Word]) -> bool:
                cs, ce = float(cand.start), float(cand.end)
                cdur = max(0.01, ce - cs)
                cnorm = cand.word.strip().lower().strip(".,!?;:\"'")
                for ew in pool:
                    es, ee = float(ew.start), float(ew.end)
                    edur = max(0.01, ee - es)
                    ov = min(ce, ee) - max(cs, es)
                    if ov >= 0.10 or (ov > 0.02 and ov / min(cdur, edur) >= 0.35):
                        return True
                    enorm = ew.word.strip().lower().strip(".,!?;:\"'")
                    if cnorm and cnorm == enorm and abs(cs - es) <= 0.32:
                        return True
                return False

            existing_in_gap = [
                w for w in updated_words
                if float(w.end) > g_start + 0.05 and float(w.start) < g_end - 0.05
            ]

            if not existing_in_gap:
                safe_valid = [vw for vw in valid_words if not _overlaps_existing(vw, updated_words)]
                if safe_valid:
                    updated_words.extend(safe_valid)
                    total_added += len(safe_valid)
                    logger.info(
                        f"🎯 Boş konuşma adası kurtarıldı [{g_start:.2f}s - {g_end:.2f}s] ({engine_used}): "
                        f"'{' '.join(w.word for w in safe_valid)}'"
                    )
            elif len(valid_words) > len(existing_in_gap):
                old_text = " ".join(w.word for w in existing_in_gap)
                existing_ids = {id(w) for w in existing_in_gap}
                remaining_pool = [w for w in updated_words if id(w) not in existing_ids]
                safe_valid = [vw for vw in valid_words if not _overlaps_existing(vw, remaining_pool)]
                if len(safe_valid) >= len(existing_in_gap):
                    new_text = " ".join(w.word for w in safe_valid)
                    updated_words = remaining_pool + safe_valid
                    total_added += len(safe_valid) - len(existing_in_gap)
                    logger.info(
                        f"🔄 Kısmi konuşma adası tamamlandı [{g_start:.2f}s - {g_end:.2f}s] ({engine_used}): "
                        f"'{old_text}' ({len(existing_in_gap)} klm) -> '{new_text}' ({len(safe_valid)} klm)"
                    )
            else:
                non_overlapping = [
                    vw for vw in valid_words
                    if not _overlaps_existing(vw, updated_words)
                ]
                if non_overlapping:
                    updated_words.extend(non_overlapping)
                    total_added += len(non_overlapping)
                    logger.info(
                        f"🎯 Alt-boşluk kelimeleri eklendi [{g_start:.2f}s - {g_end:.2f}s] ({engine_used}): "
                        f"'{' '.join(w.word for w in non_overlapping)}'"
                    )

        updated_words.sort(key=lambda w: (float(w.start), -float(w.end)))

        deduped_words: List[Word] = []
        for w in updated_words:
            if not deduped_words:
                deduped_words.append(w)
                continue
            prev = deduped_words[-1]
            ws, we = float(w.start), float(w.end)
            ps, pe = float(prev.start), float(prev.end)
            ov = min(we, pe) - max(ws, ps)
            w_norm = w.word.strip().lower().strip(".,!?;:\"'")
            p_norm = prev.word.strip().lower().strip(".,!?;:\"'")
            if w_norm and w_norm == p_norm and (abs(ws - ps) <= 0.20 or ov > 0.02):
                continue
            if pe > ws and w_norm != p_norm:
                mid = round(max(ps + 0.04, min(pe, 0.5 * (pe + ws))), 3)
                prev.end = mid
                if we > mid + 0.02:
                    w.start = mid
            deduped_words.append(w)

        logger.info(
            f"✨ GapFiller V2 tamamlandı: Net +{total_added} kayıp tekrar kelimesi kurtarıldı "
            f"(Toplam {len(deduped_words)} kelime)."
        )
        return deduped_words
