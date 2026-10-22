from typing import List, Dict, Any, Optional

try:
    import importlib
    pyd = importlib.import_module("pydantic")
    BaseModel = pyd.BaseModel
    Field = pyd.Field
except Exception:
    class BaseModel:
        def __init__(self, **kwargs):
            for cls_base in reversed(self.__class__.__mro__):
                if cls_base is object or cls_base is BaseModel:
                    continue
                for k, v in cls_base.__dict__.items():
                    if not k.startswith("_") and not callable(v):
                        setattr(self, k, v() if callable(v) else ( list(v) if isinstance(v, list) else (dict(v) if isinstance(v, dict) else v) ))
            for k, v in kwargs.items():
                setattr(self, k, v)
        def __getitem__(self, item):
            return getattr(self, item)
        def get(self, item, default=None):
            return getattr(self, item, default)
        def model_dump(self):
            out = {}
            for k, v in self.__dict__.items():
                if hasattr(v, "model_dump"):
                    out[k] = v.model_dump()
                elif isinstance(v, list):
                    out[k] = [x.model_dump() if hasattr(x, "model_dump") else x for x in v]
                else:
                    out[k] = v
            return out
    def Field(default_factory=None, **kwargs):
        return default_factory() if default_factory else None


class CutItem(BaseModel):
    id: str
    start: float
    end: float
    reason: str  # "silence", "gesture_dislike", "gesture_rewind", "user_command"
    source: str = "auto"  # "auto", "chat", "manual"
    command: Optional[str] = None


class OverlayItem(BaseModel):
    id: str
    type: str  # "text", "image", "sticker", "video", "gif"
    content: Optional[str] = None  # Metin veya resim açıklaması
    text: Optional[str] = None     # Frontend uyumlu metin alanı
    source: Optional[str] = None   # Resim URL'si veya MinIO yolu
    sourceUrl: Optional[str] = None
    font: Optional[str] = "Montserrat-Bold"
    fontFamily: Optional[str] = None
    fontSize: Optional[int] = 48
    color: Optional[str] = "#FFFFFF"
    backgroundColor: Optional[str] = "#00000080"
    timestamp: float = 0.0
    start: Optional[float] = None
    end: Optional[float] = None
    seqTimestamp: Optional[float] = None
    duration: float = 5.0
    preset: Optional[str] = None
    backgroundBox: Optional[bool] = None
    boxColor: Optional[str] = None
    boxOpacity: Optional[float] = None
    shape: Optional[str] = None
    anchorSlot: Optional[str] = None
    isTextBadge: Optional[bool] = None
    animation: Optional[str] = "pop-up"  # "pop-up", "fade", "slide-left", "bounce", "typewriter", "glitch", "blur-in", "zoom-crash"
    exitAnimation: Optional[str] = "fade"  # "fade", "pop-up", "slide-down", "slide-up", "scale-out", "none"
    loopAnimation: Optional[str] = "none"  # "none", "pulse", "float", "wiggle", "shake", "pendulum"
    keyframes: Optional[List[Dict[str, Any]]] = None
    position: List[str] = Field(default_factory=lambda: ["center", "bottom"])
    positionX: Optional[float] = None
    positionY: Optional[float] = None
    scale: Optional[float] = 1.0
    track_id: Optional[int] = 1
    trackId: Optional[int] = 1
    # Tipografi & Rozet (Pillow / ASS)
    strokeColor: Optional[str] = None
    strokeWidth: Optional[float] = 0.0
    outerStrokeColor: Optional[str] = None
    outerStrokeWidth: Optional[float] = 0.0
    fillType: Optional[str] = "solid"  # "solid", "gradient", "radial"
    gradientStart: Optional[str] = None
    gradientEnd: Optional[str] = None
    gradientAngle: Optional[float] = 45.0
    glowEnabled: Optional[bool] = False
    glowColor: Optional[str] = None
    glowRadius: Optional[float] = 0.0
    shadowColor: Optional[str] = None
    shadowBlur: Optional[float] = None
    shadowDistance: Optional[float] = 4.0
    shadowAngle: Optional[float] = 90.0
    boxStyle: Optional[str] = "none"  # "none", "pill", "rounded", "badge", "highlight-marker"
    boxBgColor: Optional[str] = None
    boxPadding: Optional[int] = 16
    borderRadius: Optional[int] = 24
    allCaps: Optional[bool] = False
    letterSpacing: Optional[float] = 0.0
    curveBend: Optional[float] = 0.0
    rotateX: Optional[float] = 0.0
    rotateY: Optional[float] = 0.0
    skewX: Optional[float] = 0.0
    skewY: Optional[float] = 0.0
    # Görsel Düzenleme, Photoshop Katman Ayarları & AI Arka Plan
    removeBg: Optional[bool] = False
    stickerBorder: Optional[bool] = False
    stickerBorderWidth: Optional[int] = 6
    stickerBorderColor: Optional[str] = "#FFFFFF"
    rotation: Optional[float] = 0.0
    maskShape: Optional[str] = "rect"  # "rect", "circle", "rounded", "star", "heart", "hexagon", "diamond"
    maskFeather: Optional[int] = 0
    chromaKeyColor: Optional[str] = None
    chromaKeySimilarity: Optional[float] = 0.35
    brightness: Optional[float] = 0.0
    contrast: Optional[float] = 0.0
    saturation: Optional[float] = 0.0
    warmth: Optional[float] = 0.0
    hue: Optional[float] = 0.0
    blur: Optional[float] = 0.0
    sharpen: Optional[float] = 0.0
    opacity: Optional[float] = 100.0
    flipH: Optional[bool] = False
    flipV: Optional[bool] = False
    dropShadow: Optional[bool] = False
    # Otonom Yönetmen (LlmDirector) tipografi & kurgu meta alanları — Pydantic'in bunları
    # sessizce atmaması için açıkça tanımlanır (yan sütun genişliği, satır aralığı, mini-tema rolü)
    maxWidthCqi: Optional[float] = None
    lineHeight: Optional[float] = None
    stackCount: Optional[int] = None
    subThemeRole: Optional[str] = None
    actionType: Optional[str] = None
    semanticPriority: Optional[bool] = None


