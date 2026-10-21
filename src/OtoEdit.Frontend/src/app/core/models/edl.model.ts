export interface CutItem {
  id: string;
  start: number;
  end: number;
  reason?: string;
  source?: string;
  command?: string;
  /** Jump-Cut ince ayarı uygulanmadan önceki orijinal (AI) sınırlar */
  origStart?: number;
  origEnd?: number;
}

export interface OverlayKeyframe {
  id?: string;
  /** Katman başlangıcına göre saniye ofseti (0 .. duration) */
  timeOffset: number;
  x: number;
  y: number;
  scale: number;
  rotation: number;
  opacity: number;
  easing?: 'linear' | 'ease-in-out' | 'bounce';
}

export interface EdlTransition {
  id: string;
  /** İki klibin birleştiği kaynak saniye noktası */
  boundarySourceTime?: number;
  boundaryTime?: number;
  type:
    | 'fade'
    | 'fadeblack'
    | 'fadewhite'
    | 'wipeleft'
    | 'wiperight'
    | 'slideleft'
    | 'slideright'
    | 'slideup'
    | 'slidedown'
    | 'circleopen'
    | 'circleclose'
    | 'zoomin'
    | 'radial'
    | 'pixelize'
    | 'hlslice'
    | string;
  duration: number;
  autoSfxId?: string;
  action?: 'add' | 'update' | 'remove';
}

export interface EdlSfxClip {
  id: string;
  name: string;
  title?: string;
  category?: 'whoosh' | 'pop' | 'cinematic' | 'ui' | 'funny' | 'custom' | string;
  presetId?: string;
  sourceUrl?: string;
  synthPreset?: string;
  start: number;
  duration: number;
  volume?: number;
  fadeIn?: number;
  fadeOut?: number;
  peaks?: number[];
  action?: 'add' | 'update' | 'remove';
}

export interface VideoClipItem {
  id: string;
  start: number;
  end: number;
  visStart?: number;
  visEnd?: number;
  duration?: number;
  order?: number;
  isCut?: boolean;
  reason?: string;
  cutReason?: string;
  source?: string;
  sourceUrl?: string;
  title?: string;
  label?: string;
  speed?: number;
  action?: 'add' | 'update' | 'remove';
}

