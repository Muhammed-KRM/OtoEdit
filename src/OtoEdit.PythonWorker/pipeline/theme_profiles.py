"""
Kilitli Tasarım Jetonları (Locked ThemeProfile Registry) ve
Türkçe Morfo-Sözdizimsel Anahtar Terim/Başlık Çıkarıcı.
"""

from dataclasses import dataclass, field
import re
from typing import Dict, List


@dataclass(frozen=True)
class SubThemeRule:
    role_id: str                # "PERSON_OR_WORK_CARD" | "PROGRESSIVE_LIST" | "SINGLE_OR_PAIRED_TERM" | "TOPIC_TRANSITION"
    entry_animation: str        # "pop-up" | "typewriter" | "slide-up"
    exit_animation: str         # "fade"
    sfx_type: str               # "ding" | "keyboard" | "pop" | "whoosh"
    sfx_preset_id: str          # "ding-bright" | "keyboard-type" | "pop-bubble" | "whoosh-fast"
    sfx_name: str               # "Ding Parlak Çan (Tın)" | "Mekanik Klavye (Daktilo)" | "Pop Baloncuk" | "Whoosh Hızlı Geçiş"
    sfx_volume: float           # 0.14 .. 0.20
    sfx_duration: float         # 0.25 .. 0.90
    use_accent_color: bool = False


DEFAULT_ROLE_SUB_THEMES: Dict[str, SubThemeRule] = {
    # Mini-Tema A: Kişi / Eser Tanıtımı -> Aniden belirir (pop-up) + "Tın" sesi (ding-bright)
    "PERSON_OR_WORK_CARD": SubThemeRule(
        role_id="PERSON_OR_WORK_CARD",
        entry_animation="pop-up",
        exit_animation="fade",
        sfx_type="ding",
        sfx_preset_id="ding-bright",
        sfx_name="Ding Parlak Çan (Tın)",
        sfx_volume=0.18,
        sfx_duration=0.90,
        use_accent_color=False,
    ),
    # Mini-Tema B: Alt Alta Kümülatif Sıralama -> Yavaşça yazılır (typewriter) + Klavye sesi (keyboard-type)
    "PROGRESSIVE_LIST": SubThemeRule(
        role_id="PROGRESSIVE_LIST",
        entry_animation="typewriter",
        exit_animation="fade",
        sfx_type="keyboard",
        sfx_preset_id="keyboard-type",
        sfx_name="Mekanik Klavye (Daktilo)",
        sfx_volume=0.14,
        sfx_duration=0.45,
        use_accent_color=True,
    ),
    # Mini-Tema C: Tekil veya İkili Kavram Vurgusu -> Kayarak/Pop belirir (slide-up) + Tok Pop (pop-bubble)
    "SINGLE_OR_PAIRED_TERM": SubThemeRule(
        role_id="SINGLE_OR_PAIRED_TERM",
        entry_animation="slide-up",
        exit_animation="fade",
        sfx_type="pop",
        sfx_preset_id="pop-bubble",
        sfx_name="Pop Baloncuk (Kavram)",
        sfx_volume=0.15,
        sfx_duration=0.25,
        use_accent_color=False,
    ),
    # Mini-Tema D: Konu Bitimi / Sahne Geçişi -> Sola kayarak geçiş (smoothleft) + Swish Whoosh (Large 794558)
    "TOPIC_TRANSITION": SubThemeRule(
        role_id="TOPIC_TRANSITION",
        entry_animation="slide-left",
        exit_animation="fade",
        sfx_type="whoosh",
        sfx_preset_id="capcut-swish-large",
        sfx_name="Swish Whoosh (Large 794558)",
        sfx_volume=0.22,
        sfx_duration=0.81,
        use_accent_color=True,
    ),
}

