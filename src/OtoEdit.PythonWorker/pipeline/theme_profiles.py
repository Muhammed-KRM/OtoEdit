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
        allowed_transitions=["smoothleft", "slideleft", "wipeleft", "fade", "dissolve"],
        transition_duration_sec=0.45,
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
        allowed_transitions=["smoothleft", "slideleft", "wipeleft", "fade"],
        transition_duration_sec=0.45,
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
        allowed_transitions=["smoothleft", "slideleft", "wipeleft", "circleopen"],
        transition_duration_sec=0.42,
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
        allowed_transitions=["smoothleft", "slideleft", "dissolve", "fade", "fadeblack"],
        transition_duration_sec=0.50,
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
        allowed_transitions=["smoothleft", "wipeleft", "slidedown", "circleopen", "fade"],
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


# Türkçe başlık sonuna asla gelemeyecek bağlaç, edat, zarf, yarım fiil ve tamlayan ekleri
TR_DANGLING_STOPWORDS = {
    "ve", "veya", "ile", "için", "gibi", "kadar", "göre", "karşı",
    "ama", "fakat", "ancak", "lakin", "çünkü", "dolayısıyla", "örneğin",
    "mesela", "yani", "ise", "de", "da", "ki", "bu", "şu", "o", "bir",
    "her", "en", "çok", "daha", "hiç", "hem", "ya", "ne", "nasıl", "neden",
    "olarak", "olan", "olup", "olduğu", "olduğunu", "olur", "olmaz",
    "vardır", "yoktur", "değildir", "demektir", "denir", "diyebiliriz",
    "düşü", "düşünün", "düşünelim", "bakalım", "görüyoruz", "biliyoruz",
    "eden", "edilen", "yapan", "yapılan", "gelen", "geçen", "bulunan",
    "intikal", "uğrardı", "şekilde", "anlamda", "noktada", "konuda",
    "çevresinde", "kapsamında", "üzerinde", "içerisinde", "hakkında",
    "tarafından", "arasında", "sonucunda", "nedeniyle", "sebebiyle",
    "ilgili", "ilişkin", "itibariyle", "bakımından", "açısından",
    "oldu", "etti", "yaptı", "çıktı", "geldi", "gitti", "kaldı", "aldı",
    "şimdi", "böyle", "şöyle", "falan", "filan", "eti", "diye", "dedi",
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


def extract_turkish_semantic_title(text: str, max_chars: int = 34) -> str:
    """
    Cümleden ASLA kelime veya isim tamlaması ortasından kesilmeyen,
    maksimum `max_chars` uzunluğunda tam ve anlamlı bir Türkçe başlık çıkarır.
    Örn:
      - "Hukuk Muhakemeleri Kanununun çevresinde şekillenen dava şartları..."
        -> "HUKUK MUHAKEMELERİ KANUNU"
      - "1. TENZİLİ (TEŞRİ) ŞERİAT" (zaten yapılandırılmış başlık)
        -> "1. TENZİLİ (TEŞRİ) ŞERİAT"
    """
    if not text or not text.strip():
        return ""

    raw_stripped = re.sub(r"\s+", " ", text.strip())

    # Eğer girdi zaten yapılandırılmış temiz bir başlık ise (örn. "1. ...", "PROF. ...", "KAVRAM: ...")
    # kelime içi tireleri (-), numaraları (1.) ve parantezleri koruyarak doğrudan büyük harfe çevir!
    if len(raw_stripped) <= max_chars + 4 and (
        re.match(r"^(\d+\.|PROF\.|DR\.|HZ\.|İMAM\b|MD\.)", to_turkish_upper(raw_stripped))
        or (":" in raw_stripped and len(raw_stripped.split()) <= 6)
        or ("&" in raw_stripped and len(raw_stripped.split()) <= 6)
        or ("(" in raw_stripped and ")" in raw_stripped and len(raw_stripped.split()) <= 6)
    ):
        return to_turkish_upper(raw_stripped[:max_chars + 4].strip())

    # Kelime içi tireleri (Kur'an-ı, Sünnet-i, Bürhan-ı) ve kısaltma noktalarını (1., Prof., Dr., Hz.)
    # bozmadan yalnızca cümle sonu noktalama işaretlerinden ayır
    clauses = re.split(
        r"[!?;:—–]+|(?<!\d)(?<!Prof)(?<!Dr)(?<!Hz)(?<!Md)\.(?!\w)",
        raw_stripped,
        flags=re.IGNORECASE,
    )
    clause = next((c.strip() for c in clauses if len(c.strip()) >= 6), raw_stripped)

    # Kelime içi tire (-), kesme işareti ('), parantez ve iki noktayı koru
    cleaned = re.sub(r"[^\w\sğüşıöçĞÜŞİÖÇ0-9/'():&\-]", " ", clause)
    words = [w for w in cleaned.split() if len(w) > 1 or w.isdigit()]
    if not words:
        return ""

    # Baştaki dolgu kelimelerini temizle ("Arkadaşlar", "Şimdi", "Bakın", "Dolayısıyla", "Ve" vb.)
    filler_prefixes = {
        "arkadaşlar", "şimdi", "bakın", "tabii", "elbette", "burada",
        "dolayısıyla", "öncelikle", "mesela", "örneğin", "aslında", "peki",
        "evet", "bugün", "bugünkü", "dersimizde", "ve", "ama", "fakat",
        "ancak", "çünkü", "yani", "işte", "hatta", "bir", "bu", "şu",
        "ayrıntılı", "özellikle",
    }
    while len(words) > 2 and to_turkish_lower(words[0].strip(".,:;")) in filler_prefixes:
        words.pop(0)

    # Maksimum 5 kelime ve max_chars sınırı içinde kalacak şekilde tam kelimeleri birleştir
    selected: List[str] = []
    for w in words[:5]:
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

    # Eğer son kelime tamlayan ekiyle ("Kanununun", "Mahkemenin", "Varlığın") bitiyorsa yalın hale indirge
    last_lower = to_turkish_lower(selected[-1])
    if last_lower.endswith(("nun", "nün", "nın", "nin")) and len(last_lower) >= 6:
        for suf in ("unun", "ünün", "ının", "inin", "nun", "nün", "nın", "nin"):
            if last_lower.endswith(suf) and len(selected[-1]) - len(suf) >= 3:
                stem_len = len(selected[-1]) - (3 if suf.startswith(("u", "ü", "ı", "i")) else len(suf))
                selected[-1] = selected[-1][:stem_len]
                break

    # Tekrar kontrol: son kelime hala stopword ise çıkar
    while len(selected) > 1 and to_turkish_lower(selected[-1].strip(".,:;")) in TR_DANGLING_STOPWORDS:
        selected.pop()

    # Baştaki kelime tekrar kontrol: stopword ise çıkar
    while len(selected) > 1 and to_turkish_lower(selected[0].strip(".,:;")) in TR_DANGLING_STOPWORDS:
        selected.pop(0)

    final_str = " ".join(selected).strip()
    if len(final_str) < 5 or len(selected) == 0:
        return ""
    if len(selected) == 1 and to_turkish_lower(selected[0]) in TR_DANGLING_STOPWORDS:
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
