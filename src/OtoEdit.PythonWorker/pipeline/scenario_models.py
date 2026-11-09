"""
Otonom Kurgu Senaryosu (Master Editing Script) Veri Modelleri.
5 Aşamalı Hiyerarşik Map-Reduce + Başeditör Denetim (Critic-Refiner) +
İnsan-Döngüde Onay/Revizyon (Human-in-the-Loop) mimarisinin veri yapılarını tanımlar.
"""

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass
class SceneBoundary:
    """İki sahne (parça) arasındaki retorik/anlamsal [geçiş] noktasını temsil eder."""
    boundary_id: str
    timestamp: float
    sentence_a_end: float
    sentence_b_start: float
    before_word_idx: int
    after_word_idx: int
    sentence_a_preview: str
    sentence_b_preview: str
    category: str
    reason: str
    transition_type: str = "slideleft"
    duration: float = 0.40

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SceneBoundary":
        return cls(
            boundary_id=str(data.get("boundary_id", "tr_1")),
            timestamp=float(data.get("timestamp", 0.0)),
            sentence_a_end=float(data.get("sentence_a_end", data.get("timestamp", 0.0))),
            sentence_b_start=float(data.get("sentence_b_start", data.get("timestamp", 0.0))),
            before_word_idx=int(data.get("before_word_idx", 0)),
            after_word_idx=int(data.get("after_word_idx", 0)),
            sentence_a_preview=str(data.get("sentence_a_preview", "")),
            sentence_b_preview=str(data.get("sentence_b_preview", "")),
            category=str(data.get("category", "RHETORICAL_PIVOT")),
            reason=str(data.get("reason", "")),
            transition_type=str(data.get("transition_type", "slideleft")),
            duration=float(data.get("duration", 0.40)),
        )


@dataclass
class PlannedScenarioItem:
    """Bir sahne (parça) içindeki tekil kurgu olayını (yazı, portre/eser resmi, liste, ikili kavram) temsil eder."""
    item_id: str
    scene_id: int
    action_type: str
    start_word_idx: int
    end_word_idx: int
    start_sec: float
    end_sec: float
    text_primary: str
    text_secondary: str = ""
    wiki_query_tr: str = ""
    wiki_query_en: str = ""
    stock_query_en: str = ""
    group_id: str = ""
    stack_slot: Optional[int] = None
    semantic_priority: bool = True
    rationale: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PlannedScenarioItem":
        slot_val = data.get("stack_slot")
        return cls(
            item_id=str(data.get("item_id", "")),
            scene_id=int(data.get("scene_id", 1)),
            action_type=str(data.get("action_type", "KEY_TERM_CALLOUT")),
            start_word_idx=int(data.get("start_word_idx", 0)),
            end_word_idx=int(data.get("end_word_idx", 0)),
            start_sec=float(data.get("start_sec", 0.0)),
            end_sec=float(data.get("end_sec", 0.0)),
            text_primary=str(data.get("text_primary", "")),
            text_secondary=str(data.get("text_secondary", "")),
            wiki_query_tr=str(data.get("wiki_query_tr", "")),
            wiki_query_en=str(data.get("wiki_query_en", "")),
            stock_query_en=str(data.get("stock_query_en", "")),
            group_id=str(data.get("group_id", "")),
            stack_slot=int(slot_val) if slot_val is not None else None,
            semantic_priority=bool(data.get("semantic_priority", True)),
            rationale=str(data.get("rationale", "")),
        )


@dataclass
class SceneChunkPlan:
    """Videonun iki [geçiş] arasındaki tek bir parçasının (sahnesinin) kurgu senaryosu."""
    scene_id: int
    title_tr: str
    start_sec: float
    end_sec: float
    start_word_idx: int
    end_word_idx: int
    transcript_text: str
    narrative_role: str = "BODY_EXPLANATION"
    key_terms: List[str] = field(default_factory=list)
    items: List[PlannedScenarioItem] = field(default_factory=list)
    transition_after: Optional[SceneBoundary] = None
    status: str = "completed"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scene_id": self.scene_id,
            "title_tr": self.title_tr,
            "start_sec": round(self.start_sec, 2),
            "end_sec": round(self.end_sec, 2),
            "start_word_idx": self.start_word_idx,
            "end_word_idx": self.end_word_idx,
            "transcript_text": self.transcript_text,
            "narrative_role": self.narrative_role,
            "key_terms": list(self.key_terms),
            "items": [it.to_dict() for it in self.items],
            "transition_after": self.transition_after.to_dict() if self.transition_after else None,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SceneChunkPlan":
        tr_after = data.get("transition_after")
        return cls(
            scene_id=int(data.get("scene_id", 1)),
            title_tr=str(data.get("title_tr", "")),
            start_sec=float(data.get("start_sec", 0.0)),
            end_sec=float(data.get("end_sec", 0.0)),
            start_word_idx=int(data.get("start_word_idx", 0)),
            end_word_idx=int(data.get("end_word_idx", 0)),
            transcript_text=str(data.get("transcript_text", "")),
            narrative_role=str(data.get("narrative_role", "BODY_EXPLANATION")),
            key_terms=[str(k) for k in data.get("key_terms", [])],
            items=[PlannedScenarioItem.from_dict(x) for x in data.get("items", [])],
            transition_after=SceneBoundary.from_dict(tr_after) if isinstance(tr_after, dict) else None,
            status=str(data.get("status", "completed")),
        )


