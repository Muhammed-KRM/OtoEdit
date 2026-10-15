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

export interface OverlayItem {
  id: string;
  type: 'text' | 'image';
  content?: string;
  source?: string;
  timestamp: number;
  duration: number;
  font?: string;
  fontSize?: number;
  color?: string;
  backgroundColor?: string;
  animation?: 'fade' | 'pop-up' | 'slide-left' | 'slide-right' | 'slide-up' | 'slide-down' | 'none';
  exitAnimation?: 'fade' | 'pop-up' | 'slide-down' | 'slide-up' | 'scale-out' | 'none';
  position?: [string, string];
  positionX?: number; // 0-100 percentage
  positionY?: number; // 0-100 percentage
  scale?: number;
  trackId?: number;
  // Tipografi & Rozet (Pill, Stroke, Shadow)
  strokeColor?: string;
  strokeWidth?: number;
  shadowColor?: string;
  shadowBlur?: number;
  boxStyle?: 'none' | 'pill' | 'rounded' | 'badge';
  boxBgColor?: string;
  boxPadding?: number;
  borderRadius?: number;
  allCaps?: boolean;
  letterSpacing?: number;
  // Görsel Düzenleme & AI Arka Plan
  removeBg?: boolean;
  stickerBorder?: boolean;
  stickerBorderWidth?: number;
  stickerBorderColor?: string;
  rotation?: number; // -180 to 180 degrees
  maskShape?: 'rect' | 'circle' | 'rounded';
  chromaKeyColor?: string;
  chromaKeySimilarity?: number;
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
  type: 'image_broll' | 'text_highlight';
  title: string;
  content: string;
  sourceUrl?: string;
  timestamp: number;
  duration: number;
  reason?: string;
  status: 'pending' | 'accepted' | 'rejected';
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

export interface EdlSettings {
  targetFormat?: string;
  templateId?: string;
  faceTrackingEnabled?: boolean;
  audioEnhancement?: boolean;
  gestureCommandsEnabled?: boolean;
  subtitlesEnabled?: boolean;
  subtitleStyle?: SubtitleStyleConfig;
  backgroundMusic?: BackgroundMusicConfig;
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
  suggestions?: (SuggestionItem & { action?: 'add' | 'update' | 'remove' })[];
  settings?: Partial<EdlSettings>;
}