ACTION_TO_SUB_THEME_ROLE: Dict[str, str] = {
    "PERSON_INTRODUCTION": "PERSON_OR_WORK_CARD",
    "WORK_INTRODUCTION": "PERSON_OR_WORK_CARD",
    "STAT_OR_ARTICLE_CALLOUT": "PERSON_OR_WORK_CARD",
    "CONCEPT_IMAGE_CARD": "PERSON_OR_WORK_CARD",
    "PROGRESSIVE_LIST": "PROGRESSIVE_LIST",
    "PAIRED_TERMS": "SINGLE_OR_PAIRED_TERM",
    "SINGLE_TERM": "SINGLE_OR_PAIRED_TERM",
    "ENUMERATION_CALLOUT": "SINGLE_OR_PAIRED_TERM",
    "DEFINITION_CALLOUT": "SINGLE_OR_PAIRED_TERM",
    "KEY_TERM_CALLOUT": "SINGLE_OR_PAIRED_TERM",
    "KEY_POINT": "SINGLE_OR_PAIRED_TERM",
    "HIGHLIGHT": "SINGLE_OR_PAIRED_TERM",
    "CHAPTER_TITLE_CARD": "TOPIC_TRANSITION",
    "TOPIC_TRANSITION": "TOPIC_TRANSITION",
}


@dataclass(frozen=True)
class ThemeProfile:
    id: str
    display_name: str
    preset_id: str
    font_family: str
    secondary_font_family: str
    title_font_size_1080p: int
    text_color_hex: str
    accent_color_hex: str
    secondary_accent_hex: str
    background_box: bool
    box_color_hex: str
    box_opacity: float
    border_color_hex: str
    border_width_px: int
    border_radius_px: int
    shadow_blur_px: int
    text_case: str  # "UPPERCASE_TR" | "TITLE_CASE_TR"
    max_chars_per_line: int
    max_lines: int
    entry_animation: str
    exit_animation: str
    allow_gifs: bool
    allow_emojis: bool
    min_gap_between_overlays_sec: float
    max_overlays_per_minute: float
    allowed_transitions: List[str] = field(default_factory=list)
    transition_duration_sec: float = 0.45
    allowed_sfx_map: Dict[str, dict] = field(default_factory=dict)
    stroke_color_hex: str = "#000000"
    stroke_width_px: int = 5


def resolve_sub_theme(theme_profile: ThemeProfile, action_type: str) -> SubThemeRule:
    """
    Verilen kurgusal olay tipi (action_type) için kilitli Mini-Tema kuralını döndürür.
    Böylece tüm videoda aynı rol her zaman %100 aynı animasyon ve aynı SFX ile çalışır.
    """
    role_key = ACTION_TO_SUB_THEME_ROLE.get(action_type, "SINGLE_OR_PAIRED_TERM")
    return DEFAULT_ROLE_SUB_THEMES.get(role_key, DEFAULT_ROLE_SUB_THEMES["SINGLE_OR_PAIRED_TERM"])