class SuggestionItem(BaseModel):
    id: str
    type: str  # "text_callout", "image_broll"
    title: str
    content: str
    sourceUrl: Optional[str] = None
    timestamp: float
    duration: float = 4.0
    reason: str
    status: str = "pending"  # "pending", "accepted", "rejected"


class ViralClipItem(BaseModel):
    id: str
    title: str
    start: float
    end: float
    duration: float
    targetFormat: str  # "9:16", "16:9"
    viralityScore: int  # 1-100
    reason: str


class RepurposingData(BaseModel):
    clips: List[ViralClipItem] = Field(default_factory=list)
    faceTrackingData: List[Dict[str, Any]] = Field(default_factory=list)


class SubtitleStyleConfig(BaseModel):
    preset: str = "tiktok_yellow"     # "tiktok_yellow", "cinematic_shadow", "opaque_banner", "neon_glow", "custom"
    fontFamily: str = "Montserrat-Bold"
    fontSize: int = 48
    textColor: str = "#FFFFFF"
    highlightColor: str = "#FFD700"
    strokeColor: str = "#000000"
    strokeWidth: float = 3.0
    shadowColor: str = "#00000080"
    shadowDistance: float = 3.0
    shadowBlur: float = 2.0
    backgroundColor: Optional[str] = None
    backgroundPadding: int = 12
    borderRadius: int = 8
    verticalPosition: float = 85.0     # %5 - %95
    allCaps: bool = False
    letterSpacing: float = 0.0


class BackgroundMusicConfig(BaseModel):
    url: Optional[str] = None
    title: Optional[str] = "Arka Plan Müziği"
    volume: float = 0.25
    autoDucking: bool = True
    duckingAmount: float = 0.15
    fadeIn: float = 1.0
    fadeOut: float = 2.0
    loop: bool = True


class ColorGradingConfig(BaseModel):
    brightness: float = 0.0
    contrast: float = 0.0
    saturation: float = 0.0
    temperature: float = 0.0
    hue: float = 0.0
    vignette: float = 0.0


class EdlSettings(BaseModel):
    targetFormat: str = "16:9"
    templateId: Optional[str] = None
    faceTrackingEnabled: bool = True
    audioEnhancement: bool = True
    gestureCommandsEnabled: bool = True
    subtitlesEnabled: bool = True
    smartPunchIn: bool = False
    normalizeAudio: bool = False
    playbackSpeed: float = 1.0
    subtitleStyle: Optional[SubtitleStyleConfig] = None
    backgroundMusic: Optional[BackgroundMusicConfig] = None
    colorGrading: Optional[ColorGradingConfig] = None


class EdlDocument(BaseModel):
    projectId: str
    videoId: Optional[str] = None
    sourceVideoUrl: Optional[str] = None
    duration: float = 0.0
    settings: EdlSettings = Field(default_factory=EdlSettings)
    transcript: Dict[str, Any] = Field(default_factory=dict)
    cuts: List[CutItem] = Field(default_factory=list)
    overlays: List[OverlayItem] = Field(default_factory=list)
    transitions: List[Dict[str, Any]] = Field(default_factory=list)
    sfxClips: List[Dict[str, Any]] = Field(default_factory=list)
    videoClips: List[Dict[str, Any]] = Field(default_factory=list)
    suggestions: List[SuggestionItem] = Field(default_factory=list)
    proactiveSuggestions: List[Dict[str, Any]] = Field(default_factory=list)
    repurposing: RepurposingData = Field(default_factory=RepurposingData)
    template: Dict[str, Any] = Field(default_factory=dict)
    audioPeaks: Optional[List[float]] = None
