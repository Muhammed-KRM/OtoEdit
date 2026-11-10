"""OtoEdit Python Worker Sabit Değerleri ve Pipeline Eşleşmeleri."""


class VideoFormat:
    YATAY_16_9 = 0
    DIKEY_9_16 = 1
    KARE_1_1 = 2

    TO_STRING = {
        0: "16:9",
        1: "9:16",
        2: "1:1"
    }


class PipelineStage:
    SES_IYILESTIRME = "SesIyilestirme"
    STT = "Stt"
    SESSIZLIK_ALGILAMA = "SessizlikAlgilama"
    KOMUT_ALGILAMA = "KomutAlgilama"
    YUZ_TAKIBI = "YuzTakibi"
    REPURPOSING = "Repurposing"
    ONERI_OLUSTURMA = "OneriOlusturma"
    EDL_OLUSTURMA = "EdlOlusturma"
    RENDER = "Render"
    TAMAMLANDI = "Tamamlandi"
    SENARYO_BIRLESTIRME = "SenaryoBirlestirme"
    SENARYO_DENETIMI = "SenaryoDenetimi"
    SENARYO_ONAYI_BEKLIYOR = "SenaryoOnayiBekliyor"

    # Kolaylık ve Takma Adlar (.NET PipelineAsamasi enum eşleşmeleri)
    RETAKE = "SessizlikAlgilama"
    VIRAL_KLIP = "Repurposing"
    BROLL = "OneriOlusturma"
    OTONOM_YONETMEN = "EdlOlusturma"



class RabbitMQConstants:
    # Gelen Mesajlar (.NET -> Python)
    EXCHANGE_VIDEO_UPLOADED = "VideoUploadedEvent"
    QUEUE_VIDEO_UPLOADED = "video-uploaded"

    EXCHANGE_RENDER_REQUESTED = "RenderRequestedEvent"
    QUEUE_RENDER_REQUESTED = "render-requested"

    EXCHANGE_SCENARIO_REVISION_REQUESTED = "ScenarioRevisionRequestedEvent"
    QUEUE_SCENARIO_REVISION_REQUESTED = "scenario-revision-requested"

    EXCHANGE_SCENARIO_APPROVED = "ScenarioApprovedEvent"
    QUEUE_SCENARIO_APPROVED = "scenario-approved"

    # Giden Mesajlar (Python -> .NET MassTransit)
    EXCHANGE_STAGE_CHANGED = "PipelineStageChangedEvent"
    EXCHANGE_ANALYSIS_COMPLETED = "AnalysisCompletedEvent"
    EXCHANGE_SCENARIO_APPROVAL_REQUIRED = "ScenarioApprovalRequiredEvent"
    EXCHANGE_PIPELINE_ERROR = "PipelineErrorEvent"
    EXCHANGE_RENDER_COMPLETED = "RenderCompletedEvent"


# El hareketi ve ses komutu arasındaki izin verilen azami zaman farkı (saniye)
GESTURE_VOICE_SYNC_TOLERANCE_SECONDS = 2.0