THEME_PROFILE_REGISTRY: Dict[str, ThemeProfile] = {
    "academic_lecture": ThemeProfile(
        id="academic_lecture",
        display_name="Akademik Ders, Felsefe & Hukuk/Bilim Anlatımı",
        preset_id="youtube_clean_stroke",
        font_family="Montserrat",
        secondary_font_family="Inter",
        title_font_size_1080p=52,
        text_color_hex="#FFFFFF",
        accent_color_hex="#FACC15",
        secondary_accent_hex="#38BDF8",
        background_box=False,
        box_color_hex="#0F172A",
        box_opacity=0.0,
        border_color_hex="#000000",
        border_width_px=0,
        border_radius_px=0,
        shadow_blur_px=10,
        text_case="UPPERCASE_TR",
        max_chars_per_line=22,
        max_lines=2,
        entry_animation="pop-up",
        exit_animation="fade",
        allow_gifs=False,
        allow_emojis=False,
        min_gap_between_overlays_sec=14.0,
        max_overlays_per_minute=4.5,
        allowed_transitions=["slideleft", "smoothleft"],
        transition_duration_sec=0.40,
        allowed_sfx_map={
            "TOPIC_TRANSITION": {"type": "whoosh", "presetId": "capcut-swish-large", "volume": 0.22},
            "CHAPTER_TITLE_CARD": {"type": "whoosh", "presetId": "capcut-swish-large", "volume": 0.22},
            "PERSON_INTRODUCTION": {"type": "ding", "presetId": "ding-bright", "volume": 0.18},
            "WORK_INTRODUCTION": {"type": "ding", "presetId": "ding-bright", "volume": 0.18},
            "STAT_OR_ARTICLE_CALLOUT": {"type": "ding", "presetId": "ding-bright", "volume": 0.18},
            "PROGRESSIVE_LIST": {"type": "keyboard", "presetId": "keyboard-type", "volume": 0.14},
            "PAIRED_TERMS": {"type": "pop", "presetId": "pop-bubble", "volume": 0.15},
            "SINGLE_TERM": {"type": "pop", "presetId": "pop-bubble", "volume": 0.15},
            "ENUMERATION_CALLOUT": {"type": "pop", "presetId": "pop-bubble", "volume": 0.15},
            "DEFINITION_CALLOUT": {"type": "pop", "presetId": "pop-bubble", "volume": 0.15},
            "KEY_TERM_CALLOUT": {"type": "pop", "presetId": "pop-bubble", "volume": 0.15},
            "CONCEPT_IMAGE_CARD": {"type": "ding", "presetId": "ding-bright", "volume": 0.18},
        },
        stroke_color_hex="#000000",
        stroke_width_px=5,
    ),
    "corporate_explainer": ThemeProfile(
        id="corporate_explainer",
        display_name="Kurumsal Sunum & İş Dünyası",
        preset_id="glass_card_modern",
        font_family="Inter",
        secondary_font_family="Roboto",
        title_font_size_1080p=52,
        text_color_hex="#FFFFFF",
        accent_color_hex="#10B981",
        secondary_accent_hex="#3B82F6",
        background_box=True,
        box_color_hex="#111827",
        box_opacity=0.88,
        border_color_hex="#1F2937",
        border_width_px=2,
        border_radius_px=16,
        shadow_blur_px=18,
        text_case="UPPERCASE_TR",
        max_chars_per_line=32,
        max_lines=2,
        entry_animation="slide-up",
        exit_animation="fade",
        allow_gifs=False,
        allow_emojis=False,
        min_gap_between_overlays_sec=18.0,
        max_overlays_per_minute=3.0,
        allowed_transitions=["slideleft", "smoothleft"],
        transition_duration_sec=0.40,
        allowed_sfx_map={
            "TOPIC_TRANSITION": {"type": "whoosh", "presetId": "capcut-swish-large", "volume": 0.22},
            "CHAPTER_TITLE_CARD": {"type": "whoosh", "presetId": "capcut-swish-large", "volume": 0.22},
            "PERSON_INTRODUCTION": {"type": "ding", "presetId": "ding-bright", "volume": 0.18},
            "WORK_INTRODUCTION": {"type": "ding", "presetId": "ding-bright", "volume": 0.18},
            "PROGRESSIVE_LIST": {"type": "keyboard", "presetId": "keyboard-type", "volume": 0.14},
            "KEY_TERM_CALLOUT": {"type": "pop", "presetId": "pop-bubble", "volume": 0.16},
            "CONCEPT_IMAGE_CARD": {"type": "whoosh", "presetId": "capcut-swish-large", "volume": 0.18},
            "STAT_OR_ARTICLE_CALLOUT": {"type": "ding", "presetId": "ding-bright", "volume": 0.18},
        },
    ),
    "tech_review": ThemeProfile(
        id="tech_review",
        display_name="Teknoloji, Yazılım & Ürün İncelemesi",
        preset_id="apple_minimal",
        font_family="Inter",
        secondary_font_family="Roboto",
        title_font_size_1080p=52,
        text_color_hex="#F9FAFB",
        accent_color_hex="#06B6D4",
        secondary_accent_hex="#8B5CF6",
        background_box=True,
        box_color_hex="#090D16",
        box_opacity=0.84,
        border_color_hex="#06B6D4",
        border_width_px=2,
        border_radius_px=18,
        shadow_blur_px=20,
        text_case="UPPERCASE_TR",
        max_chars_per_line=30,
        max_lines=2,
        entry_animation="slide-left",
        exit_animation="fade",
        allow_gifs=False,
        allow_emojis=True,
        min_gap_between_overlays_sec=14.0,
        max_overlays_per_minute=3.8,
        allowed_transitions=["slideleft", "smoothleft"],
        transition_duration_sec=0.40,
        allowed_sfx_map={
            "TOPIC_TRANSITION": {"type": "whoosh", "presetId": "capcut-swish-large", "volume": 0.22},
            "CHAPTER_TITLE_CARD": {"type": "whoosh", "presetId": "capcut-swish-large", "volume": 0.22},
            "PERSON_INTRODUCTION": {"type": "ding", "presetId": "ding-bright", "volume": 0.18},
            "WORK_INTRODUCTION": {"type": "ding", "presetId": "ding-bright", "volume": 0.18},
            "PROGRESSIVE_LIST": {"type": "keyboard", "presetId": "keyboard-type", "volume": 0.15},
            "KEY_TERM_CALLOUT": {"type": "pop", "presetId": "pop-bubble", "volume": 0.18},
            "CONCEPT_IMAGE_CARD": {"type": "whoosh", "presetId": "capcut-swish-large", "volume": 0.20},
            "STAT_OR_ARTICLE_CALLOUT": {"type": "ding", "presetId": "ding-bright", "volume": 0.20},
        },
    ),
    "cinematic_documentary": ThemeProfile(
        id="cinematic_documentary",
        display_name="Sinematik Belgesel & Tarih/Hikaye Anlatımı",
        preset_id="cinematic_serif",
        font_family="Playfair Display",
        secondary_font_family="Montserrat",
        title_font_size_1080p=54,
        text_color_hex="#FEF3C7",
        accent_color_hex="#D97706",
        secondary_accent_hex="#92400E",
        background_box=True,
        box_color_hex="#0C0A09",
        box_opacity=0.78,
        border_color_hex="#78350F",
        border_width_px=1,
        border_radius_px=8,
        shadow_blur_px=24,
        text_case="TITLE_CASE_TR",
        max_chars_per_line=34,
        max_lines=2,
        entry_animation="fade",
        exit_animation="fade",
        allow_gifs=False,
        allow_emojis=False,
        min_gap_between_overlays_sec=22.0,
        max_overlays_per_minute=2.5,
        allowed_transitions=["slideleft", "smoothleft"],
        transition_duration_sec=0.40,
        allowed_sfx_map={
            "TOPIC_TRANSITION": {"type": "whoosh", "presetId": "capcut-swish-large", "volume": 0.20},
            "CHAPTER_TITLE_CARD": {"type": "whoosh", "presetId": "capcut-swish-large", "volume": 0.20},
            "PERSON_INTRODUCTION": {"type": "ding", "presetId": "ding-bright", "volume": 0.16},
            "WORK_INTRODUCTION": {"type": "ding", "presetId": "ding-bright", "volume": 0.16},
            "PROGRESSIVE_LIST": {"type": "keyboard", "presetId": "keyboard-type", "volume": 0.14},
            "KEY_TERM_CALLOUT": {"type": "pop", "presetId": "pop-bubble", "volume": 0.14},
            "CONCEPT_IMAGE_CARD": {"type": "whoosh", "presetId": "capcut-swish-large", "volume": 0.18},
            "STAT_OR_ARTICLE_CALLOUT": {"type": "ding", "presetId": "ding-bright", "volume": 0.15},
        },
    ),
    "energetic_vlog": ThemeProfile(
        id="energetic_vlog",
        display_name="Yüksek Enerjili Vlog, Eğlence & Viral Shorts",
        preset_id="hormozi_pill",
        font_family="Montserrat",
        secondary_font_family="Anton",
        title_font_size_1080p=58,
        text_color_hex="#FFFFFF",
        accent_color_hex="#00E676",
        secondary_accent_hex="#FFD700",
        background_box=True,
        box_color_hex="#111111",
        box_opacity=0.90,
        border_color_hex="#00E676",
        border_width_px=3,
        border_radius_px=22,
        shadow_blur_px=16,
        text_case="UPPERCASE_TR",
        max_chars_per_line=26,
        max_lines=2,
        entry_animation="pop-up",
        exit_animation="zoom-out",
        allow_gifs=True,
        allow_emojis=True,
        min_gap_between_overlays_sec=9.0,
        max_overlays_per_minute=5.5,
        allowed_transitions=["slideleft", "smoothleft"],
        transition_duration_sec=0.40,
        allowed_sfx_map={
            "TOPIC_TRANSITION": {"type": "whoosh", "presetId": "whoosh-fast", "volume": 0.22},
            "CHAPTER_TITLE_CARD": {"type": "whoosh", "presetId": "whoosh-fast", "volume": 0.24},
            "PERSON_INTRODUCTION": {"type": "ding", "presetId": "ding-bright", "volume": 0.20},
            "WORK_INTRODUCTION": {"type": "ding", "presetId": "ding-bright", "volume": 0.20},
            "PROGRESSIVE_LIST": {"type": "keyboard", "presetId": "keyboard-type", "volume": 0.16},
            "KEY_TERM_CALLOUT": {"type": "pop", "presetId": "pop-bubble", "volume": 0.20},
            "CONCEPT_IMAGE_CARD": {"type": "whoosh", "presetId": "whoosh-fast", "volume": 0.22},
            "STAT_OR_ARTICLE_CALLOUT": {"type": "ding", "presetId": "ding-bright", "volume": 0.20},
            "EMPHASIS_STICKER": {"type": "pop", "presetId": "pop-bubble", "volume": 0.20},
        },
    ),
}