@dataclass
class CritiqueRevision:
    """Başeditör (Critic) AI'ın veya kullanıcının senaryo üzerinde istediği tekil düzeltme emri."""
    action: str  # "REMOVE" | "MODIFY" | "ADD" | "REMOVE_TRANSITION" | "ADD_TRANSITION"
    target_id: str = ""
    scene_id: int = 1
    action_type: str = "KEY_TERM_CALLOUT"
    start_word_idx: Optional[int] = None
    end_word_idx: Optional[int] = None
    text_primary: str = ""
    text_secondary: str = ""
    wiki_query_tr: str = ""
    wiki_query_en: str = ""
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CritiqueRevision":
        sw = data.get("start_word_idx")
        ew = data.get("end_word_idx")
        return cls(
            action=str(data.get("action", "MODIFY")).upper().strip(),
            target_id=str(data.get("target_id", data.get("target_event_id", ""))),
            scene_id=int(data.get("scene_id", 1)),
            action_type=str(data.get("action_type", "KEY_TERM_CALLOUT")),
            start_word_idx=int(sw) if sw is not None else None,
            end_word_idx=int(ew) if ew is not None else None,
            text_primary=str(data.get("text_primary", data.get("new_text_primary", ""))),
            text_secondary=str(data.get("text_secondary", data.get("new_text_secondary", ""))),
            wiki_query_tr=str(data.get("wiki_query_tr", "")),
            wiki_query_en=str(data.get("wiki_query_en", "")),
            reason=str(data.get("reason", "")),
        )


@dataclass
class CritiqueReport:
    """Başeditör (Critic) AI'ın senaryo denetim raporu."""
    iteration: int
    is_approved: bool
    overall_score: int
    summary_feedback: str
    revisions: List[CritiqueRevision] = field(default_factory=list)
    applied_changes_log: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "iteration": self.iteration,
            "is_approved": self.is_approved,
            "overall_score": self.overall_score,
            "summary_feedback": self.summary_feedback,
            "revisions": [r.to_dict() for r in self.revisions],
            "applied_changes_log": list(self.applied_changes_log),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CritiqueReport":
        return cls(
            iteration=int(data.get("iteration", 1)),
            is_approved=bool(data.get("is_approved", False)),
            overall_score=int(data.get("overall_score", 80)),
            summary_feedback=str(data.get("summary_feedback", "")),
            revisions=[CritiqueRevision.from_dict(r) for r in data.get("revisions", []) if isinstance(r, dict)],
            applied_changes_log=[str(c) for c in data.get("applied_changes_log", [])],
        )


@dataclass
class MasterEditingScript:
    """
    Tüm parçaların (sahnelerin), geçişlerin ve Başeditör AI / Kullanıcı denetim geçmişinin
    birleştiği Tam Kurgu Senaryosu.
    """
    project_id: str = ""
    video_id: str = ""
    theme_profile_id: str = "academic_lecture"
    theme_display_name: str = "Akademik Ders & Felsefe"
    video_duration: float = 0.0
    scenes: List[SceneChunkPlan] = field(default_factory=list)
    transitions: List[SceneBoundary] = field(default_factory=list)
    critique_history: List[CritiqueReport] = field(default_factory=list)
    iteration_count: int = 0
    is_approved: bool = False
    requires_user_approval: bool = False
    approval_status: str = "pending"  # "auto_approved" | "awaiting_user" | "user_approved" | "user_revised"
    last_critic_message: str = ""
    user_feedback_history: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "video_id": self.video_id,
            "theme_profile_id": self.theme_profile_id,
            "theme_display_name": self.theme_display_name,
            "video_duration": round(self.video_duration, 2),
            "scenes": [s.to_dict() for s in self.scenes],
            "transitions": [t.to_dict() for t in self.transitions],
            "critique_history": [c.to_dict() for c in self.critique_history],
            "iteration_count": self.iteration_count,
            "is_approved": self.is_approved,
            "requires_user_approval": self.requires_user_approval,
            "approval_status": self.approval_status,
            "last_critic_message": self.last_critic_message,
            "user_feedback_history": list(self.user_feedback_history),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MasterEditingScript":
        return cls(
            project_id=str(data.get("project_id", "")),
            video_id=str(data.get("video_id", "")),
            theme_profile_id=str(data.get("theme_profile_id", "academic_lecture")),
            theme_display_name=str(data.get("theme_display_name", "")),
            video_duration=float(data.get("video_duration", 0.0)),
            scenes=[SceneChunkPlan.from_dict(s) for s in data.get("scenes", []) if isinstance(s, dict)],
            transitions=[SceneBoundary.from_dict(t) for t in data.get("transitions", []) if isinstance(t, dict)],
            critique_history=[CritiqueReport.from_dict(c) for c in data.get("critique_history", []) if isinstance(c, dict)],
            iteration_count=int(data.get("iteration_count", 0)),
            is_approved=bool(data.get("is_approved", False)),
            requires_user_approval=bool(data.get("requires_user_approval", False)),
            approval_status=str(data.get("approval_status", "pending")),
            last_critic_message=str(data.get("last_critic_message", "")),
            user_feedback_history=[str(u) for u in data.get("user_feedback_history", [])],
        )
