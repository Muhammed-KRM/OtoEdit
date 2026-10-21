"""
Aşama 1: Bütüncül Video Analizcisi (HolisticAnalyzer).
Videonun tamamını (00:00 -> son saniye) anlamsal bölümlere (Chapters) ayırır,
tek bir kilitli ThemeProfile seçer ve kayan çoklu-segment penceresi (Sliding 3-Segment Window)
üzerinden:
  1. Kişi / Alim / Filozof Tanıtımlarını (PERSON_INTRODUCTION -> İsim + Wikipedia Portresi)
  2. Sıralama ve Maddelendirmeleri (ENUMERATION_CALLOUT -> "Birincisi..., İkincisi..., Üçüncüsü...")
  3. Kavram Tanımları, Deliller ve Hukuki/Felsefi İlkeleri (DEFINITION_CALLOUT)
  4. Bölüm Başlıkları ve Madde/İstatistik Vurgularını (CHAPTER_TITLE_CARD, STAT_OR_ARTICLE_CALLOUT)
tespit ederek her bölüme orantılı kurgu eylemleri planlar.
"""

import json
import math
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from pipeline.theme_profiles import (
    THEME_PROFILE_REGISTRY,
    ThemeProfile,
    detect_theme_profile_heuristic,
    extract_turkish_semantic_title,
    to_turkish_lower,
    to_turkish_upper,
)
from utils.logger import get_logger

logger = get_logger("HolisticAnalyzer")


# Tanınmış filozof, alim, bilim insanı ve tarihsel şahsiyetlerin
# (anahtar_kelime -> (Ekran Başlığı, Türkçe Wikipedia Başlığı, İngilizce Wikipedia Başlığı)) eşlemesi
KNOWN_PERSONS_WIKI_MAP: List[Tuple[Tuple[str, ...], str, str, str]] = [
    (("imam gazali", "imam-ı gazali", "gazali", "gazzali"), "İMAM GAZALİ", "Gazzâlî", "Al-Ghazali"),
    (("aristoteles", "aristo"), "ARİSTOTELES", "Aristoteles", "Aristotle"),
    (("farabi", "fârâbî"), "FÂRÂBÎ", "Fârâbî", "Al-Farabi"),
    (("ibn sina", "ibni sina", "ibn-i sina"), "İBN SÎNÂ", "İbn Sînâ", "Avicenna"),
    (("ibn rüşd", "ibni rüşd", "ibn-i rüşd"), "İBN RÜŞD", "İbn Rüşd", "Averroes"),
    (("ibn haldun", "ibni haldun"), "İBN HALDUN", "İbn Haldun", "Ibn Khaldun"),
    (("sokrates",), "SOKRATES", "Sokrates", "Socrates"),
    (("platon", "eflatun"), "PLATON (EFLATUN)", "Platon", "Plato"),
    (("immanuel kant",), "IMMANUEL KANT", "Immanuel Kant", "Immanuel Kant"),
    (("descartes", "dekart"), "RENÉ DESCARTES", "René Descartes", "René Descartes"),
    (("hans küng", "hans künk", "haskünkü", "künk"), "PROF. HANS KÜNG", "Hans Küng", "Hans Küng"),
    (("said nursi", "bediüzzaman"), "BEDİÜZZAMAN SAİD NURSİ", "Said Nursi", "Said Nursi"),
    (("muaz bin cebel", "muaz bilcebel"), "MUAZ BİN CEBEL", "Muâz bin Cebel", "Muadh ibn Jabal"),
    (("imam şafii", "imam-ı şafii"), "İMAM ŞÂFİÎ", "Şâfiî", "Al-Shafi'i"),
    (("ebu hanife", "imam-ı azam"), "İMAM-I ÂZAM EBÛ HANÎFE", "Ebû Hanîfe", "Abu Hanifa"),
    (("imam malik", "malik bin enes"), "İMAM MÂLİK", "Mâlik bin Enes", "Malik ibn Anas"),
    (("ahmed bin hanbel",), "AHMED BİN HANBEL", "Ahmed bin Hanbel", "Ahmad ibn Hanbal"),
    (("fahreddin razi", "fahreddin-i razi"), "FAHREDDİN ER-RÂZÎ", "Fahreddin er-Râzî", "Fakhr al-Din al-Razi"),
    (("ibn arabi", "ibnü'l-arabi", "muhyiddin"), "İBNÜ'L-ARABÎ", "İbnü'l-Arabî", "Ibn Arabi"),
    (("mevlana", "celaleddin rumi"), "MEVLÂNÂ CELÂLEDDÎN-İ RÛMÎ", "Mevlânâ Celâleddîn-i Rûmî", "Rumi"),
    (("albert einstein", "einstein"), "ALBERT EINSTEIN", "Albert Einstein", "Albert Einstein"),
    (("isaac newton", "newton"), "ISAAC NEWTON", "Isaac Newton", "Isaac Newton"),
]