# Türkçe başlık sonuna veya tek başına asla gelemeyecek bağlaç, edat, zarf ve yarım fiil kelimeleri
TR_DANGLING_STOPWORDS = {
    "ve", "veya", "ile", "için", "gibi", "kadar", "göre", "karşı",
    "ama", "fakat", "ancak", "lakin", "çünkü", "dolayısıyla", "örneğin",
    "mesela", "yani", "ise", "de", "da", "ki", "bu", "şu", "o", "bir",
    "her", "en", "çok", "daha", "hiç", "hem", "ya", "ne", "nasıl", "neden",
    "olarak", "olup", "olduğu", "olmadığı", "olduğunu", "olmadığını", "olur",
    "vardır", "yoktur", "değildir", "demektir", "denir", "diyebiliriz",
    "düşü", "düşünün", "düşünelim", "bakalım", "görüyoruz", "biliyoruz",
    "intikal", "uğrardı", "şekilde", "anlamda", "noktada", "konuda", "konusu",
    "çevresinde", "kapsamında", "üzerinde", "içerisinde", "hakkında",
    "tarafından", "arasında", "sonucunda", "nedeniyle", "sebebiyle",
    "ilgili", "ilişkin", "itibariyle", "bakımından", "açısından",
    "oldu", "etti", "yaptı", "çıktı", "geldi", "gitti", "kaldı", "aldı",
    "şimdi", "böyle", "şöyle", "falan", "filan", "eti", "diye", "dedi", "diyor",
    "oraya", "buraya", "şuraya", "orada", "burada", "şurada", "bunun", "şunun", "onun",
    "ihtimal", "durumu", "üretiyor", "gerekiyor", "yapıyor", "ediyor", "oluyor", "geliyor",
    "mı", "mi", "mu", "mü", "eğer", "kendi", "size", "bize", "bana", "sana",
    "günkü", "acaba", "boşa", "zararım", "başıma", "başına", "olmadı", "olmazsa",
    "geliştirilerek", "profesyonelleştirerek", "yapılarak", "edilerek", "alınarak",
    "verilerek", "kurularak", "dayanarak", "başlayarak", "atarak", "diyerek",
}

