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
        r"^(hazırsanız|kanunun bir lafzı|bediüzzaman|hakim önüne gelen|evet\b|hayır\b|işte\b|bakın\b|aslında\b|öncelikle\b)",
        re.IGNORECASE,
    )

    INTERVIEW_QUESTION_END_RE = re.compile(
        r"\b(siz nasıl bakıyorsunuz|ne dersiniz|nasıl değerlendiriyorsunuz|buna ne diyorsunuz|bu konuda ne düşünüyorsunuz)\s*\??$",
        re.IGNORECASE,
    )

    UNIVERSAL_DISCOURSE_SHIFT_RE = re.compile(
        r"^(peki|şimdi|gelelim|geçelim|bakalım|şimdi de|burada ise|bu aşamada|bu noktada|"
        r"yeri gelmişken|bir diğer|diğer bir|ikinci olarak|üçüncü olarak|son olarak|"
        r"öte yandan|bunun yanında|ayrıca|sıradaki)\b",
        re.IGNORECASE,
    )

    UNIVERSAL_CLOSURE_END_RE = re.compile(
        r"\b(özetlersek|özetle|gördüğünüz gibi|tamamladık|temel mantığı budur|"
        r"bu şekilde çalışır|diyebiliriz|ifade edebiliriz|anlaşılmaktadır|"
        r"ortaya çıkmaktadır|göstermektedir|gerekmektedir)\s*[.!]?$",
        re.IGNORECASE,
    )

    PROSODIC_PREDICATE_WORDS = {
        "vardır", "yoktur", "demektir", "olur", "olmaz", "eder", "etmez",
        "diyor", "denir", "gerekir", "lazım", "lazımdır", "şarttır", "değildir",
        "ibarettir", "mümkündür", "haramdır", "helaldir", "budur", "şudur", "odur",
    }

    PROSODIC_PREDICATE_SUFFIXES = (
        "mıştır", "miştir", "muştur", "müştür",
        "acaktır", "ecektir", "malıdır", "melidir",
        "maktadır", "mektedir",
        "dır", "dir", "dur", "dür", "tır", "tir", "tur", "tür",
        "iyor", "ıyor", "uyor", "üyor",
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

            # Noktalamasız Whisper çıktılarında akustik boşluk + Türkçe yüklem/söylem sınırı kontrolü
            prosodic_end = False
            if nxt is not None and len(cur) >= 3:
                gap = nxt.start - w.end
                w_low = w.lower
                nxt_low = nxt.lower
                is_predicate = (
                    w_low in cls.PROSODIC_PREDICATE_WORDS
                    or (len(w_low) >= 5 and w_low.endswith(cls.PROSODIC_PREDICATE_SUFFIXES))
                )
                nxt_is_pivot = nxt_low in (
                    "peki", "şimdi", "gelelim", "geçelim", "birincisi", "ikincisi",
                    "üçüncüsü", "dördüncüsü", "mesela", "örneğin", "özetle", "dolayısıyla",
                )
                if (gap >= 0.45 and (is_predicate or nxt_is_pivot)) or (gap >= 0.85 and len(cur) >= 5):
                    prosodic_end = True

            if (ends_punct and not is_abbr and not nxt_starts_lower) or prosodic_end:
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
            if len(sa) < 3 or len(sb) < 3:
                continue
            ta = " ".join(w.raw for w in sa).strip()
            tb = " ".join(w.raw for w in sb).strip()
            la = to_turkish_lower(ta).rstrip(".!?:; ")
            lb = to_turkish_lower(tb).lstrip()

            t_end = sa[-1].end
            t_start = sb[0].start
            # Kesim (Jump-Cut / Retake > 1.2s) boşluğunun ortasına düşmemesi için geçiş zamanını
            # doğrudan yeni konunun başladığı korunan kelimenin başına (t_start) kilitle;
            # normal cümle arası nefes duraksamalarında (<= 1.2s) orta noktayı kullan.
            t_mid = round(t_start, 2) if (t_start - t_end) > 1.2 else round((t_end + t_start) / 2.0, 2)
            if t_mid < 8.0 or t_mid > video_duration - 8.0:
                continue
            if lb.startswith(cls.ANTI_TRANSITION_START_PREFIXES):
                continue

            cat = None
            score = 0.0
            reason = ""
            pause_gap = max(0.0, min(1.5, t_start - t_end))

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

            # Kategori 3: RHETORICAL_QUESTION_TO_THESIS (Yalnızca gerçek soru-cevap / tez dönüşümlerinde tetiklenir;
            # konuşmacının paragraf ortasında kendi kendine sorduğu "boşa mı gidecek?", "gördünüz mü?" gibi ara sorularda tetiklenmez)
            elif ta.endswith("?") and not tb.endswith("?") and (
                cls.THESIS_ANSWER_START_RE.search(lb)
                or cls.UNIVERSAL_DISCOURSE_SHIFT_RE.search(lb)
                or cls.INTERVIEW_QUESTION_END_RE.search(la)
            ):
                cat = "RHETORICAL_QUESTION_TO_THESIS"
                score = 90.0 if (cls.THESIS_ANSWER_START_RE.search(lb) or cls.INTERVIEW_QUESTION_END_RE.search(la)) else (80.0 + pause_gap * 4.0)
                reason = "Retorik çerçeveleme sorusu bitimi (?) -> Tez/cevap açıklamasına giriş"

            # Kategori 4: EVRENSEL TÜRKÇE SÖYLEM DÖNEMECİ (Yeni Konu / Soru Başlangıcı)
            elif cls.UNIVERSAL_DISCOURSE_SHIFT_RE.search(lb) and (
                ta.endswith((".", "!", "?"))
                or sa[-1].lower in cls.PROSODIC_PREDICATE_WORDS
                or sa[-1].lower.endswith(cls.PROSODIC_PREDICATE_SUFFIXES)
                or cls.UNIVERSAL_CLOSURE_END_RE.search(la)
            ):
                cat = "RETROSPECTIVE_CLOSURE_TO_NEW_TOPIC"
                is_q_pivot = any(q in lb[:45] for q in ("nedir", "nasıl", "neden", "niçin", "ne demek", "hangi"))
                score = (84.0 if is_q_pivot else 74.0) + pause_gap * 5.0
                reason = "Evrensel Türkçe söylem dönüşümü + cümle kapanışı"

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
    (("bakara suresi 219", "bakara 219"), "BAKARA SURESİ 219. AYET", "Bakara Suresi", "Al-Baqara"),
    (("bakara suresi",), "BAKARA SURESİ", "Bakara Suresi", "Al-Baqara"),
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
    def strip_turkish_suffixes(cls, word: str) -> str:
        w = cls.normalize_root(word)
        if len(w) <= 3:
            return w
        suffixes = (
            "larından", "lerinden", "larımız", "lerimiz", "larınız", "leriniz",
            "larının", "lerinin", "larıyla", "leriyle", "odaklı", "سند",
            "sından", "sinden", "sundan", "sünden", "mından", "minden",
            "ğından", "ğinden", "ğundan", "ğünden", "bından", "binden",
            "larının", "lerinin", "larımız", "lerimiz",
            "ndan", "nden", "dan", "den", "tan", "ten",
            "nın", "nin", "nun", "nün", "yla", "yle", "lar", "ler",
            "dır", "dir", "dur", "dür", "tır", "tir", "tur", "tür",
            "sını", "sini", "sunu", "sünü", "mızı", "mizi",
            "nda", "nde", "da", "de", "ta", "te",
            "ın", "in", "un", "ün", "ya", "ye", "yi", "yı", "yu", "yü",
            "sı", "si", "su", "sü", "la", "le", "a", "e", "ı", "i", "u", "ü",
        )
        for suf in suffixes:
            if w.endswith(suf) and len(w) - len(suf) >= 3:
                w = w[: -len(suf)]
                break
        if len(w) >= 3:
            if w.endswith("b"):
                w = w[:-1] + "p"
            elif w.endswith("c"):
                w = w[:-1] + "ç"
            elif w.endswith("d"):
                w = w[:-1] + "t"
            elif w.endswith("ğ"):
                w = w[:-1] + "k"
        return w

    @classmethod
    def word_similarity_score(cls, label_word: str, spoken_word: str) -> float:
        import difflib

        u = cls.normalize_root(label_word)
        v = cls.normalize_root(spoken_word)
        if not u or not v:
            return 0.0
        if u == v:
            return 1.0
        u_stem = cls.strip_turkish_suffixes(u)
        v_stem = cls.strip_turkish_suffixes(v)
        if u_stem == v_stem and len(u_stem) >= 3:
            return 0.98
        if min(len(u), len(v)) >= 4 and (v.startswith(u) or u.startswith(v)):
            return 0.94
        if min(len(u_stem), len(v_stem)) >= 3 and (v_stem.startswith(u_stem) or u_stem.startswith(v_stem)):
            return 0.90
        lcp = 0
        for ch_a, ch_b in zip(u_stem, v_stem):
            if ch_a == ch_b:
                lcp += 1
            else:
                break
        r_lcp = lcp / float(max(1, min(len(u_stem), len(v_stem))))
        r_seq = difflib.SequenceMatcher(None, u_stem, v_stem).ratio()
        return round(0.55 * r_lcp + 0.45 * r_seq, 3)

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
            # Kişi tanıtımlarında ve can alıcı cümle vurgularında tam metin korunur
            if evt.action_type in ("PERSON_INTRODUCTION", "KEY_POINT", "HIGHLIGHT"):
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
        target_chapter_len = 50.0 if safe_duration >= 200.0 else max(20.0, safe_duration / 3.0)
        num_chapters = max(2, min(30, int(round(safe_duration / target_chapter_len))))
        chapter_boundaries = self._find_natural_chapter_boundaries(
            active_segments, safe_duration, num_chapters, word_stream=word_stream
        )

        # 4. Tüm kelime-senkronlu olayları çıkar
        global_semantic_triggers = self._detect_global_semantic_triggers(
            active_segments,
            safe_duration,
            word_stream=word_stream,
            chapter_boundaries=chapter_boundaries,
        )

        # 4.1 Aktif grup (PROGRESSIVE_LIST / PAIRED_TERMS) sınırlarını koru:
        # Hiçbir bölüm sınırı (transition) aktif bir sıralama grubunun ortasına düşemez!
        group_spans: Dict[str, Tuple[float, float]] = {}
        for trig in global_semantic_triggers:
            if trig.group_id:
                g_st, g_en = group_spans.get(trig.group_id, (trig.start_sec, trig.end_sec))
                group_spans[trig.group_id] = (min(g_st, trig.start_sec), max(g_en, trig.end_sec))

        if len(chapter_boundaries) > 2 and group_spans:
            adjusted_bounds = [chapter_boundaries[0]]
            for b_ts in chapter_boundaries[1:-1]:
                shifted_ts = b_ts
                for g_st, g_en in group_spans.values():
                    if (g_st - 0.35) <= shifted_ts <= (g_en + 0.35):
                        shifted_ts = round(min(safe_duration - 2.0, g_en + 0.25), 2)
                if shifted_ts > adjusted_bounds[-1] + 4.0 and shifted_ts < safe_duration - 3.0:
                    adjusted_bounds.append(shifted_ts)
            adjusted_bounds.append(chapter_boundaries[-1])
            chapter_boundaries = adjusted_bounds

        # 5. Bölüm planlarına dağıt (Grup öğeleri atomik olarak ilk öğenin bölümüne atanır)
        chapter_plans: List[ChapterPlan] = []
        self._used_chapter_keyphrases: Set[str] = {t.text_primary for t in global_semantic_triggers}
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
            ch_triggers = []
            for t in global_semantic_triggers:
                anchor_sec = group_spans[t.group_id][0] if (t.group_id and t.group_id in group_spans) else t.start_sec
                if (ch_start <= anchor_sec < ch_end) or (is_last_ch and ch_start <= anchor_sec <= ch_end + 1.0):
                    ch_triggers.append(t)

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

    _TR_FINITE_END_RE = re.compile(
        r"(?:dır|dir|dur|dür|tır|tir|tur|tür|mıştır|miştir|muştur|müştür|"
        r"maktadır|mektedir|acaktır|ecektir|malıdır|melidir|"
        r"yordu|دم|dı|di|du|dü|tı|ti|tu|tü|mış|miş|muş|müş|"
        r"yor|makta|mekte|acak|ecek|malı|meli|"
        r"সুন|sınız|siniz|sunuz|sünüz|ız|iz|uz|üz|k|n|lar|ler)$",
        re.IGNORECASE | re.UNICODE,
    )
    _TR_CLAUSE_BOUNDARY_RE = re.compile(
        r"(?:ğında|ğinde|ğunda|ğünde|dığında|diğinde|duğunda|düğünde|"
        r"tığında|tiğinde|tuğunda|tüğünde|ınca|ince|unca|ünce|"
        r"arak|erek|dikçe|dıkça|dukça|dükçe|madan|meden|"
        r"ken|sa|se|ysa|yse)$",
        re.IGNORECASE | re.UNICODE,
    )
    _TR_DISCOURSE_STARTERS = {
        "ancak", "fakat", "lakin", "ama", "çünkü", "zira", "dolayısıyla",
        "nitekim", "örneğin", "mesela", "ayrıca", "üstelik", "böylece",
        "özetle", "kısacası", "sonuçta", "şimdi", "peki", "halbuki", "oysa",
    }

    def _find_sentence_end_word(
        self,
        word_stream: List[WordToken],
        start_tok: WordToken,
        max_seg_idx: int,
        end_hint: str = "",
    ) -> WordToken:
        """
        4 Katmanlı Hibrit Akustik + Morfolojik Türkçe Cümle/Yan Cümle Sonu Bulucu (PROB-3.1):
        Whisper'ın 6 kelimelik yapay altyazı segment sınırlarına (`seg_idx`) takılmadan,
        noktalama, akustik duraksama, Türkçe çekimli yüklem ekleri ve zarf-fiil sınırlarını
        birlikte değerlendirerek kavramın ait olduğu cümlenin gerçek bitiş kelimesini bulur.
        """
        n_stream = len(word_stream)
        if not word_stream or start_tok.idx >= n_stream:
            return start_tok

        # Katman 1: Açık ipucu kelimesi (end_hint) varsa segment sınırını +3 esneterek ara
        if end_hint:
            found_end = self._find_word_in_range(
                word_stream,
                start_tok.seg_idx,
                max(max_seg_idx, start_tok.seg_idx + 3),
                end_hint,
                after_word_idx=start_tok.idx - 1,
            )
            if found_end and (found_end.end - start_tok.start) <= 6.5:
                return found_end

        # Katman 2: Kelime akışı üzerinde 18 kelime veya 5.2 saniye ileriye kadar hibrit tarama
        max_lookahead_words = 18
        max_lookahead_sec = 5.2
        upper_idx = min(n_stream - 1, start_tok.idx + max_lookahead_words)

        best_clause_tok: Optional[WordToken] = None
        for idx in range(start_tok.idx, upper_idx + 1):
            tok = word_stream[idx]
            elapsed = tok.end - start_tok.start
            if idx > start_tok.idx and elapsed > max_lookahead_sec:
                break

            next_tok = word_stream[idx + 1] if (idx + 1) < n_stream else None
            gap_after = max(0.0, (next_tok.start - tok.end)) if next_tok else 1.0

            # 2.a) Açık cümle sonu noktalama işareti (. ? ! : ;)
            if tok.has_sentence_end and elapsed >= 0.65:
                return tok

            # 2.b) Belirgin akustik nefes/cümle duraksaması (>= 0.38s)
            if gap_after >= 0.38 and elapsed >= 0.85:
                return tok

            # 2.c) Türkçe çekimli fiil / bildirme eki + mikro akustik duraksama (>= 0.18s) veya virgül
            if elapsed >= 0.95 and len(tok.lower) >= 4 and self._TR_FINITE_END_RE.search(tok.lower):
                if gap_after >= 0.18 or tok.has_comma:
                    return tok
                if best_clause_tok is None and elapsed >= 1.25:
                    best_clause_tok = tok

            # 2.d) Yan cümle / zarf-fiil sınırı (-dığında, -ınca, -arak, -ken, -sa) + duraksama
            if elapsed >= 1.45 and len(tok.lower) >= 5 and self._TR_CLAUSE_BOUNDARY_RE.search(tok.lower):
                if gap_after >= 0.14 or tok.has_comma:
                    return tok

            # 2.e) Bir sonraki kelime yeni bir söylem/bağlaç başlatıyorsa mevcut kelimede bitir
            if next_tok and elapsed >= 1.10 and next_tok.lower in self._TR_DISCOURSE_STARTERS:
                return tok

        if best_clause_tok is not None:
            return best_clause_tok

        # Katman 3: Güvenli Bilişsel Süre Penceresi (~2.4s hedef, [1.2s, 4.0s] aralığı)
        target_end_sec = start_tok.start + 2.4
        fallback_tok = start_tok
        for idx in range(start_tok.idx, upper_idx + 1):
            tok = word_stream[idx]
            if (tok.end - start_tok.start) <= 4.0:
                fallback_tok = tok
                if tok.end >= target_end_sec and (tok.has_comma or (idx + 1 < n_stream and (word_stream[idx + 1].start - tok.end) >= 0.12)):
                    return tok
            else:
                break
        return fallback_tok

    def _detect_global_semantic_triggers(
        self,
        active_segments: List[Dict[str, Any]],
        video_duration: float,
        word_stream: Optional[List[WordToken]] = None,
        chapter_boundaries: Optional[List[float]] = None,
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
                        shared_end_sec = round(
                            min(last_item_tok.end + 6.5, max(last_item_tok.end + 0.55, end_tok.end)),
                            2,
                        )
                        seen_groups[rule_trigger] = seg_st
                        grp_id = f"grp_list_{len(seen_groups):02d}"

                        for slot_idx, (item_tok, label_tr) in enumerate(matched_items):
                            item_start = round(item_tok.start, 2)
                            item_end = round(max(item_start + 0.65, shared_end_sec), 2)
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
        # Çok Cümleli Sıra Sayılı ("Birincisi X... İkincisi Y... Üçüncüsü Z...") Kümülatif Liste Yakalayıcı
        self._detect_multi_sentence_ordinal_lists(
            active_segments, word_stream, triggers, occupied_ranges, is_range_busy, seen_groups
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
                chapter_boundaries=chapter_boundaries,
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
                new_end = round(max(cur_ev.start_sec + 0.55, nxt_ev.start_sec - 0.08), 2)
                if cur_ev.group_id:
                    target_grp = cur_ev.group_id
                    for g_ev in triggers:
                        if g_ev.group_id == target_grp:
                            g_ev.end_sec = round(max(g_ev.start_sec + 0.55, new_end), 2)
                else:
                    cur_ev.end_sec = new_end

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
        virgüllerle ardışık saydığı (ör. "A, B, C ve D" veya "faiz, kumar ve akdin belirsiz olması"
        gibi Behaghel sağ-bağlaç genişlemeli) 3+ maddelik öbek dizilerini otomatik olarak yakalayıp
        kelime-senkronlu PROGRESSIVE_LIST'e dönüştürür (PROB-2.1, PROB-2.2, PROB-3.2).
        """
        n_tokens = len(word_stream)
        salutation_and_discourse_Blacklist = {
            "değerli", "izleyenler", "izleyiciler", "arkadaşlar", "dostlar", "sayın",
            "merhaba", "hoş", "geldiniz", "evet", "şimdi", "öncelikle", "kısacası",
            "dolayısıyla", "nitekim", "halbuki", "ancak", "fakat", "lakin", "örneğin",
            "mesela", "hatta", "zaten", "aslında", "tabii", "elbette", "peki", "işte",
            "burada", "bugün", "geçen", "bölümde", "dersimizde", "videomuzda",
            "şey", "yani", "filan", "falan", "var", "yok", "adlarını", "isimlerini",
            "bilmiyoruz", "saymıyoruz", "biliyoruz", "diyoruz", "ediyoruz", "yapıyoruz",
            "geliyoruz", "görüyoruz", "bunun", "şunun", "onun", "bunu", "şunu", "buna",
            "şuna", "ona", "öyle", "böyle", "şöyle", "kez", "defa", "zaman",
        }
        finite_clause_breakers = {
            "yasaklanmıştır", "yasaktır", "haramdır", "gerekmektedir", "gerekir",
            "oluşur", "bulunur", "vardır", "yoktur", "denir", "görülür", "kabul",
            "edilir", "edilmektedir", "sayılır", "olmalıdır", "olamaz", "değildir",
            "gibidir", "içindir", "üzerinedir", "ibarettir", "dayanır", "söz", "konusuysa",
        }
        narrative_clause_blacklist = {
            "yerde", "diye", "başlayarak", "içinden", "yanındaki", "mahallendeki",
            "ulaşabileceğin", "yakınlarından", "yatırıyor", "götürüyor", "parasını",
            "parayı", "parasın", "paray", "evlendireceği", "alacağı", "edeceği",
            "olmayana", "evlenemeyeni", "biriktirmek", "fazla",
        }
        idx = 0
        while idx < n_tokens - 3:
            tok = word_stream[idx]
            if (
                tok.has_comma
                and len(tok.clean) >= 3
                and tok.lower not in salutation_and_discourse_Blacklist
                and tok.lower not in narrative_clause_blacklist
            ):
                # 1. Öbeğin başlangıcını bul (virgülden önceki 1-2 kelime)
                first_phrase_tokens: List[WordToken] = [tok]
                back = idx - 1
                while back >= 0 and len(first_phrase_tokens) < 2:
                    prev_t = word_stream[back]
                    next_in_phrase = first_phrase_tokens[0]
                    if (
                        prev_t.has_sentence_end
                        or prev_t.has_comma
                        or prev_t.lower in (
                            "ve", "ile", "ise", "ki", "çünkü", "ancak", "fakat", "örneğin", "mesela",
                            "gibi", "olan", "olarak", "başta", "özellikle", "hem", "gerek", "bir", "bu", "şu",
                        )
                        or prev_t.lower in salutation_and_discourse_Blacklist
                        or prev_t.lower in finite_clause_breakers
                        or prev_t.lower in narrative_clause_blacklist
                    ):
                        break
                    if (prev_t.seg_idx == tok.seg_idx or (next_in_phrase.start - prev_t.end) <= 0.35) and len(prev_t.clean) >= 3:
                        first_phrase_tokens.insert(0, prev_t)
                        back -= 1
                    else:
                        break

                phrase_chain: List[List[WordToken]] = [first_phrase_tokens]
                cur = idx + 1
                while cur < n_tokens and len(phrase_chain) < 7:
                    # Bağlaç öncesi ara maddeler kısa (1-2 kelime) olmalıdır; uzun yan cümleler elenir
                    sub_tokens: List[WordToken] = []
                    found_comma = False
                    found_conj = False
                    found_asyndetic_end = False
                    scan = cur
                    while scan < min(n_tokens, cur + 3):
                        st_tok = word_stream[scan]
                        if st_tok.lower in ("ve", "ile", "yahut", "veya"):
                            found_conj = True
                            break
                        if st_tok.lower in narrative_clause_blacklist:
                            sub_tokens = []
                            break
                        if st_tok.lower in ("yani", "işte", "bunlar", "gibi", "hepsi", "tamamı", "demek"):
                            if len(phrase_chain) >= 2 and sub_tokens:
                                found_asyndetic_end = True
                            break
                        if st_tok.has_sentence_end and not st_tok.has_comma:
                            if len(st_tok.clean) >= 2 and len(sub_tokens) == 0 and len(phrase_chain) >= 2:
                                sub_tokens.append(st_tok)
                                found_asyndetic_end = True
                            break
                        if len(st_tok.clean) >= 2:
                            sub_tokens.append(st_tok)
                        if st_tok.has_comma:
                            found_comma = True
                            scan += 1
                            break
                        # Eğer halihazırda en az 2 virgüllü madde varsa ve 3. madde tek kelimelik paralel bir kavram olup
                        # arkasından duraksama (>= 0.25s) veya bağlaçsız açıklama geliyorsa (asyndetic list: "yardımlaşma, danışma, destekleşme yani...")
                        if len(phrase_chain) >= 2 and len(sub_tokens) == 1:
                            nxt_after = word_stream[scan + 1] if (scan + 1) < n_tokens else None
                            prev_last_low = phrase_chain[-1][-1].lower
                            same_morph = (
                                len(prev_last_low) >= 4
                                and len(st_tok.lower) >= 4
                                and prev_last_low[-2:] == st_tok.lower[-2:]
                            )
                            if nxt_after and (
                                nxt_after.lower in ("yani", "işte", "bunlar", "gibi", "hepsi", "bu", "yoksa", "varsa")
                                or (nxt_after.start - st_tok.end) >= 0.28
                                or same_morph
                            ) and not nxt_after.has_comma and nxt_after.lower not in ("ve", "ile", "yahut", "veya"):
                                found_asyndetic_end = True
                                scan += 1
                                break
                        scan += 1

                    if found_comma and sub_tokens and len(sub_tokens) <= 2:
                        phrase_chain.append(sub_tokens)
                        cur = scan
                        continue

                    if found_asyndetic_end and sub_tokens and len(sub_tokens) <= 2:
                        phrase_chain.append(sub_tokens)
                        cur = scan
                        break

                    if found_conj:
                        if sub_tokens and len(sub_tokens) <= 2:
                            phrase_chain.append(sub_tokens)
                        cur = scan
                        after_idx = cur + 1
                        # "ve bir de" / "ve ayrıca" gibi bağlaç pekiştiricilerini atla
                        while after_idx < n_tokens and word_stream[after_idx].lower in ("bir", "de", "da", "ayrıca", "hatta"):
                            after_idx += 1
                        tail_tokens: List[WordToken] = []
                        # Behaghel Sağ-Bağlaç Yasası (PROB-2.1):
                        # Son öğe ("ve akdin belirsiz olması") önceki öğelerden ("faiz, kumar") daha uzun
                        # bir isim-fiil / tamlama grubu olabilir; cümle yüklemine veya 4 kelimeye kadar topla!
                        while after_idx < min(n_tokens, cur + 7):
                            at_tok = word_stream[after_idx]
                            if (
                                at_tok.lower in salutation_and_discourse_Blacklist
                                or at_tok.lower in narrative_clause_blacklist
                                or at_tok.lower in ("gibi", "başta", "olarak", "üzere", "dolayı", "nedeniyle", "sebebiyle", "için")
                            ):
                                break
                            if at_tok.lower in finite_clause_breakers and tail_tokens:
                                break
                            is_verbal_noun = at_tok.lower.endswith(("ması", "mesi", "mak", "mek", "lığı", "liği", "luğu", "lüğü"))
                            if (
                                not is_verbal_noun
                                and tail_tokens
                                and self._TR_FINITE_END_RE.search(at_tok.lower)
                                and at_tok.lower.endswith(("dır", "dir", "dur", "dür", "tır", "tir", "tur", "tür", "mıştır", "miştir", "di", "dı", "du", "dü", "ti", "tı", "tu", "tü", "yor", "acak", "ecek"))
                            ):
                                break
                            if len(at_tok.clean) >= 2:
                                tail_tokens.append(at_tok)
                            next_after = word_stream[after_idx + 1] if (after_idx + 1) < n_tokens else None
                            pause_after = (next_after.start - at_tok.end) if next_after else 1.0
                            if (
                                at_tok.has_sentence_end
                                or at_tok.has_comma
                                or pause_after >= 0.38
                                or len(tail_tokens) >= 4
                                or (is_verbal_noun and len(tail_tokens) >= 2)
                            ):
                                after_idx += 1
                                break
                            after_idx += 1
                        if tail_tokens:
                            phrase_chain.append(tail_tokens)
                            cur = after_idx
                        break
                    break

                # Filtre: Liste öğeleri anlamsız ara kelimelerden, zarf-fiillerden (-erek/-arak) veya çekimli fiillerden arındırılır
                cleaned_phrases = []
                for p in phrase_chain:
                    p_txt = " ".join(t.clean for t in p).strip()
                    p_low = to_turkish_lower(p_txt)
                    if (
                        len(p_txt) < 3
                        or p_low in salutation_and_discourse_Blacklist
                        or any(t.lower in salutation_and_discourse_Blacklist or t.lower in narrative_clause_blacklist for t in p)
                        or any(
                            t.lower.endswith(("erek", "arak", "ip", "ıp", "up", "üp", "ince", "ınca", "ken", "dikçe", "dıkça"))
                            for t in p
                        )
                        or any(p_low.endswith(suf) for suf in ("mıyoruz", "miyoruz", "muyoruz", "müyoruz", "madık", "medik", "mayız", "meyiz", "yor", "yordu"))
                    ):
                        continue
                    cleaned_phrases.append(p)

                if len(cleaned_phrases) >= 3:
                    phrase_chain = cleaned_phrases
                    # Eğer orta öğeler 1'er kelimelikse ve ilk öbeğin başında cümle öznesi/zarfı kaldıysa
                    # ilk öbeği de son kelimesine (asıl birinci maddeye) indirge
                    if all(len(p) == 1 for p in phrase_chain[1:-1]) and len(phrase_chain[0]) > 1:
                        phrase_chain[0] = [phrase_chain[0][-1]]

                    last_tok = phrase_chain[-1][-1]
                    end_tok = self._find_sentence_end_word(
                        word_stream, last_tok, min(len(active_segments) - 1, last_tok.seg_idx + 2)
                    )
                    first_start = phrase_chain[0][0].start
                    # Uzun kesim boşlukları nedeniyle listenin ekranda 25-30sn asılı kalmasını önle (24s üst sınır)
                    if (last_tok.end - first_start) > 24.0:
                        idx += 1
                        continue
                    shared_end = round(
                        min(
                            first_start + 18.0,
                            last_tok.end + 2.5,
                            max(last_tok.end + 0.65, end_tok.end),
                        ),
                        2,
                    )
                    if not is_range_busy(max(0.0, first_start - 0.25), shared_end):
                        grp_id = f"grp_auto_list_{phrase_chain[0][0].idx}"
                        for slot_idx, p_toks in enumerate(phrase_chain):
                            label = to_turkish_upper(" ".join(t.clean for t in p_toks))
                            item_st = round(p_toks[0].start, 2)
                            item_en = round(max(item_st + 0.65, shared_end), 2)
                            triggers.append(
                                PlannedEditorialEvent(
                                    event_id=f"{grp_id}_{slot_idx + 1}",
                                    chapter_id=0,
                                    action_type="PROGRESSIVE_LIST",
                                    start_sec=item_st,
                                    end_sec=item_en,
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

        # 2. Tekrarlı Koşul / Varlık Kalıbıyla Yapılan Konuşma Dili Sıralamaları:
        # Örn: "içinde faiz varsa, kumar varsa ve bir de akdin belirsiz olması söz konusuysa"
        cond_markers = {"varsa", "yoksa", "olursa", "olmazsa", "olsun"}
        c_idx = 1
        while c_idx < n_tokens - 4:
            m_tok = word_stream[c_idx]
            if m_tok.lower in cond_markers:
                first_item = word_stream[c_idx - 1]
                if (
                    len(first_item.clean) >= 3
                    and first_item.lower not in salutation_and_discourse_Blacklist
                    and first_item.lower not in narrative_clause_blacklist
                ):
                    cond_chain: List[List[WordToken]] = [[first_item]]
                    scan = c_idx + 1
                    while scan < min(n_tokens - 1, c_idx + 6):
                        if word_stream[scan].lower == m_tok.lower and scan > c_idx + 1:
                            cand_prev = word_stream[scan - 1]
                            if len(cand_prev.clean) >= 3 and cand_prev.lower not in salutation_and_discourse_Blacklist:
                                cond_chain.append([cand_prev])
                                scan += 1
                                continue
                        if word_stream[scan].lower in ("ve", "ile", "yahut", "veya") and len(cond_chain) >= 2:
                            after_c = scan + 1
                            while after_c < n_tokens and word_stream[after_c].lower in ("bir", "de", "da", "ayrıca", "hatta"):
                                after_c += 1
                            tail_toks: List[WordToken] = []
                            while after_c < min(n_tokens, scan + 7):
                                at_t = word_stream[after_c]
                                if (
                                    at_t.lower in cond_markers
                                    or at_t.lower in finite_clause_breakers
                                    or at_t.lower in salutation_and_discourse_Blacklist
                                    or at_t.lower in narrative_clause_blacklist
                                ):
                                    break
                                is_vn = at_t.lower.endswith(("ması", "mesi", "mak", "mek", "lığı", "liği", "luğu", "lüğü"))
                                if len(at_t.clean) >= 2:
                                    tail_toks.append(at_t)
                                if at_t.has_sentence_end or at_t.has_comma or len(tail_toks) >= 4 or (is_vn and len(tail_toks) >= 2):
                                    after_c += 1
                                    break
                                after_c += 1
                            if tail_toks:
                                cond_chain.append(tail_toks)
                            break
                        scan += 1

                    if len(cond_chain) >= 3:
                        first_st = cond_chain[0][0].start
                        last_t = cond_chain[-1][-1]
                        end_t = self._find_sentence_end_word(
                            word_stream, last_t, min(len(active_segments) - 1, last_t.seg_idx + 2)
                        )
                        if (last_t.end - first_st) <= 24.0:
                            sh_end = round(
                                min(first_st + 18.0, last_t.end + 2.5, max(last_t.end + 0.65, end_t.end)),
                                2,
                            )
                            if not is_range_busy(max(0.0, first_st - 0.25), sh_end):
                                grp_id = f"grp_cond_list_{cond_chain[0][0].idx}"
                                for slot_idx, p_toks in enumerate(cond_chain):
                                    lbl = to_turkish_upper(" ".join(t.clean for t in p_toks))
                                    it_st = round(p_toks[0].start, 2)
                                    it_en = round(max(it_st + 0.65, sh_end), 2)
                                    triggers.append(
                                        PlannedEditorialEvent(
                                            event_id=f"{grp_id}_{slot_idx + 1}",
                                            chapter_id=0,
                                            action_type="PROGRESSIVE_LIST",
                                            start_sec=it_st,
                                            end_sec=it_en,
                                            text_primary=lbl,
                                            text_secondary=f"Sıralama {slot_idx + 1}",
                                            semantic_priority=True,
                                            group_id=grp_id,
                                            stack_slot=slot_idx,
                                        )
                                    )
                                occupied_ranges.append((first_st, sh_end))
                                c_idx = last_t.idx + 1
                                continue
            c_idx += 1

    def _detect_multi_sentence_ordinal_lists(
        self,
        active_segments: List[Dict[str, Any]],
        word_stream: List[WordToken],
        triggers: List[PlannedEditorialEvent],
        occupied_ranges: List[Tuple[float, float]],
        is_range_busy: Any,
        seen_groups: Dict[str, float],
    ) -> None:
        """
        Çok cümleli sıra sayılı anlatımları ("Birincisi X... İkincisi Y... Üçüncüsü Z...")
        ayrı ayrı tekil kutular yerine tek bir kümülatif PROGRESSIVE_LIST grubunda birleştirir (PROB-2.3).
        """
        n_tokens = len(word_stream)
        if n_tokens < 6:
            return

        ordinal_ranks = {
            "birincisi": 1,
            "ilk": 1,
            "ikincisi": 2,
            "ikinci": 2,
            "üçüncüsü": 3,
            "üçüncü": 3,
            "dördüncüsü": 4,
            "dördüncü": 4,
            "beşincisi": 5,
            "beşinci": 5,
        }

        i = 0
        while i < n_tokens - 3:
            tok = word_stream[i]
            rank = ordinal_ranks.get(tok.lower, 0)
            if rank == 1:
                # "ilk" ise arkasından "olarak" veya "madde/unsur/şart" gelmeli
                if tok.lower == "ilk" and (i + 1 >= n_tokens or word_stream[i + 1].lower not in ("olarak", "madde", "şart", "ilke", "unsur")):
                    i += 1
                    continue

                chain: List[Tuple[WordToken, str]] = []
                cur_rank = 1
                scan = i
                while scan < n_tokens and (word_stream[scan].start - tok.start) <= 32.0:
                    st_tok = word_stream[scan]
                    r = ordinal_ranks.get(st_tok.lower, 0)
                    if r == cur_rank:
                        # Sıra kelimesinden sonraki 1-5 kelimelik kavram öbeğini çıkar
                        phrase_start = scan + 1
                        if phrase_start < n_tokens and word_stream[phrase_start].lower in ("olarak", "ise", "yani", "de", "da", "madde", "şart"):
                            phrase_start += 1
                        cand_toks = word_stream[phrase_start : min(n_tokens, phrase_start + 5)]
                        if cand_toks:
                            raw_cand = " ".join(t.clean for t in cand_toks)
                            title = extract_turkish_semantic_title(raw_cand, max_chars=26)
                            if title and len(title) >= 3:
                                anchor_tok = cand_toks[0]
                                chain.append((anchor_tok, title))
                                cur_rank += 1
                                scan = phrase_start + 2
                                continue
                    scan += 1

                if len(chain) >= 2:
                    first_tok = chain[0][0]
                    last_tok = chain[-1][0]
                    end_tok = self._find_sentence_end_word(
                        word_stream, last_tok, min(len(active_segments) - 1, last_tok.seg_idx + 2)
                    )
                    shared_end = round(
                        min(
                            first_tok.start + 22.0,
                            last_tok.end + 2.8,
                            max(last_tok.end + 0.85, end_tok.end),
                        ),
                        2,
                    )
                    if not is_range_busy(first_tok.start, shared_end):
                        grp_id = f"grp_ord_list_{first_tok.idx}"
                        seen_groups[grp_id] = first_tok.start
                        for slot_idx, (item_tok, item_lbl) in enumerate(chain):
                            item_st = round(item_tok.start, 2)
                            item_en = round(max(item_st + 0.65, shared_end), 2)
                            triggers.append(
                                PlannedEditorialEvent(
                                    event_id=f"{grp_id}_{slot_idx + 1}",
                                    chapter_id=0,
                                    action_type="PROGRESSIVE_LIST",
                                    start_sec=item_st,
                                    end_sec=item_en,
                                    text_primary=item_lbl,
                                    text_secondary=f"Sıralama {slot_idx + 1}",
                                    semantic_priority=True,
                                    group_id=grp_id,
                                    stack_slot=slot_idx,
                                )
                            )
                        occupied_ranges.append((first_tok.start, shared_end))
                        i = last_tok.idx + 2
                        continue
            i += 1

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
            r"\b([a-zçğıöşüâîû]{3,16})(?:\s+ve\s+|\s+)([a-zçğıöşüâîû]{3,16})\s+"
            r"(kanun(?:u|ları|larıdır)?|sıfat(?:ı|ından|ları|larıdır)?|ilke(?:si|leri|leridir)?|"
            r"kavram(?:ı|ları|larıdır)?|denge(?:si|sini|sidir)?|irade(?:si|sini|sidir)?|"
            r"sistem(?:i|leri|leridir)?|yöntem(?:i|leri|leridir)?|hormon(?:u|ları|larıdır)?|"
            r"mimari(?:si|sidir)?|yapı(?:sı|sıdır)?|hak(?:kı|ları|larıdır)?|"
            r"ilişki(?:si|sini|sidir)?|çelişki(?:si|sini|sidir)?|çatışma(?:sı|sını|sıdır)?|"
            r"ayrım(?:ı|ını|ıdır)?|fark(?:ı|ını|ıdır)?)\b",
            re.IGNORECASE | re.UNICODE,
        )
        contrast_pair_re = re.compile(
            r"\b([a-zçğıöşüâîû]{3,16})\s+(helal|hak|doğru|adil|meşru)[,\s]+"
            r"([a-zçğıöşüâîû]{3,16})\s+(haram|batıl|yanlış|zulüm|gayrimeşru)\b",
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

            # Kalıp 2: Bağlaçlı veya İlişkisel İkili Kavram Tamlamaları ("X ve Y kanunlarıdır...", "ezen ezilen ilişkisi...")
            m_conj = conj_pair_re.search(win_text)
            if m_conj and m_conj.start() < len(str(active_segments[i].get("text", ""))) + 6:
                c1, c2, head_w = m_conj.group(1), m_conj.group(2), m_conj.group(3)
                stop_ignore = {
                    "bu", "şu", "o", "bir", "her", "hem", "ne", "çok", "daha", "en",
                    "için", "gibi", "kadar", "olan", "olarak", "böyle", "şöyle", "kendi",
                }
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
                                continue

            # Kalıp 3: Karşıt / Hüküm İkilileri ("ticareti helal, faizi haram kılmıştır" -> "TİCARET HELAL" / "FAİZ HARAM")
            m_contrast = contrast_pair_re.search(win_text)
            if m_contrast and m_contrast.start() < len(str(active_segments[i].get("text", ""))) + 6:
                n1, p1, n2, p2 = m_contrast.group(1), m_contrast.group(2), m_contrast.group(3), m_contrast.group(4)
                key = to_turkish_lower(f"{n1}_{n2}")
                if seg_st - seen_groups.get(key, -999.0) >= 90.0:
                    tok1 = self._find_word_in_range(word_stream, i, min(n_segs - 1, i + 1), n1)
                    tok2 = (
                        self._find_word_in_range(word_stream, tok1.seg_idx, min(n_segs - 1, tok1.seg_idx + 2), n2, after_word_idx=tok1.idx)
                        if tok1
                        else None
                    )
                    if tok1 and tok2 and (tok2.start - tok1.start) <= 6.0:
                        end_tok = self._find_sentence_end_word(word_stream, tok2, min(n_segs - 1, tok2.seg_idx + 1))
                        shared_end = round(min(tok2.end + 2.2, max(tok2.end + 0.55, end_tok.end)), 2)
                        if not is_range_busy(tok1.start, shared_end):
                            seen_groups[key] = seg_st
                            grp_id = f"grp_contrast_pair_{len(seen_groups):02d}"
                            stem1 = n1[:-1] if len(n1) >= 5 and to_turkish_lower(n1)[-1] in ("ı", "i", "u", "ü") else n1
                            stem2 = n2[:-1] if len(n2) >= 5 and to_turkish_lower(n2)[-1] in ("ı", "i", "u", "ü") else n2
                            lbl1 = to_turkish_upper(f"{stem1} {p1}")
                            lbl2 = to_turkish_upper(f"{stem2} {p2}")
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
                                        text_secondary="İkili Karşılaştırma",
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
        chapter_boundaries: Optional[List[float]] = None,
    ) -> None:
        """
        Katman 1: Her türlü video konusu (Tıp, Yazılım, Tarih, Ekonomi, Psikoloji, Vlog vb.)
        için bölüm-hizalı (chapter-aligned) 140 kelimelik + 25 kelimelik örtüşmeli (sliding-window)
        pencereleri LLM'e göndererek eksik kalan semantik olayları konuşulan kelimelere %100 sadık
        şekilde çıkarır (PROB-1.2, PROB-1.3, PROB-2.4).
        """
        if not word_stream or not self.gemini:
            return

        from services.gemini_client import GeminiClient

        chunk_size = 140
        overlap = 25
        step = max(40, chunk_size - overlap)
        max_chunks = max(30, int(video_duration / 22.0))
        chunks: List[List[WordToken]] = []

        # Bölüm sınırları varsa her bölüm içinde 140 kelimelik örtüşmeli pencereler üret
        bounds = chapter_boundaries if (chapter_boundaries and len(chapter_boundaries) >= 2) else [0.0, video_duration]
        for b_idx in range(len(bounds) - 1):
            c_st, c_en = bounds[b_idx], bounds[b_idx + 1]
            ch_tokens = [t for t in word_stream if c_st <= t.start < c_en]
            if not ch_tokens:
                continue
            for start_i in range(0, len(ch_tokens), step):
                sub = ch_tokens[start_i : start_i + chunk_size]
                if len(sub) < 8:
                    continue
                w_start, w_end = sub[0].start, sub[-1].end
                win_trigs = [t for t in triggers if w_start <= t.start_sec <= w_end]
                unique_groups = len({t.group_id if t.group_id else t.event_id for t in win_trigs})
                # Pencere içindeki en büyük boşluğu (gap) hesapla
                sorted_ts = sorted([w_start] + [t.start_sec for t in win_trigs] + [w_end])
                max_gap = max((sorted_ts[k + 1] - sorted_ts[k]) for k in range(len(sorted_ts) - 1)) if len(sorted_ts) > 1 else (w_end - w_start)
                if unique_groups < 3 or max_gap >= 25.0:
                    chunks.append(sub)
                if len(chunks) >= max_chunks:
                    break
            if len(chunks) >= max_chunks:
                break

        def _resolve_llm_word_index(raw_idx: int, label_str: str, window_tokens: List[WordToken], min_idx: int = 0) -> int:
            if 0 <= raw_idx < len(word_stream) and raw_idx >= min_idx:
                # Eğer indeks kelimesi etiketle makul düzeyde örtüşüyorsa doğrudan kabul et
                cand_tok = word_stream[raw_idx]
                lbl_words = [w for w in label_str.split() if len(w) >= 2]
                if not lbl_words or VerbatimTranscriptValidator.word_similarity_score(lbl_words[0], cand_tok.clean) >= 0.65:
                    return raw_idx
            # Aksi halde pencere içinde min_idx sonrasında en yüksek morfolojik benzerliğe sahip kelimeyi bul
            lbl_first = to_turkish_lower(label_str.split()[0]) if label_str and label_str.split() else ""
            if not lbl_first:
                return raw_idx if (0 <= raw_idx < len(word_stream)) else -1
            best_tok_idx = -1
            best_sim = 0.0
            for tok_cand in window_tokens:
                if tok_cand.idx < min_idx:
                    continue
                sim = VerbatimTranscriptValidator.word_similarity_score(lbl_first, tok_cand.clean)
                if sim > best_sim:
                    best_sim = sim
                    best_tok_idx = tok_cand.idx
                    if sim >= 0.92:
                        break
            if best_sim >= 0.72 and best_tok_idx >= 0:
                return best_tok_idx
            return raw_idx if (0 <= raw_idx < len(word_stream) and raw_idx >= min_idx) else -1

        for chunk in chunks:
            indexed_text = " ".join(f"[w{t.idx}|{t.start:.1f}] {t.raw}" for t in chunk)
            prompt = (
                "Sen profesyonel bir kurgu yönetmenisin. Aşağıda bir videonun kelime indeksli transkript kesiti verilmiştir.\n"
                "GÖREVİN: Bu kesitte konuşmacının vurguladığı önemli kavramları şu tiplerde JSON dizisi olarak çıkarmaktır:\n"
                "- 'PERSON_INTRODUCTION': Sadece gerçek bir kişi/bilim insanı/düşünür tanıtılıyorsa.\n"
                "- 'WORK_INTRODUCTION': Sadece somut bir kitap/eser/kanun/sure/eser adı tanıtılıyorsa (SADECE konuşulan eser adını yaz!).\n"
                "- 'PROGRESSIVE_LIST': Ardışık 3+ madde sıralanıyorsa (items dizisiyle).\n"
                "- 'PAIRED_TERMS': İki kavram birbirine paralel veya karşıt vurgulanıyorsa (items dizisiyle).\n"
                "- 'DEFINITION_CALLOUT': Tekil bir anahtar terim veya ilke tanımlanıyorsa.\n"
                "- 'KEY_POINT': Konuşmacının can alıcı ana fikri, kilit tespiti veya özellikle dikkat çektiği önemli argüman/cümle.\n\n"
                "KURALLAR:\n"
                "1. `text_primary` konuşmacının o an söylediği kelimelerle doğrudan ilişkili ve net bir İSİM/KAVRAM TAMLAMASI olmalıdır.\n"
                "2. 'ŞEY', 'KEZ', 'VARDIR', 'BUNLAR', 'EVET', 'ORAYA AYLIK PARA', 'İHTİMAL', 'ÜRETİYOR' gibi yarım cümle parçalarını veya çekimli fiilleri ASLA seçme!\n"
                "3. `items` alanında her madde için başlangıç kelime indeksini de verebilirsin: [{\"start_word_idx\": 14, \"text_primary\": \"MADDE 1\"}]\n\n"
                "Sadece JSON dizisi döndür:\n"
                '[{"action_type":"DEFINITION_CALLOUT","start_word_idx":12,"end_word_idx":13,"sentence_end_word_idx":18,"text_primary":"ÖRNEK KAVRAM"}]\n\n'
                f"TRANSKRİPT:\n{indexed_text}"
            )
            try:
                raw_resp = self.gemini.generate_text(prompt, max_retries=1)
                if not raw_resp:
                    continue
                parsed = GeminiClient.extract_balanced_json(raw_resp)
                if isinstance(parsed, dict) and isinstance(parsed.get("events"), list):
                    parsed = parsed["events"]
                if not isinstance(parsed, list):
                    continue

                for item in parsed:
                    try:
                        if not isinstance(item, dict):
                            continue
                        act = str(item.get("action_type", "")).strip()
                        sent_end_idx = int(item.get("sentence_end_word_idx", -1) or -1)

                        if act in ("PROGRESSIVE_LIST", "PAIRED_TERMS") and isinstance(item.get("items"), list):
                            sub_items = item["items"]
                            if len(sub_items) < 2:
                                continue
                            parent_sw = int(item.get("start_word_idx", -1) or -1)
                            forward_cursor = max(chunk[0].idx, parent_sw) if parent_sw >= 0 else chunk[0].idx
                            resolved_subs: List[Tuple[Optional[WordToken], str]] = []

                            for si in sub_items:
                                if isinstance(si, dict):
                                    raw_sw = int(si.get("start_word_idx", -1) or -1)
                                    raw_lbl = str(si.get("text_primary", "")).strip()
                                else:
                                    raw_sw = -1
                                    raw_lbl = str(si).strip()
                                clean_lbl = extract_turkish_semantic_title(raw_lbl, max_chars=28) or to_turkish_upper(raw_lbl)
                                if len(clean_lbl) < 2:
                                    continue
                                sw_idx = _resolve_llm_word_index(raw_sw, clean_lbl, chunk, min_idx=forward_cursor)
                                if 0 <= sw_idx < len(word_stream):
                                    resolved_subs.append((word_stream[sw_idx], clean_lbl))
                                    forward_cursor = sw_idx + 1
                                else:
                                    resolved_subs.append((None, clean_lbl))

                            # Monotonik doğrusal enterpolasyon: eşleşen çapalar arasındaki eksik kelimeleri hizala (PROB-2.4)
                            valid_subs: List[Tuple[WordToken, str]] = []
                            anchored_indices = [k for k, (tk, _) in enumerate(resolved_subs) if tk is not None]
                            if anchored_indices:
                                for k, (tk, lbl) in enumerate(resolved_subs):
                                    if tk is not None:
                                        valid_subs.append((tk, lbl))
                                    else:
                                        prev_a = max((a for a in anchored_indices if a < k), default=anchored_indices[0])
                                        next_a = min((a for a in anchored_indices if a > k), default=anchored_indices[-1])
                                        t_prev = resolved_subs[prev_a][0] or chunk[0]
                                        t_next = resolved_subs[next_a][0] or chunk[-1]
                                        interp_idx = min(
                                            len(word_stream) - 1,
                                            max(t_prev.idx + 1, int(round((t_prev.idx + t_next.idx) / 2.0))),
                                        )
                                        valid_subs.append((word_stream[interp_idx], lbl))

                            # Kesin artan zaman sırası garantisi
                            dedup_subs: List[Tuple[WordToken, str]] = []
                            last_used_idx = -1
                            for tk, lbl in valid_subs:
                                use_idx = max(tk.idx, last_used_idx + 1)
                                if use_idx < len(word_stream):
                                    dedup_subs.append((word_stream[use_idx], lbl))
                                    last_used_idx = use_idx

                            if len(dedup_subs) >= 2:
                                first_t = dedup_subs[0][0]
                                last_t = dedup_subs[-1][0]
                                end_t = (
                                    word_stream[sent_end_idx]
                                    if 0 <= sent_end_idx < len(word_stream) and sent_end_idx >= last_t.idx and (word_stream[sent_end_idx].end - last_t.start) <= 6.0
                                    else self._find_sentence_end_word(word_stream, last_t, last_t.seg_idx + 2)
                                )
                                shared_end = round(
                                    min(
                                        first_t.start + 18.0,
                                        last_t.end + 2.5,
                                        max(last_t.end + 0.65, end_t.end),
                                    ),
                                    2,
                                )
                                if not is_range_busy(first_t.start, shared_end):
                                    grp_id = f"grp_llm_{first_t.idx}"
                                    for slot_i, (st_tok, lbl) in enumerate(dedup_subs):
                                        item_st = round(st_tok.start, 2)
                                        item_en = round(max(item_st + 0.65, shared_end), 2)
                                        triggers.append(
                                            PlannedEditorialEvent(
                                                event_id=f"{grp_id}_{slot_i + 1}",
                                                chapter_id=0,
                                                action_type=act,
                                                start_sec=item_st,
                                                end_sec=item_en,
                                                text_primary=lbl,
                                                text_secondary=f"Sıralama {slot_i + 1}" if act == "PROGRESSIVE_LIST" else "İkili Kavram",
                                                semantic_priority=True,
                                                group_id=grp_id,
                                                stack_slot=slot_i,
                                            )
                                        )
                                    occupied_ranges.append((first_t.start, shared_end))
                        elif act in (
                            "PERSON_INTRODUCTION",
                            "WORK_INTRODUCTION",
                            "DEFINITION_CALLOUT",
                            "SINGLE_TERM",
                            "KEY_POINT",
                            "HIGHLIGHT",
                            "KEY_TERM_CALLOUT",
                        ):
                            raw_sw = int(item.get("start_word_idx", -1) or -1)
                            raw_lbl = str(item.get("text_primary", "")).strip()
                            lbl = (
                                to_turkish_upper(raw_lbl)
                                if act in ("PERSON_INTRODUCTION", "WORK_INTRODUCTION")
                                else extract_turkish_semantic_title(raw_lbl, max_chars=28)
                            )
                            if not lbl or len(lbl) < 3:
                                continue
                            sw_idx = _resolve_llm_word_index(raw_sw, lbl, chunk, min_idx=chunk[0].idx)
                            if not (0 <= sw_idx < len(word_stream)):
                                continue
                            if lbl in {"ŞEY", "KEZ", "DEFÂ", "VARDIR", "YOKTUR", "BUNLAR", "ONLAR", "ŞUNLAR", "EVET", "HAYIR", "YANİ", "FİLAN", "FALAN"}:
                                continue
                            if act not in ("PERSON_INTRODUCTION", "WORK_INTRODUCTION") and not self._is_valid_conceptual_callout(lbl):
                                continue
                            st_tok = word_stream[sw_idx]
                            end_t = (
                                word_stream[sent_end_idx]
                                if 0 <= sent_end_idx < len(word_stream) and sent_end_idx >= st_tok.idx and (word_stream[sent_end_idx].end - st_tok.start) <= 4.8
                                else self._find_sentence_end_word(word_stream, st_tok, st_tok.seg_idx + 2)
                            )
                            ev_st = round(st_tok.start, 2)
                            min_cps_dur = max(1.35, min(2.6, len(lbl) / 13.0 + 0.55))
                            ev_en = round(max(ev_st + min_cps_dur, min(ev_st + 3.8, end_t.end)), 2)
                            if is_range_busy(ev_st, ev_en) or ev_st - seen_terms.get(lbl, -999.0) < 60.0:
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
                                    text_secondary="Kavram Vurgusu" if act not in ("KEY_POINT", "HIGHLIGHT") else "Önemli Vurgu",
                                    primary_web_query_tr=wiki_q if act in ("PERSON_INTRODUCTION", "WORK_INTRODUCTION") else "",
                                    person_wiki_tr=wiki_q if act in ("PERSON_INTRODUCTION", "WORK_INTRODUCTION") else "",
                                    person_wiki_en=str(item.get("wiki_query_en") or wiki_q).strip()
                                    if act in ("PERSON_INTRODUCTION", "WORK_INTRODUCTION")
                                    else "",
                                    semantic_priority=True,
                                )
                            )
                            occupied_ranges.append((ev_st, ev_en))
                    except Exception as item_err:
                        logger.warning(f"[HolisticAnalyzer] LLM tekil öğe parse uyarısı: {item_err}")
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
        semantic_list: List[float] = []
        if tokens and video_duration >= 25.0:
            semantic_bounds = SemanticTransitionBoundaryDetector.detect_boundaries(
                word_stream=tokens,
                video_duration=video_duration,
                min_gap_sec=22.0,
            )
            if semantic_bounds:
                for sb in semantic_bounds:
                    if 8.0 < sb.timestamp < (video_duration - 8.0):
                        if not semantic_list or (sb.timestamp - semantic_list[-1]) >= 22.0:
                            semantic_list.append(round(sb.timestamp, 2))
                if semantic_list:
                    logger.info(
                        f"[HolisticAnalyzer] SemanticTransitionBoundaryDetector {len(semantic_list)} anlamsal geçiş sınırı tespit etti: "
                        f"{semantic_list}"
                    )

        # Semantik sınırları koru, ancak 125 saniyeden daha uzun boş kalan devasa aralıklar varsa
        # SADECE gerçek cümle sonlarında ve konu/özne dönüşümlerinde ara sınır ekle (PROB-6.2, PROB-6.3)
        full_bounds = sorted(set([0.0] + semantic_list + [round(video_duration, 2)]))
        max_allowed_chapter_span = 125.0
        refined_bounds: List[float] = [0.0]

        continuation_starts = (
            "orada ", "burada ", "işte bu ", "ama ", "fakat ", "çünkü ", "yani ", "ssk ve ",
            "bağ kur ", "ben ", "sen ", "o zaman ", "bakıyoruz ", "verdiğim ", "zararım ",
        )
        topic_pivot_starts = (
            "şimdi ", "peki ", "aksi halde ", "özel sigorta ", "sigorta kurumu ", "şu anda ",
            "bunun gibi ", "ikincisi ", "üçüncüsü ", "bir diğer ", "gelelim ", "kur'an", "bakara ",
        )

        for b_idx in range(len(full_bounds) - 1):
            span_start = refined_bounds[-1]
            span_end = full_bounds[b_idx + 1]
            span_dur = span_end - span_start

            if span_dur > max_allowed_chapter_span and len(active_segments) > 2:
                sub_divisions = max(2, int(round(span_dur / 90.0)))
                sub_step = span_dur / float(sub_divisions)
                for s_i in range(1, sub_divisions):
                    ideal_ts = span_start + s_i * sub_step
                    best_ts: Optional[float] = None
                    best_score = -999.0
                    for k in range(len(active_segments) - 1):
                        cur_txt = str(active_segments[k].get("text", "")).strip()
                        nxt_txt = to_turkish_lower(str(active_segments[k + 1].get("text", "")).strip())
                        ends_sentence = cur_txt.endswith((".", "!"))
                        if not ends_sentence:
                            continue
                        if any(nxt_txt.startswith(cs) for cs in continuation_starts):
                            continue
                        gap_start = float(active_segments[k].get("end", 0))
                        gap_end = float(active_segments[k + 1].get("start", gap_start))
                        mid_gap = (gap_start + gap_end) / 2.0
                        if mid_gap <= refined_bounds[-1] + 45.0 or mid_gap >= span_end - 35.0:
                            continue
                        dist = abs(mid_gap - ideal_ts)
                        if dist <= max(24.0, sub_step * 0.48):
                            pause_dur = min(1.2, max(0.0, gap_end - gap_start))
                            pivot_bonus = 6.0 if any(nxt_txt.startswith(tp) for tp in topic_pivot_starts) else 0.0
                            score = pause_dur * 3.5 + 4.0 + pivot_bonus - (dist / 15.0)
                            if score > best_score:
                                best_score = score
                                best_ts = round(mid_gap, 2)
                    if best_ts is not None and best_ts > refined_bounds[-1] + 45.0 and best_ts < span_end - 35.0:
                        refined_bounds.append(best_ts)

            if span_end > refined_bounds[-1] + 8.0 or b_idx == len(full_bounds) - 2:
                refined_bounds.append(round(span_end, 2))

        if refined_bounds[-1] != round(video_duration, 2):
            refined_bounds[-1] = round(video_duration, 2)
        return refined_bounds

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
          - Rastgele cümlelerin ilk 5 kelimesini kesen eski mekanik dolgu döngüsünü ASLA çalıştırmaz;
            yalnızca bölümde hiç tetikleyici yoksa Türkçe İsim Tamlaması + RAKE (Keyphrase) skorlayıcısıyla
            gerçek kavram öbeklerini kelime sınırlarına kilitleyerek ekler (PROB-1.1).
        """
        chapter_triggers = list(chapter_triggers or [])
        events: List[PlannedEditorialEvent] = []

        for idx, trig in enumerate(chapter_triggers):
            trig.chapter_id = chapter_id
            if not trig.event_id:
                trig.event_id = f"evt_ch{chapter_id}_{idx + 1:02d}"
            events.append(trig)

        # Eğer bölümde hiç semantik tetikleyici yakalanmadıysa, mekanik ilk-5-kelime yerine
        # Türkçe İsim Tamlaması + RAKE tabanlı anahtar kavram çıkarıcısını çalıştır (PROB-1.1)
        if not events and ch_segments:
            events.extend(self._extract_chapter_keyphrase_events(chapter_id, ch_start, ch_end, ch_segments))

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

    _FORBIDDEN_CALLOUT_WORDS: Set[str] = {
        "ben", "sen", "o", "biz", "siz", "onlar", "bana", "sana", "bize", "size",
        "benim", "senin", "onun", "bizim", "sizin", "kendi", "kendine", "bunu", "şunu",
        "onu", "bunun", "şunun", "buraya", "oraya", "şuraya", "burada", "orada", "şurada",
        "buradan", "oradan", "buralara", "oralara", "böyle", "şöyle", "öyle", "bir", "bu",
        "şu", "her", "hiç", "bazı", "kimi", "mı", "mi", "mu", "mü", "mıdır", "midir",
        "mudur", "müdür", "ne", "nasıl", "neden", "niçin", "niye", "hangi", "kim", "acaba",
        "kadar", "kadarsa", "diyor", "dedi", "der", "derler", "olur", "olmaz", "oldu",
        "olmadı", "olacak", "olursa", "olmazsa", "gelir", "gelmez", "gelirse", "gelmeyeceği",
        "gelip", "gider", "gidecek", "gitti", "var", "yok", "vardır", "yoktur", "varsa",
        "yoksa", "lazım", "gerekir", "gerekiyor", "değil", "eder", "ediyor", "etti",
        "edildiği", "yapılır", "yapılması", "verir", "veriyor", "verdiğim", "aldığım",
        "almak", "vermek", "çıkarıyor", "yatıracağım", "birikiyor", "dayanarak", "atarak",
        "bakıyoruz", "gördünüz", "adam", "hocalar", "şey", "şeyler", "başına", "başıma",
        "zararım", "zarara", "boşa", "günkü", "da", "de", "ki", "eğer", "ama", "fakat",
        "yani", "işte", "mesela", "örneğin", "zaten", "şimdi", "sonra", "önce", "daha",
        "çok", "az", "gibi", "için", "üzere", "üzerinden", "halde", "aksi", "olanlara",
        "biriktirmek", "yaşayacaksın", "düşünmemeliler", "paralar", "iş", "işler", "el",
        "belli", "caiz", "diye", "olup", "olarak", "ancak", "lakin", "çünkü", "ise",
        "ve", "veya", "ile", "kadar", "göre", "karşı", "en", "hem", "ya", "birbiriyle", "birbirine",
    }

    _FORBIDDEN_CALLOUT_SUFFIXES: Tuple[str, ...] = (
        "erek", "arak", "ıyor", "iyor", "uyor", "üyor", "acak", "ecek",
        "mış", "miş", "muş", "müş", "meli", "malı", "dığı", "diği",
        "duğu", "düğü", "tığı", "tiği", "tuğu", "tüğü", "acağı", "eceği",
        "yorsa", "mazsa", "mezse", "dikçe", "dıkça", "incelenir", "başlıyor",
        "yorsunuz", "ıyoruz", "iyoruz", "uyoruz", "üyoruz", "acaksınız", "eceksiniz",
    )

    _CONCEPTUAL_NOUN_HEADS: Set[str] = {
        "şirketi", "şirketleri", "kurumu", "kurumları", "hizmeti", "hizmetleri",
        "sistemi", "sistemleri", "ilkesi", "ilkeleri", "kanunu", "kanunları",
        "hukuku", "delili", "delilleri", "teorisi", "düzeni", "fonu", "fonları",
        "borsası", "bankası", "devleti", "mahkemesi", "sigortası", "dayanışması",
        "ticareti", "ahlakı", "felsefesi", "metodolojisi", "hiyerarşisi",
        "anayasası", "yasası", "yasaları", "maddesi", "ayeti", "suresi",
        "şeriatı", "fıtratı", "hakikati", "adaleti", "özgürlüğü", "mülkiyeti",
        "ekonomisi", "politikası", "eğitimi", "sağlığı", "güvencesi", "güvenliği",
        "sermayesi", "yatırımı", "sözleşmesi", "akdi", "fıkhı", "kelamı",
        "faaliyeti", "üretimi", "tüketimi", "dağılımı", "bölüşümü", "ilişkisi",
        "şartları", "kuralları", "hakları", "suçları", "davaları", "kararları",
        "unsurları", "esasları", "kapsamı", "kavramı", "kavramları", "modeli",
        "yöntemi", "yöntemleri", "analizi", "süreci", "yapısı", "teknolojisi",
        "mimarisi", "performansı",
    }

    @classmethod
    def _is_valid_conceptual_callout(cls, title: str) -> bool:
        toks = [to_turkish_lower(w.strip(".,:;!?()'\"")) for w in title.split() if w.strip(".,:;!?()'\"")]
        if not (1 <= len(toks) <= 4):
            return False
        for t in toks:
            if len(t) < 2 and not t.isdigit():
                return False
            if t in cls._FORBIDDEN_CALLOUT_WORDS:
                return False
            if any(t.endswith(suf) for suf in cls._FORBIDDEN_CALLOUT_SUFFIXES):
                return False
        return True

    def _extract_chapter_keyphrase_events(
        self,
        chapter_id: int,
        ch_start: float,
        ch_end: float,
        ch_segments: List[Dict[str, Any]],
    ) -> List[PlannedEditorialEvent]:
        """
        Bölüm içinde deterministik veya LLM tetikleyicisi bulunmadığında, cümlelerin ilk kelimelerini
        mekanik olarak kesmek yerine, yalnızca gerçek Türkçe İsim/Sıfat Tamlaması (örn. 'ÖZEL SİGORTA ŞİRKETLERİ',
        'KAMU HİZMETİ', 'SOSYAL GÜVENLİK KURUMU', 'BELİRSİZLİK İLKESİ', 'FON YATIRIM ŞİRKETLERİ')
        niteliği taşıyan kavramsal öbekleri çıkarır; uygun kavram yoksa boş döner (PROB-1.1).
        """
        from pipeline.theme_profiles import strip_turkish_genitive_safe

        word_stream = self._build_word_stream(ch_segments)
        if not word_stream:
            return []

        candidates: List[Tuple[float, WordToken, WordToken, str]] = []
        seen_titles: set = set(getattr(self, "_used_chapter_keyphrases", set()))
        n_toks = len(word_stream)

        for i in range(n_toks):
            for win_len in (3, 2):
                if i + win_len > n_toks:
                    continue
                span = word_stream[i : i + win_len]
                # Pencere içindeki kelimeler arasında cümle sonu, virgül veya uzun duraksama olmamalı
                if any(t.has_sentence_end or t.has_comma for t in span[:-1]):
                    continue
                if any((span[k + 1].start - span[k].end) > 0.35 for k in range(win_len - 1)):
                    continue
                head_norm = to_turkish_lower(strip_turkish_genitive_safe(span[-1].clean))
                is_conceptual_head = head_norm in self._CONCEPTUAL_NOUN_HEADS
                if not is_conceptual_head:
                    continue
                words_clean = [t.clean for t in span[:-1]] + [strip_turkish_genitive_safe(span[-1].clean)]
                raw_phrase = " ".join(words_clean)
                title = to_turkish_upper(raw_phrase)
                if not self._is_valid_conceptual_callout(title) or title in seen_titles:
                    continue
                score = win_len * 3.5 + sum(min(8, len(w)) for w in words_clean) * 0.4
                end_tok = self._find_sentence_end_word(
                    word_stream, span[-1], min(len(ch_segments) - 1, span[-1].seg_idx + 1)
                )
                seen_titles.add(title)
                candidates.append((score, span[0], end_tok, title))

        # Yalnızca çok kısa (1-3 segmentlik) tek bölümlü videolarda yedek çıkarıcıyı çalıştır
        if not candidates and ch_start == 0.0 and len(ch_segments) <= 3:
            for seg_idx, seg in enumerate(ch_segments):
                s_text = str(seg.get("text", "")).strip()
                if not s_text:
                    continue
                title = extract_turkish_semantic_title(s_text, max_chars=26, max_words=3)
                if not title or len(title) < 4 or title in seen_titles:
                    continue
                if not self._is_valid_conceptual_callout(title):
                    continue
                w_list = title.split()
                if not (2 <= len(w_list) <= 3):
                    continue
                start_tok = self._find_word_in_range(word_stream, max(0, seg_idx - 1), min(len(ch_segments) - 1, seg_idx + 1), w_list[0])
                if not start_tok:
                    continue
                end_tok = self._find_sentence_end_word(word_stream, start_tok, min(len(ch_segments) - 1, seg_idx + 1))
                seen_titles.add(title)
                candidates.append((len(w_list) * 2.0, start_tok, end_tok, title))

        candidates.sort(key=lambda x: x[0], reverse=True)
        picked: List[PlannedEditorialEvent] = []
        max_picks = 2 if (ch_start == 0.0 and len(ch_segments) <= 3) else 1
        for idx_c, (_, st_tok, en_tok, title) in enumerate(candidates):
            if len(picked) >= max_picks:
                break
            st_sec = round(st_tok.start, 2)
            if any(abs(st_sec - p.start_sec) < 12.0 for p in picked):
                continue
            en_sec = round(max(st_sec + 1.4, min(st_sec + 3.4, en_tok.end)), 2)
            if hasattr(self, "_used_chapter_keyphrases"):
                self._used_chapter_keyphrases.add(title)
            picked.append(
                PlannedEditorialEvent(
                    event_id=f"evt_ch{chapter_id}_kp_{idx_c + 1}",
                    chapter_id=chapter_id,
                    action_type="KEY_TERM_CALLOUT",
                    start_sec=st_sec,
                    end_sec=en_sec,
                    text_primary=title,
                    text_secondary=f"Bölüm {chapter_id}",
                    semantic_priority=True,
                )
            )
        return picked

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
        """
        Kelime düzeyinde kesim (Retake + Silence) filtrelemesi:
        Bir segmentin yalnızca bir kısmı kesilmişse (örn. cümle ortası retake), kesilen kelimeleri
        çıkarıp korunan kelimelerden temiz segment oluşturur. Böylece silinen hiçbir retake kelimesi
        yazı/görsel/liste tetikleyicisi üretemez!
        """
        active = []
        for s in segments:
            seg_words = s.get("words") or []
            if seg_words and cuts:
                kept_w = []
                for w in seg_words:
                    ws = float(w.get("start", 0.0) if isinstance(w, dict) else getattr(w, "start", 0.0))
                    we = float(w.get("end", ws) if isinstance(w, dict) else getattr(w, "end", ws))
                    wt = str(w.get("word", "") if isinstance(w, dict) else getattr(w, "word", "")).strip()
                    if not wt:
                        continue
                    w_mid = (ws + we) / 2.0
                    if any(c_st - 0.02 <= w_mid <= c_en + 0.02 for c_st, c_en in cuts):
                        continue
                    kept_w.append({"word": wt, "start": ws, "end": we})
                if not kept_w:
                    continue
                new_seg = dict(s)
                new_seg["words"] = kept_w
                new_seg["start"] = kept_w[0]["start"]
                new_seg["end"] = kept_w[-1]["end"]
                new_seg["text"] = " ".join(kw["word"] for kw in kept_w)
                active.append(new_seg)
                continue

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
