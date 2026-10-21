"""
Aşama 1: Kelime-Senkronlu Bütüncül Video Analizcisi (HolisticAnalyzer).
Videonun tamamını (00:00 -> son saniye) kelime bazlı zaman damgaları (words[]) üzerinden tarar:
  1. Kişi veya Eser Tanıtımları (PERSON_INTRODUCTION / WORK_INTRODUCTION):
     - SADECE bir kişi/alim/filozof veya somut bir kitap/eser tanıtıldığında görsel (Wikipedia portresi/eser resmi) koyar.
     - Kişi/eser adı geçtiği kelimenin 'start' salisesinde başlar, o cümlenin son kelimesinin 'end' salisesinde biter.
  2. Kümülatif Sıralamalar (PROGRESSIVE_LIST):
     - Konuşmacı maddeleri sayarken (ör. "Fizik, kimya, biyoloji, tıp ve astronomi ilimlerinin...")
       her madde ağzından çıktığı kelimenin 'start' salisesinde sol sütuna alt alta (Y=18%, 27.5%, 37%, 46.5%) yazılır,
       sol sütun (4 satır) dolduğunda sağ sütuna (X=84%, Y=18%...) geçer ve cümlenin bitiş kelimesi ('end') tamamlandığında
       tüm liste aynı anda ekrandan kalkar.
  3. İkili Kavram Vurguları (PAIRED_TERMS):
     - Ör. "tabiat ve fıtrat kanunlarıdır" dediğinde tam "tabiat" kelimesinde 'TABİAT', tam "fıtrat" kelimesinde
       altına 'FITRAT' yazılır; "kanunlarıdır" kelimesi biter bitmez (bir sonraki cümle başlamadan önce) ikisi birlikte silinir.
  4. Anlık Kısa Terim Vurguları (SINGLE_TERM / DEFINITION_CALLOUT / ENUMERATION_CALLOUT):
     - Ör. "İkincisi: Tekvinî Şeriat'tır" dediğinde tam "tekvini" kelimesinde 'TEKVİNÎ ŞERİAT' çıkar ve "şeriattır"
       kelimesi bittiği salisede hemen kaybolur (sabit saniye kullanılmaz, kelime sınırlarına kilitlenir).
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


@dataclass
class WordToken:
    idx: int
    raw: str
    clean: str
    lower: str
    start: float
    end: float
    seg_idx: int
    has_comma: bool
    has_sentence_end: bool


# Tanınmış filozof, alim, bilim insanı ve tarihsel şahsiyetlerin
# (anahtar_kelime_listesi, Ekran Başlığı, Türkçe Wikipedia Başlığı, İngilizce Wikipedia Başlığı) eşlemesi
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

# Sadece somut bir Kitap / Eser / Kanunname tanıtıldığında görsel konulacak eserler
KNOWN_WORKS_WIKI_MAP: List[Tuple[Tuple[str, ...], str, str, str]] = [
    (("mecellenin", "mecelle-i", "mecelle"), "MECELLE-İ AHKÂM-I ADLİYE", "Mecelle", "Mecelle"),
    (("risale-i nur", "lemeat adlı eserinde"), "RİSALE-İ NUR KÜLLİYATI", "Risale-i Nur", "Risale-i Nur"),
]

# Kısa, öz (1-2 kelimelik) kavramsal terimler — Görsel KONULMAZ, yalnızca kelime-senkronlu kısa terim yazılır!
# (tetikleyici_alt_dizeler, Başlangıç_Kelimesi_İpucu, Bitiş_Kelimesi_İpucu, Ekran_Metni)
SHORT_CONCEPT_TERMS: List[Tuple[Tuple[str, ...], str, str, str]] = [
    (("tahkikat ve ön inceleme",), "tahkikat", "dengesini", "TAHKİKAT VE ÖN İNCELEME"),
    (("bürhan-ı inni", "burhan-ı inni"), "bürhan-ı", "inniyle", "BÜRHAN-I İNNÎ"),
    (("bürhan-ı limmi", "burhan-ı limmi"), "bürhan-ı", "metodolojisini", "BÜRHAN-I LİMMÎ"),
    (("hudus delili", "hudûs delili"), "hudus", "fısıldar", "HUDÛS DELİLİ"),
    (("imkan delili", "imkân delili"), "imkan", "hatırlatır", "İMKÂN DELİLİ"),
    (("inayet delili", "inayet ve gaye"), "inayet", "gösterir", "İNAYET DELİLİ"),
    (("temanü delili", "temânü delili"), "temanü", "delili", "TEMÂNÜ DELİLİ"),
    (("normlar hiyerarşisidir", "normlar yararçisiyle"), "normlar", "hiyerarşisidir", "NORMLAR HİYERARŞİSİ"),
    (("kaziye-i muhkeme", "kaziye-i muhakeme"), "kaziye-i", "haline", "KAZİYE-İ MUHKEME"),
    (("mukayeseli hukukun", "mukayeseli hukuk"), "mukayeseli", "hukukun", "MUKAYESELİ HUKUK"),
    (("edille-i şer'iyye", "edilley-i şehriye"), "edilley-i", "inşa", "EDİLLE-İ ŞER'İYYE"),
    (("içtihat ile içtihat nakz", "içtihatla içtihat nakz"), "içtihat", "olunmaz", "İÇTİHAT İLE İÇTİHAT NAKZOLUNMAZ"),
    (("türk medeni kanunu'nun birinci",), "türk", "maddesi", "TMK MADDE 1"),
    (("adalet-i mahza",), "adalet-i", "mahza", "ADALET-İ MAHZA"),
    (("üç büyük şeriat",), "üç", "şeriat", "ÜÇ BÜYÜK ŞERİAT"),
    (("birincisi tenzili", "teşri şeriatdır"), "tenzili", "şeriatdır", "TENZİLÎ (TEŞRÎ) ŞERİAT"),
    (("ikincisi tekvini şeriattır", "ikincisi ise tekvini"), "tekvini", "şeriattır", "TEKVİNÎ ŞERİAT"),
    (("üçüncüsü ise mahiyet", "yani akli şeriattır"), "akli", "şeriattır", "AKLÎ ŞERİAT"),
    (("zülcenahen", "zülcenaheyn"), "zülcenahen", "arar", "ZÜLCENAHEYN"),
    (("ismet sıfatı",), "ismet", "sıfatı", "İSMET SIFATI"),
    (("ratio legis", "ratyolegesini"), "ratyolegesini", "arar", "RATIO LEGIS"),
]

# İkili kavram vurguları (Önce 1. kelime çıkar, tam 2. kelime söylendiğinde altına 2. kelime eklenir, cümle sonunda ikisi birden gider)
# (pencere_tetikleyici, [(kelime1_ipucu, Ekran1), (kelime2_ipucu, Ekran2)], bitiş_kelimesi_ipucu)
PAIRED_TERM_RULES: List[Tuple[str, List[Tuple[str, str]], str]] = [
    ("mutlak irade ve kudret", [("irade", "İRADE"), ("kudret", "KUDRET")], "sıvatından"),
    ("tabiat ve fıtrat", [("tabiat", "TABİAT"), ("fıtrat", "FITRAT")], "kanunlarıdır"),
    ("eserlerden müessire", [("eserlerden", "ESERDEN MÜESSİRE"), ("sebepten", "SEBEPTEN SONUCA")], "inen"),
    ("amiriyet ve hakimiyet", [("amiriyet", "AMİRİYET"), ("hakimiyet", "HAKİMİYET")], "ortaklık"),
    ("kanunun bir lafzı", [("lafzı", "KANUNUN LAFZI"), ("ruhu", "KANUNUN RUHU")], "vardır"),
    ("kalem sıfatının kelimeleridir", [("kalem", "KALEM SIFATI (KUR'AN)"), ("kudret", "KUDRET SIFATI (KAİNAT)")], "ayetleridir"),
    ("sübjektif ve objektif iradesini", [("sübjektif", "SÜBJEKTİF İRADE"), ("objektif", "OBJEKTİF İRADE")], "gayesini"),
    ("kanunu bilip kanun koyucuğu", [("kanunu", "KANUN VE NİZAM"), ("koyucuğu", "KANUN KOYUCU")], "tanımamak"),
]

# Çoklu/Kümülatif Sıralama Kalıpları (Her madde kendi kelimesi söylendiği salisede alt alta eklenir,
# sol sütun 4 satır dolunca sağ sütuna geçer, bitiş kelimesi tamamlandığında hepsi aynı anda silinir!)
# (pencere_tetikleyici, [(kelime_ipucu, Ekran_Metni), ...], bitiş_kelimesi_ipucu)
PROGRESSIVE_LIST_RULES: List[Tuple[str, List[Tuple[str, str]], str]] = [
    (
        "hakim, fehim",
        [
            ("hakim,", "HAKÎM"),
            ("fehim", "FEHÎM"),
            ("mekin", "MEKÎN"),
            ("mitin", "METÎN"),
        ],
        "vasıflarını",
    ),
    (
        "hukuk, vahiy ve tabiat",
        [
            ("hukuk", "HUKUK"),
            ("vahiy", "VAHİY"),
            ("tabiat", "TABİAT KANUNLARI"),
        ],
        "olabilir",
    ),
    (
        "piramidin en tepesinde",
        [
            ("uluslararası", "ULUSLARARASI SÖZLEŞMELER"),
            ("anayasa", "ANAYASA"),
            ("kanunlar", "KANUNLAR"),
            ("yönetmelik", "YÖNETMELİK VE GENELGE"),
            ("yargıtay", "YARGITAY İÇTİHATLARI"),
        ],
        "sıralanır",
    ),
    (
        "idare hukukumuzu fransa",
        [
            ("idare", "İDARE HUKUKU (FRANSA)"),
            ("yargılama", "USUL HUKUKU (İSVİÇRE)"),
            ("medeni", "MEDENİ HUKUK (İSVİÇRE)"),
            ("ceza", "CEZA HUKUKU (İTALYA)"),
            ("ticaret", "TİCARET HUKUKU (ALMANYA)"),
        ],
        "ettik",
    ),
    (
        "birinci ve mutlak kaynak",
        [
            ("kur'an-ı", "1. KUR'AN-I KERİM"),
            ("sünnet-i", "2. SÜNNET-İ SENİYYE"),
            ("icma", "3. İCMÂ"),
            ("kıyastır", "4. KIYAS"),
        ],
        "kıyastır",
    ),
    (
        "allah'ın kitabı ile",
        [
            ("kitabı", "1. ALLAH'IN KİTABI"),
            ("sünneti", "2. RESÛLULLAH'IN SÜNNETİ"),
            ("iştihat", "3. AKILLA İÇTİHAT"),
        ],
        "ararım",
    ),
    (
        "medeni kanunu'nun madde bir",
        [
            ("lafzıyla", "1. KANUNUN LAFZI VE RUHU"),
            ("örf", "2. ÖRF VE ÂDET HUKUKU"),
            ("koyucu", "3. HAKİMİN HUKUK YARATMASI"),
        ],
        "verir",
    ),
    (
        "tefsir, tastik ve teyit",
        [
            ("tefsir", "TEFSİR"),
            ("tastik", "TASDİK"),
            ("teyit", "TEYİT"),
        ],
        "eder",
    ),
    (
        "adaleti, ibadeti, ahlakı",
        [
            ("adaleti", "ADALET"),
            ("ibadeti", "İBADET"),
            ("ahlakı", "AHLAK"),
            ("helali", "HELAL"),
            ("haramı", "HARAM"),
        ],
        "gösterir",
    ),
    (
        "fizik, kimya, biyoloji",
        [
            ("fizik", "FİZİK"),
            ("kimya", "KİMYA"),
            ("biyoloji", "BİYOLOJİ"),
            ("tıp", "TIP"),
            ("astronomi", "ASTRONOMİ"),
        ],
        "maddeleridir",
    ),
    (
        "suyun kaldırma kuvveti",
        [
            ("suyun", "SUYUN KALDIRMA KUVVETİ"),
            ("yerçekimi", "YERÇEKİMİ KANUNU"),
            ("fotosentez", "FOTOSENTEZ NİZAMI"),
            ("gezegenlerin", "GEZEGENLERİN YÖRÜNGELERİ"),
        ],
        "yörüngeleri",
    ),
    (
        "doğru düşünme, çelişkiden",
        [
            ("doğru", "DOĞRU DÜŞÜNME"),
            ("çelişkiden", "ÇELİŞKİDEN KAÇINMA"),
            ("sebep", "SEBEP-SONUÇ BAĞI"),
            ("tutarlı", "TUTARLI DAVRANMA"),
        ],
        "kurallarıdır",
    ),
    (
        "necisin nereden geliyorsun",
        [
            ("necisin", "NECİSİN?"),
            ("nereden", "NEREDEN GELİYORSUN?"),
            ("nereye", "NEREYE GİDİYORSUN?"),
        ],
        "çözecek",
    ),
    (
        "yahudilerin, hristiyanların ve müslümanların",
        [
            ("yahudilerin", "YAHUDİLİK"),
            ("hristiyanların", "HRİSTİYANLIK"),
            ("müslümanların", "İSLAM"),
        ],
        "tanrı'dır",
    ),
    (
        "hz. ibrahim'i, hz. musa",
        [
            ("ibrahim'i", "HZ. İBRAHİM"),
            ("musa'ya", "HZ. MUSA"),
            ("isa'ya", "HZ. İSA"),
        ],
        "kılar",
    ),
    (
        "fen bilimleri, laboratuvarlar",
        [
            ("fen", "FEN BİLİMLERİ"),
            ("laboratuvarlar", "LABORATUVARLAR"),
            ("teleskoplar", "TELESKOPLAR"),
            ("mikroskoplar", "MİKROSKOPLAR"),
        ],
        "anlatır",
    ),
    (
        "inayet, hudus, imkan",
        [
            ("inayet", "İNAYET DELİLİ"),
            ("hudus", "HUDÛS DELİLİ"),
            ("imkan", "İMKÂN DELİLİ"),
            ("iştira", "İHTİRA DELİLİ"),
            ("temanü", "TEMÂNÜ DELİLİ"),
        ],
        "delilleriyle",
    ),
]


@dataclass
class PlannedEditorialEvent:
    event_id: str
    chapter_id: int
    action_type: str  # "PERSON_INTRODUCTION" | "WORK_INTRODUCTION" | "PROGRESSIVE_LIST" | "PAIRED_TERMS" | "SINGLE_TERM" | "ENUMERATION_CALLOUT" | "DEFINITION_CALLOUT" | "CHAPTER_TITLE_CARD"
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
    group_id: str = ""
    stack_slot: Optional[int] = None


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
    Videoyu kelime-zamanlamalı (Word-Synchronized) olarak analiz eden ve:
      - Kişi/Eser tanıtımlarında (ve SADECE bunlarda) İsim + Wikipedia Görseli,
      - Sıralama anlarında ("Fizik, kimya, biyoloji, tıp ve astronomi") her kelime söylendiğinde
        sol sütuna alt alta, sol dolunca sağ sütuna geçen kümülatif liste,
      - İkili kavramlarda ("tabiat ve fıtrat") önce 1., sonra 2. kavramı çıkarıp cümle bitiminde birlikte silen,
      - Tekil kavramlarda ("Tekvinî Şeriat'tır") kavram kelimesinde başlayıp o cümlenin bitiş kelimesinde hemen silen
    kurgu planlayıcısı.
    """

    def __init__(self, gemini_client: Any = None, enable_llm_planning: bool = True):
        self.gemini = gemini_client
        self.enable_llm_planning = enable_llm_planning

    def analyze_video(
        self,
        segments: List[Dict[str, Any]],
        video_duration: float,
        cuts: Optional[List[Any]] = None,
    ) -> Tuple[ThemeProfile, str, List[ChapterPlan]]:
        normalized_cuts = self._normalize_cuts(cuts or [])
        active_segments = self._filter_active_segments(segments, normalized_cuts)
        full_text = " ".join(str(s.get("text", "")).strip() for s in active_segments)

        # 1. Kilitli ThemeProfile tespiti
        theme_profile = detect_theme_profile_heuristic(full_text)

        # 2. Videoyu kronolojik bölümlere (Chapters) ayır
        safe_duration = max(5.0, float(video_duration or 30.0))
        target_chapter_len = 135.0 if safe_duration >= 300.0 else max(25.0, safe_duration / 3.0)
        num_chapters = max(1, min(16, int(round(safe_duration / target_chapter_len))))
        chapter_boundaries = self._find_natural_chapter_boundaries(
            active_segments, safe_duration, num_chapters
        )

        # 3. Düzleştirilmiş kelime akışı (WordToken listesi) oluştur ve tüm kelime-senkronlu olayları çıkar
        word_stream = self._build_word_stream(active_segments)
        global_semantic_triggers = self._detect_global_semantic_triggers(
            active_segments, safe_duration, word_stream=word_stream
        )

        # 4. Bölüm planlarına dağıt
        chapter_plans: List[ChapterPlan] = []
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

            is_last_ch = ch_idx == len(chapter_boundaries) - 2
            ch_triggers = [
                t
                for t in global_semantic_triggers
                if (ch_start <= t.start_sec < ch_end)
                or (is_last_ch and ch_start <= t.start_sec <= ch_end + 1.0)
            ]

            ch_plan = self._plan_single_chapter(
                chapter_id=ch_idx + 1,
                ch_start=ch_start,
                ch_end=ch_end,
                ch_segments=ch_segs,
                theme_profile=theme_profile,
                chapter_triggers=ch_triggers,
            )
            chapter_plans.append(ch_plan)

        subject_summary = (
            f"{theme_profile.display_name} ({len(chapter_plans)} Bölüm, {safe_duration:.1f}s)"
        )
        logger.info(
            f"[HolisticAnalyzer] Tamamlandı: Tema='{theme_profile.id}', "
            f"Bölüm Sayısı={len(chapter_plans)}, "
            f"Toplam Kelime-Senkronlu Olay={sum(len(c.events) for c in chapter_plans)}"
        )
        return theme_profile, subject_summary, chapter_plans

    def _build_word_stream(self, active_segments: List[Dict[str, Any]]) -> List[WordToken]:
        """
        Her segmentteki 'words' dizisini (yoksa metinden orantılı enterpolasyonla)
        düz ve salise hassasiyetli bir WordToken akışına dönüştürür.
        """
        tokens: List[WordToken] = []
        for seg_idx, seg in enumerate(active_segments):
            s_start = float(seg.get("start", 0.0))
            s_end = max(s_start + 0.2, float(seg.get("end", s_start + 2.5)))
            raw_words = seg.get("words") or []
            if raw_words and isinstance(raw_words, list):
                for w in raw_words:
                    w_str = str(w.get("word", "")).strip()
                    if not w_str:
                        continue
                    w_start = float(w.get("start", s_start))
                    w_end = max(w_start + 0.08, float(w.get("end", w_start + 0.35)))
                    clean = re.sub(r"^[^\wçğıöşüâîûÇĞİÖŞÜÂÎÛ]+|[^\wçğıöşüâîûÇĞİÖŞÜÂÎÛ'-]+$", "", w_str)
                    tokens.append(
                        WordToken(
                            idx=len(tokens),
                            raw=w_str,
                            clean=clean or w_str,
                            lower=to_turkish_lower(clean or w_str),
                            start=round(w_start, 2),
                            end=round(w_end, 2),
                            seg_idx=seg_idx,
                            has_comma="," in w_str,
                            has_sentence_end=any(p in w_str for p in (".", "?", "!", ":", ";")),
                        )
                    )
            else:
                parts = [p for p in str(seg.get("text", "")).strip().split() if p]
                if not parts:
                    continue
                step = (s_end - s_start) / float(len(parts))
                for k, w_str in enumerate(parts):
                    w_start = s_start + k * step
                    w_end = w_start + step
                    clean = re.sub(r"^[^\wçğıöşüâîûÇĞİÖŞÜÂÎÛ]+|[^\wçğıöşüâîûÇĞİÖŞÜÂÎÛ'-]+$", "", w_str)
                    tokens.append(
                        WordToken(
                            idx=len(tokens),
                            raw=w_str,
                            clean=clean or w_str,
                            lower=to_turkish_lower(clean or w_str),
                            start=round(w_start, 2),
                            end=round(w_end, 2),
                            seg_idx=seg_idx,
                            has_comma="," in w_str,
                            has_sentence_end=any(p in w_str for p in (".", "?", "!", ":", ";")),
                        )
                    )
        return tokens

    def _find_word_in_range(
        self,
        word_stream: List[WordToken],
        min_seg_idx: int,
        max_seg_idx: int,
        keyword_hint: str,
        after_word_idx: int = -1,
    ) -> Optional[WordToken]:
        hint_low = to_turkish_lower(keyword_hint.strip())
        if not hint_low:
            return None
        for tok in word_stream:
            if tok.idx <= after_word_idx:
                continue
            if tok.seg_idx < min_seg_idx:
                continue
            if tok.seg_idx > max_seg_idx:
                break
            if tok.lower.startswith(hint_low) or hint_low in tok.lower or hint_low in to_turkish_lower(tok.raw):
                return tok
        return None

    def _find_sentence_end_word(
        self,
        word_stream: List[WordToken],
        start_tok: WordToken,
        max_seg_idx: int,
        end_hint: str = "",
    ) -> WordToken:
        if end_hint:
            found_end = self._find_word_in_range(
                word_stream, start_tok.seg_idx, max_seg_idx, end_hint, after_word_idx=start_tok.idx - 1
            )
            if found_end:
                return found_end
        # Cümle sonu noktalama işaretine (. ? ! ; :) sahip ilk kelimeyi bul
        for tok in word_stream[start_tok.idx :]:
            if tok.seg_idx > max_seg_idx:
                break
            if tok.idx > start_tok.idx and tok.has_sentence_end:
                return tok
        # Bulunamazsa mevcut segmentin son kelimesini döndür
        seg_tokens = [t for t in word_stream if t.seg_idx == start_tok.seg_idx]
        return seg_tokens[-1] if seg_tokens else start_tok

    def _detect_global_semantic_triggers(
        self,
        active_segments: List[Dict[str, Any]],
        video_duration: float,
        word_stream: Optional[List[WordToken]] = None,
    ) -> List[PlannedEditorialEvent]:
        if not active_segments:
            return []
        if word_stream is None:
            word_stream = self._build_word_stream(active_segments)

        triggers: List[PlannedEditorialEvent] = []
        seen_persons: Dict[str, float] = {}
        seen_works: Dict[str, float] = {}
        seen_groups: Dict[str, float] = {}
        seen_terms: Dict[str, float] = {}
        occupied_ranges: List[Tuple[float, float]] = []

        def is_range_busy(st: float, en: float) -> bool:
            for o_st, o_en in occupied_ranges:
                if max(st, o_st) < min(en, o_en) - 0.15:
                    return True
            return False

        n_segs = len(active_segments)

        # ------------------------------------------------------------------
        # AŞAMA A: KÜMÜLATİF SIRALAMALAR (PROGRESSIVE_LIST)
        # ("Fizik, kimya, biyoloji, tıp ve astronomi", "Adalet, ibadet, ahlak, helal ve haram", vb.)
        # ------------------------------------------------------------------
        for i in range(n_segs):
            seg_window_max = min(n_segs - 1, i + 15)
            window_3_text = " ".join(
                str(active_segments[k].get("text", "")).strip()
                for k in range(i, min(n_segs, i + 3))
            )
            lower_win3 = to_turkish_lower(window_3_text)
            lower_cur = to_turkish_lower(str(active_segments[i].get("text", "")).strip())

            for rule_trigger, item_specs, end_hint in PROGRESSIVE_LIST_RULES:
                if rule_trigger in lower_cur or (
                    rule_trigger in lower_win3
                    and rule_trigger.split()[0] in lower_cur
                ):
                    last_seen = seen_groups.get(rule_trigger, -999.0)
                    seg_st = float(active_segments[i].get("start", 0.0))
                    if seg_st - last_seen < 90.0:
                        continue

                    matched_items: List[Tuple[WordToken, str]] = []
                    last_tok_idx = -1
                    for word_hint, label_tr in item_specs:
                        tok = self._find_word_in_range(
                            word_stream, i, seg_window_max, word_hint, after_word_idx=last_tok_idx
                        )
                        if tok:
                            matched_items.append((tok, label_tr))
                            last_tok_idx = tok.idx

                    if len(matched_items) >= 2:
                        last_item_tok = matched_items[-1][0]
                        end_tok = self._find_sentence_end_word(
                            word_stream, last_item_tok, min(n_segs - 1, last_item_tok.seg_idx + 2), end_hint
                        )
                        shared_end_sec = round(max(last_item_tok.end + 0.35, end_tok.end), 2)
                        seen_groups[rule_trigger] = seg_st
                        grp_id = f"grp_list_{len(seen_groups):02d}"

                        for slot_idx, (item_tok, label_tr) in enumerate(matched_items):
                            item_start = round(item_tok.start, 2)
                            item_end = round(max(item_start + 0.45, shared_end_sec), 2)
                            triggers.append(
                                PlannedEditorialEvent(
                                    event_id=f"{grp_id}_item_{slot_idx + 1:02d}",
                                    chapter_id=0,
                                    action_type="PROGRESSIVE_LIST",
                                    start_sec=item_start,
                                    end_sec=item_end,
                                    text_primary=label_tr,
                                    text_secondary=f"Sıralama {slot_idx + 1}",
                                    semantic_priority=True,
                                    group_id=grp_id,
                                    stack_slot=slot_idx,
                                )
                            )
                        occupied_ranges.append((matched_items[0][0].start, shared_end_sec))
                        break

        # Genel Virgüllü / "ve" Bağlaçlı Sıralama Yakalayıcı (Özel listede olmayan her türlü yeni video için!)
        self._detect_generic_comma_lists(
            active_segments, word_stream, triggers, occupied_ranges, is_range_busy
        )

        # ------------------------------------------------------------------
        # AŞAMA B: İKİLİ KAVRAM VURGULARI (PAIRED_TERMS)
        # (Ör. "tabiat ve fıtrat kanunlarıdır" -> Önce TABİAT, sonra altına FITRAT, "kanunlarıdır" bitince ikisi de gider!)
        # ------------------------------------------------------------------
        for i in range(n_segs):
            window_2_text = " ".join(
                str(active_segments[k].get("text", "")).strip()
                for k in range(i, min(n_segs, i + 3))
            )
            lower_win2 = to_turkish_lower(window_2_text)
            lower_cur = to_turkish_lower(str(active_segments[i].get("text", "")).strip())

            for pair_trigger, pair_specs, end_hint in PAIRED_TERM_RULES:
                if pair_trigger in lower_cur or (
                    pair_trigger in lower_win2 and pair_trigger.split()[0] in lower_cur
                ):
                    seg_st = float(active_segments[i].get("start", 0.0))
                    if seg_st - seen_groups.get(pair_trigger, -999.0) < 90.0:
                        continue
                    tok1 = self._find_word_in_range(word_stream, i, min(n_segs - 1, i + 2), pair_specs[0][0])
                    if not tok1:
                        continue
                    tok2 = self._find_word_in_range(
                        word_stream, tok1.seg_idx, min(n_segs - 1, tok1.seg_idx + 2), pair_specs[1][0], after_word_idx=tok1.idx
                    )
                    if not tok2:
                        continue
                    end_tok = self._find_sentence_end_word(
                        word_stream, tok2, min(n_segs - 1, tok2.seg_idx + 1), end_hint
                    )
                    shared_end = round(max(tok2.end + 0.35, end_tok.end), 2)
                    if is_range_busy(tok1.start, shared_end):
                        continue

                    seen_groups[pair_trigger] = seg_st
                    grp_id = f"grp_pair_{len(seen_groups):02d}"
                    for slot_idx, (tok, label_tr) in enumerate([(tok1, pair_specs[0][1]), (tok2, pair_specs[1][1])]):
                        st_s = round(tok.start, 2)
                        en_s = round(max(st_s + 0.45, shared_end), 2)
                        triggers.append(
                            PlannedEditorialEvent(
                                event_id=f"{grp_id}_{slot_idx + 1}",
                                chapter_id=0,
                                action_type="PAIRED_TERMS",
                                start_sec=st_s,
                                end_sec=en_s,
                                text_primary=label_tr,
                                text_secondary="İkili Kavram",
                                semantic_priority=True,
                                group_id=grp_id,
                                stack_slot=slot_idx,
                            )
                        )
                    occupied_ranges.append((tok1.start, shared_end))

        # ------------------------------------------------------------------
        # AŞAMA C: KİŞİ VEYA ESER TANITIMLARI (SADECE BUNLARDA GÖRSEL KONUR!)
        # ------------------------------------------------------------------
        for i in range(n_segs):
            text_cur = str(active_segments[i].get("text", "")).strip()
            text_next = str(active_segments[i + 1].get("text", "")).strip() if i + 1 < n_segs else ""
            window_2 = f"{text_cur} {text_next}".strip()
            lower_cur = to_turkish_lower(text_cur)
            lower_win2 = to_turkish_lower(window_2)
            s_start = float(active_segments[i].get("start", 0.0))

            # 1. Kişi Tanıtımı (PERSON_INTRODUCTION)
            matched_person = False
            for kw_tuple, display_name, wiki_tr, wiki_en in KNOWN_PERSONS_WIKI_MAP:
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
                    if s_start - seen_persons.get(display_name, -999.0) >= 240.0:
                        first_kw = next((k.split()[0] for k in kw_tuple if k in lower_win2), kw_tuple[0].split()[0])
                        start_tok = self._find_word_in_range(word_stream, i, min(n_segs - 1, i + 1), first_kw)
                        ev_start = round(start_tok.start if start_tok else s_start, 2)
                        if start_tok:
                            end_tok = self._find_sentence_end_word(word_stream, start_tok, min(n_segs - 1, i + 2))
                            ev_end = round(max(ev_start + 1.8, min(ev_start + 4.8, end_tok.end)), 2)
                        else:
                            ev_end = round(min(video_duration - 0.2, ev_start + 3.8), 2)

                        if not is_range_busy(ev_start, ev_end):
                            seen_persons[display_name] = s_start
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
                            occupied_ranges.append((ev_start, ev_end))
                            matched_person = True
                            break

            # Dinamik Unvanlı Kişi Yakalayıcı (Örn. "Prof. Dr. Ahmet Arslan")
            if not matched_person:
                dyn_match = re.search(
                    r"\b((?:Prof\.?\s*(?:Dr\.?\s*)?|Doç\.?\s*Dr\.?\s*|İmam(?:-ı)?\s+)[A-ZÇĞİÖŞÜÂÎÛ][a-zçğıöşüâîû]+(?:\s+[A-ZÇĞİÖŞÜÂÎÛ][a-zçğıöşüâîû]+){0,2})",
                    window_2,
                )
                if dyn_match and dyn_match.start() < len(text_cur) + 6:
                    raw_person = re.sub(r"['’].*$", "", dyn_match.group(1).strip())
                    disp_person = to_turkish_upper(raw_person)
                    if len(disp_person) >= 7 and s_start - seen_persons.get(disp_person, -999.0) >= 240.0:
                        clean_wiki = re.sub(r"^(Prof\.?\s*(?:Dr\.?\s*)?|Doç\.?\s*Dr\.?\s*)", "", raw_person, flags=re.I).strip()
                        start_tok = self._find_word_in_range(word_stream, i, min(n_segs - 1, i + 1), clean_wiki.split()[0])
                        ev_start = round(start_tok.start if start_tok else s_start, 2)
                        ev_end = round(min(video_duration - 0.2, ev_start + 3.6), 2)
                        if not is_range_busy(ev_start, ev_end):
                            seen_persons[disp_person] = s_start
                            triggers.append(
                                PlannedEditorialEvent(
                                    event_id=f"trig_person_{len(triggers) + 1:02d}",
                                    chapter_id=0,
                                    action_type="PERSON_INTRODUCTION",
                                    start_sec=ev_start,
                                    end_sec=ev_end,
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
                            occupied_ranges.append((ev_start, ev_end))

            # 2. Somut Eser / Kitap / Kanunname Tanıtımı (WORK_INTRODUCTION)
            for kw_tuple, work_title, wiki_tr, wiki_en in KNOWN_WORKS_WIKI_MAP:
                if any(k in lower_cur for k in kw_tuple):
                    if s_start - seen_works.get(work_title, -999.0) >= 300.0:
                        first_kw = next((k.split()[0] for k in kw_tuple if k in lower_cur), kw_tuple[0].split()[0])
                        start_tok = self._find_word_in_range(word_stream, i, i, first_kw)
                        ev_start = round(start_tok.start if start_tok else s_start, 2)
                        end_tok = (
                            self._find_sentence_end_word(word_stream, start_tok, min(n_segs - 1, i + 1))
                            if start_tok
                            else None
                        )
                        ev_end = round(
                            max(ev_start + 1.5, min(ev_start + 3.8, end_tok.end if end_tok else ev_start + 2.8)),
                            2,
                        )
                        if not is_range_busy(ev_start, ev_end):
                            seen_works[work_title] = s_start
                            triggers.append(
                                PlannedEditorialEvent(
                                    event_id=f"trig_work_{len(triggers) + 1:02d}",
                                    chapter_id=0,
                                    action_type="WORK_INTRODUCTION",
                                    start_sec=ev_start,
                                    end_sec=ev_end,
                                    text_primary=work_title,
                                    text_secondary="Eser / Kanunname",
                                    primary_web_query_tr=wiki_tr,
                                    secondary_stock_query_en=wiki_en,
                                    fallback_minimal_query_en=wiki_en,
                                    person_wiki_tr=wiki_tr,
                                    person_wiki_en=wiki_en,
                                    semantic_priority=True,
                                )
                            )
                            occupied_ranges.append((ev_start, ev_end))
                            break

        # ------------------------------------------------------------------
        # AŞAMA D: ANLIK KISA TERİM VURGULARI (SINGLE_TERM / DEFINITION / ENUMERATION)
        # (Tam o kelimede başlar, o cümlenin bitiş kelimesinde hemen kaybolur — GÖRSEL KONULMAZ!)
        # ------------------------------------------------------------------
        for i in range(n_segs):
            text_cur = str(active_segments[i].get("text", "")).strip()
            text_next = str(active_segments[i + 1].get("text", "")).strip() if i + 1 < n_segs else ""
            window_2 = f"{text_cur} {text_next}".strip()
            lower_cur = to_turkish_lower(text_cur)
            lower_win2 = to_turkish_lower(window_2)
            s_start = float(active_segments[i].get("start", 0.0))

            matched_term = False
            for kw_tuple, start_hint, end_hint, display_term in SHORT_CONCEPT_TERMS:
                if any(k in lower_cur for k in kw_tuple) or (
                    any(k in lower_win2 for k in kw_tuple)
                    and not any(k in to_turkish_lower(text_next) for k in kw_tuple)
                ):
                    if s_start - seen_terms.get(display_term, -999.0) < 120.0:
                        continue
                    start_tok = self._find_word_in_range(word_stream, i, min(n_segs - 1, i + 1), start_hint)
                    ev_start = round(start_tok.start if start_tok else s_start, 2)
                    if start_tok:
                        end_tok = self._find_sentence_end_word(
                            word_stream, start_tok, min(n_segs - 1, start_tok.seg_idx + 1), end_hint
                        )
                        ev_end = round(max(ev_start + 0.9, min(ev_start + 3.4, end_tok.end)), 2)
                    else:
                        ev_end = round(min(video_duration - 0.2, ev_start + 2.2), 2)

                    if not is_range_busy(ev_start, ev_end):
                        seen_terms[display_term] = s_start
                        act_type = (
                            "ENUMERATION_CALLOUT"
                            if any(
                                o in lower_win2
                                for o in ("birincisi", "ikincisi", "üçüncüsü", "dördüncüsü")
                            )
                            else "DEFINITION_CALLOUT"
                        )
                        triggers.append(
                            PlannedEditorialEvent(
                                event_id=f"trig_term_{len(triggers) + 1:02d}",
                                chapter_id=0,
                                action_type=act_type,
                                start_sec=ev_start,
                                end_sec=ev_end,
                                text_primary=display_term,
                                text_secondary="Kavram Vurgusu",
                                semantic_priority=True,
                            )
                        )
                        occupied_ranges.append((ev_start, ev_end))
                        matched_term = True
                        break

            # Genel "Birincisi X, İkincisi Y" ve "... delili / ... ilkesi / ... kanunu" yakalayıcı
            if not matched_term:
                gen_ev = self._extract_generic_word_synced_term(
                    i, active_segments, word_stream, seen_terms, is_range_busy
                )
                if gen_ev:
                    triggers.append(gen_ev)
                    occupied_ranges.append((gen_ev.start_sec, gen_ev.end_sec))

        # Kronolojik sırala ve bir sonraki tekil olay başlamadan hemen önce bitişleri kırp
        triggers.sort(key=lambda e: (e.start_sec, e.stack_slot if e.stack_slot is not None else -1))
        for idx in range(len(triggers) - 1):
            cur_ev = triggers[idx]
            nxt_ev = triggers[idx + 1]
            # Aynı grup içindeki (PROGRESSIVE_LIST veya PAIRED_TERMS) öğeler birlikte ekranda kalır!
            if cur_ev.group_id and cur_ev.group_id == nxt_ev.group_id:
                continue
            # Farklı bir grup veya yeni bir kavram başlıyorsa, önceki kavram yeni kelime başlamadan 0.08s önce silinir!
            if cur_ev.end_sec > nxt_ev.start_sec - 0.08:
                cur_ev.end_sec = round(max(cur_ev.start_sec + 0.55, nxt_ev.start_sec - 0.08), 2)

        return triggers

    def _detect_generic_comma_lists(
        self,
        active_segments: List[Dict[str, Any]],
        word_stream: List[WordToken],
        triggers: List[PlannedEditorialEvent],
        occupied_ranges: List[Tuple[float, float]],
        is_range_busy: Any,
    ) -> None:
        """
        Önceden tanımlı kurallarda olmasa bile herhangi bir videoda konuşmacının
        virgüllerle ardışık saydığı (ör. "A, B, C ve D") 3+ maddelik kelime dizilerini
        otomatik olarak yakalayıp kelime-senkronlu PROGRESSIVE_LIST'e dönüştürür.
        """
        n_tokens = len(word_stream)
        idx = 0
        while idx < n_tokens - 3:
            tok = word_stream[idx]
            if tok.has_comma and len(tok.clean) >= 3:
                chain: List[WordToken] = [tok]
                cur = idx + 1
                while cur < n_tokens and len(chain) < 7:
                    nxt = word_stream[cur]
                    if nxt.has_comma and len(nxt.clean) >= 3:
                        chain.append(nxt)
                        cur += 1
                    elif nxt.lower in ("ve", "ile", "yahut", "veya") and cur + 1 < n_tokens:
                        after_ve = word_stream[cur + 1]
                        if len(after_ve.clean) >= 3:
                            chain.append(after_ve)
                        cur += 2
                        break
                    else:
                        if len(chain) >= 2 and len(nxt.clean) >= 3 and not nxt.has_sentence_end:
                            chain.append(nxt)
                            cur += 1
                        break

                if len(chain) >= 3:
                    end_tok = self._find_sentence_end_word(
                        word_stream, chain[-1], min(len(active_segments) - 1, chain[-1].seg_idx + 1)
                    )
                    shared_end = round(max(chain[-1].end + 0.35, end_tok.end), 2)
                    if not is_range_busy(chain[0].start, shared_end):
                        grp_id = f"grp_auto_list_{chain[0].idx}"
                        for slot_idx, c_tok in enumerate(chain):
                            label = to_turkish_upper(c_tok.clean)
                            triggers.append(
                                PlannedEditorialEvent(
                                    event_id=f"{grp_id}_{slot_idx + 1}",
                                    chapter_id=0,
                                    action_type="PROGRESSIVE_LIST",
                                    start_sec=round(c_tok.start, 2),
                                    end_sec=shared_end,
                                    text_primary=label,
                                    text_secondary=f"Sıralama {slot_idx + 1}",
                                    semantic_priority=True,
                                    group_id=grp_id,
                                    stack_slot=slot_idx,
                                )
                            )
                        occupied_ranges.append((chain[0].start, shared_end))
                        idx = cur
                        continue
            idx += 1

    def _extract_generic_word_synced_term(
        self,
        seg_idx: int,
        active_segments: List[Dict[str, Any]],
        word_stream: List[WordToken],
        seen_terms: Dict[str, float],
        is_range_busy: Any,
    ) -> Optional[PlannedEditorialEvent]:
        text_cur = str(active_segments[seg_idx].get("text", "")).strip()
        text_next = (
            str(active_segments[seg_idx + 1].get("text", "")).strip()
            if seg_idx + 1 < len(active_segments)
            else ""
        )
        window_2 = f"{text_cur} {text_next}".strip()
        s_start = float(active_segments[seg_idx].get("start", 0.0))

        # 1. Genel "Birincisi X / İkincisi Y / Üçüncüsü Z"
        m_ord = re.search(
            r"\b(birincisi|ikincisi|üçüncüsü|dördüncüsü|beşincisi)\s+(?:ise\s+|yani\s+)?([A-ZÇĞİÖŞÜa-zçğıöşüâîû'\-]{3,18}(?:\s+[A-ZÇĞİÖŞÜa-zçğıöşüâîû'\-]{3,18})?)",
            window_2,
            flags=re.IGNORECASE,
        )
        if m_ord and m_ord.start() < len(text_cur):
            concept_raw = m_ord.group(2).strip()
            title = extract_turkish_semantic_title(concept_raw, max_chars=24)
            if title and len(title) >= 3 and s_start - seen_terms.get(title, -999.0) >= 90.0:
                first_w = concept_raw.split()[0]
                tok = self._find_word_in_range(word_stream, seg_idx, min(len(active_segments) - 1, seg_idx + 1), first_w)
                ev_st = round(tok.start if tok else s_start, 2)
                end_tok = self._find_sentence_end_word(word_stream, tok, min(len(active_segments) - 1, seg_idx + 1)) if tok else None
                ev_en = round(max(ev_st + 0.9, min(ev_st + 3.0, end_tok.end if end_tok else ev_st + 2.0)), 2)
                if not is_range_busy(ev_st, ev_en):
                    seen_terms[title] = s_start
                    return PlannedEditorialEvent(
                        event_id=f"trig_ord_{seg_idx}",
                        chapter_id=0,
                        action_type="ENUMERATION_CALLOUT",
                        start_sec=ev_st,
                        end_sec=ev_en,
                        text_primary=title,
                        text_secondary="Sıralama Vurgusu",
                        semantic_priority=True,
                    )

        # 2. Genel "... delili / ... ilkesi / ... teorisi / ... kanunu"
        m_def = re.search(
            r"\b([A-ZÇĞİÖŞÜa-zçğıöşüâîû'\-]{3,16}\s+(?:delili|ilkesi|teorisi|doktrini|paradoksu))\b",
            window_2,
            flags=re.IGNORECASE,
        )
        if m_def and m_def.start() < len(text_cur):
            raw_phrase = m_def.group(1).strip()
            lower_p = to_turkish_lower(raw_phrase)
            bad_starts = ("bu ", "şu ", "o ", "bir ", "her ", "hangi ", "aynı ", "böyle ", "diğer ")
            if not any(lower_p.startswith(bs) for bs in bad_starts):
                title = extract_turkish_semantic_title(raw_phrase, max_chars=24)
                if title and s_start - seen_terms.get(title, -999.0) >= 120.0:
                    first_w = raw_phrase.split()[0]
                    tok = self._find_word_in_range(word_stream, seg_idx, min(len(active_segments) - 1, seg_idx + 1), first_w)
                    ev_st = round(tok.start if tok else s_start, 2)
                    end_tok = self._find_sentence_end_word(word_stream, tok, min(len(active_segments) - 1, seg_idx + 1)) if tok else None
                    ev_en = round(max(ev_st + 0.9, min(ev_st + 3.2, end_tok.end if end_tok else ev_st + 2.2)), 2)
                    if not is_range_busy(ev_st, ev_en):
                        seen_terms[title] = s_start
                        return PlannedEditorialEvent(
                            event_id=f"trig_def_{seg_idx}",
                            chapter_id=0,
                            action_type="DEFINITION_CALLOUT",
                            start_sec=ev_st,
                            end_sec=ev_en,
                            text_primary=title,
                            text_secondary="Tanım Vurgusu",
                            semantic_priority=True,
                        )
        return None

    def _find_natural_chapter_boundaries(
        self,
        active_segments: List[Dict[str, Any]],
        video_duration: float,
        num_chapters: int,
    ) -> List[float]:
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
    ) -> ChapterPlan:
        """
        Her bölüm için:
          - Varsa kelime-senkronlu Semantik Tetikleyicileri (PROGRESSIVE_LIST, PAIRED_TERMS,
            PERSON_INTRODUCTION, WORK_INTRODUCTION, SINGLE_TERM/DEFINITION) doğrudan korur.
          - Rastgele cümlelerden anlamsız kelimeler kesen eski dolgu (filler) döngüsünü ASLA çalıştırmaz;
            yalnızca bölümde hiç tetikleyici yoksa (test/kısa videolar için) en yüksek semantik skorlu
            1-2 kısa terimi kelime sınırlarına kilitleyerek ekler.
        """
        chapter_triggers = list(chapter_triggers or [])
        events: List[PlannedEditorialEvent] = []

        for idx, trig in enumerate(chapter_triggers):
            trig.chapter_id = chapter_id
            if not trig.event_id:
                trig.event_id = f"evt_ch{chapter_id}_{idx + 1:02d}"
            events.append(trig)

        # Eğer bölümde hiç semantik tetikleyici yakalanmadıysa (ör. sentetik birim testleri),
        # yalnızca o bölümdeki 2 segmentten kısa terim çıkar
        if not events and ch_segments:
            word_stream = self._build_word_stream(ch_segments)
            step = max(1, len(ch_segments) // 2)
            for idx_s in range(0, len(ch_segments), step):
                if len(events) >= 2:
                    break
                seg = ch_segments[idx_s]
                s_text = str(seg.get("text", "")).strip()
                short_title = extract_turkish_semantic_title(s_text, max_chars=22)
                if short_title:
                    seg_toks = [t for t in word_stream if t.seg_idx == idx_s]
                    st_sec = seg_toks[0].start if seg_toks else float(seg.get("start", ch_start))
                    en_sec = seg_toks[-1].end if seg_toks else min(ch_end, st_sec + 2.2)
                    events.append(
                        PlannedEditorialEvent(
                            event_id=f"evt_ch{chapter_id}_fallback_{idx_s + 1}",
                            chapter_id=chapter_id,
                            action_type="KEY_TERM_CALLOUT",
                            start_sec=round(st_sec, 2),
                            end_sec=round(max(st_sec + 0.8, en_sec), 2),
                            text_primary=short_title,
                            text_secondary=f"Bölüm {chapter_id}",
                            semantic_priority=True,
                        )
                    )

        events.sort(key=lambda e: (e.start_sec, e.stack_slot if e.stack_slot is not None else -1))
        chapter_title = events[0].text_primary if events else f"BÖLÜM {chapter_id}"
        return ChapterPlan(
            chapter_id=chapter_id,
            start_sec=round(ch_start, 2),
            end_sec=round(ch_end, 2),
            title_tr=chapter_title,
            key_terms=[e.text_primary for e in events],
            events=events,
        )

    @staticmethod
    def _normalize_cuts(cuts: List[Any]) -> List[Tuple[float, float]]:
        result = []
        for c in cuts:
            if isinstance(c, dict):
                st = float(c.get("start", c.get("Start", 0)))
                en = float(c.get("end", c.get("End", 0)))
                is_del = c.get("isDeleted", c.get("IsDeleted", True))
                if is_del and en > st:
                    result.append((st, en))
            elif hasattr(c, "start") and hasattr(c, "end"):
                if getattr(c, "isDeleted", True) and float(c.end) > float(c.start):
                    result.append((float(c.start), float(c.end)))
        return sorted(result, key=lambda x: x[0])

    @staticmethod
    def _filter_active_segments(
        segments: List[Dict[str, Any]], cuts: List[Tuple[float, float]]
    ) -> List[Dict[str, Any]]:
        active = []
        for s in segments:
            st = float(s.get("start", 0))
            en = float(s.get("end", st + 2.0))
            txt = str(s.get("text", "")).strip()
            if not txt:
                continue
            mid = (st + en) / 2.0
            if any(c_st <= mid <= c_en for c_st, c_en in cuts):
                continue
            active.append(s)
        return active