# Sıfat-fiiller: Başlık ortasında veya 2-3 kelimelik bileşik sıfat/isim öbeklerinde ("KABUL EDİLEN", "EZEN VE EZİLEN") korunur;
# yalnızca tek başına veya uzun cümlenin sonunda nitelediği isim kesilmişse budanır.
TR_PARTICIPLES = {
    "eden", "edilen", "olan", "olmayan", "yapan", "yapılan",
    "gelen", "geçen", "bulunan", "verilen", "alınan", "kurulan", "sayılan",
}

# Sonu doğal '-n' ile biten ve tamlayan eki (-ın/-in/-un/-ün) aldığında yalnızca 2 harf kesilmesi gereken kökler
TR_N_ENDING_ROOTS = {
    "kanun", "sorun", "oyun", "boyun", "koyun", "beyin", "yayın", "yığın",
    "fırın", "tütün", "bütün", "düğün", "hüzün", "üstün", "aydın", "kadın",
    "yakın", "akın", "altın", "yangın", "baskın", "salgın", "sürgün", "vurgun",
    "uygun", "olgun", "uzun", "karın", "burun", "torun", "sütun", "mezun",
    "mümin", "zemin", "yemin", "temin", "tayin", "hain", "metin", "rehin",
    "zihin", "şahin", "vatan", "insan", "kur'an", "kuran", "vicdan", "zaman",
    "mekan", "imkan", "oran", "plan", "ilan", "divan", "düzen", "özen",
    "güven", "tören", "evren", "ergin", "kesin", "derin", "serin", "gelin",
}

