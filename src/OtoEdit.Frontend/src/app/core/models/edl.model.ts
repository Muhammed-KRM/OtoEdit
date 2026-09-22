export interface CutItem {
  id: string;
  start: number;
  end: number;
  reason?: string;
  source?: string;
  command?: string;
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

export interface EdlSettings {
  targetFormat?: string;
  templateId?: string;
  faceTrackingEnabled?: boolean;
  audioEnhancement?: boolean;
  gestureCommandsEnabled?: boolean;
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