# Felsefi, hukuki, kelami ve bilimsel özel kavram/tanım kalıpları
# (anahtar_kelimeler, Ekran Başlığı, Somut Ansiklopedik Görsel Başlığı (TR|EN) veya Boş)
KNOWN_DEFINITIONS_MAP: List[Tuple[Tuple[str, ...], str, str]] = [
    (("hakim, fehim", "mecellenin bir hakim", "mekin ve mitin"), "MECELLE: HAKİMİN VASIFLARI", "Mecelle|Mecelle"),
    (("bürhan-ı inni", "burhan-ı inni", "eserden müessire", "eserlerden müessire"), "BÜRHAN-I İNNİ (ESERDEN MÜESSİRE)", ""),
    (("bürhan-ı limmi", "burhan-ı limmi", "müessirden esere", "sebepten esere inen"), "BÜRHAN-I LİMMİ (SEBEPTEN SONUCA)", ""),
    (("kainat kitabı", "tekvini bir nizam alanı"), "KAİNAT KİTABI (TEKVİNİ NİZAM)", "Evren|Universe"),
    (("hudus delili", "hudûs delili"), "HUDUS DELİLİ (YARATILIŞ KANITI)", ""),
    (("imkan delili", "imkân delili"), "İMKÂN DELİLİ (ZORUNLU VARLIK)", ""),
    (("inayet ve gaye delili", "inayet delili", "gaye ve nizam"), "İNAYET VE GAYE DELİLİ", ""),
    (("temanü delili", "temânü delili", "lev kane fihima", "nizam fesada uğrardı"), "TEMÂNÜ DELİLİ (KOZMİK NİZAM)", ""),
    (("normlar hiyerarşisi", "normlar yararçisi"), "NORMLAR HİYERARŞİSİ", "Normlar hiyerarşisi|Hierarchy"),
    (("piramidin en tepesinde", "türkiye cumhuriyeti anayasası"), "ANAYASA VE EVRENSEL HUKUK", ""),
    (("kaziye-i muhkeme", "kaziye-i muhakeme"), "KAZİYE-İ MUHKEME (KESİN HÜKÜM)", ""),
    (("mukayeseli hukuk", "farklı hukuk ekollerinden iktibas"), "MUKAYESELİ HUKUK VE İKTİBAS", ""),
    (("kanunun bir lafzı", "ruhu, felsefesi ve vicdani adalet"), "KANUNUN LAFZI VE RUHU", "Adalet|Lady Justice"),
    (("edille-i şer'iyye", "edille-i şeriyye", "edilley-i şehriye", "edille-i erbaa"), "EDİLLE-İ ŞER'İYYE (DÖRT DELİL)", ""),
    (("içtihat ile içtihat nakz", "içtihatla içtihat nakz"), "İÇTİHAT İLE İÇTİHAT NAKZOLUNMAZ", ""),
    (("türk medeni kanunu'nun birinci", "medeni kanunu'nun madde bir"), "TÜRK MEDENİ KANUNU MADDE 1", ""),
    (("adalet-i mahza",), "ADALET-İ MAHZA (MUTLAK ADALET)", ""),
    (("üç büyük şeriat", "üç devasa kanunlar manzumesi"), "ÜÇ BÜYÜK ŞERİAT (İLAHİ KANUNLAR)", ""),
    (("yerçekimi kanunu", "suyun kaldırma kuvveti"), "FİZİK VE TABİAT KANUNLARI", "Kütleçekim|Gravity"),
    (("küre-i arz", "24 bin senede kat edebileceği"), "DÜNYA'NIN YÖRÜNGE NİZAMI", "Dünya|Earth"),
    (("pozitif ilimler islam'ın evlatlarıdır", "fenler yeni bir kanun icat etmez"), "POZİTİF BİLİMLER VE TEKVİNİ KANUN", ""),
    (("nübüvvete lüzum yoktur", "peygambere ne ihtiyaç vardır"), "AKIL VE PEYGAMBERLİK (NÜBÜVVET)", ""),
    (("kanun icra maddelerine", "kağıt üzerinde kalmaktan başka"), "KANUN VE İCRA MEKANİZMASI", ""),
    (("kainat devasa bir mektep", "semavi suhflar ve kur'an ilahi müfredat"), "KAİNAT MEKTEBİ VE İLAHİ MÜFREDAT", "Kur'an|Quran"),
    (("zülcenahen", "zülcenaheyn", "iki kanatlı bir temsilci"), "ZÜLCENAHEYN (İKİ KANATLI ELÇİ)", ""),
    (("necisin nereden geliyorsun", "3 muazzam tılsım"), "VARLIĞIN 3 BÜYÜK SORUSU", ""),
    (("ibrahim'i dinler", "hz. ibrahim'i, hz. musa"), "İBRAHİMİ DİNLER VE PEYGAMBERLER", ""),
    (("ismet sıfatı", "tek bir yalana tenezzül etmemesi"), "İSMET SIFATI (DOĞRULUK VE GÜVEN)", ""),
    (("mekke'nin fethi", "bugün size başa kakma ve kınama yoktur"), "MEKKE'NİN FETHİ VE AF AHLAKI", "Kâbe|Kaaba"),
    (("ratio legis", "ratyoleges", "kanunun gayesi", "hikmet-i teşri"), "RATIO LEGIS (KANUNUN GAYESİ)", ""),
    (("kanunu bilip kanun koyucuğu tanımamak", "mimariyi alkışlayıp mimarı inkar"), "ESERDEN MÜESSİRE: KANUN VE KANUN KOYUCU", ""),
    (("ihtira", "iştira ve temanü", "nizam-nazım ilişkisini"), "İHTİRA DELİLİ VE NİZAM-NAZIM İLİŞKİSİ", ""),
    (("makasıdu'ş-şeria", "makasıdu şeria", "zaruriyat-ı diniyye", "maslahat"), "MAKÂSIDU'Ş-ŞERİA (TEMEL GAYELER)", ""),
    (("fitne katilden beterdir", "fitne çıkarmak"), "İLKE: FİTNE KATİLDEN BETERDİR", ""),
    (("cihat kelimesi", "ceht kökünden"), "CİHAT (CEHD: ÜSTÜN GAYRET)", ""),
    (("laiklik", "din ve devlet işleri"), "LAİKLİK VE DİN-DEVLET İLİŞKİSİ", ""),
    (("emaneti ehline", "ehliyet ve liyakat"), "EMANET VE LİYAKAT İLKESİ", ""),
    (("şura", "meşveret", "istişare"), "ŞÛRÂ VE İSTİŞARE İLKESİ", ""),
]


@dataclass
class PlannedEditorialEvent:
    event_id: str
    chapter_id: int
    action_type: str  # "CHAPTER_TITLE_CARD" | "PERSON_INTRODUCTION" | "ENUMERATION_CALLOUT" | "DEFINITION_CALLOUT" | "CONCEPT_IMAGE_CARD" | "KEY_TERM_CALLOUT" | "STAT_OR_ARTICLE_CALLOUT"
    start_sec: float
    end_sec: float
    text_primary: str
    text_secondary: str = ""
    primary_web_query_tr: str = ""
    secondary_stock_query_en: str = ""
    fallback_minimal_query_en: str = ""
    prefer_video_broll: bool = False
    person_wiki_tr: str = ""
    person_wiki_en: str = ""
    semantic_priority: bool = False


@dataclass
class ChapterPlan:
    chapter_id: int
    start_sec: float
    end_sec: float
    title_tr: str
    key_terms: List[str] = field(default_factory=list)
    events: List[PlannedEditorialEvent] = field(default_factory=list)