export interface OverlayItem {
  id: string;
  type: 'text' | 'image' | 'video' | 'sticker' | 'gif';
  content?: string;
  source?: string;
  originalSource?: string;
  timestamp: number;
  /** Görünür Sekans Zamanı (Ripple Timeline başlangıç saniyesi - 0ms kaymasız hizalama için) */
  seqTimestamp?: number;
  duration: number;
  /** Video katmanları (type === 'video') için: Tam ekran B-Roll (true) veya PiP (false) */
  fullScreen?: boolean;
  /** Video katmanları için ses seviyesi (0 - 100) */
  volume?: number;
  /** Video katmanları için kaynak video içindeki başlangıç ofseti (saniye) */
  trimStart?: number;
  font?: string;
  fontSize?: number;
  fontWeight?: string | number;
  italic?: boolean;
  underline?: boolean;
  textAlign?: 'left' | 'center' | 'right';
  lineHeight?: number;
  color?: string;
  backgroundColor?: string;
  // Gradyan Dolgu (Photoshop Gradient Overlay)
  fillType?: 'solid' | 'gradient' | 'radial';
  gradientStart?: string;
  gradientEnd?: string;
  gradientAngle?: number;
  // Zengin Giriş / Çıkış / Döngü Animasyonları
  animation?: 'fade' | 'pop-up' | 'bounce' | 'slide-left' | 'slide-right' | 'slide-up' | 'slide-down' | 'typewriter' | 'glitch' | 'blur-in' | 'zoom-crash' | 'flip-3d' | 'none';
  exitAnimation?: 'fade' | 'pop-up' | 'slide-down' | 'slide-up' | 'slide-left' | 'slide-right' | 'scale-out' | 'blur-out' | 'glitch-out' | 'none';
  loopAnimation?: 'none' | 'pulse' | 'float' | 'wiggle' | 'shake' | 'neon-flicker' | 'pendulum';
  position?: [string, string];
  positionX?: number; // 0-100 percentage
  positionY?: number; // 0-100 percentage
  scale?: number;
  trackId?: number;
  // Tipografi, Çift Kontur, Neon Glow & Rozet (Pill, Stroke, Shadow)
  strokeColor?: string;
  strokeWidth?: number;
  outerStrokeColor?: string;
  outerStrokeWidth?: number;
  glowEnabled?: boolean;
  glowColor?: string;
  glowRadius?: number;
  shadowColor?: string;
  shadowBlur?: number;
  shadowDistance?: number;
  shadowAngle?: number;
  boxStyle?: 'none' | 'pill' | 'rounded' | 'badge' | 'highlight-marker';
  boxBgColor?: string;
  boxPadding?: number;
  borderRadius?: number;
  allCaps?: boolean;
  letterSpacing?: number;
  presetId?: string;
  // Photoshop Deformasyon (Yay / Eğri Metin & 3D Perspektif)
  curveBend?: number; // -100 .. +100
  rotateX?: number;   // -75 .. +75 deg
  rotateY?: number;   // -75 .. +75 deg
  skewX?: number;     // -45 .. +45 deg
  skewY?: number;     // -45 .. +45 deg
  blendMode?: 'normal' | 'multiply' | 'screen' | 'overlay' | 'lighten' | 'darken' | 'difference';
  // Keyframe (Anahtar Kare ◆)
  keyframes?: OverlayKeyframe[];
  // Photoshop Görsel Düzenleme & AI Arka Plan
  removeBg?: boolean;
  stickerBorder?: boolean;
  stickerBorderWidth?: number;
  stickerBorderColor?: string;
  rotation?: number; // -180 to 180 degrees
  maskShape?: 'rect' | 'circle' | 'rounded' | 'star' | 'heart' | 'hexagon' | 'diamond';
  feather?: number;
  chromaKeyColor?: string;
  chromaKeySimilarity?: number;
  brightness?: number; // -100 .. +100
  contrast?: number;   // -100 .. +100
  saturation?: number; // -100 .. +100
  warmth?: number;     // -100 .. +100
  hue?: number;        // -180 .. +180
  blur?: number;       // 0 .. 50
  sharpen?: number;    // 0 .. 100
  opacity?: number;    // 0 .. 100
  flipH?: boolean;
  flipV?: boolean;
  dropShadow?: boolean;
  action?: 'add' | 'update' | 'remove';
}

export interface TranscriptWord {
  word: string;
  start: number;
  end: number;
}

export interface TranscriptSegment {
  start: number;
  end: number;
  text: string;
  words?: TranscriptWord[];
}

export interface TranscriptData {
  fullText: string;
  duration?: number;
  segments: TranscriptSegment[];
}

export interface ViralClipItem {
  id: string;
  title: string;
  start: number;
  end: number;
  duration: number;
  targetFormat: string;
  viralityScore: number;
  reason: string;
}

export interface SuggestionItem {
  id: string;
  type: 'image_broll' | 'text_highlight' | 'viral_hook' | 'transition_sfx' | 'sticker_callout' | 'audio_master' | 'smart_zoom' | 'text_template' | 'text_overlay' | 'sticker' | 'audio_enhance' | string;
  title: string;
  content: string;
  sourceUrl?: string;
  timestamp: number;
  /** Görünür Sekans Zamanı (Ripple Timeline başlangıç saniyesi - 0ms kaymasız hizalama için) */
  seqTimestamp?: number;
  duration: number;
  /** Video katmanları (type === 'video') için: Tam ekran B-Roll (true) veya PiP (false) */
  fullScreen?: boolean;
  /** Video katmanları için ses seviyesi (0 - 100) */
  volume?: number;
  /** Video katmanları için kaynak video içindeki başlangıç ofseti (saniye) */
  trimStart?: number;
  reason?: string;
  category?: string;
  confidence?: number;
  presetId?: string;
  templatePreset?: string;
  transitionType?: EdlTransition['type'];
  sfxPreset?: string;
  overlayPayload?: Partial<OverlayItem>;
  transitionPayload?: EdlTransition;
  sfxPayload?: EdlSfxClip;
  payload?: any;
  status: 'pending' | 'accepted' | 'rejected';
  action?: 'add' | 'update' | 'remove';
}

