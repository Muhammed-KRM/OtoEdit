from typing import List, Dict, Any, Optional

try:
    import importlib
    pyd = importlib.import_module("pydantic")
    BaseModel = pyd.BaseModel
    Field = pyd.Field
except Exception:
    class BaseModel:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
        def model_dump(self):
            return self.__dict__
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
    type: str  # "text", "image"
    content: Optional[str] = None  # Metin veya resim açıklaması
    source: Optional[str] = None   # Resim URL'si veya MinIO yolu
    font: Optional[str] = "Montserrat-Bold"
    fontSize: Optional[int] = 48
    color: Optional[str] = "#FFFFFF"
    backgroundColor: Optional[str] = "#00000080"
    timestamp: float
    duration: float = 5.0
    animation: Optional[str] = "pop-up"  # "pop-up", "fade", "slide-left"
    exitAnimation: Optional[str] = "fade"  # "fade", "pop-up", "slide-down", "slide-up", "scale-out", "none"
    position: List[str] = Field(default_factory=lambda: ["center", "bottom"])
    positionX: Optional[float] = None
    positionY: Optional[float] = None
    scale: Optional[float] = 1.0
    track_id: Optional[int] = 1


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


class EdlSettings(BaseModel):
    targetFormat: str = "16:9"
    templateId: Optional[str] = None
    faceTrackingEnabled: bool = True
    audioEnhancement: bool = True
    gestureCommandsEnabled: bool = True


class EdlDocument(BaseModel):
    projectId: str
    videoId: Optional[str] = None
    sourceVideoUrl: Optional[str] = None
    duration: float = 0.0
    settings: EdlSettings = Field(default_factory=EdlSettings)
    transcript: Dict[str, Any] = Field(default_factory=dict)
    cuts: List[CutItem] = Field(default_factory=list)
    overlays: List[OverlayItem] = Field(default_factory=list)
    suggestions: List[SuggestionItem] = Field(default_factory=list)
    repurposing: RepurposingData = Field(default_factory=RepurposingData)
    template: Dict[str, Any] = Field(default_factory=dict)
    audioPeaks: Optional[List[float]] = None