TR_ROMAN_NUMERALS = {"I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"}
TR_CLAUSE_CLASSIFIERS = {
    "bendi", "bendinde", "şıkkı", "fıkrası", "maddesi", "grubu",
    "kategorisi", "tipi", "vitamini", "sınıfı", "bölümü", "kısmı",
}

TR_GENITIVE_SUFFIXES = (
    "nın", "nin", "nun", "nün", "ın", "in", "un", "ün",
    "ndan", "nden", "dan", "den", "nda", "nde",
)


def to_turkish_lower(text: str) -> str:
    """Türkçe İ -> i ve I -> ı dönüşümünü doğru yapan küçük harf fonksiyonu."""
    return text.replace("İ", "i").replace("I", "ı").lower()


def to_turkish_upper(text: str) -> str:
    """Türkçe i -> İ ve ı -> I dönüşümünü doğru yapan büyük harf fonksiyonu."""
    return text.replace("i", "İ").replace("ı", "I").upper()


def strip_turkish_genitive_safe(word: str) -> str:
    """
    Türkçe F5 morfotaktik kurallarına göre tamlayan ekini (-nın/-nin/-nun/-nün veya -ın/-in/-un/-ün)
    kelime kökünü ('kanun', 'sorun', 'oyun' vb.) ASLA bozmadan soyar.
    """
    w_clean = word.strip(".,:;")
    w_lower = to_turkish_lower(w_clean)

    if w_lower in ("bunun", "şunun", "onun"):
        return w_clean

    apostrophe_match = re.match(r"^(.+?)'(?:nın|nin|nun|nün|ın|in|un|ün)$", w_clean, flags=re.IGNORECASE)
    if apostrophe_match and len(apostrophe_match.group(1)) >= 3:
        return apostrophe_match.group(1)

    if len(w_lower) < 6:
        return word

    for double_suf in ("unun", "ünün", "ının", "inin"):
        if w_lower.endswith(double_suf):
            cand_2 = w_lower[:-2]
            cand_4 = w_lower[:-4]
            if cand_2 in TR_N_ENDING_ROOTS:
                return w_clean[:-2]
            if cand_4 in TR_N_ENDING_ROOTS:
                return w_clean[:-3]
            if len(w_lower) >= 8:
                return w_clean[:-3]

    for vowel_gen in ("nın", "nin", "nun", "nün"):
        if w_lower.endswith(vowel_gen):
            cand_2 = w_lower[:-2]
            if cand_2 in TR_N_ENDING_ROOTS:
                return w_clean[:-2]
            stem_3 = w_lower[:-3]
            if len(stem_3) >= 3 and stem_3[-1] in "aeıioöuüâîû":
                return w_clean[:-3]
            if len(cand_2) >= 5 and cand_2[-2] in "aeıioöuüâîû":
                return w_clean[:-2]

    return word