export interface SubtitleStyleConfig {
  preset: 'tiktok_yellow' | 'cinematic_shadow' | 'opaque_banner' | 'neon_glow' | 'custom';
  fontFamily: string;
  fontSize: number;
  textColor: string;
  highlightColor: string;
  strokeColor: string;
  strokeWidth: number;
  shadowColor: string;
  shadowDistance: number;
  shadowBlur: number;
  backgroundColor?: string;
  backgroundPadding?: number;
  borderRadius?: number;
  verticalPosition: number; // 5 - 95 (%)
  allCaps?: boolean;
  letterSpacing?: number;
}

export interface BackgroundMusicConfig {
  url?: string;
  title?: string;
  volume: number; // 0.0 - 1.0
  autoDucking: boolean;
  duckingAmount: number; // 0.05 - 0.5
  fadeIn: number;
  fadeOut: number;
  loop: boolean;
}

export interface ColorGradingConfig {
  brightness: number;
  contrast: number;
  saturation: number;
  temperature: number;
}

export interface EdlSettings {
  targetFormat?: string;
  templateId?: string;
  faceTrackingEnabled?: boolean;
  audioEnhancement?: boolean;
  normalizeAudio?: boolean;
  smartPunchIn?: boolean;
  rippleSyncOverlays?: boolean;
  clipSpeeds?: Record<string, number>;
  gestureCommandsEnabled?: boolean;
  subtitlesEnabled?: boolean;
  subtitleStyle?: SubtitleStyleConfig;
  backgroundMusic?: BackgroundMusicConfig;
  bgmVolume?: number;
  bgmAutoDuck?: boolean;
  colorGrading?: ColorGradingConfig;
  videoClips?: VideoClipItem[];
}

export interface EdlTemplate {
  logo?: string;
  logoPosition?: [string, string];
  speakerName?: string;
  speakerTitle?: string;
}

export interface EdlDto {
  projectId: string;
  versiyon: number;
  edl: EdlContent;
  guncellemeTarihi: string;
}

export interface EdlContent {
  projectId: string;
  videoId?: string;
  sourceVideoUrl?: string;
  duration?: number;
  settings?: EdlSettings;
  cuts?: CutItem[];
  overlays?: OverlayItem[];
  transitions?: EdlTransition[];
  sfxClips?: EdlSfxClip[];
  videoClips?: VideoClipItem[];
  transcript?: TranscriptData;
  repurposing?: {
    clips?: ViralClipItem[];
    faceTrackingData?: any[];
  };
  suggestions?: SuggestionItem[];
  template?: EdlTemplate;
  audioPeaks?: number[];
}

export interface EdlPatchDto {
  cuts?: (CutItem & { action?: 'add' | 'update' | 'remove' })[];
  overlays?: (OverlayItem & { action?: 'add' | 'update' | 'remove' })[];
  transitions?: (EdlTransition & { action?: 'add' | 'update' | 'remove' })[];
  sfxClips?: (EdlSfxClip & { action?: 'add' | 'update' | 'remove' })[];
  videoClips?: (VideoClipItem & { action?: 'add' | 'update' | 'remove' })[];
  suggestions?: (SuggestionItem & { action?: 'add' | 'update' | 'remove' })[];
  settings?: Partial<EdlSettings>;
}