class HolisticAnalyzer:
    """
    Uzun veya kısa videoları bütünsel olarak analiz edip Bölüm Orantılı
    (Chapter-Proportional) ve Semantik Tetikleyici Duyarlı kurgu eylem planı çıkaran yönetmen katmanı.
    """

    def __init__(self, gemini_client: Any = None, enable_llm_planning: bool = False):
        self.gemini = gemini_client
        self.enable_llm_planning = enable_llm_planning

    def analyze_video(
        self,
        segments: List[Dict[str, Any]],
        video_duration: float,
        cuts: Optional[List[Any]] = None,
    ) -> Tuple[ThemeProfile, str, List[ChapterPlan]]:
        """
        Döndürür: (locked_theme_profile, subject_summary, chapter_plans)
        """
        normalized_cuts = self._normalize_cuts(cuts or [])
        active_segments = self._filter_active_segments(segments, normalized_cuts)
        full_text = " ".join(str(s.get("text", "")).strip() for s in active_segments)

        # 1. Kilitli ThemeProfile tespiti
        theme_profile = detect_theme_profile_heuristic(full_text)

        # 2. Videoyu kronolojik bölümlere (Chapters) ayır (00:00 -> video_duration)
        safe_duration = max(5.0, float(video_duration or 30.0))
        target_chapter_len = 135.0 if safe_duration >= 300.0 else max(25.0, safe_duration / 3.0)
        num_chapters = max(1, min(16, int(round(safe_duration / target_chapter_len))))
        chapter_boundaries = self._find_natural_chapter_boundaries(
            active_segments, safe_duration, num_chapters
        )

        # 3. Önce tüm videodaki yüksek öncelikli semantik tetikleyicileri
        # (Kişi Tanıtımları, Birincisi/İkincisi Sıralamalar, Tanımlar/Deliller) kayan pencere ile tespit et
        global_semantic_triggers = self._detect_global_semantic_triggers(
            active_segments, safe_duration
        )

        # 4. Her bölüm için semantik tetikleyicileri ve bölüm başlıklarını birleştirerek plan üret
        chapter_plans: List[ChapterPlan] = []
        used_titles_global: Set[str] = set()

        for ch_idx in range(len(chapter_boundaries) - 1):
            ch_start = chapter_boundaries[ch_idx]
            ch_end = chapter_boundaries[ch_idx + 1]
            ch_segs = [
                s
                for s in active_segments
                if float(s.get("start", 0)) >= ch_start - 0.5
                and float(s.get("end", s.get("start", 0))) <= ch_end + 1.5
            ]
            if not ch_segs and active_segments:
                nearest = min(
                    active_segments,
                    key=lambda s: abs(float(s.get("start", 0)) - (ch_start + ch_end) / 2.0),
                )
                ch_segs = [nearest]
            if not ch_segs:
                continue

            ch_triggers = [
                t for t in global_semantic_triggers
                if ch_start - 0.5 <= t.start_sec < ch_end + 0.5
            ]

            ch_plan = self._plan_single_chapter(
                chapter_id=ch_idx + 1,
                ch_start=ch_start,
                ch_end=ch_end,
                ch_segments=ch_segs,
                theme_profile=theme_profile,
                chapter_triggers=ch_triggers,
                used_titles_global=used_titles_global,
            )
            chapter_plans.append(ch_plan)

        subject_summary = (
            f"{theme_profile.display_name} ({len(chapter_plans)} Bölüm, {safe_duration:.1f}s)"
        )
        logger.info(
            f"[HolisticAnalyzer] Tamamlandı: Tema='{theme_profile.id}', "
            f"Bölüm Sayısı={len(chapter_plans)}, "
            f"Toplam Olay={sum(len(c.events) for c in chapter_plans)}"
        )
        return theme_profile, subject_summary, chapter_plans

    def _detect_global_semantic_triggers(
        self,
        active_segments: List[Dict[str, Any]],
        video_duration: float,
    ) -> List[PlannedEditorialEvent]:
        """
        Whisper segmentleri cümleleri 2.5 - 3.5 saniyelik parçalara böldüğü için
        3'lü kayan pencere (seg[i] + seg[i+1] + seg[i+2]) kullanarak:
          - PERSON_INTRODUCTION (Kişi / Alim / Filozof tanıtımı + Wikipedia portresi)
          - ENUMERATION_CALLOUT ("Birincisi..., İkincisi..., Üçüncüsü..., Birinci kaynak...")
          - DEFINITION_CALLOUT (Felsefi deliller, hukuki/bilimsel tanımlar ve ilkeler)
        olaylarını tam ve kesintisiz olarak yakalar.
        """
        triggers: List[PlannedEditorialEvent] = []
        if not active_segments:
            return triggers

        seen_persons: Dict[str, float] = {}
        seen_definitions: Dict[str, float] = {}
        seen_enumerations: Dict[str, float] = {}
        n_segs = len(active_segments)

        for i in range(n_segs):
            seg_cur = active_segments[i]
            s_start = float(seg_cur.get("start", 0.0))
            s_end = float(seg_cur.get("end", s_start + 3.2))
            text_cur = str(seg_cur.get("text", "")).strip()
            text_next = str(active_segments[i + 1].get("text", "")).strip() if i + 1 < n_segs else ""
            text_next2 = str(active_segments[i + 2].get("text", "")).strip() if i + 2 < n_segs else ""

            window_2 = f"{text_cur} {text_next}".strip()
            window_3 = f"{text_cur} {text_next} {text_next2}".strip()
            lower_cur = to_turkish_lower(text_cur)
            lower_win2 = to_turkish_lower(window_2)
            lower_win3 = to_turkish_lower(window_3)

            # ------------------------------------------------------------------
            # 1. KİŞİ / ALİM / FİLOZOF TANITIMI (PERSON_INTRODUCTION)
            # ------------------------------------------------------------------
            matched_person = False
            for kw_tuple, display_name, wiki_tr, wiki_en in KNOWN_PERSONS_WIKI_MAP:
                # Kişi adı mevcut segmentte başlıyor veya (Prof. + Hans Küng gibi) cur->next sınırında bölünmüşse
                in_cur = any(k in lower_cur for k in kw_tuple)
                in_boundary = (
                    not in_cur
                    and any(k in lower_win2 for k in kw_tuple)
                    and any(
                        lower_cur.endswith(prefix)
                        for prefix in ("prof.", "prof", "dr.", "imam", "imam-ı", "hazreti", "hz.", "filozof")
                    )
                )
                if in_cur or in_boundary:
                    last_seen = seen_persons.get(display_name, -999.0)
                    if s_start - last_seen >= 240.0:
                        seen_persons[display_name] = s_start
                        ev_start = round(s_start, 2)
                        ev_end = round(min(video_duration - 0.2, ev_start + 4.5), 2)
                        triggers.append(
                            PlannedEditorialEvent(
                                event_id=f"trig_person_{len(triggers) + 1:02d}",
                                chapter_id=0,
                                action_type="PERSON_INTRODUCTION",
                                start_sec=ev_start,
                                end_sec=ev_end,
                                text_primary=display_name,
                                text_secondary="Kişi / Düşünür",
                                primary_web_query_tr=wiki_tr,
                                secondary_stock_query_en=wiki_en,
                                fallback_minimal_query_en=wiki_en,
                                person_wiki_tr=wiki_tr,
                                person_wiki_en=wiki_en,
                                semantic_priority=True,
                            )
                        )
                        matched_person = True
                        break

            # Dinamik Unvanlı Kişi Yakalayıcı (Örn. "Prof. Dr. Ahmet Arslan", "İmam Maturidi")
            if not matched_person:
                dyn_match = re.search(
                    r"\b((?:Prof\.?\s*(?:Dr\.?\s*)?|Doç\.?\s*Dr\.?\s*|İmam(?:-ı)?\s+)[A-ZÇĞİÖŞÜÂÎÛ][a-zçğıöşüâîû]+(?:\s+[A-ZÇĞİÖŞÜÂÎÛ][a-zçğıöşüâîû]+){0,2})",
                    window_2,
                )
                if dyn_match and dyn_match.start() < len(text_cur) + 6:
                    raw_person = re.sub(r"['’].*$", "", dyn_match.group(1).strip())
                    disp_person = to_turkish_upper(raw_person)
                    if len(disp_person) >= 7 and s_start - seen_persons.get(disp_person, -999.0) >= 240.0:
                        seen_persons[disp_person] = s_start
                        clean_wiki = re.sub(r"^(Prof\.?\s*(?:Dr\.?\s*)?|Doç\.?\s*Dr\.?\s*)", "", raw_person, flags=re.I).strip()
                        ev_start = round(s_start, 2)
                        triggers.append(
                            PlannedEditorialEvent(
                                event_id=f"trig_person_{len(triggers) + 1:02d}",
                                chapter_id=0,
                                action_type="PERSON_INTRODUCTION",
                                start_sec=ev_start,
                                end_sec=round(min(video_duration - 0.2, ev_start + 4.5), 2),
                                text_primary=disp_person,
                                text_secondary="Kişi / Düşünür",
                                primary_web_query_tr=clean_wiki,
                                secondary_stock_query_en=clean_wiki,
                                fallback_minimal_query_en=clean_wiki,
                                person_wiki_tr=clean_wiki,
                                person_wiki_en=clean_wiki,
                                semantic_priority=True,
                            )
                        )

            # ------------------------------------------------------------------
            # 2. SIRALAMA VE MADDELENDİRME (ENUMERATION_CALLOUT)
            # ("Birincisi..., İkincisi..., Üçüncüsü..., Dördüncüsü..., Birinci kaynak...")
            # ------------------------------------------------------------------
            enum_results = self._extract_enumerations_from_segment(
                text_cur=text_cur,
                window_3=window_3,
                seg_start=s_start,
                seg_end=s_end,
            )
            for enum_ts, enum_title in enum_results:
                if enum_title and enum_ts - seen_enumerations.get(enum_title, -999.0) >= 60.0:
                    seen_enumerations[enum_title] = enum_ts
                    triggers.append(
                        PlannedEditorialEvent(
                            event_id=f"trig_enum_{len(triggers) + 1:02d}",
                            chapter_id=0,
                            action_type="ENUMERATION_CALLOUT",
                            start_sec=round(enum_ts, 2),
                            end_sec=round(min(video_duration - 0.2, enum_ts + 3.4), 2),
                            text_primary=enum_title,
                            text_secondary="Sıralama Vurgusu",
                            semantic_priority=True,
                        )
                    )

            # ------------------------------------------------------------------
            # 3. KAVRAM TANIMI, DELİL VE İLKE VURGULARI (DEFINITION_CALLOUT)
            # (Eğer aynı segmentte zaten bir Kişi Tanıtımı veya 1./2./3. Sıralama yakalandıysa çakışmayı önle!)
            # ------------------------------------------------------------------
            if matched_person or enum_results:
                continue

            for kw_tuple, def_title, stock_en in KNOWN_DEFINITIONS_MAP:
                if any(k in lower_cur for k in kw_tuple) or (
                    any(k in lower_win2 for k in kw_tuple)
                    and not any(k in to_turkish_lower(text_next) for k in kw_tuple)
                ):
                    last_def_ts = seen_definitions.get(def_title, -999.0)
                    if s_start - last_def_ts >= 180.0:
                        seen_definitions[def_title] = s_start
                        ev_start = round(s_start, 2)
                        w_tr, w_en = "", ""
                        if "|" in stock_en:
                            w_tr, w_en = stock_en.split("|", 1)
                        elif stock_en:
                            w_en = stock_en
                        triggers.append(
                            PlannedEditorialEvent(
                                event_id=f"trig_def_{len(triggers) + 1:02d}",
                                chapter_id=0,
                                action_type="CONCEPT_IMAGE_CARD" if (w_tr or w_en) else "DEFINITION_CALLOUT",
                                start_sec=ev_start,
                                end_sec=round(min(video_duration - 0.2, ev_start + 4.0), 2),
                                text_primary=def_title,
                                text_secondary="Kavram / Tanım",
                                primary_web_query_tr=w_tr,
                                secondary_stock_query_en=w_en,
                                fallback_minimal_query_en=w_en,
                                semantic_priority=True,
                            )
                        )
                        break
            else:
                # Genel Türkçe Tanım Kalıbı ("... delili", "... ilkesi", "... teorisi", "... demektir")
                gen_def = self._extract_generic_definition_from_window(text_cur, window_2)
                if gen_def and s_start - seen_definitions.get(gen_def, -999.0) >= 120.0:
                    seen_definitions[gen_def] = s_start
                    ev_start = round(s_start, 2)
                    triggers.append(
                        PlannedEditorialEvent(
                            event_id=f"trig_def_{len(triggers) + 1:02d}",
                            chapter_id=0,
                            action_type="DEFINITION_CALLOUT",
                            start_sec=ev_start,
                            end_sec=round(min(video_duration - 0.2, ev_start + 3.8), 2),
                            text_primary=gen_def,
                            text_secondary="Tanım",
                            semantic_priority=True,
                        )
                    )

        # Zaman sırasına göre diz ve aynı saniyeye düşen mükerrer tetikleyicileri birleştir
        triggers.sort(key=lambda e: (e.start_sec, 0 if e.action_type == "PERSON_INTRODUCTION" else 1))
        deduped: List[PlannedEditorialEvent] = []
        for trig in triggers:
            if deduped and abs(trig.start_sec - deduped[-1].start_sec) < 16.0:
                if trig.text_primary in deduped[-1].text_primary or deduped[-1].text_primary in trig.text_primary:
                    continue
            if deduped and abs(trig.start_sec - deduped[-1].start_sec) < 2.2:
                # Eğer biri PERSON_INTRODUCTION ise onu koru, ya da ikincisini +3.2sn ötele
                if trig.action_type == "ENUMERATION_CALLOUT" and deduped[-1].action_type == "ENUMERATION_CALLOUT":
                    trig.start_sec = round(deduped[-1].start_sec + 3.0, 2)
                    trig.end_sec = round(trig.start_sec + 3.2, 2)
                    deduped.append(trig)
                continue
            deduped.append(trig)

        return deduped

    def _extract_enumerations_from_segment(
        self,
        text_cur: str,
        window_3: str,
        seg_start: float,
        seg_end: float,
    ) -> List[Tuple[float, str]]:
        """
        Mevcut segmentte başlayan "Birincisi..., İkincisi..., Üçüncüsü..., Dördüncüsü...,
        Birinci kaynak..., İkinci kaynak..." ifadelerini 3 segmentlik pencereden tam olarak çıkarır.
        """
        results: List[Tuple[float, str]] = []
        lower_cur = to_turkish_lower(text_cur)
        lower_win = to_turkish_lower(window_3)

        # Özel yüksek doğruluklu kalıplar (İslam Hukuku Kaynakları & Şeriat Türleri vb.)
        special_enum_patterns: List[Tuple[str, str, str]] = [
            ("birinci ve mutlak kaynak", "birinci ve mutlak kaynak", "1. KAYNAK: KUR'AN-I KERİM"),
            ("ikinci kaynak", "sünnet", "2. KAYNAK: SÜNNET-İ SENİYYE"),
            ("üçüncü kaynak", "icma", "3. KAYNAK: İCMA"),
            ("dördüncü kaynak", "kıyas", "4. KAYNAK: KIYAS"),
            ("birincisi tenzili", "tenzili", "1. TENZİLİ (TEŞRİ) ŞERİAT"),
            ("ikincisi ise tekvini", "tekvini", "2. TEKVİNİ ŞERİAT (KAİNAT KİTABI)"),
            ("ikincisi tekvini", "tekvini", "2. TEKVİNİ ŞERİAT (TABİAT KANUNLARI)"),
            ("üçüncüsü ise mahiyet", "akli şeriat", "3. AKLİ ŞERİAT (MANTIK İLKELERİ)"),
        ]
        for cur_trigger, win_confirm, formatted_title in special_enum_patterns:
            if cur_trigger in lower_cur and win_confirm in lower_win:
                # Eğer cümlenin ikinci yarısında geçiyorsa zaman damgasını hafifçe ileri kaydır
                pos_ratio = lower_cur.find(cur_trigger) / max(1.0, float(len(lower_cur)))
                ts = seg_start + pos_ratio * max(0.5, (seg_end - seg_start) * 0.6)
                results.append((round(ts, 2), formatted_title))

        if results:
            return results

        # Genel Türkçe Sıralama Kalıbı:
        # "Birincisi X", "İkincisi Y", "Üçüncüsü Z", "Dördüncüsü W", "Birinci adım X", "İkinci şart Y"
        ordinal_map = {
            "birincisi": "1.",
            "ikincisi": "2.",
            "üçüncüsü": "3.",
            "dördüncüsü": "4.",
            "beşincisi": "5.",
            "birinci": "1.",
            "ikinci": "2.",
            "üçüncü": "3.",
            "dördüncü": "4.",
            "beşinci": "5.",
        }
        pattern = re.compile(
            r"\b(birincisi|ikincisi|üçüncüsü|dördüncüsü|beşincisi|"
            r"(?:birinci|ikinci|üçüncü|dördüncü|beşinci)\s+(?:kaynak|delil|şart|ilke|kural|adım|aşama|bölüm|husus|nokta))"
            r"\s*(?:ise\s+|olarak\s+|yani\s+)?([^.!?;:]{4,55})",
            flags=re.IGNORECASE,
        )
        for m in pattern.finditer(window_3):
            if m.start() >= len(text_cur):
                continue
            ord_raw = to_turkish_lower(m.group(1).strip())
            first_word = ord_raw.split()[0]
            num_prefix = ordinal_map.get(first_word, "1.")
            rest_phrase = m.group(2).strip()

            # "dir / dır / tir / tır / dur / dür" bildirme eklerini temizle
            rest_title = extract_turkish_semantic_title(rest_phrase, max_chars=28)
            if rest_title and len(rest_title) >= 3:
                pos_ratio = m.start() / max(1.0, float(len(text_cur)))
                ts = seg_start + pos_ratio * max(0.4, (seg_end - seg_start) * 0.5)
                results.append((round(ts, 2), f"{num_prefix} {rest_title}"))

        return results

    def _extract_generic_definition_from_window(
        self, text_cur: str, window_2: str
    ) -> Optional[str]:
        """
        Herhangi bir Türkçe eğitim/felsefe/hukuk/bilim videosunda geçen
        '... delili', '... ilkesi', '... teorisi', '... kanunu' kavramlarını yakalar.
        """
        m = re.search(
            r"\b([A-ZÇĞİÖŞÜa-zçğıöşüâîû'\-]{3,18}(?:\s+[A-ZÇĞİÖŞÜa-zçğıöşüâîû'\-]{2,18}){0,2}\s+"
            r"(?:delili|ilkesi|teorisi|kanunu|doktrini|hipotezi|paradoksu|yasası))\b",
            window_2,
            flags=re.IGNORECASE,
        )
        if m and m.start() < len(text_cur):
            raw_phrase = m.group(1).strip()
            lower_p = to_turkish_lower(raw_phrase)
            # Zamir veya sıfat tamlamalarını ("bu delili", "bir kanunu") ele
            bad_starts = ("bu ", "şu ", "o ", "bir ", "her ", "hangi ", "aynı ", "böyle ", "diğer ")
            if not any(lower_p.startswith(bs) for bs in bad_starts):
                return extract_turkish_semantic_title(raw_phrase, max_chars=34)
        return None

    def _find_natural_chapter_boundaries(
        self,
        active_segments: List[Dict[str, Any]],
        video_duration: float,
        num_chapters: int,
    ) -> List[float]:
        """
        İdeal eşit zaman noktalarına (i * D / M) en yakın cümle arası boşluğu
        (seg[k].end -> seg[k+1].start) bularak cümle ortasında kesmeyi önler.
        """
        if num_chapters <= 1 or not active_segments:
            return [0.0, video_duration]

        boundaries = [0.0]
        ideal_step = video_duration / num_chapters
        min_chapter_gap = min(15.0, max(4.0, video_duration * 0.08))

        for i in range(1, num_chapters):
            ideal_ts = i * ideal_step
            best_ts = round(ideal_ts, 2)
            best_score = -999.0
            for k in range(len(active_segments) - 1):
                gap_start = float(active_segments[k].get("end", 0))
                gap_end = float(active_segments[k + 1].get("start", gap_start))
                mid_gap = (gap_start + gap_end) / 2.0
                dist = abs(mid_gap - ideal_ts)
                if dist <= max(8.0, ideal_step * 0.35):
                    pause_dur = max(0.0, gap_end - gap_start)
                    score = pause_dur * 5.0 - (dist / 20.0)
                    if score > best_score:
                        best_score = score
                        best_ts = round(mid_gap, 2)
            if best_ts > boundaries[-1] + min_chapter_gap and best_ts < video_duration - min_chapter_gap:
                boundaries.append(best_ts)

        boundaries.append(round(video_duration, 2))
        return boundaries

    def _plan_single_chapter(
        self,
        chapter_id: int,
        ch_start: float,
        ch_end: float,
        ch_segments: List[Dict[str, Any]],
        theme_profile: ThemeProfile,
        chapter_triggers: Optional[List[PlannedEditorialEvent]] = None,
        used_titles_global: Optional[Set[str]] = None,
    ) -> ChapterPlan:
        """
        Tek bir bölüm (ör. 05:00 - 07:15) için:
          1. Yüksek öncelikli Semantik Tetikleyicileri (PERSON_INTRODUCTION, ENUMERATION_CALLOUT, DEFINITION_CALLOUT)
          2. Bölüm Başlığı Kartını (CHAPTER_TITLE_CARD)
          3. Gerekirse tamamlayıcı anahtar kavram vurgularını
        birleştirerek zengin ve anlamlı bir ChapterPlan üretir.
        """
        if used_titles_global is None:
            used_titles_global = set()
        chapter_triggers = list(chapter_triggers or [])

        ch_duration = max(1.0, ch_end - ch_start)
        base_max_events = max(
            3,
            min(
                8,
                int(math.floor((ch_duration / 60.0) * theme_profile.max_overlays_per_minute)) + 1,
            ),
        )
        max_events = max(base_max_events, len(chapter_triggers) + 1)

        if (
            self.enable_llm_planning
            and not chapter_triggers
            and self.gemini
            and getattr(self.gemini, "is_available", lambda: False)()
        ):
            llm_plan = self._call_llm_for_chapter(
                chapter_id, ch_start, ch_end, ch_segments, theme_profile, max_events
            )
            if llm_plan:
                return llm_plan

        # Bölüm başlığını 2 segmentlik birleştirilmiş tam cümleden çıkar (yarım segment kesilmesini önle!)
        joined_opening = " ".join(str(s.get("text", "")).strip() for s in ch_segments[:2])
        chapter_title = (
            extract_turkish_semantic_title(joined_opening, max_chars=34)
            or f"BÖLÜM {chapter_id}"
        )

        events: List[PlannedEditorialEvent] = []

        # 1. Önce bu bölümdeki tüm Semantik Tetikleyicileri (Kişi, Sıralama, Tanım) ekle
        for idx, trig in enumerate(chapter_triggers):
            trig.chapter_id = chapter_id
            trig.event_id = f"evt_ch{chapter_id}_sem_{idx + 1:02d}"
            events.append(trig)
            used_titles_global.add(trig.text_primary)

        # 2. Bölüm açılışında (ilk 6 saniyede) zaten bir semantik tetikleyici yoksa Bölüm Başlığı ekle
        used_titles_chapter: Set[str] = set(e.text_primary for e in events)
        first_ts = max(0.3, float(ch_segments[0].get("start", ch_start)) + 0.3)
        has_early_trigger = any(abs(e.start_sec - first_ts) < 12.0 for e in events)
        if not has_early_trigger and len(chapter_triggers) < 2:
            if chapter_title in used_titles_global:
                alt_open = " ".join(str(ch_segments[0].get("text", "")).split()[3:])
                chapter_title = extract_turkish_semantic_title(alt_open, max_chars=34) or f"BÖLÜM {chapter_id}: {chapter_title[:22]}"
            first_end = min(ch_end - 0.3, first_ts + 3.6)
            if first_end <= first_ts + 0.8:
                first_end = first_ts + 2.5
            events.append(
                PlannedEditorialEvent(
                    event_id=f"evt_ch{chapter_id}_01",
                    chapter_id=chapter_id,
                    action_type="CHAPTER_TITLE_CARD",
                    start_sec=round(first_ts, 2),
                    end_sec=round(first_end, 2),
                    text_primary=chapter_title,
                    text_secondary=f"Bölüm {chapter_id}",
                )
            )
            used_titles_chapter.add(chapter_title)
            used_titles_global.add(chapter_title)

        # 3. Eğer bu bölümde en az 2 adet gerçek semantik tetikleyici (Tanım, Sıralama, Kişi) zaten yakalandıysa,
        # rastgele cümlelerden başlık kesen dolgu döngüsünü çalıştırma!
        if len(chapter_triggers) >= 2:
            events.sort(key=lambda e: e.start_sec)
            return ChapterPlan(
                chapter_id=chapter_id,
                start_sec=round(ch_start, 2),
                end_sec=round(ch_end, 2),
                title_tr=events[0].text_primary if events else chapter_title,
                key_terms=[e.text_primary for e in events],
                events=events,
            )
        min_gap = min(theme_profile.min_gap_between_overlays_sec, max(4.0, ch_duration / 3.5))
        scored_candidates = []
        for idx_s in range(len(ch_segments)):
            s = ch_segments[idx_s]
            s_start = float(s.get("start", 0))
            s_text = str(s.get("text", "")).strip()
            next_text = str(ch_segments[idx_s + 1].get("text", "")).strip() if idx_s + 1 < len(ch_segments) else ""
            combined_text = f"{s_text} {next_text}".strip()
            if len(s_text) < 12:
                continue
            score = self._score_semantic_importance(combined_text)
            scored_candidates.append((score, s_start, combined_text, s_text))

        scored_candidates.sort(key=lambda x: (-x[0], x[1]))

        evt_counter = len(events) + 1
        for _score, s_start, combined_text, s_text in scored_candidates:
            if len(events) >= max_events:
                break
            if any(abs(s_start - existing.start_sec) < max(12.0, min_gap) for existing in events):
                continue

            # Eğer cümlede "madde 114 ..." gibi spesifik bir kanun maddesi varsa onu öne çıkar
            art_match = re.search(r"\b(madde\s+\d+(?:\s+[a-zçğıöşüA-ZÇĞİÖŞÜ]+){0,2})", combined_text, flags=re.I)
            if art_match:
                semantic_title = extract_turkish_semantic_title(art_match.group(1), max_chars=34)
            else:
                semantic_title = extract_turkish_semantic_title(combined_text, max_chars=34)

            if semantic_title in used_titles_chapter or semantic_title in used_titles_global:
                tail_words = combined_text.split()[3:]
                if len(tail_words) >= 2:
                    alt_title = extract_turkish_semantic_title(" ".join(tail_words), max_chars=34)
                    if alt_title and len(alt_title) >= 4:
                        semantic_title = alt_title

            if (
                not semantic_title
                or len(semantic_title) < 4
                or semantic_title in used_titles_chapter
                or len(semantic_title.split()) < 2
            ):
                continue

            lower_text = to_turkish_lower(combined_text)
            has_number = bool(re.search(r"\b(\d+|madde|md\.|fıkra|yüzde|%)\b", lower_text))
            if has_number:
                action_type = "STAT_OR_ARTICLE_CALLOUT"
            elif evt_counter % 3 == 0:
                action_type = "CONCEPT_IMAGE_CARD"
            else:
                action_type = "KEY_TERM_CALLOUT"

            web_q_tr, stock_q_en, fallback_q_en = self._build_visual_queries(
                semantic_title, combined_text, theme_profile.id
            )

            ev_end = min(ch_end - 0.2, s_start + 3.8)
            if ev_end <= s_start + 1.0:
                ev_end = s_start + 3.0

            events.append(
                PlannedEditorialEvent(
                    event_id=f"evt_ch{chapter_id}_{evt_counter:02d}",
                    chapter_id=chapter_id,
                    action_type=action_type,
                    start_sec=round(s_start, 2),
                    end_sec=round(ev_end, 2),
                    text_primary=semantic_title,
                    text_secondary="",
                    primary_web_query_tr=web_q_tr,
                    secondary_stock_query_en=stock_q_en,
                    fallback_minimal_query_en=fallback_q_en,
                )
            )
            used_titles_chapter.add(semantic_title)
            used_titles_global.add(semantic_title)
            evt_counter += 1

        events.sort(key=lambda e: e.start_sec)
        if events and chapter_title.startswith("BÖLÜM "):
            chapter_title = events[0].text_primary

        return ChapterPlan(
            chapter_id=chapter_id,
            start_sec=round(ch_start, 2),
            end_sec=round(ch_end, 2),
            title_tr=chapter_title,
            key_terms=[e.text_primary for e in events],
            events=events,
        )

    def _call_llm_for_chapter(
        self,
        chapter_id: int,
        ch_start: float,
        ch_end: float,
        ch_segments: List[Dict[str, Any]],
        theme_profile: ThemeProfile,
        max_events: int,
    ) -> Optional[ChapterPlan]:
        """GeminiClient üzerinden bölüm için yapılandırılmış JSON kurgu planı üretir."""
        try:
            lines = [
                f"[{float(s.get('start', 0)):.1f}s - {float(s.get('end', 0)):.1f}s] {str(s.get('text', '')).strip()}"
                for s in ch_segments[:45]
            ]
            transcript_block = "\n".join(lines)
            prompt = (
                f"Sen profesyonel bir kurgu yönetmenisin. Video teması: {theme_profile.display_name}.\n"
                f"Bu bölüm [{ch_start:.1f}s - {ch_end:.1f}s] aralığındadır.\n"
                f"Aşağıdaki transkriptten en fazla {max_events} adet kurgu olayı seç.\n"
                "KURALLAR:\n"
                "1. 'text_primary' TAM BİR TÜRKÇE KAVRAM VEYA İSİM TAMLAMASI olmalıdır (en fazla 34 karakter). "
                "ASLA cümleyi ortasından kesme, ASLA '...' kullanma!\n"
                "2. Kişi tanıtımlarını ('PERSON_INTRODUCTION'), sıralamaları ('ENUMERATION_CALLOUT': 1. ..., 2. ...) "
                "ve tanımları ('DEFINITION_CALLOUT') mutlaka yakala.\n"
                "Sadece aşağıdaki JSON formatında yanıt ver:\n"
                '{"chapter_title": "...", "events": [{"action_type": "CHAPTER_TITLE_CARD|PERSON_INTRODUCTION|ENUMERATION_CALLOUT|DEFINITION_CALLOUT|KEY_TERM_CALLOUT", '
                '"start_sec": 12.5, "text_primary": "...", "primary_web_query_tr": "...", "secondary_stock_query_en": "..."}]}\n\n'
                f"TRANSKRİPT:\n{transcript_block}"
            )
            raw = self.gemini.generate_text(prompt, max_retries=1)
            if not raw:
                return None
            cleaned = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
            data = self.gemini._safe_parse_json(cleaned) if hasattr(self.gemini, "_safe_parse_json") else json.loads(cleaned)
            if not isinstance(data, dict):
                return None
            raw_events = data.get("events", [])
            if not raw_events:
                return None

            events: List[PlannedEditorialEvent] = []
            for idx, ev in enumerate(raw_events[:max_events]):
                st = max(ch_start + 0.2, min(ch_end - 2.0, float(ev.get("start_sec", ch_start))))
                title = extract_turkish_semantic_title(str(ev.get("text_primary", "")), max_chars=34)
                if not title:
                    continue
                web_q, stock_q, fallback_q = self._build_visual_queries(title, title, theme_profile.id)
                events.append(
                    PlannedEditorialEvent(
                        event_id=f"evt_ch{chapter_id}_{idx + 1:02d}",
                        chapter_id=chapter_id,
                        action_type=str(ev.get("action_type", "KEY_TERM_CALLOUT")),
                        start_sec=round(st, 2),
                        end_sec=round(min(ch_end - 0.2, st + 3.8), 2),
                        text_primary=title,
                        primary_web_query_tr=str(ev.get("primary_web_query_tr") or web_q),
                        secondary_stock_query_en=str(ev.get("secondary_stock_query_en") or stock_q),
                        fallback_minimal_query_en=fallback_q,
                    )
                )
            if not events:
                return None
            return ChapterPlan(
                chapter_id=chapter_id,
                start_sec=round(ch_start, 2),
                end_sec=round(ch_end, 2),
                title_tr=extract_turkish_semantic_title(str(data.get("chapter_title", "")), 34) or events[0].text_primary,
                key_terms=[e.text_primary for e in events],
                events=events,
            )
        except Exception as exc:
            logger.warning(f"[HolisticAnalyzer] Bölüm {chapter_id} LLM çağrısı yedek plana düştü: {exc}")
            return None

    def _score_semantic_importance(self, text: str) -> float:
        lower = to_turkish_lower(text)
        score = 1.0
        for kw in (
            "önemli", "dikkat", "şart", "kural", "madde", "kanun",
            "temel", "birincisi", "ikincisi", "üçüncüsü", "dördüncüsü",
            "delil", "ilke", "kavram", "tanım", "yani", "demektir",
            "sonuç", "kritik", "özetle", "kaynak", "hüküm", "adalet",
        ):
            if kw in lower:
                score += 1.5
        if "?" in text or "!" in text:
            score += 1.0
        return score

    def _build_visual_queries(
        self, title_tr: str, sentence_tr: str, theme_id: str
    ) -> Tuple[str, str, str]:
        """
        Türkçe kavramı YALNIZCA somut görsel karşılığı varsa ansiklopedik/stok sorguya çevirir.
        Soyut cümle parçalarını ASLA ham web sorgusu olarak döndürmez!
        """
        lower = to_turkish_lower(title_tr + " " + sentence_tr)
        if any(k in lower for k in ("kur'an", "kuran-ı kerim", "vahiy", "ayet", "sure")):
            return (
                "Kur'an",
                "Quran",
                "Islamic calligraphy manuscript Quran",
            )
        if any(k in lower for k in ("mahkeme", "dava", "hukuk", "kanun", "hakim", "hmk", "yargı", "anayasa", "adalet")):
            return (
                "Adalet",
                "Lady Justice",
                "wooden judge gavel law book courtroom desk",
            )
        if any(k in lower for k in ("kainat", "evren", "kozmos", "uzay", "galaksi", "yıldız", "güneş")):
            return (
                "Evren",
                "Universe",
                "cosmos galaxy stars nebula space",
            )
        if any(k in lower for k in ("sözleşme", "imza", "borç", "taraflar", "dilekçe", "tebligat")):
            return (
                "Sözleşme",
                "Contract",
                "signing legal contract document fountain pen desk",
            )
        if theme_id == "corporate_explainer":
            return (
                "",
                "modern executive boardroom presentation analytics",
                "minimalist corporate office architecture",
            )
        if theme_id == "tech_review":
            return (
                "",
                "modern software engineering monitor code close up",
                "clean minimal technology desk hardware",
            )
        if theme_id == "cinematic_documentary":
            return (
                "",
                "cinematic historical architecture dramatic lighting",
                "vintage archive manuscript library",
            )
        # Soyut akademik/felsefi konularda rastgele haber sitesi görseli çekilmemesi için web_q_tr boş bırakılır
        return (
            "",
            "",
            "",
        )

    @staticmethod
    def _normalize_cuts(cuts: List[Any]) -> List[Tuple[float, float]]:
        out: List[Tuple[float, float]] = []
        for c in cuts:
            if isinstance(c, (tuple, list)) and len(c) >= 2:
                out.append((float(c[0]), float(c[1])))
            elif isinstance(c, dict):
                out.append((float(c.get("start", 0.0)), float(c.get("end", 0.0))))
            elif hasattr(c, "start") and hasattr(c, "end"):
                out.append((float(getattr(c, "start", 0.0)), float(getattr(c, "end", 0.0))))
        return out

    def _filter_active_segments(
        self, segments: List[Dict[str, Any]], cuts: List[Tuple[float, float]]
    ) -> List[Dict[str, Any]]:
        active = []
        for s in segments:
            s_start = float(s.get("start", 0.0))
            s_end = float(s.get("end", s_start + 2.0))
            mid = (s_start + s_end) / 2.0
            if not any(c_start <= mid <= c_end for c_start, c_end in cuts):
                active.append(s)
        return active