def extract_turkish_semantic_title(text: str, max_chars: int = 34, max_words: int = 7) -> str:
    """
    Cümleden ASLA kelime veya isim tamlaması ortasından kesilmeyen,
    maksimum `max_chars` uzunluğunda tam ve anlamlı bir Türkçe başlık çıkarır.
    3-4 harfli temel Türkçe kavramları ("FAİZ", "EZEN", "HAK", "SUÇ", "TIP", "ÖRF")
    ve '-n' ile biten kökleri ("KANUNUN" -> "KANUN") korur.
    """
    if not text or not text.strip():
        return ""

    raw_stripped = re.sub(r"\s+", " ", text.strip())

    # Eğer girdi zaten yapılandırılmış temiz bir başlık ise doğrudan büyük harfe çevir
    if len(raw_stripped) <= max_chars + 4 and (
        re.match(r"^(\d+[\.\)\-]|[IVX]{1,5}[\.\)\-]|PROF\.|DR\.|HZ\.|İMAM\b|MD\.)", to_turkish_upper(raw_stripped))
        or (":" in raw_stripped and len(raw_stripped.split()) <= 6)
        or ("&" in raw_stripped and len(raw_stripped.split()) <= 6)
        or ("(" in raw_stripped and ")" in raw_stripped and len(raw_stripped.split()) <= 6)
    ):
        return to_turkish_upper(raw_stripped[:max_chars + 4].strip())

    clauses = re.split(
        r"[!?;:—–]+|(?<!\d)(?<!\b[IVX])(?<!\b[IVX]{2})(?<!\b[IVX]{3})(?<!\b[IVX]{4})(?<!Prof)(?<!Dr)(?<!Hz)(?<!Md)\.(?!\w)",
        raw_stripped,
        flags=re.IGNORECASE,
    )
    clause = next((c.strip() for c in clauses if len(c.strip()) >= 2), raw_stripped)

    cleaned = re.sub(r"[^\w\sğüşıöçĞÜŞİÖÇâîûÂÎÛ0-9/'():&\-\.]", " ", clause)
    raw_tokens = cleaned.split()
    words: List[str] = []
    for idx_t, w in enumerate(raw_tokens):
        w_str = w.strip(",")
        if not w_str:
            continue
        w_no_dot = w_str.strip(".")
        nxt_low = to_turkish_lower(raw_tokens[idx_t + 1].strip(".,:;")) if idx_t + 1 < len(raw_tokens) else ""
        is_roman_or_clause = (
            to_turkish_upper(w_no_dot) in TR_ROMAN_NUMERALS
            or nxt_low in TR_CLAUSE_CLASSIFIERS
        )
        if len(w_no_dot) > 1 or w_no_dot.isdigit() or is_roman_or_clause:
            words.append(w_str if is_roman_or_clause or w_no_dot.isdigit() else w_no_dot)

    if not words:
        return ""

    filler_prefixes = {
        "arkadaşlar", "şimdi", "bakın", "tabii", "elbette", "burada", "oraya", "buraya",
        "dolayısıyla", "öncelikle", "mesela", "örneğin", "aslında", "peki",
        "evet", "bugün", "bugünkü", "dersimizde", "ve", "ama", "fakat",
        "ancak", "çünkü", "yani", "işte", "hatta", "bir", "bu", "şu",
        "ayrıntılı", "özellikle", "söz",
    }
    while len(words) > 1 and to_turkish_lower(words[0].strip(".,:;")) in filler_prefixes:
        words.pop(0)

    selected: List[str] = []
    for w in words[: max(1, int(max_words or 7))]:
        candidate = " ".join(selected + [w])
        if len(candidate) <= max_chars:
            selected.append(w)
        else:
            break

    if not selected:
        selected = [words[0][:max_chars]]

    # Sondaki asılı kalan bağlaç/edat/yarım fiilleri temizle
    while len(selected) > 1 and to_turkish_lower(selected[-1].strip(".,:;")) in TR_DANGLING_STOPWORDS:
        selected.pop()

    # Uzun (4+ kelimeli) cümle kırıntılarının sonunda asılı kalmış sıfat-fiili buda (ancak 2-3 kelimeli "KABUL EDİLEN", "EZEN VE EZİLEN" korunur)
    while len(selected) >= 4 and to_turkish_lower(selected[-1].strip(".,:;")) in TR_PARTICIPLES:
        selected.pop()

    # Son kelime tamlayan ekiyle ("Kanunun", "Mahkemenin") bitiyorsa F5 morfotaktik kuralıyla yalın hale indirge
    if selected:
        selected[-1] = strip_turkish_genitive_safe(selected[-1])

    while len(selected) > 1 and to_turkish_lower(selected[-1].strip(".,:;")) in TR_DANGLING_STOPWORDS:
        selected.pop()

    while len(selected) > 1 and to_turkish_lower(selected[0].strip(".,:;")) in TR_DANGLING_STOPWORDS:
        selected.pop(0)

    final_str = " ".join(selected).strip()
    if len(final_str) < 3 or len(selected) == 0:
        return ""
    if len(selected) == 1:
        single_low = to_turkish_lower(selected[0].strip(".,:;"))
        if single_low in TR_DANGLING_STOPWORDS or single_low in TR_PARTICIPLES:
            return ""
    if to_turkish_lower(final_str) in ("oraya aylık para", "aylık para", "konusu olmadığı", "söz konusu"):
        return ""

    return to_turkish_upper(final_str)


