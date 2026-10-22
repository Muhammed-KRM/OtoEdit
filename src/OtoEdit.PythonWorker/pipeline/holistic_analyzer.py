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

# Hangi analiz motorunun çalıştığını loglardan doğrulamak için sürüm etiketi
ENGINE_VERSION = "holistic-v2.1-verbatim-lock+asr-glossary+sync-audit"


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


@dataclass
class SemanticTransitionBoundary:
    timestamp: float
    sentence_a_end: float
    sentence_b_start: float
    sentence_a_last_word: str
    sentence_b_first_word: str
    category: str  # "RETROSPECTIVE_CLOSURE_TO_NEW_TOPIC" | "PRE_EXPLANATION_PIVOT" | "RHETORICAL_QUESTION_TO_THESIS"
    priority_score: float
    reason: str


TR_ABBREVIATIONS = {"prof", "dr", "doç", "hz", "av", "md", "bkz", "vb", "vs", "yy", "st", "mr"}


class SemanticTransitionBoundaryDetector:
    """
    Kelime akışı (WordToken[]) üzerinden gerçek cümle birimlerini (SentenceUnit) inşa eder ve:
      1. RETROSPECTIVE_CLOSURE_TO_NEW_TOPIC (Özet/Konu Bitimi -> Yeni Konuya Giriş)
      2. PRE_EXPLANATION_PIVOT (Köprü/Hazırlık Cümlesi Bitimi -> Derin Kavram Açıklamasına Giriş)
      3. RHETORICAL_QUESTION_TO_THESIS (Retorik Soru Bitimi -> Tez/Cevap Girişi)
    sınırlarını milisaniye hassasiyetle tespit eder.
    """

    RETROSPECTIVE_END_RE = re.compile(
        r"\b(incelemiştik|tahlil etmiştik|ele almıştık|görmüştük|değinmiştik|konuşmuştuk|"
        r"özetlemiştik|tamamladık|geride bıraktık|[a-zçğıöşüâîû]+(?:miştik|mıştık|muştuk|müştük)|"
        r"sıralanır|zorunlu kıldığını haykırır|zorunlu kıldığını aykırır|"
        r"cisme bürünmüş ayetleridir|boğulmaya mahkumdur|kalemi şahididir|kelami şahididir|"
        r"en büyük adaletsizliktir)\s*[.!]?$",
        re.IGNORECASE,
    )

    NEW_TOPIC_START_RE = re.compile(
        r"^(işte bugün|bugün ise|şimdi ise|bu buluşmamızda|bu bölümde|bu dersimizde|"
        r"bir sonraki bölümde|bir sonraki bölümümüzde|normal hiyerarşisinden|normlar hiyerarşisinden|"
        r"cumhuriyet dönemine geldiğimizde|tarihsel süreçte|vahyin bu evrensel|"
        r"hukuk metodolojisinde bir hakimin|peki adli koridorlarında|peki tabiatta bu kusursuz)",
        re.IGNORECASE,
    )

    PRE_EXPLANATION_END_RE = re.compile(
        r"\b(çevirmek zorundayız|bakmamız gerekir|bakmak zorundayız|incelememiz gerekir|"
        r"yolculuğumuza başlıyoruz|başlıyoruz|dikkat buyurunuz|benzerliğe bakın|"
        r"ilkesiyle karşılaşırız|kanunlar manzumesi vardır|tefsir,?\s*tas[dt]ik ve teyit eder|"
        r"derlemeler yapmıştır|bir uygulayıcıya muhtaçtır|tas\s*tamam odur|"
        r"emsalsiz ahlakıdır|prof\.?\s*hans\s*kün[gk]['’]?dür)\s*[.!:;]?$",
        re.IGNORECASE,
    )

    ANTI_TRANSITION_START_PREFIXES = (
        "ve bu ", "yani ", "çünkü kainat", "zira ", "fakat ", "lakin ", "böylece ", "dolayısıyla ",
    )

    THESIS_ANSWER_START_RE = re.compile(
        r"^(hazırsanız|kanunun bir lafzı|bediüzzaman|hakim önüne gelen)",
        re.IGNORECASE,
    )

    @classmethod
    def build_clean_sentences(cls, word_stream: List[WordToken]) -> List[List[WordToken]]:
        raw_sents: List[List[WordToken]] = []
        cur: List[WordToken] = []
        n = len(word_stream)
        for i, w in enumerate(word_stream):
            cur.append(w)
            raw_s = w.raw.strip().rstrip("\"'”’)")
            ends_punct = raw_s.endswith((".", "?", "!", ":", ";"))
            is_abbr = (w.lower in TR_ABBREVIATIONS) or w.clean.isdigit()
            nxt = word_stream[i + 1] if i + 1 < n else None
            nxt_starts_lower = bool(nxt and nxt.clean and nxt.clean[0].islower())
            if ends_punct and not is_abbr and not nxt_starts_lower:
                raw_sents.append(cur)
                cur = []
        if cur:
            raw_sents.append(cur)

        # Eksik yüklemli veya ek-fiil devamlı alt-parçaları birleştir
        merged: List[List[WordToken]] = []
        idx = 0
        while idx < len(raw_sents):
            s = list(raw_sents[idx])
            txt_low = to_turkish_lower(" ".join(w.raw for w in s))
            while idx + 1 < len(raw_sents):
                nxt_s = raw_sents[idx + 1]
                nxt_low = to_turkish_lower(" ".join(w.raw for w in nxt_s))
                if (
                    txt_low.endswith("bir diğer kaynağı.")
                    or (len(nxt_s) <= 3 and nxt_low in ("icra edicisidir.", "nübüvvettir.", "tas tamam odur.", "yani akli şeriattır."))
                    or (txt_low.endswith("ismet sıfatı.") and nxt_low.startswith("yani "))
                ):
                    s.extend(nxt_s)
                    idx += 1
                    txt_low = to_turkish_lower(" ".join(w.raw for w in s))
                else:
                    break
            merged.append(s)
            idx += 1
        return merged

    @classmethod
    def detect_boundaries(
        cls,
        word_stream: List[WordToken],
        video_duration: float,
        min_gap_sec: float = 22.0,
    ) -> List[SemanticTransitionBoundary]:
        sents = cls.build_clean_sentences(word_stream)
        candidates: List[SemanticTransitionBoundary] = []

        for i in range(len(sents) - 1):
            sa = sents[i]
            sb = sents[i + 1]
            ta = " ".join(w.raw for w in sa).strip()
            tb = " ".join(w.raw for w in sb).strip()
            la = to_turkish_lower(ta).rstrip(".!?:; ")
            lb = to_turkish_lower(tb).lstrip()

            t_end = sa[-1].end
            t_start = sb[0].start
            t_mid = round((t_end + t_start) / 2.0, 2)
            if t_mid < 5.0 or t_mid > video_duration - 8.0:
                continue
            if lb.startswith(cls.ANTI_TRANSITION_START_PREFIXES):
                continue

            cat = None
            score = 0.0
            reason = ""

            # Kategori 1: RETROSPECTIVE_CLOSURE_TO_NEW_TOPIC
            if cls.RETROSPECTIVE_END_RE.search(la) and cls.NEW_TOPIC_START_RE.search(lb):
                cat = "RETROSPECTIVE_CLOSURE_TO_NEW_TOPIC"
                score = 100.0 if ("miştik" in la or "mıştık" in la) else 88.0
                reason = "Konu/özet kapanış yüklemi + yeni konu/perspektif başlatıcı söylem işareti"

            # Kategori 2: PRE_EXPLANATION_PIVOT
            elif cls.PRE_EXPLANATION_END_RE.search(la):
                cat = "PRE_EXPLANATION_PIVOT"
                tail_stems = {w.lower[:5] for w in sa[-7:] if len(w.lower) >= 5}
                head_stems = {w.lower[:5] for w in sb[:5] if len(w.lower) >= 5}
                has_echo = bool(tail_stems & head_stems)
                score = 98.0 if has_echo else 92.0
                reason = "Kataforik hazırlık/köprü cümlesi bitimi -> Derin kavram/madde açıklamasına giriş"

            # Kategori 3: RHETORICAL_QUESTION_TO_THESIS
            elif ta.endswith("?") and not tb.endswith("?") and cls.THESIS_ANSWER_START_RE.search(lb):
                cat = "RHETORICAL_QUESTION_TO_THESIS"
                score = 90.0
                reason = "Retorik çerçeveleme sorusu bitimi (?) -> Tez/cevap açıklamasına giriş"

            if cat:
                candidates.append(
                    SemanticTransitionBoundary(
                        timestamp=t_mid,
                        sentence_a_end=t_end,
                        sentence_b_start=t_start,
                        sentence_a_last_word=sa[-1].raw,
                        sentence_b_first_word=sb[0].raw,
                        category=cat,
                        priority_score=score,
                        reason=reason,
                    )
                )

        # Local Non-Maximum Suppression (Yakın adaylardan yüksek öncelikli/açıklama girişi olanı seç)
        selected: List[SemanticTransitionBoundary] = []
        for cand in candidates:
            if selected and (cand.timestamp - selected[-1].timestamp) < min_gap_sec:
                if cand.priority_score >= selected[-1].priority_score:
                    selected[-1] = cand
            else:
                selected.append(cand)

        return selected


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
    (("said nursi", "bediüzzaman", "beniz zaman"), "BEDİÜZZAMAN SAİD NURSİ", "Said Nursi", "Said Nursi"),
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
    (("lemeat adlı", "lemeât adlı", "lemeat"), "LEMEÂT", "Risale-i Nur", "Risale-i Nur"),
    (("risale-i nur",), "RİSALE-İ NUR KÜLLİYATI", "Risale-i Nur", "Risale-i Nur"),
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
    (("türk medeni kanunu'nun birinci",), "türk", "maddesi", "TÜRK MEDENİ KANUNU 1. MADDE"),
    (("adalet-i mahza",), "adalet-i", "mahza", "ADALET-İ MAHZA"),
    (("üç büyük şeriat",), "üç", "şeriat", "ÜÇ BÜYÜK ŞERİAT"),
    (("birincisi tenzili", "teşri şeriatdır"), "tenzili", "şeriatdır", "TENZİLÎ ŞERİAT"),
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
    ("eserlerden müessire", [("eserlerden", "ESERDEN MÜESSİRE"), ("sebepten", "SEBEPTEN ESERE")], "inen"),
    ("amiriyet ve hakimiyet", [("amiriyet", "AMİRİYET"), ("hakimiyet", "HAKİMİYET")], "ortaklık"),
    ("kanunun bir lafzı", [("lafzı", "KANUNUN LAFZI"), ("ruhu", "KANUNUN RUHU")], "vardır"),
    ("kalem sıfatının kelimeleridir", [("kalem", "KALEM SIFATI"), ("kudret", "KUDRET SIFATI")], "ayetleridir"),
    ("sübjektif ve objektif iradesini", [("sübjektif", "SÜBJEKTİF İRADE"), ("objektif", "OBJEKTİF İRADE")], "gayesini"),
    ("kanunu bilip kanun koyucuğu", [("kanunu", "KANUN"), ("koyucuğu", "KANUN KOYUCU")], "tanımamak"),
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
            ("tabiat", "TABİAT"),
        ],
        "olabilir",
    ),
    (
        "piramidin en tepesinde",
        [
            ("uluslararası", "ULUSLARARASI SÖZLEŞMELER"),
            ("anayasa", "ANAYASA"),
            ("kanunlar", "KANUNLAR"),
            ("yönetmelik", "YÖNETMELİKLER"),
            ("yargıtay", "YARGITAY İÇTİHATLARI"),
        ],
        "sıralanır",
    ),
    (
        "idare hukukumuzu fransa",
        [
            ("idare", "İDARE HUKUKU"),
            ("yargılama", "YARGILAMA USULÜ"),
            ("medeni", "MEDENİ HUKUK"),
            ("ceza", "CEZA HUKUKU"),
            ("ticaret", "TİCARET HUKUKU"),
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
            ("koyucu", "3. KANUN KOYUCU KURALI"),
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
            ("yahudilerin", "YAHUDİLER"),
            ("hristiyanların", "HRİSTİYANLAR"),
            ("müslümanların", "MÜSLÜMANLAR"),
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
            ("inayet", "İNAYET"),
            ("hudus", "HUDÛS"),
            ("imkan", "İMKÂN"),
            ("iştira", "İHTİRA"),
            ("temanü", "TEMÂNÜ"),
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


class VerbatimTranscriptValidator:
    """
    Katman 3: Üretilen her PlannedEditorialEvent.text_primary etiketini, [start_sec, end_sec]
    zaman aralığındaki gerçek konuşulan kelimelerle (WordToken[]) karşılaştırır.
    Konuşmacının ağzından çıkmayan kelimelerin (örn. 'esere' yerine 'SONUCA',
    'Lemeât' yerine 'RİSALE-İ NUR KÜLLİYATI') ekrana yazılmasına izin vermez!
    """

    ALLOWED_SYNTHETIC_TOKENS = {
        "1.", "2.", "3.", "4.", "5.", "PROF.", "DR.", "DOÇ.", "HZ.", "İMAM", "İMAM-I", "MADDE"
    }

    @classmethod
    def normalize_root(cls, word: str) -> str:
        w = to_turkish_lower(word.strip())
        w = re.sub(r"[^\wçğıöşüâîû]", "", w)
        return w.replace("â", "a").replace("î", "i").replace("û", "u")

    @classmethod
    def word_matches_spoken_tokens(cls, label_word: str, spoken_norms: List[str]) -> bool:
        up = to_turkish_upper(label_word.strip(",.;:!?()"))
        if up in cls.ALLOWED_SYNTHETIC_TOKENS or up.rstrip(".").isdigit():
            return True
        lw = cls.normalize_root(label_word)
        if not lw:
            return True
        if len(lw) <= 2:
            return lw in spoken_norms

        prefix_len = min(len(lw), max(3, len(lw) - 3))
        lw_pref = lw[:prefix_len]
        soft_variants = {lw_pref}
        if lw_pref.endswith("p"):
            soft_variants.add(lw_pref[:-1] + "b")
        elif lw_pref.endswith("ç"):
            soft_variants.add(lw_pref[:-1] + "c")
        elif lw_pref.endswith("t"):
            soft_variants.add(lw_pref[:-1] + "d")
        elif lw_pref.endswith("k"):
            soft_variants.add(lw_pref[:-1] + "ğ")

        import difflib

        for idx_sp, sp in enumerate(spoken_norms):
            if not sp:
                continue
            if sp == lw or sp.startswith(lw) or lw.startswith(sp):
                return True
            if any(sp.startswith(sv) or sv.startswith(sp[: max(3, len(sp) - 2)]) for sv in soft_variants):
                return True
            # ASR fonetik yazım hatalarını ("hiyerarşisi" <-> "yararçisiyle", "şeriyye" <-> "şehriye") koru
            if len(lw) >= 4 and len(sp) >= 4:
                if difflib.SequenceMatcher(None, lw, sp).ratio() >= 0.48:
                    return True
            # İki kelimelik ASR bölünmelerini ("içtihatları" <-> "içli" + "hatları") koru
            if idx_sp + 1 < len(spoken_norms):
                joined_sp = sp + spoken_norms[idx_sp + 1]
                if difflib.SequenceMatcher(None, lw, joined_sp).ratio() >= 0.55:
                    return True
        return False

    @classmethod
    def enforce_verbatim_fidelity(
        cls,
        events: List[PlannedEditorialEvent],
        word_stream: List[WordToken],
    ) -> List[PlannedEditorialEvent]:
        import difflib

        if not events or not word_stream:
            return events

        for evt in events:
            # Kişi tanıtımlarında tam tarihsel unvan/isim korunur (ASR bozuk telaffuzlarını düzeltmek için)
            if evt.action_type == "PERSON_INTRODUCTION":
                continue

            window_tokens = [
                t for t in word_stream
                if (evt.start_sec - 1.5) <= t.start <= (evt.end_sec + 1.8)
            ]
            if not window_tokens:
                continue

            spoken_norms = [cls.normalize_root(t.clean) for t in window_tokens if t.clean]
            raw_label = evt.text_primary.strip()

            # Parantez içi konuşulmayan eklemeleri temizle (ör. "(FRANSA)", "(KUR'AN)")
            if "(" in raw_label and ")" in raw_label:
                inner_m = re.search(r"\(([^)]+)\)", raw_label)
                if inner_m:
                    inner_words = inner_m.group(1).split()
                    if not all(cls.word_matches_spoken_tokens(iw, spoken_norms) for iw in inner_words):
                        raw_label = re.sub(r"\s*\([^)]+\)", "", raw_label).strip()
                        evt.text_primary = raw_label

            # Eser tanıtımlarında eğer 'mecelle' konuşulduysa tam kanun adı korunabilir;
            # ancak konuşmacı 'lemeat' dediğinde 'RİSALE-İ NUR' yazılmışsa anında 'LEMEÂT' olarak onar!
            if evt.action_type == "WORK_INTRODUCTION":
                if "mecelle" in spoken_norms and "MECELLE" in raw_label:
                    continue
                if not any(cls.word_matches_spoken_tokens(w, spoken_norms) for w in raw_label.split()):
                    anchor = min(window_tokens, key=lambda t: abs(t.start - evt.start_sec))
                    repaired_work = to_turkish_upper(anchor.clean)
                    if len(repaired_work) >= 3:
                        logger.warning(
                            f"[VerbatimValidator] Eser adı konuşulan kelimeye kilitlendi: "
                            f"'{evt.text_primary}' -> '{repaired_work}'"
                        )
                        evt.text_primary = repaired_work
                        evt.primary_web_query_tr = anchor.clean
                        evt.person_wiki_tr = anchor.clean
                continue

            label_words = [w for w in raw_label.split() if w]
            unspoken_indices = [
                idx for idx, lw in enumerate(label_words)
                if not cls.word_matches_spoken_tokens(lw, spoken_norms)
            ]
            if not unspoken_indices:
                continue

            anchor_tok = min(window_tokens, key=lambda t: abs(t.start - evt.start_sec))

            # İkili veya 2 kelimeli ifadede 1. kelime konuşulmuş ama 2. kelime uydurulmuşsa
            # (Örn: Konuşmacı 'sebepten esere' dedi ama etikette 'SEBEPTEN SONUCA' yazıyor!)
            if len(label_words) == 2 and 0 not in unspoken_indices and 1 in unspoken_indices:
                if anchor_tok.idx + 1 < len(word_stream):
                    nxt_tok = word_stream[anchor_tok.idx + 1]
                    lw2_norm = cls.normalize_root(label_words[1])
                    nxt_norm = cls.normalize_root(nxt_tok.clean)
                    # Yalnızca gerçekten farklı bir kelime uydurulmuşsa (fonetik benzerlik < 0.45)
                    # ve sonraki kelime anlamlı bir isim/yönelme eki taşıyorsa onar
                    if (
                        len(nxt_norm) >= 3
                        and difflib.SequenceMatcher(None, lw2_norm, nxt_norm).ratio() < 0.45
                        and nxt_norm not in {"bir", "iki", "üç", "ile", "için", "gibi", "olan", "arar", "eder", "olur"}
                    ):
                        repaired = f"{label_words[0]} {to_turkish_upper(nxt_tok.clean)}"
                        logger.warning(
                            f"[VerbatimValidator] Transkript dışı kelime onarıldı: "
                            f"'{evt.text_primary}' -> '{repaired}'"
                        )
                        evt.text_primary = repaired
                continue

        return events


# ----------------------------------------------------------------------------
# ASR (Whisper) yazım hatalarına dayanıklı sözlük eşleştirme
# ----------------------------------------------------------------------------
_ASR_PUNCT_RE = re.compile(r"^([^\wçğıöşüâîûÇĞİÖŞÜÂÎÛ]*)(.*?)([^\wçğıöşüâîûÇĞİÖŞÜÂÎÛ'’-]*)$", re.UNICODE)


def _asr_norm(word: str) -> str:
    return VerbatimTranscriptValidator.normalize_root(word)


def _build_asr_glossary() -> List[List[str]]:
    """Sözlüklerdeki tetikleyici ifadelerden ASR düzeltmesinde kullanılacak güvenli öbek listesi."""
    phrases: Set[str] = set()

    def add(p: str) -> None:
        p = to_turkish_lower(p.strip())
        if not p:
            return
        words = p.split()
        # Yanlış pozitifleri önlemek için: çok kelimeli öbekler veya en az 7 harfli tek kelimeler
        if len(words) >= 2 or (len(words) == 1 and len(_asr_norm(words[0])) >= 7):
            phrases.add(p)

    for kw_tuple, *_rest in SHORT_CONCEPT_TERMS:
        for k in kw_tuple:
            add(k)
    for kw_tuple, *_rest in KNOWN_PERSONS_WIKI_MAP:
        for k in kw_tuple:
            add(k)
    for kw_tuple, *_rest in KNOWN_WORKS_WIKI_MAP:
        for k in kw_tuple:
            add(k)
    return [p.split() for p in sorted(phrases, key=lambda s: -len(s))]


def canonicalize_asr_variants(segments: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], int]:
    """
    Whisper'ın terimleri fonetik olarak yanlış yazdığı yerleri ('kudus delili' -> 'hudus delili',
    'imkam delili' -> 'imkan delili') analiz için sözlükteki doğru yazıma çevirir.
    Kelime zaman damgaları DEĞİŞMEZ; yalnızca analizcinin kendi kopyasındaki metin düzeltilir
    (editördeki altyazı/transkript etkilenmez).
    """
    import copy
    import difflib

    glossary = _build_asr_glossary()
    out = copy.deepcopy(segments)
    fixes = 0
    for seg in out:
        words = seg.get("words") or []
        if not words:
            continue
        norms = [_asr_norm(str(w.get("word", ""))) for w in words]
        i = 0
        while i < len(words):
            matched = False
            for phrase in glossary:
                m = len(phrase)
                if i + m > len(words):
                    continue
                window = norms[i : i + m]
                if any(not w for w in window):
                    continue
                phrase_norm = [_asr_norm(p) for p in phrase]
                if window == phrase_norm:
                    continue
                joined_w = " ".join(window)
                joined_p = " ".join(phrase_norm)
                ratio = difflib.SequenceMatcher(None, joined_w, joined_p).ratio()
                if m >= 2:
                    exact_words = sum(1 for a, b in zip(window, phrase_norm) if a == b)
                    ok = ratio >= 0.86 and exact_words >= 1 and abs(len(joined_w) - len(joined_p)) <= 2
                else:
                    ok = ratio >= 0.88 and abs(len(joined_w) - len(joined_p)) <= 1
                if not ok:
                    continue
                for k in range(m):
                    w_obj = words[i + k]
                    raw = str(w_obj.get("word", ""))
                    pm = _ASR_PUNCT_RE.match(raw.strip())
                    lead, trail = (pm.group(1), pm.group(3)) if pm else ("", "")
                    w_obj["word"] = f"{lead}{phrase[k]}{trail}"
                    norms[i + k] = phrase_norm[k]
                logger.info(f"[ASR-Glossary] '{joined_w}' -> '{' '.join(phrase)}' @ {float(words[i].get('start', 0)):.2f}s")
                fixes += 1
                i += m
                matched = True
                break
            if not matched:
                i += 1
        seg["text"] = " ".join(str(w.get("word", "")).strip() for w in words).strip()
    return out, fixes


def audit_overlay_sync(
    overlays: List[Dict[str, Any]],
    segments: List[Dict[str, Any]],
    lead_tolerance: float = 1.2,
    lag_tolerance: float = 2.5,
) -> Dict[str, Any]:
    """
    Her otomatik yazının, aynı projenin transkriptinde etiket kelimelerinden birinin konuşulduğu
    ana yakın başladığını doğrular. Farklı bir videonun transkriptiyle üretilmiş veya kaymış
    planlar burada 'mismatch' olarak yakalanır.
    """
    import difflib

    spoken: List[Tuple[float, str]] = []
    for seg in segments or []:
        words = seg.get("words") or []
        if words:
            for w in words:
                spoken.append((float(w.get("start", seg.get("start", 0.0))), _asr_norm(str(w.get("word", "")))))
        else:
            parts = str(seg.get("text", "")).split()
            s0 = float(seg.get("start", 0.0))
            s1 = max(s0 + 0.2, float(seg.get("end", s0 + 2.0)))
            step = (s1 - s0) / max(1, len(parts))
            for k, p in enumerate(parts):
                spoken.append((s0 + k * step, _asr_norm(p)))
    spoken.sort(key=lambda x: x[0])

    def word_spoken_near(label_word: str, ts: float) -> bool:
        lw = _asr_norm(label_word)
        if len(lw) < 2:
            return False
        for st, sp in spoken:
            if st < ts - lead_tolerance:
                continue
            if st > ts + lag_tolerance:
                break
            if not sp:
                continue
            if sp == lw or sp.startswith(lw[:4]) or (len(sp) >= 4 and lw.startswith(sp[:4])):
                return True
            if len(lw) >= 4 and difflib.SequenceMatcher(None, lw, sp).ratio() >= 0.8:
                return True
        return False

    checked = 0
    mismatches: List[Dict[str, Any]] = []
    for ov in overlays or []:
        if not isinstance(ov, dict) or ov.get("type") != "text":
            continue
        content = str(ov.get("content") or ov.get("text") or "").strip()
        if not content:
            continue
        try:
            ts = float(ov.get("timestamp", ov.get("start", 0.0)))
        except (TypeError, ValueError):
            continue
        label_words = [w for w in re.split(r"[\s\-/]+", content) if len(_asr_norm(w)) >= 2]
        if not label_words:
            continue
        checked += 1
        if not any(word_spoken_near(w, ts) for w in label_words):
            mismatches.append({"timestamp": round(ts, 2), "content": content})
    return {"checked": checked, "mismatches": mismatches}

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
        # Whisper'ın fonetik yazım hatalarını ('kudus delili' -> 'hudus delili') analiz kopyasında düzelt
        active_segments, asr_fixes = canonicalize_asr_variants(active_segments)
        logger.info(f"[HolisticAnalyzer] Motor={ENGINE_VERSION} | ASR sözlük düzeltmesi={asr_fixes}")
        full_text = " ".join(str(s.get("text", "")).strip() for s in active_segments)

        # 1. Kilitli ThemeProfile tespiti
        theme_profile = detect_theme_profile_heuristic(full_text)

        # 2. Düzleştirilmiş kelime akışı (WordToken listesi) oluştur
        safe_duration = max(5.0, float(video_duration or 30.0))
        word_stream = self._build_word_stream(active_segments)

        # 3. Videoyu Söylem Analizi (SemanticTransitionBoundaryDetector) ile konu bitimi ve
        #    açıklama öncesi anlamsal bölümlere (Chapters) ayır
        target_chapter_len = 135.0 if safe_duration >= 300.0 else max(25.0, safe_duration / 3.0)
        num_chapters = max(1, min(18, int(round(safe_duration / target_chapter_len))))
        chapter_boundaries = self._find_natural_chapter_boundaries(
            active_segments, safe_duration, num_chapters, word_stream=word_stream
        )

        # 4. Tüm kelime-senkronlu olayları çıkar
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
                    lower_clean = to_turkish_lower(clean or w_str)
                    raw_stripped = w_str.rstrip("\"'”’)")
                    is_sent_end = (
                        raw_stripped.endswith((".", "?", "!", ":", ";"))
                        and lower_clean not in TR_ABBREVIATIONS
                        and not (clean or "").isdigit()
                    )
                    tokens.append(
                        WordToken(
                            idx=len(tokens),
                            raw=w_str,
                            clean=clean or w_str,
                            lower=lower_clean,
                            start=round(w_start, 2),
                            end=round(w_end, 2),
                            seg_idx=seg_idx,
                            has_comma="," in w_str,
                            has_sentence_end=is_sent_end,
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
                    lower_clean = to_turkish_lower(clean or w_str)
                    raw_stripped = w_str.rstrip("\"'”’)")
                    is_sent_end = (
                        raw_stripped.endswith((".", "?", "!", ":", ";"))
                        and lower_clean not in TR_ABBREVIATIONS
                        and not (clean or "").isdigit()
                    )
                    tokens.append(
                        WordToken(
                            idx=len(tokens),
                            raw=w_str,
                            clean=clean or w_str,
                            lower=lower_clean,
                            start=round(w_start, 2),
                            end=round(w_end, 2),
                            seg_idx=seg_idx,
                            has_comma="," in w_str,
                            has_sentence_end=is_sent_end,
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

        # Evrensel İkili Kavram Yakalayıcı (Her türlü video konusu için paralel ve bağlaçlı ikililer)
        self._detect_universal_paired_terms(
            active_segments, word_stream, triggers, occupied_ranges, is_range_busy, seen_groups
        )

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
            matched_work = False
            for kw_tuple, work_title, wiki_tr, wiki_en in KNOWN_WORKS_WIKI_MAP:
                if any(k in lower_cur for k in kw_tuple) or (
                    any(k in lower_win2 for k in kw_tuple)
                    and not any(k in to_turkish_lower(text_next) for k in kw_tuple)
                ):
                    if s_start - seen_works.get(work_title, -999.0) >= 300.0:
                        first_kw = next((k.split()[0] for k in kw_tuple if k in lower_win2), kw_tuple[0].split()[0])
                        start_tok = self._find_word_in_range(word_stream, i, min(n_segs - 1, i + 1), first_kw)
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
                        # Eğer aynı cümlede az önce bir Kişi (Yazar) tanıtımı eklendiyse, yazarın bitişini
                        # eser kelimesinin başlangıcına kırp (veya çok yakınsa esere öncelik ver)
                        if triggers and triggers[-1].action_type == "PERSON_INTRODUCTION" and triggers[-1].end_sec > ev_start - 0.1:
                            prev_p = triggers[-1]
                            if ev_start - prev_p.start_sec >= 1.2:
                                prev_p.end_sec = round(ev_start - 0.12, 2)
                                if occupied_ranges:
                                    occupied_ranges[-1] = (prev_p.start_sec, prev_p.end_sec)
                            else:
                                triggers.pop()
                                if occupied_ranges:
                                    occupied_ranges.pop()
                        # Sonraki meşgul aralığa taşmayı kırp
                        for o_st, _ in occupied_ranges:
                            if o_st > ev_start + 1.0 and ev_end > o_st - 0.12:
                                ev_end = round(o_st - 0.12, 2)
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
                            matched_work = True
                            break

            # Evrensel Dinamik Eser / Kitap / Makale / Kanun Yakalayıcı ("X adlı eserinde/kitabında...")
            if not matched_work:
                univ_work_ev = self._detect_universal_works(
                    i, active_segments, word_stream, video_duration, seen_works, is_range_busy, occupied_ranges, triggers
                )
                if univ_work_ev:
                    triggers.append(univ_work_ev)
                    occupied_ranges.append((univ_work_ev.start_sec, univ_work_ev.end_sec))

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

        # ------------------------------------------------------------------
        # AŞAMA E: EVRENSEL LLM KELİME-SENKRONLU ÇIKARIM (KATMAN 1)
        # (Tıp, Yazılım, Tarih, Ekonomi, Psikoloji, Spor vb. her türlü yeni videoda
        # deterministik kalıpların yakalamadığı boş pencereleri LLM ile zenginleştirir)
        # ------------------------------------------------------------------
        if self.enable_llm_planning and self.gemini and hasattr(self.gemini, "is_available") and self.gemini.is_available():
            self._extract_events_via_llm(
                word_stream=word_stream,
                video_duration=video_duration,
                triggers=triggers,
                occupied_ranges=occupied_ranges,
                is_range_busy=is_range_busy,
                seen_persons=seen_persons,
                seen_works=seen_works,
                seen_terms=seen_terms,
            )

        # ------------------------------------------------------------------
        # AŞAMA F: SIKI TRANSKRİPT SADAKATİ KİLİDİ (KATMAN 3 — VERBATIM LOCK)
        # (Üretilen tüm etiketlerin konuşmacının ağzından çıkan kelimelerle %100 uyuşmasını zorunlu kılar!)
        # ------------------------------------------------------------------
        triggers = VerbatimTranscriptValidator.enforce_verbatim_fidelity(triggers, word_stream)

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
        virgüllerle ardışık saydığı (ör. "A, B, C ve D" veya "suyun kaldırma kuvveti,
        yerçekimi kanunu, fotosentez nizamı ve gezegenlerin yörüngeleri" gibi 1-4 kelimeli)
        3+ maddelik öbek dizilerini otomatik olarak yakalayıp kelime-senkronlu PROGRESSIVE_LIST'e dönüştürür.
        """
        n_tokens = len(word_stream)
        idx = 0
        while idx < n_tokens - 3:
            tok = word_stream[idx]
            if tok.has_comma and len(tok.clean) >= 3:
                # 1. Öbeğin başlangıcını bul (virgülden önceki 1-3 kelime, eğer aynı cümle içindeyse)
                first_phrase_tokens: List[WordToken] = [tok]
                back = idx - 1
                while back >= 0 and len(first_phrase_tokens) < 3:
                    prev_t = word_stream[back]
                    if prev_t.has_sentence_end or prev_t.has_comma or prev_t.lower in (
                        "ve", "ile", "ise", "ki", "çünkü", "ancak", "fakat", "örneğin", "mesela"
                    ):
                        break
                    # Fiil veya cümle zarfı değilse öbeğe dahil et
                    if prev_t.seg_idx == tok.seg_idx and len(prev_t.clean) >= 3:
                        first_phrase_tokens.insert(0, prev_t)
                        back -= 1
                    else:
                        break

                phrase_chain: List[List[WordToken]] = [first_phrase_tokens]
                cur = idx + 1
                while cur < n_tokens and len(phrase_chain) < 7:
                    # Bir sonraki virgüle veya "ve/ile" bağlacına kadar 1-4 kelimelik öbek topla
                    sub_tokens: List[WordToken] = []
                    found_comma = False
                    found_conj = False
                    scan = cur
                    while scan < min(n_tokens, cur + 4):
                        st_tok = word_stream[scan]
                        if st_tok.lower in ("ve", "ile", "yahut", "veya"):
                            found_conj = True
                            break
                        if st_tok.has_sentence_end and not st_tok.has_comma:
                            break
                        if len(st_tok.clean) >= 2:
                            sub_tokens.append(st_tok)
                        if st_tok.has_comma:
                            found_comma = True
                            scan += 1
                            break
                        scan += 1

                    if found_comma and sub_tokens:
                        phrase_chain.append(sub_tokens)
                        cur = scan
                        continue

                    if found_conj:
                        if sub_tokens:
                            phrase_chain.append(sub_tokens)
                        cur = scan
                        after_idx = cur + 1
                        tail_tokens: List[WordToken] = []
                        target_len = len(phrase_chain[-1]) if len(phrase_chain) > 1 else len(first_phrase_tokens)
                        while after_idx < min(n_tokens, cur + 4):
                            at_tok = word_stream[after_idx]
                            if len(at_tok.clean) >= 2:
                                tail_tokens.append(at_tok)
                            if at_tok.has_sentence_end or at_tok.has_comma or len(tail_tokens) >= target_len:
                                after_idx += 1
                                break
                            after_idx += 1
                        if tail_tokens:
                            phrase_chain.append(tail_tokens)
                            cur = after_idx
                        break
                    break

                if len(phrase_chain) >= 3:
                    # Eğer tüm zincir 1'er kelimelikse ilk öbeği de 1 kelimeye indirge (tutarlılık için)
                    if all(len(p) == 1 for p in phrase_chain[1:]) and len(phrase_chain[0]) > 1:
                        phrase_chain[0] = [phrase_chain[0][-1]]

                    last_tok = phrase_chain[-1][-1]
                    end_tok = self._find_sentence_end_word(
                        word_stream, last_tok, min(len(active_segments) - 1, last_tok.seg_idx + 1)
                    )
                    shared_end = round(max(last_tok.end + 0.35, end_tok.end), 2)
                    first_start = phrase_chain[0][0].start
                    if not is_range_busy(first_start, shared_end):
                        grp_id = f"grp_auto_list_{phrase_chain[0][0].idx}"
                        for slot_idx, p_toks in enumerate(phrase_chain):
                            label = to_turkish_upper(" ".join(t.clean for t in p_toks))
                            triggers.append(
                                PlannedEditorialEvent(
                                    event_id=f"{grp_id}_{slot_idx + 1}",
                                    chapter_id=0,
                                    action_type="PROGRESSIVE_LIST",
                                    start_sec=round(p_toks[0].start, 2),
                                    end_sec=shared_end,
                                    text_primary=label,
                                    text_secondary=f"Sıralama {slot_idx + 1}",
                                    semantic_priority=True,
                                    group_id=grp_id,
                                    stack_slot=slot_idx,
                                )
                            )
                        occupied_ranges.append((first_start, shared_end))
                        idx = cur
                        continue
            idx += 1

    def _detect_universal_paired_terms(
        self,
        active_segments: List[Dict[str, Any]],
        word_stream: List[WordToken],
        triggers: List[PlannedEditorialEvent],
        occupied_ranges: List[Tuple[float, float]],
        is_range_busy: Any,
        seen_groups: Dict[str, float],
    ) -> None:
        """
        Her türlü videoda konuşmacının iki kavramı paralel morfolojiyle veya
        bağlaçlı tamlama olarak ("X'ten Y'ye uzanan ... A'dan B'ye inen",
        "X ve Y kanunlarıdır/ilkeleridir/dengesini/iradesini/sistemidir") söylediği
        anları doğrudan konuşulan kelimelerle (Verbatim) yakalar.
        """
        n_segs = len(active_segments)
        parallel_re = re.compile(
            r"\b([a-zçğıöşüâîû]{3,}(?:den|dan|ten|tan))\s+([a-zçğıöşüâîû]{3,}(?:e|a|ye|ya))\s+"
            r"(?:uzanan|giden|çıkan|yükselen|geçen|ulaşan|varan)\b.*?"
            r"\b([a-zçğıöşüâîû]{3,}(?:den|dan|ten|tan))\s+([a-zçğıöşüâîû]{3,}(?:e|a|ye|ya))\s+"
            r"(?:inen|gelen|dönen|ulaşan|varan|bakan)\b",
            re.IGNORECASE | re.UNICODE,
        )
        conj_pair_re = re.compile(
            r"\b([a-zçğıöşüâîû]{3,16})\s+ve\s+([a-zçğıöşüâîû]{3,16})\s+"
            r"(kanun(?:u|ları|larıdır)?|sıfat(?:ı|ından|ları|larıdır)?|ilke(?:si|leri|leridir)?|"
            r"kavram(?:ı|ları|larıdır)?|denge(?:si|sini|sidir)?|irade(?:si|sini|sidir)?|"
            r"sistem(?:i|leri|leridir)?|yöntem(?:i|leri|leridir)?|hormon(?:u|ları|larıdır)?|"
            r"mimari(?:si|sidir)?|yapı(?:sı|sıdır)?|hak(?:kı|ları|larıdır)?)\b",
            re.IGNORECASE | re.UNICODE,
        )

        for i in range(n_segs):
            win_text = " ".join(
                str(active_segments[k].get("text", "")).strip()
                for k in range(i, min(n_segs, i + 3))
            )
            seg_st = float(active_segments[i].get("start", 0.0))

            # Kalıp 1: Yönelmeli / Çıkmalı Paralel Yapılar ("eserlerden müessire uzanan ... sebepten esere inen")
            m_par = parallel_re.search(win_text)
            if m_par and m_par.start() < len(str(active_segments[i].get("text", ""))) + 10:
                w1_a, w1_b, w2_a, w2_b = m_par.group(1), m_par.group(2), m_par.group(3), m_par.group(4)
                key = to_turkish_lower(f"{w1_a}_{w2_a}")
                if seg_st - seen_groups.get(key, -999.0) >= 90.0:
                    tok1 = self._find_word_in_range(word_stream, i, min(n_segs - 1, i + 2), w1_a)
                    tok2 = (
                        self._find_word_in_range(word_stream, tok1.seg_idx, min(n_segs - 1, tok1.seg_idx + 2), w2_a, after_word_idx=tok1.idx)
                        if tok1
                        else None
                    )
                    if tok1 and tok2:
                        end_tok = self._find_sentence_end_word(word_stream, tok2, min(n_segs - 1, tok2.seg_idx + 1))
                        shared_end = round(max(tok2.end + 0.45, end_tok.end), 2)
                        if not is_range_busy(tok1.start, shared_end):
                            seen_groups[key] = seg_st
                            grp_id = f"grp_univ_pair_{len(seen_groups):02d}"
                            lbl1 = to_turkish_upper(f"{w1_a} {w1_b}")
                            lbl2 = to_turkish_upper(f"{w2_a} {w2_b}")
                            for slot_idx, (tok, lbl) in enumerate([(tok1, lbl1), (tok2, lbl2)]):
                                st_s = round(tok.start, 2)
                                en_s = round(max(st_s + 0.45, shared_end), 2)
                                triggers.append(
                                    PlannedEditorialEvent(
                                        event_id=f"{grp_id}_{slot_idx + 1}",
                                        chapter_id=0,
                                        action_type="PAIRED_TERMS",
                                        start_sec=st_s,
                                        end_sec=en_s,
                                        text_primary=lbl,
                                        text_secondary="İkili Kavram",
                                        semantic_priority=True,
                                        group_id=grp_id,
                                        stack_slot=slot_idx,
                                    )
                                )
                            occupied_ranges.append((tok1.start, shared_end))
                            continue

            # Kalıp 2: Bağlaçlı İkili Kavram Tamlamaları ("X ve Y kanunlarıdır/dengesini/ilkeleridir...")
            m_conj = conj_pair_re.search(win_text)
            if m_conj and m_conj.start() < len(str(active_segments[i].get("text", ""))) + 6:
                c1, c2, head_w = m_conj.group(1), m_conj.group(2), m_conj.group(3)
                stop_ignore = {"bu", "şu", "o", "bir", "her", "hem", "ne", "çok", "daha", "en"}
                if to_turkish_lower(c1) not in stop_ignore and to_turkish_lower(c2) not in stop_ignore:
                    key = to_turkish_lower(f"{c1}_{c2}")
                    if seg_st - seen_groups.get(key, -999.0) >= 90.0:
                        tok1 = self._find_word_in_range(word_stream, i, min(n_segs - 1, i + 1), c1)
                        tok2 = (
                            self._find_word_in_range(word_stream, tok1.seg_idx, min(n_segs - 1, tok1.seg_idx + 1), c2, after_word_idx=tok1.idx)
                            if tok1
                            else None
                        )
                        if tok1 and tok2:
                            end_tok = self._find_sentence_end_word(
                                word_stream, tok2, min(n_segs - 1, tok2.seg_idx + 1), head_w
                            )
                            shared_end = round(max(tok2.end + 0.4, end_tok.end), 2)
                            if not is_range_busy(tok1.start, shared_end):
                                seen_groups[key] = seg_st
                                grp_id = f"grp_univ_pair_{len(seen_groups):02d}"
                                lbl1 = to_turkish_upper(c1)
                                lbl2 = to_turkish_upper(c2)
                                for slot_idx, (tok, lbl) in enumerate([(tok1, lbl1), (tok2, lbl2)]):
                                    st_s = round(tok.start, 2)
                                    en_s = round(max(st_s + 0.45, shared_end), 2)
                                    triggers.append(
                                        PlannedEditorialEvent(
                                            event_id=f"{grp_id}_{slot_idx + 1}",
                                            chapter_id=0,
                                            action_type="PAIRED_TERMS",
                                            start_sec=st_s,
                                            end_sec=en_s,
                                            text_primary=lbl,
                                            text_secondary="İkili Kavram",
                                            semantic_priority=True,
                                            group_id=grp_id,
                                            stack_slot=slot_idx,
                                        )
                                    )
                                occupied_ranges.append((tok1.start, shared_end))

    def _detect_universal_works(
        self,
        seg_idx: int,
        active_segments: List[Dict[str, Any]],
        word_stream: List[WordToken],
        video_duration: float,
        seen_works: Dict[str, float],
        is_range_busy: Any,
        occupied_ranges: Optional[List[Tuple[float, float]]] = None,
        triggers: Optional[List[PlannedEditorialEvent]] = None,
    ) -> Optional[PlannedEditorialEvent]:
        """
        Herhangi bir videoda konuşmacı 'X adlı/isimli/başlıklı eserinde/kitabında/risalesinde/makalesinde/filminde'
        dediğinde doğrudan konuşulan eser adını ('LEMEÂT', 'CLEAN CODE', 'DEVLET' vb.) yakalar.
        """
        text_cur = str(active_segments[seg_idx].get("text", "")).strip()
        text_next = (
            str(active_segments[seg_idx + 1].get("text", "")).strip()
            if seg_idx + 1 < len(active_segments)
            else ""
        )
        window_2 = f"{text_cur} {text_next}".strip()
        s_start = float(active_segments[seg_idx].get("start", 0.0))

        work_re = re.compile(
            r"\b([A-ZÇĞİÖŞÜÂÎÛa-zçğıöşüâîû][\wçğıöşüâîû'’-]{2,20}(?:\s+[A-ZÇĞİÖŞÜÂÎÛa-zçğıöşüâîû][\wçğıöşüâîû'’-]{2,20}){0,2})\s+"
            r"(?:adlı|isimli|başlıklı)\s+"
            r"(?:eser(?:i|inde|inden|iyle)?|kitab(?:ı|ında|ından)?|risale(?:si|sinde)?|"
            r"makale(?:si|sinde)?|kanun(?:u|unda)?|film(?:i|inde)?|şiir(?:i|inde)?|rapor(?:u|unda)?)",
            re.UNICODE,
        )
        m_w = work_re.search(window_2)
        if not m_w or m_w.start() >= len(text_cur) + 4:
            return None

        raw_candidate = m_w.group(1).strip()
        # Eğer önünde bilinen bir kişi/yazar adı veya zamir varsa sadece eser adını ayıkla
        cand_words = raw_candidate.split()
        filtered_words: List[str] = []
        person_tokens = {
            "bediüzzaman", "said", "nursi", "imam", "gazali", "gazzali", "ibn", "ibni",
            "sina", "rüşd", "haldun", "farabi", "platon", "aristoteles", "kant", "hans",
            "küng", "künk", "kendi", "onun", "bu", "bir", "meşhur", "ünlü", "büyük",
        }
        for cw in cand_words:
            if to_turkish_lower(cw.strip(",.;:'\"")) not in person_tokens:
                filtered_words.append(cw)
        if not filtered_words:
            filtered_words = [cand_words[-1]]
        # Eğer 3 kelime yakalandıysa ve ilk 2 kelime Yazar Adı + Soyadı ise ("Martin Fowler Refactoring"),
        # son kelimeyi eser adı olarak al
        elif len(filtered_words) == 3 and all(w[0].isupper() for w in filtered_words):
            filtered_words = [filtered_words[-1]]

        work_clean = " ".join(filtered_words).strip()
        work_upper = to_turkish_upper(work_clean)
        # Bilinen bir esere karşılık geliyorsa sözlükteki doğru yazımı/wiki başlığını kullan
        # ('Lemeat' -> 'LEMEÂT'); bilinmeyen eserlerde konuşulan ad aynen kalır.
        wiki_tr_q, wiki_en_q = work_clean, work_clean
        work_norm = VerbatimTranscriptValidator.normalize_root(work_clean.replace(" ", ""))
        for kw_tuple, k_title, k_wiki_tr, k_wiki_en in KNOWN_WORKS_WIKI_MAP:
            if any(VerbatimTranscriptValidator.normalize_root(k.split()[0]) == work_norm for k in kw_tuple):
                work_upper, wiki_tr_q, wiki_en_q = k_title, k_wiki_tr, k_wiki_en
                break
        if len(work_upper) < 3 or s_start - seen_works.get(work_upper, -999.0) < 240.0:
            return None

        start_tok = self._find_word_in_range(
            word_stream, seg_idx, min(len(active_segments) - 1, seg_idx + 1), filtered_words[0]
        )
        ev_start = round(start_tok.start if start_tok else s_start, 2)
        end_tok = (
            self._find_sentence_end_word(word_stream, start_tok, min(len(active_segments) - 1, seg_idx + 1))
            if start_tok
            else None
        )
        ev_end = round(
            max(ev_start + 1.5, min(ev_start + 3.8, end_tok.end if end_tok else ev_start + 2.6)),
            2,
        )
        if triggers and triggers[-1].action_type == "PERSON_INTRODUCTION" and triggers[-1].end_sec > ev_start - 0.1:
            prev_p = triggers[-1]
            if ev_start - prev_p.start_sec >= 1.2:
                prev_p.end_sec = round(ev_start - 0.12, 2)
                if occupied_ranges:
                    occupied_ranges[-1] = (prev_p.start_sec, prev_p.end_sec)
            else:
                triggers.pop()
                if occupied_ranges:
                    occupied_ranges.pop()
        if occupied_ranges:
            for o_st, _ in occupied_ranges:
                if o_st > ev_start + 1.0 and ev_end > o_st - 0.12:
                    ev_end = round(o_st - 0.12, 2)
        if is_range_busy(ev_start, ev_end):
            return None

        seen_works[work_upper] = s_start
        return PlannedEditorialEvent(
            event_id=f"trig_univ_work_{seg_idx}",
            chapter_id=0,
            action_type="WORK_INTRODUCTION",
            start_sec=ev_start,
            end_sec=ev_end,
            text_primary=work_upper,
            text_secondary="Eser / Kitap",
            primary_web_query_tr=wiki_tr_q,
            secondary_stock_query_en=wiki_en_q,
            fallback_minimal_query_en=wiki_en_q,
            person_wiki_tr=wiki_tr_q,
            person_wiki_en=wiki_en_q,
            semantic_priority=True,
        )

    def _extract_events_via_llm(
        self,
        word_stream: List[WordToken],
        video_duration: float,
        triggers: List[PlannedEditorialEvent],
        occupied_ranges: List[Tuple[float, float]],
        is_range_busy: Any,
        seen_persons: Dict[str, float],
        seen_works: Dict[str, float],
        seen_terms: Dict[str, float],
    ) -> None:
        """
        Katman 1: Her türlü video konusu (Tıp, Yazılım, Tarih, Ekonomi, Psikoloji, Vlog vb.)
        için kelime-indeksli pencereleri LLM'e göndererek eksik kalan semantik olayları
        konuşulan kelimelere %100 sadık şekilde çıkarır.
        """
        if not word_stream or not self.gemini:
            return

        # Yalnızca deterministik kuralların yoğun olmadığı pencereler için (veya genel zenginleştirme için)
        # kelime akışını 280 kelimelik pencerelere böl (en fazla 4 pencere çağrısı ile süreyi koru)
        chunk_size = 280
        max_chunks = 4
        chunks: List[List[WordToken]] = []
        for start_i in range(0, len(word_stream), chunk_size):
            sub = word_stream[start_i : start_i + chunk_size]
            if not sub:
                continue
            w_start, w_end = sub[0].start, sub[-1].end
            # Bu pencerede zaten yeterince (4+) olay yakalandıysa LLM çağrısına gerek yok
            existing_in_win = sum(1 for t in triggers if w_start <= t.start_sec <= w_end)
            if existing_in_win < 3:
                chunks.append(sub)
            if len(chunks) >= max_chunks:
                break

        for chunk in chunks:
            indexed_text = " ".join(f"[w{t.idx}|{t.start:.1f}] {t.raw}" for t in chunk)
            prompt = (
                "Sen profesyonel bir kurgu yönetmenisin. Aşağıda bir videonun kelime indeksli transkript kesiti verilmiştir.\n"
                "GÖREVİN: Bu kesitte konuşmacının vurguladığı önemli kavramları şu tiplerde JSON dizisi olarak çıkarmaktır:\n"
                "- 'PERSON_INTRODUCTION': Sadece gerçek bir kişi/bilim insanı/düşünür tanıtılıyorsa.\n"
                "- 'WORK_INTRODUCTION': Sadece somut bir kitap/eser/kanun/film tanıtılıyorsa (SADECE konuşulan eser adını yaz!).\n"
                "- 'PROGRESSIVE_LIST': Ardışık 3+ madde sıralanıyorsa (items dizisiyle).\n"
                "- 'PAIRED_TERMS': İki kavram birbirine paralel veya karşıt vurgulanıyorsa (items dizisiyle).\n"
                "- 'DEFINITION_CALLOUT': Tekil bir anahtar terim veya ilke tanımlanıyorsa.\n\n"
                "ALTIN KURAL: `text_primary` içinde YALNIZCA konuşmacının o kelimelerde AĞZINDAN ÇIKAN kelimeleri kullan! "
                "Konuşmacının söylemediği hiçbir kelimeyi ekleme veya değiştirme!\n"
                "Sadece JSON dizisi döndür:\n"
                '[{"action_type":"DEFINITION_CALLOUT","start_word_idx":12,"end_word_idx":13,"sentence_end_word_idx":18,"text_primary":"ÖRNEK KAVRAM"}]\n\n'
                f"TRANSKRİPT:\n{indexed_text}"
            )
            try:
                raw_resp = self.gemini.generate_text(prompt, max_retries=1)
                if not raw_resp:
                    continue
                m_json = re.search(r"\[.*\]", raw_resp, flags=re.DOTALL)
                if not m_json:
                    continue
                import json
                parsed = json.loads(m_json.group(0))
                if not isinstance(parsed, list):
                    continue

                for item in parsed:
                    if not isinstance(item, dict):
                        continue
                    act = str(item.get("action_type", "")).strip()
                    sent_end_idx = int(item.get("sentence_end_word_idx", -1) or -1)

                    if act in ("PROGRESSIVE_LIST", "PAIRED_TERMS") and isinstance(item.get("items"), list):
                        sub_items = item["items"]
                        if len(sub_items) < 2:
                            continue
                        valid_subs = []
                        for si in sub_items:
                            sw_idx = int(si.get("start_word_idx", -1) or -1)
                            lbl = to_turkish_upper(str(si.get("text_primary", "")).strip())
                            if 0 <= sw_idx < len(word_stream) and len(lbl) >= 2:
                                valid_subs.append((word_stream[sw_idx], lbl))
                        if len(valid_subs) >= 2:
                            last_t = valid_subs[-1][0]
                            end_t = (
                                word_stream[sent_end_idx]
                                if 0 <= sent_end_idx < len(word_stream) and sent_end_idx >= last_t.idx
                                else self._find_sentence_end_word(word_stream, last_t, last_t.seg_idx + 1)
                            )
                            shared_end = round(max(last_t.end + 0.35, end_t.end), 2)
                            if not is_range_busy(valid_subs[0][0].start, shared_end):
                                grp_id = f"grp_llm_{valid_subs[0][0].idx}"
                                for slot_i, (st_tok, lbl) in enumerate(valid_subs):
                                    triggers.append(
                                        PlannedEditorialEvent(
                                            event_id=f"{grp_id}_{slot_i + 1}",
                                            chapter_id=0,
                                            action_type=act,
                                            start_sec=round(st_tok.start, 2),
                                            end_sec=shared_end,
                                            text_primary=lbl,
                                            text_secondary="LLM Vurgusu",
                                            semantic_priority=True,
                                            group_id=grp_id,
                                            stack_slot=slot_i,
                                        )
                                    )
                                occupied_ranges.append((valid_subs[0][0].start, shared_end))
                    elif act in ("PERSON_INTRODUCTION", "WORK_INTRODUCTION", "DEFINITION_CALLOUT", "SINGLE_TERM"):
                        sw_idx = int(item.get("start_word_idx", -1) or -1)
                        lbl = to_turkish_upper(str(item.get("text_primary", "")).strip())
                        if not (0 <= sw_idx < len(word_stream)) or len(lbl) < 3:
                            continue
                        st_tok = word_stream[sw_idx]
                        end_t = (
                            word_stream[sent_end_idx]
                            if 0 <= sent_end_idx < len(word_stream) and sent_end_idx >= st_tok.idx
                            else self._find_sentence_end_word(word_stream, st_tok, st_tok.seg_idx + 1)
                        )
                        ev_st = round(st_tok.start, 2)
                        ev_en = round(max(ev_st + 1.0, min(ev_st + 3.6, end_t.end)), 2)
                        if is_range_busy(ev_st, ev_en) or ev_st - seen_terms.get(lbl, -999.0) < 90.0:
                            continue
                        seen_terms[lbl] = ev_st
                        wiki_q = str(item.get("wiki_query_tr") or lbl).strip()
                        triggers.append(
                            PlannedEditorialEvent(
                                event_id=f"trig_llm_{sw_idx}",
                                chapter_id=0,
                                action_type=act,
                                start_sec=ev_st,
                                end_sec=ev_en,
                                text_primary=lbl,
                                text_secondary="Kavram Vurgusu",
                                primary_web_query_tr=wiki_q if act in ("PERSON_INTRODUCTION", "WORK_INTRODUCTION") else "",
                                person_wiki_tr=wiki_q if act in ("PERSON_INTRODUCTION", "WORK_INTRODUCTION") else "",
                                person_wiki_en=str(item.get("wiki_query_en") or wiki_q).strip()
                                if act in ("PERSON_INTRODUCTION", "WORK_INTRODUCTION")
                                else "",
                                semantic_priority=True,
                            )
                        )
                        occupied_ranges.append((ev_st, ev_en))
            except Exception as ex:
                logger.warning(f"[HolisticAnalyzer] LLM pencere çıkarımı atlandı: {ex}")

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
        word_stream: Optional[List[WordToken]] = None,
    ) -> List[float]:
        if not active_segments:
            return [0.0, video_duration]

        # ÖNCE Söylem Analizi (SemanticTransitionBoundaryDetector) ile gerçek konu bitimi ve
        # açıklama öncesi geçiş noktalarını (Örn: "etmiştik. || İşte bugün...", "çevirmek zorundayız. || İslam hukuku...") tespit et!
        tokens = word_stream if word_stream is not None else self._build_word_stream(active_segments)
        if tokens and video_duration >= 25.0:
            semantic_bounds = SemanticTransitionBoundaryDetector.detect_boundaries(
                word_stream=tokens,
                video_duration=video_duration,
                min_gap_sec=22.0,
            )
            if semantic_bounds:
                boundaries = [0.0]
                for sb in semantic_bounds:
                    if sb.timestamp > boundaries[-1] + 8.0 and sb.timestamp < video_duration - 6.0:
                        boundaries.append(round(sb.timestamp, 2))
                boundaries.append(round(video_duration, 2))
                if len(boundaries) >= 3:
                    logger.info(
                        f"[HolisticAnalyzer] SemanticTransitionBoundaryDetector {len(boundaries) - 2} anlamsal geçiş sınırı tespit etti: "
                        f"{[round(b, 2) for b in boundaries[1:-1]]}"
                    )
                    return boundaries

        if num_chapters <= 1:
            return [0.0, video_duration]

        # Fallback: Sadece gerçek cümle sonlarında (nokta/soru işareti ile biten segmentlerde) sınır seç
        boundaries = [0.0]
        ideal_step = video_duration / num_chapters
        min_chapter_gap = min(15.0, max(4.0, video_duration * 0.08))

        for i in range(1, num_chapters):
            ideal_ts = i * ideal_step
            best_ts = round(ideal_ts, 2)
            best_score = -999.0
            for k in range(len(active_segments) - 1):
                cur_txt = str(active_segments[k].get("text", "")).strip()
                ends_sentence = cur_txt.endswith((".", "?", "!"))
                gap_start = float(active_segments[k].get("end", 0))
                gap_end = float(active_segments[k + 1].get("start", gap_start))
                mid_gap = (gap_start + gap_end) / 2.0
                dist = abs(mid_gap - ideal_ts)
                if dist <= max(8.0, ideal_step * 0.35):
                    pause_dur = max(0.0, gap_end - gap_start)
                    sent_bonus = 3.0 if ends_sentence else -4.0
                    score = pause_dur * 5.0 + sent_bonus - (dist / 20.0)
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