def detect_theme_profile_heuristic(full_transcript: str) -> ThemeProfile:
    """
    LLM erişilemediğinde veya hızlı ön-sınıflandırma gerektiğinde
    transkriptteki alan kelimelerinden en uygun ThemeProfile'ı seçer.
    """
    lower = to_turkish_lower(full_transcript or "")
    academic_kw = (
        "kanun", "mahkeme", "dava", "hukuk", "madde", "fıkra", "mevzuat",
        "teori", "hipotez", "ders", "sınav", "fakülte", "kavram", "literatür",
        "analiz", "formül", "denklem", "tarih", "felsefe", "anatomi", "tıp",
        "anayasa", "yargıtay", "danıştay", "muhakeme", "hüküm", "delil",
        "şeriat", "kelam", "fıkıh", "akaid", "mantık", "kozmolojik", "ontolojik",
        "gazali", "aristoteles", "farabi", "ibn sina", "içtihat", "icma", "kıyas",
    )
    corporate_kw = (
        "şirket", "yatırım", "bütçe", "strateji", "pazarlama", "müşteri",
        "büyüme", "finans", "rapor", "kurumsal", "yönetim", "satış", "bilanço",
    )
    tech_kw = (
        "yazılım", "kod", "algoritma", "yapay zeka", "uygulama", "donanım",
        "işlemci", "ekran kartı", "api", "sunucu", "veritabanı", "teknoloji",
    )
    doc_kw = (
        "belgesel", "yüzyıl", "imparatorluk", "savaş", "keşif", "doğa",
        "evren", "antik", "medeniyet", "hikaye",
    )

    scores = {
        "academic_lecture": sum(3 for k in academic_kw if k in lower),
        "corporate_explainer": sum(2 for k in corporate_kw if k in lower),
        "tech_review": sum(2 for k in tech_kw if k in lower),
        "cinematic_documentary": sum(2 for k in doc_kw if k in lower),
        "energetic_vlog": 1,
    }
    best_id = max(scores, key=lambda k: scores[k])
    return THEME_PROFILE_REGISTRY[best_id]
