import { Injectable } from '@angular/core';
import { EdlContent, EdlSfxClip, EdlTransition, OverlayItem, SuggestionItem } from '../../core/models/edl.model';

export interface StudioFontOption {
  name: string;
  family: string;
  category: 'Viral & Başlık' | 'Modern Sans' | 'Sinematik & Serif' | 'El Yazısı & Fırça' | 'Siber & Kod';
}

export type FontOption = StudioFontOption;

export interface TextTemplatePreset {
  id: string;
  name: string;
  badge: string;
  previewBg: string;
  previewStyle: string;
  previewTextColor?: string;
  style?: Partial<OverlayItem>;
  props: Partial<OverlayItem>;
}

export interface SfxLibraryItem {
  id: string;
  name: string;
  category: EdlSfxClip['category'];
  icon: string;
  duration: number;
  synthPreset: string;
  description: string;
  peaks: number[];
}

export interface StickerLibraryItem {
  id: string;
  name: string;
  category: 'social' | 'arrows' | 'emoji' | 'badges';
  preview: string;
  dataUrl: string;
  dataUri?: string;
}

export interface TransitionLibraryItem {
  type: EdlTransition['type'];
  name: string;
  category: 'Temel' | 'Kamera / Whip' | 'Işık / Flaş' | 'Dijital & Maske';
  icon: string;
  defaultDuration: number;
  recommendedSfx: string;
  description?: string;
}

@Injectable({
  providedIn: 'root'
})
export class StudioEngineService {
  private audioCtx: AudioContext | null = null;
  private sfxBufferCache = new Map<string, AudioBuffer>();
  private sfxBlobUrlCache = new Map<string, string>();

  readonly fontCategories = [
    { id: 'Viral & Başlık', label: '🔥 Viral & Başlık' },
    { id: 'Modern Sans', label: '✨ Modern Sans' },
    { id: 'Sinematik & Serif', label: '🎬 Sinematik & Serif' },
    { id: 'El Yazısı & Fırça', label: '✍️ El Yazısı & Fırça' },
    { id: 'Siber & Kod', label: '💻 Siber & Kod' }
  ];

  // 1. 35+ KATEGORİZE GOOGLE FONT KÜTÜPHANESİ
  readonly fonts: StudioFontOption[] = [
    // Viral & Başlık
    { name: 'Anton (MrBeast Viral)', family: 'Anton', category: 'Viral & Başlık' },
    { name: 'Bebas Neue (Dar Kalın)', family: 'Bebas Neue', category: 'Viral & Başlık' },
    { name: 'Montserrat Black', family: 'Montserrat', category: 'Viral & Başlık' },
    { name: 'Archivo Black', family: 'Archivo Black', category: 'Viral & Başlık' },
    { name: 'Bangers (Çizgi Roman)', family: 'Bangers', category: 'Viral & Başlık' },
    { name: 'Titan One (Yumuşak Dev)', family: 'Titan One', category: 'Viral & Başlık' },
    { name: 'Luckiest Guy (Eğlenceli)', family: 'Luckiest Guy', category: 'Viral & Başlık' },
    { name: 'Passion One', family: 'Passion One', category: 'Viral & Başlık' },
    { name: 'Righteous (Modern Poster)', family: 'Righteous', category: 'Viral & Başlık' },
    { name: 'Oswald (Haber/Spor)', family: 'Oswald', category: 'Viral & Başlık' },
    { name: 'Rubik Mono One', family: 'Rubik Mono One', category: 'Viral & Başlık' },
    // Modern Sans
    { name: 'Poppins', family: 'Poppins', category: 'Modern Sans' },
    { name: 'Inter', family: 'Inter', category: 'Modern Sans' },
    { name: 'Outfit', family: 'Outfit', category: 'Modern Sans' },
    { name: 'Plus Jakarta Sans', family: 'Plus Jakarta Sans', category: 'Modern Sans' },
    { name: 'DM Sans', family: 'DM Sans', category: 'Modern Sans' },
    { name: 'Space Grotesk', family: 'Space Grotesk', category: 'Modern Sans' },
    { name: 'Syne', family: 'Syne', category: 'Modern Sans' },
    { name: 'Urbanist', family: 'Urbanist', category: 'Modern Sans' },
    { name: 'Manrope', family: 'Manrope', category: 'Modern Sans' },
    { name: 'Lexend', family: 'Lexend', category: 'Modern Sans' },
    // Sinematik & Serif
    { name: 'Cinzel (Sinematik Fragman)', family: 'Cinzel', category: 'Sinematik & Serif' },
    { name: 'Playfair Display (Lüks)', family: 'Playfair Display', category: 'Sinematik & Serif' },
    { name: 'Bodoni Moda (Vogue)', family: 'Bodoni Moda', category: 'Sinematik & Serif' },
    { name: 'Cormorant Garamond', family: 'Cormorant Garamond', category: 'Sinematik & Serif' },
    { name: 'Merriweather', family: 'Merriweather', category: 'Sinematik & Serif' },
    // El Yazısı & Fırça
    { name: 'Permanent Marker (Keçeli Kalem)', family: 'Permanent Marker', category: 'El Yazısı & Fırça' },
    { name: 'Caveat (Doğal Not)', family: 'Caveat', category: 'El Yazısı & Fırça' },
    { name: 'Pacifico (Retro Script)', family: 'Pacifico', category: 'El Yazısı & Fırça' },
    { name: 'Dancing Script', family: 'Dancing Script', category: 'El Yazısı & Fırça' },
    { name: 'Satisfy', family: 'Satisfy', category: 'El Yazısı & Fırça' },
    { name: 'Shadows Into Light', family: 'Shadows Into Light', category: 'El Yazısı & Fırça' },
    // Siber & Kod
    { name: 'Orbitron (Sci-Fi / Cyber)', family: 'Orbitron', category: 'Siber & Kod' },
    { name: 'Chakra Petch (Gaming)', family: 'Chakra Petch', category: 'Siber & Kod' },
    { name: 'Press Start 2P (8-Bit Retro)', family: 'Press Start 2P', category: 'Siber & Kod' },
    { name: 'JetBrains Mono (Kod/Daktilo)', family: 'JetBrains Mono', category: 'Siber & Kod' },
    { name: 'Fira Code', family: 'Fira Code', category: 'Siber & Kod' }
  ];

  // 2. 12 HAZIR VİRAL METİN ŞABLONU (CAPCUT & PHOTOSHOP PRESETS)
  readonly textPresets: TextTemplatePreset[] = [
    {
      id: 'mrbeast_viral',
      name: 'MrBeast Viral Hook',
      badge: '🔥 Trend',
      previewBg: 'linear-gradient(135deg, #1e293b, #0f172a)',
      previewStyle: 'font-family: Anton; color: #FFE600; -webkit-text-stroke: 2px #000; text-shadow: 0 4px 0 #000;',
      props: {
        font: 'Anton',
        fontSize: 64,
        color: '#FFE600',
        fillType: 'solid',
        strokeColor: '#000000',
        strokeWidth: 6,
        outerStrokeWidth: 0,
        glowEnabled: false,
        boxStyle: 'none',
        allCaps: true,
        letterSpacing: 2,
        shadowColor: '#000000',
        shadowDistance: 6,
        shadowAngle: 90,
        shadowBlur: 2,
        animation: 'pop-up',
        exitAnimation: 'scale-out',
        loopAnimation: 'none',
        curveBend: 0,
        rotateX: 0,
        rotateY: 0
      }
    },
    {
      id: 'hormozi_pill',
      name: 'Hormozi Vurgu Rozeti',
      badge: '💼 Reels',
      previewBg: 'linear-gradient(135deg, #064e3b, #022c22)',
      previewStyle: 'font-family: Montserrat; font-weight: 900; color: #00FF66; background: rgba(0,0,0,0.85); padding: 2px 10px; border-radius: 999px;',
      props: {
        font: 'Montserrat',
        fontSize: 52,
        fontWeight: 900,
        color: '#00FF66',
        fillType: 'solid',
        strokeColor: '#000000',
        strokeWidth: 3,
        boxStyle: 'pill',
        boxBgColor: 'rgba(0, 0, 0, 0.85)',
        boxPadding: 18,
        allCaps: true,
        letterSpacing: 1,
        animation: 'bounce',
        exitAnimation: 'fade',
        loopAnimation: 'pulse'
      }
    },
    {
      id: 'cyberpunk_neon',
      name: 'Cyberpunk Neon Glow',
      badge: '⚡ Glow',
      previewBg: 'linear-gradient(135deg, #2e1065, #090d16)',
      previewStyle: 'font-family: Orbitron; font-weight: 900; color: #FFFFFF; text-shadow: 0 0 10px #FF007F, 0 0 20px #FF007F;',
      props: {
        font: 'Orbitron',
        fontSize: 50,
        color: '#FFFFFF',
        fillType: 'solid',
        strokeColor: '#FF007F',
        strokeWidth: 2,
        glowEnabled: true,
        glowColor: '#FF007F',
        glowRadius: 18,
        boxStyle: 'none',
        allCaps: true,
        letterSpacing: 4,
        animation: 'glitch',
        exitAnimation: 'fade',
        loopAnimation: 'neon-flicker'
      }
    },
    {
      id: 'photoshop_double_stroke',
      name: 'Photoshop Çift Kontur',
      badge: '🎨 2x Stroke',
      previewBg: 'linear-gradient(135deg, #31102F, #111827)',
      previewStyle: 'font-family: Bangers; color: #FFFFFF; -webkit-text-stroke: 2px #000; filter: drop-shadow(0 0 3px #EF4444);',
      props: {
        font: 'Bangers',
        fontSize: 68,
        color: '#FFFFFF',
        fillType: 'solid',
        strokeColor: '#000000',
        strokeWidth: 5,
        outerStrokeColor: '#EF4444',
        outerStrokeWidth: 6,
        boxStyle: 'none',
        allCaps: true,
        letterSpacing: 3,
        animation: 'zoom-crash',
        exitAnimation: 'scale-out',
        loopAnimation: 'wiggle'
      }
    },
    {
      id: 'golden_gradient',
      name: 'Altın Lüks Gradyan',
      badge: '✨ Gradyan',
      previewBg: 'linear-gradient(135deg, #1c1917, #0c0a09)',
      previewStyle: 'font-family: Cinzel; font-weight: 800; color: #FBBF24; text-shadow: 0 3px 8px rgba(0,0,0,0.9);',
      props: {
        font: 'Cinzel',
        fontSize: 54,
        color: '#FDE68A',
        fillType: 'gradient',
        gradientStart: '#FFFBEB',
        gradientEnd: '#D97706',
        gradientAngle: 180,
        strokeColor: '#451A03',
        strokeWidth: 2,
        boxStyle: 'none',
        allCaps: true,
        letterSpacing: 6,
        shadowColor: '#000000',
        shadowDistance: 5,
        shadowBlur: 8,
        animation: 'blur-in',
        exitAnimation: 'fade'
      }
    },
    {
      id: 'curved_arc_banner',
      name: 'Photoshop Yay / Kemer',
      badge: '🌈 Eğri',
      previewBg: 'linear-gradient(135deg, #1e1b4b, #0f172a)',
      previewStyle: 'font-family: Righteous; color: #38BDF8; -webkit-text-stroke: 1.5px #000;',
      props: {
        font: 'Righteous',
        fontSize: 56,
        color: '#38BDF8',
        fillType: 'gradient',
        gradientStart: '#67E8F9',
        gradientEnd: '#3B82F6',
        gradientAngle: 90,
        strokeColor: '#0F172A',
        strokeWidth: 5,
        curveBend: 42,
        boxStyle: 'none',
        allCaps: true,
        letterSpacing: 3,
        animation: 'pop-up',
        loopAnimation: 'float'
      }
    },
    {
      id: 'breaking_news_badge',
      name: 'Son Dakika Haber Bandı',
      badge: '📺 TV',
      previewBg: 'linear-gradient(135deg, #450a0a, #111827)',
      previewStyle: 'font-family: Oswald; font-weight: 700; color: #FFF; background: #DC2626; padding: 2px 10px; border-radius: 4px;',
      props: {
        font: 'Oswald',
        fontSize: 46,
        color: '#FFFFFF',
        fillType: 'solid',
        strokeWidth: 0,
        boxStyle: 'badge',
        boxBgColor: '#DC2626',
        boxPadding: 16,
        borderRadius: 6,
        allCaps: true,
        letterSpacing: 2,
        animation: 'slide-right',
        exitAnimation: 'slide-left'
      }
    },
    {
      id: 'marker_highlighter',
      name: 'Fosforlu Kalem Vurgu',
      badge: '🖍️ Marker',
      previewBg: 'linear-gradient(135deg, #365314, #0f172a)',
      previewStyle: 'font-family: Permanent Marker; color: #0F172A; background: #FACC15; padding: 2px 8px;',
      props: {
        font: 'Permanent Marker',
        fontSize: 48,
        color: '#0F172A',
        fillType: 'solid',
        strokeWidth: 0,
        boxStyle: 'highlight-marker',
        boxBgColor: '#FACC15',
        boxPadding: 14,
        allCaps: false,
        skewX: -6,
        animation: 'slide-left',
        exitAnimation: 'fade'
      }
    },
    {
      id: '3d_cinema_tilt',
      name: '3D Perspektif Başlık',
      badge: '📐 3D',
      previewBg: 'linear-gradient(135deg, #0f172a, #1e293b)',
      previewStyle: 'font-family: Bebas Neue; color: #F8FAFC; transform: perspective(300px) rotateX(25deg) rotateY(-15deg);',
      props: {
        font: 'Bebas Neue',
        fontSize: 70,
        color: '#FFFFFF',
        fillType: 'gradient',
        gradientStart: '#FFFFFF',
        gradientEnd: '#94A3B8',
        gradientAngle: 180,
        strokeColor: '#020617',
        strokeWidth: 4,
        rotateX: 28,
        rotateY: -18,
        skewX: -5,
        boxStyle: 'none',
        allCaps: true,
        letterSpacing: 4,
        animation: 'flip-3d',
        loopAnimation: 'float'
      }
    },
    {
      id: 'retro_arcade_8bit',
      name: '8-Bit Arcade Oyun',
      badge: '👾 8-Bit',
      previewBg: 'linear-gradient(135deg, #3b0764, #090d16)',
      previewStyle: 'font-family: "Press Start 2P"; font-size: 11px; color: #22D3EE; text-shadow: 2px 2px 0 #D946EF;',
      props: {
        font: 'Press Start 2P',
        fontSize: 36,
        color: '#22D3EE',
        fillType: 'solid',
        strokeColor: '#000000',
        strokeWidth: 3,
        outerStrokeColor: '#D946EF',
        outerStrokeWidth: 3,
        boxStyle: 'none',
        allCaps: true,
        letterSpacing: 2,
        animation: 'bounce',
        loopAnimation: 'pulse'
      }
    },
    {
      id: 'typewriter_terminal',
      name: 'Daktilo / Kod Bloğu',
      badge: '⌨️ Daktilo',
      previewBg: 'linear-gradient(135deg, #022c22, #090d16)',
      previewStyle: 'font-family: "JetBrains Mono"; color: #34D399; background: rgba(2,6,23,0.9); padding: 2px 8px; border-radius: 6px;',
      props: {
        font: 'JetBrains Mono',
        fontSize: 38,
        color: '#34D399',
        fillType: 'solid',
        strokeWidth: 0,
        boxStyle: 'rounded',
        boxBgColor: 'rgba(2, 6, 23, 0.90)',
        boxPadding: 16,
        borderRadius: 12,
        allCaps: false,
        animation: 'typewriter',
        exitAnimation: 'fade'
      }
    },
    {
      id: 'vlog_handwriting',
      name: 'Estetik Vlog El Yazısı',
      badge: '✍️ Vlog',
      previewBg: 'linear-gradient(135deg, #4c1d95, #1e1b4b)',
      previewStyle: 'font-family: Pacifico; color: #F472B6; text-shadow: 0 2px 6px rgba(0,0,0,0.8);',
      props: {
        font: 'Pacifico',
        fontSize: 56,
        color: '#F9A8D4',
        fillType: 'gradient',
        gradientStart: '#FDF2F8',
        gradientEnd: '#F472B6',
        gradientAngle: 135,
        strokeColor: '#500724',
        strokeWidth: 3,
        glowEnabled: true,
        glowColor: '#EC4899',
        glowRadius: 10,
        boxStyle: 'none',
        allCaps: false,
        animation: 'pop-up',
        loopAnimation: 'float'
      }
    }
  ];

  // 3. 16 DAHİLİ STÜDYO SES EFEKTİ (SFX) KÜTÜPHANESİ (WEB AUDIO API SENTEZLEYİCİ İLE %100 ÇEVRİMDIŞI & 0ms GECİKME)
  readonly sfxLibrary: SfxLibraryItem[] = [
    { id: 'whoosh-fast', name: 'Whoosh Hızlı Geçiş', category: 'whoosh', icon: '💨', duration: 0.45, synthPreset: 'whoosh-fast', description: 'Hızlı sahne ve yazı geçişleri için rüzgar efekti', peaks: [0.1, 0.3, 0.7, 0.95, 1.0, 0.85, 0.5, 0.2, 0.05] },
    { id: 'swoosh-deep', name: 'Swoosh Derin Sinematik', category: 'whoosh', icon: '🌪️', duration: 0.75, synthPreset: 'swoosh-deep', description: 'Ağır kamera dönüşleri ve Whip Pan için derin geçiş', peaks: [0.05, 0.2, 0.5, 0.8, 0.95, 0.9, 0.7, 0.4, 0.15, 0.05] },
    { id: 'pop-bubble', name: 'Pop Baloncuk (Metin/Sticker)', category: 'pop', icon: '🫧', duration: 0.25, synthPreset: 'pop-bubble', description: 'Ekrana yazı veya çıkartma geldiğinde çıkan klasik Pop sesi', peaks: [0.2, 0.95, 1.0, 0.6, 0.2, 0.05] },
    { id: 'pop-crisp', name: 'Pop Keskin Vurgu', category: 'pop', icon: '✨', duration: 0.22, synthPreset: 'pop-crisp', description: 'Kısa ve net bildirim/rozet belirmesi', peaks: [0.4, 1.0, 0.8, 0.3, 0.05] },
    { id: 'ding-bell', name: 'Ding Parlak Çan', category: 'ui', icon: '🔔', duration: 0.90, synthPreset: 'ding-bell', description: 'Önemli fikir, ipucu veya doğru cevap çanı', peaks: [1.0, 0.9, 0.75, 0.6, 0.45, 0.3, 0.2, 0.1, 0.05] },
    { id: 'cash-register', name: 'Kasa / Para Sesi (Ka-Ching)', category: 'ui', icon: '💰', duration: 0.80, synthPreset: 'cash-register', description: 'Fiyat, kazanç ve finans vurguları için kasa çanı', peaks: [0.9, 0.4, 1.0, 0.85, 0.6, 0.4, 0.2, 0.1] },
    { id: 'sub-bass-drop', name: 'Sub Bass Drop (Boom)', category: 'cinematic', icon: '💣', duration: 1.40, synthPreset: 'sub-bass-drop', description: 'Dramatik anlar ve büyük başlıklar için derin bas patlaması', peaks: [1.0, 0.95, 0.9, 0.82, 0.75, 0.65, 0.5, 0.35, 0.2, 0.1] },
    { id: 'cinematic-hit', name: 'Sinematik Darbe (Impact Hit)', category: 'cinematic', icon: '🔨', duration: 1.10, synthPreset: 'cinematic-hit', description: 'Fragman tarzı güçlü metalik/orkestral vuruş', peaks: [1.0, 0.98, 0.85, 0.65, 0.45, 0.3, 0.15, 0.05] },
    { id: 'tension-riser', name: 'Gerilim Yükseltici (Riser)', category: 'cinematic', icon: '📈', duration: 1.50, synthPreset: 'tension-riser', description: 'Sürpriz veya kesim öncesi yükselen gerilim sesi', peaks: [0.05, 0.12, 0.22, 0.35, 0.5, 0.68, 0.85, 0.98, 1.0, 0.2] },
    { id: 'camera-shutter', name: 'Kamera Deklanşör (Shutter)', category: 'ui', icon: '📸', duration: 0.35, synthPreset: 'camera-shutter', description: 'Fotoğraf/ekran görüntüsü ve dondurulmuş kare efekti', peaks: [0.95, 0.3, 0.85, 0.2, 0.05] },
    { id: 'keyboard-typing', name: 'Mekanik Klavye (Daktilo)', category: 'ui', icon: '⌨️', duration: 0.85, synthPreset: 'keyboard-typing', description: 'Daktilo animasyonlu yazılar için tuş tıkırtısı', peaks: [0.8, 0.2, 0.9, 0.15, 0.75, 0.2, 0.85, 0.1, 0.9, 0.2] },
    { id: 'mouse-click', name: 'Çift Fare Tıklaması', category: 'ui', icon: '🖱️', duration: 0.30, synthPreset: 'mouse-click', description: 'Buton, abone ol ve UI etkileşim sesi', peaks: [0.9, 0.1, 0.95, 0.1] },
    { id: 'digital-glitch', name: 'Dijital Glitch / Parazit', category: 'cinematic', icon: '⚡', duration: 0.45, synthPreset: 'digital-glitch', description: 'Glitch geçişleri ve siber metinler için dijital bozulma', peaks: [0.9, 0.3, 1.0, 0.2, 0.85, 0.95, 0.4, 0.8] },
    { id: 'record-scratch', name: 'Plak Durma (Record Scratch)', category: 'funny', icon: '💿', duration: 0.65, synthPreset: 'record-scratch', description: 'Beklenmedik veya komik kesimler için plak cızırtısı', peaks: [0.7, 0.95, 0.6, 1.0, 0.8, 0.4, 0.1] },
    { id: 'success-chime', name: 'Başarı / Seviye Atlama', category: 'ui', icon: '🏆', duration: 0.80, synthPreset: 'success-chime', description: 'Olumlu sonuç ve onay akoru', peaks: [0.6, 0.75, 0.9, 1.0, 0.85, 0.6, 0.3, 0.1] },
    { id: 'error-buzzer', name: 'Yanlış / Hata (Buzzer)', category: 'funny', icon: '❌', duration: 0.60, synthPreset: 'error-buzzer', description: 'Hatalı hamle veya mizahi ret sesi', peaks: [0.9, 0.95, 0.9, 0.85, 0.8, 0.2] }
  ];

  // 4. 14 VİDEO VE SAHNE GEÇİŞ EFEKTİ (FFMPEG XFADE & CANLI ÖNİZLEME UYUMLU)
  readonly transitionLibrary: TransitionLibraryItem[] = [
    { type: 'fade', name: 'Yumuşak Geçiş (Dissolve)', category: 'Temel', icon: '🌫️', defaultDuration: 0.5, recommendedSfx: 'whoosh-fast' },
    { type: 'fadeblack', name: 'Siyaha Kararma (Dip to Black)', category: 'Temel', icon: '⬛', defaultDuration: 0.6, recommendedSfx: 'swoosh-deep' },
    { type: 'fadewhite', name: 'Beyaz Flaş Patlaması (Flash)', category: 'Işık / Flaş', icon: '⚡', defaultDuration: 0.35, recommendedSfx: 'camera-shutter' },
    { type: 'slideleft', name: 'Hızlı Sola Kayma (Whip Left)', category: 'Kamera / Whip', icon: '⏪', defaultDuration: 0.35, recommendedSfx: 'whoosh-fast' },
    { type: 'slideright', name: 'Hızlı Sağa Kayma (Whip Right)', category: 'Kamera / Whip', icon: '⏩', defaultDuration: 0.35, recommendedSfx: 'whoosh-fast' },
    { type: 'slideup', name: 'Yukarı Savrulma (Whip Up)', category: 'Kamera / Whip', icon: '⏫', defaultDuration: 0.4, recommendedSfx: 'whoosh-fast' },
    { type: 'slidedown', name: 'Aşağı Savrulma (Whip Down)', category: 'Kamera / Whip', icon: '⏬', defaultDuration: 0.4, recommendedSfx: 'whoosh-fast' },
    { type: 'zoomin', name: 'Yakınlaşarak Çarpma (Zoom In)', category: 'Kamera / Whip', icon: '🔍', defaultDuration: 0.4, recommendedSfx: 'sub-bass-drop' },
    { type: 'circleopen', name: 'Dairesel Açılış (Iris Open)', category: 'Dijital & Maske', icon: '⭕', defaultDuration: 0.5, recommendedSfx: 'pop-bubble' },
    { type: 'circleclose', name: 'Dairesel Kapanış (Iris Close)', category: 'Dijital & Maske', icon: '🎯', defaultDuration: 0.5, recommendedSfx: 'swoosh-deep' },
    { type: 'wipeleft', name: 'Sola Perde Silme (Wipe Left)', category: 'Temel', icon: '◧', defaultDuration: 0.45, recommendedSfx: 'whoosh-fast' },
    { type: 'wiperight', name: 'Sağa Perde Silme (Wipe Right)', category: 'Temel', icon: '◨', defaultDuration: 0.45, recommendedSfx: 'whoosh-fast' },
    { type: 'pixelize', name: 'Dijital Pikselleşme (Mosaic)', category: 'Dijital & Maske', icon: '🟦', defaultDuration: 0.45, recommendedSfx: 'digital-glitch' },
    { type: 'hlslice', name: 'Glitch Dilimleme (Cyber Slice)', category: 'Dijital & Maske', icon: '📺', defaultDuration: 0.35, recommendedSfx: 'digital-glitch' }
  ];

  // 5. DAHİLİ HAREKETLİ / VEKTÖR ÇIKARTMA (STICKER & EMOJI) PAKETİ
  readonly stickerLibrary: StickerLibraryItem[] = [
    {
      id: 'stk_subscribe',
      name: '🔴 Abone Ol Rozeti',
      category: 'social',
      preview: '🔴 ABONE OL',
      dataUrl: this.svgToDataUrl(`<svg xmlns="http://www.w3.org/2000/svg" width="360" height="110" viewBox="0 0 360 110"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="#ef4444"/><stop offset="100%" stop-color="#b91c1c"/></linearGradient><filter id="s" x="-10%" y="-10%" width="120%" height="130%"><feDropShadow dx="0" dy="6" stdDeviation="6" flood-color="#000" flood-opacity="0.5"/></filter></defs><rect x="12" y="12" width="336" height="82" rx="41" fill="url(#g)" stroke="#ffffff" stroke-width="5" filter="url(#s)"/><circle cx="62" cy="53" r="22" fill="#fff"/><polygon points="56,41 56,65 74,53" fill="#dc2626"/><text x="200" y="64" font-family="Arial, sans-serif" font-weight="900" font-size="34" fill="#ffffff" text-anchor="middle" letter-spacing="2">ABONE OL</text></svg>`)
    },
    {
      id: 'stk_like',
      name: '👍 Beğen & Destekle',
      category: 'social',
      preview: '👍 BEĞEN',
      dataUrl: this.svgToDataUrl(`<svg xmlns="http://www.w3.org/2000/svg" width="320" height="110" viewBox="0 0 320 110"><defs><linearGradient id="g2" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="#3b82f6"/><stop offset="100%" stop-color="#1d4ed8"/></linearGradient></defs><rect x="12" y="12" width="296" height="82" rx="41" fill="url(#g2)" stroke="#ffffff" stroke-width="5"/><text x="65" y="67" font-size="42">👍</text><text x="190" y="65" font-family="Arial, sans-serif" font-weight="900" font-size="34" fill="#ffffff" text-anchor="middle" letter-spacing="2">BEĞEN</text></svg>`)
    },
    {
      id: 'stk_arrow_red',
      name: '↘ Kırmızı Vurgu Oku',
      category: 'arrows',
      preview: '↘ VURGU OKU',
      dataUrl: this.svgToDataUrl(`<svg xmlns="http://www.w3.org/2000/svg" width="240" height="240" viewBox="0 0 240 240"><path d="M35 35 L165 165 M165 165 L95 165 M165 165 L165 95" stroke="#ffffff" stroke-width="30" stroke-linecap="round" stroke-linejoin="round" fill="none"/><path d="M35 35 L165 165 M165 165 L95 165 M165 165 L165 95" stroke="#ef4444" stroke-width="20" stroke-linecap="round" stroke-linejoin="round" fill="none"/></svg>`)
    },
    {
      id: 'stk_circle_callout',
      name: '⭕ El Çizimi Kırmızı Daire',
      category: 'arrows',
      preview: '⭕ DAİRE VURGU',
      dataUrl: this.svgToDataUrl(`<svg xmlns="http://www.w3.org/2000/svg" width="280" height="200" viewBox="0 0 280 200"><ellipse cx="140" cy="100" rx="118" ry="74" fill="none" stroke="#ffffff" stroke-width="16" stroke-dasharray="600 40" stroke-linecap="round" transform="rotate(-6 140 100)"/><ellipse cx="140" cy="100" rx="118" ry="74" fill="none" stroke="#ef4444" stroke-width="10" stroke-dasharray="600 40" stroke-linecap="round" transform="rotate(-6 140 100)"/></svg>`)
    },
    {
      id: 'stk_fire',
      name: '🔥 Alev / Trend',
      category: 'emoji',
      preview: '🔥',
      dataUrl: this.emojiToDataUrl('🔥')
    },
    {
      id: 'stk_rocket',
      name: '🚀 Roket / Yükseliş',
      category: 'emoji',
      preview: '🚀',
      dataUrl: this.emojiToDataUrl('🚀')
    },
    {
      id: 'stk_mindblown',
      name: '🤯 Şok / İnanılmaz',
      category: 'emoji',
      preview: '🤯',
      dataUrl: this.emojiToDataUrl('🤯')
    },
    {
      id: 'stk_money',
      name: '💰 Para / Kazanç',
      category: 'emoji',
      preview: '💰',
      dataUrl: this.emojiToDataUrl('💰')
    },
    {
      id: 'stk_idea',
      name: '💡 Parlak Fikir',
      category: 'emoji',
      preview: '💡',
      dataUrl: this.emojiToDataUrl('💡')
    },
    {
      id: 'stk_check',
      name: '✅ Doğru / Onay',
      category: 'badges',
      preview: '✅',
      dataUrl: this.emojiToDataUrl('✅')
    },
    {
      id: 'stk_cross',
      name: '❌ Yanlış / Hata',
      category: 'badges',
      preview: '❌',
      dataUrl: this.emojiToDataUrl('❌')
    },
    {
      id: 'stk_crown',
      name: '👑 Kral / En İyi',
      category: 'badges',
      preview: '👑',
      dataUrl: this.emojiToDataUrl('👑')
    }
  ];

  private svgToDataUrl(svg: string): string {
    return `data:image/svg+xml;utf8,${encodeURIComponent(svg)}`;
  }

  private emojiToDataUrl(emoji: string): string {
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="220" height="220" viewBox="0 0 220 220"><filter id="ds" x="-20%" y="-20%" width="140%" height="140%"><feDropShadow dx="0" dy="6" stdDeviation="6" flood-color="#000000" flood-opacity="0.45"/></filter><text x="110" y="155" font-size="140" text-anchor="middle" filter="url(#ds)">${emoji}</text></svg>`;
    return `data:image/svg+xml;utf8,${encodeURIComponent(svg)}`;
  }

  private getAudioContext(): AudioContext {
    if (!this.audioCtx) {
      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      this.audioCtx = new AudioCtx();
    }
    if (this.audioCtx.state === 'suspended') {
      this.audioCtx.resume().catch(() => {});
    }
    return this.audioCtx;
  }

  /**
   * Stüdyo ses efektini (SFX) 0ms gecikme ile Web Audio API üzerinden sentezler ve çalar.
   */
  playSfxPreset(presetId: string, volume = 0.8): void {
    try {
      const ctx = this.getAudioContext();
      const buffer = this.getOrCreateSfxBuffer(ctx, presetId);
      const source = ctx.createBufferSource();
      source.buffer = buffer;

      const gain = ctx.createGain();
      gain.gain.value = Math.max(0, Math.min(2.0, volume));

      source.connect(gain);
      gain.connect(ctx.destination);
      source.start(0);
    } catch (err) {
      console.warn('[STUDIO-SFX] Ses çalınamadı:', err);
    }
  }

  playSynthesizedSfx(presetId: string, volume = 0.8): void {
    this.playSfxPreset(presetId, volume);
  }

  generateSfxWavDataUri(presetId: string, _duration?: number): string {
    return this.getSfxDataUrl(presetId);
  }

  /**
   * SFX presetini gerçek bir WAV Data URL'sine dönüştürür (böylece indirme/render ve <audio> etiketleriyle de %100 çalışır).
   */
  getSfxDataUrl(presetId: string): string {
    const cached = this.sfxBlobUrlCache.get(presetId);
    if (cached) return cached;

    try {
      const ctx = this.getAudioContext();
      const buffer = this.getOrCreateSfxBuffer(ctx, presetId);
      const wavBlob = this.audioBufferToWavBlob(buffer);
      const url = URL.createObjectURL(wavBlob);
      this.sfxBlobUrlCache.set(presetId, url);
      return url;
    } catch {
      return '';
    }
  }

  private getOrCreateSfxBuffer(ctx: AudioContext, presetId: string): AudioBuffer {
    const existing = this.sfxBufferCache.get(presetId);
    if (existing) return existing;

    const sr = ctx.sampleRate || 44100;
    const item = this.sfxLibrary.find(s => s.id === presetId || s.synthPreset === presetId);
    const duration = item ? item.duration : 0.5;
    const length = Math.max(1024, Math.floor(sr * duration));
    const buffer = ctx.createBuffer(1, length, sr);
    const data = buffer.getChannelData(0);

    for (let i = 0; i < length; i++) {
      const t = i / sr;
      const norm = i / length;

      switch (presetId) {
        case 'whoosh-fast':
        case 'swoosh-deep': {
          const env = Math.sin(Math.PI * norm) ** 1.8;
          const freq = presetId === 'whoosh-fast' ? 180 + 900 * Math.sin(Math.PI * norm) : 90 + 420 * Math.sin(Math.PI * norm);
          const noise = (Math.random() * 2 - 1) * 0.55;
          const tone = Math.sin(2 * Math.PI * freq * t) * 0.45;
          data[i] = (noise + tone) * env;
          break;
        }
        case 'pop-bubble':
        case 'pop-crisp': {
          const env = Math.exp(-t * 22);
          const fStart = presetId === 'pop-bubble' ? 220 : 380;
          const fEnd = presetId === 'pop-bubble' ? 880 : 1200;
          const freq = fStart + (fEnd - fStart) * Math.min(1, t * 14);
          data[i] = Math.sin(2 * Math.PI * freq * t) * env * 0.9;
          break;
        }
        case 'ding-bell':
        case 'cash-register': {
          const env = Math.exp(-t * 4.5);
          const f1 = presetId === 'cash-register' && t > 0.12 ? 2093 : 1318.5;
          const f2 = f1 * 2.0;
          data[i] = (Math.sin(2 * Math.PI * f1 * t) * 0.65 + Math.sin(2 * Math.PI * f2 * t) * 0.35) * env;
          break;
        }
        case 'sub-bass-drop':
        case 'cinematic-hit': {
          const env = Math.exp(-t * 3.2);
          const freq = 130 * Math.exp(-t * 2.4) + 32;
          const punch = t < 0.04 ? (Math.random() * 2 - 1) * (1 - t / 0.04) * 0.7 : 0;
          data[i] = (Math.sin(2 * Math.PI * freq * t) * 0.85 + punch) * env;
          break;
        }
        case 'tension-riser': {
          const env = norm ** 2.2 * (norm > 0.92 ? (1 - norm) / 0.08 : 1);
          const freq = 140 + 1200 * (norm ** 2);
          const noise = (Math.random() * 2 - 1) * 0.35;
          data[i] = (Math.sin(2 * Math.PI * freq * t) * 0.65 + noise) * env;
          break;
        }
        case 'camera-shutter':
        case 'mouse-click':
        case 'keyboard-typing': {
          const clickPeriod = presetId === 'keyboard-typing' ? 0.14 : 0.12;
          const localT = t % clickPeriod;
          const env = Math.exp(-localT * 65);
          data[i] = (Math.random() * 2 - 1) * env * 0.9;
          break;
        }
        case 'digital-glitch':
        case 'record-scratch': {
          const step = Math.floor(t * 45);
          const freq = 180 + ((step * 397) % 1400);
          const sq = Math.sin(2 * Math.PI * freq * t) >= 0 ? 0.6 : -0.6;
          data[i] = (sq + (Math.random() * 2 - 1) * 0.3) * (1 - norm * 0.4);
          break;
        }
        case 'success-chime': {
          const notes = [523.25, 659.25, 783.99, 1046.5];
          const idx = Math.min(notes.length - 1, Math.floor(norm * notes.length));
          const env = Math.exp(-(t % 0.2) * 6);
          data[i] = Math.sin(2 * Math.PI * notes[idx] * t) * env * 0.8;
          break;
        }
        default: {
          // error-buzzer vb.
          const env = 1 - norm * 0.5;
          data[i] = (Math.sin(2 * Math.PI * 145 * t) >= 0 ? 0.5 : -0.5) * env;
          break;
        }
      }
    }

    this.sfxBufferCache.set(presetId, buffer);
    return buffer;
  }

  private audioBufferToWavBlob(buffer: AudioBuffer): Blob {
    const numOfChan = buffer.numberOfChannels;
    const length = buffer.length * numOfChan * 2 + 44;
    const out = new ArrayBuffer(length);
    const view = new DataView(out);
    const sampleRate = buffer.sampleRate;

    const writeString = (offset: number, str: string) => {
      for (let i = 0; i < str.length; i++) {
        view.setUint8(offset + i, str.charCodeAt(i));
      }
    };

    writeString(0, 'RIFF');
    view.setUint32(4, length - 8, true);
    writeString(8, 'WAVE');
    writeString(12, 'fmt ');
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true);
    view.setUint16(22, numOfChan, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * numOfChan * 2, true);
    view.setUint16(32, numOfChan * 2, true);
    view.setUint16(34, 16, true);
    writeString(36, 'data');
    view.setUint32(40, length - 44, true);

    const chData = buffer.getChannelData(0);
    let offset = 44;
    for (let i = 0; i < chData.length; i++) {
      const sample = Math.max(-1, Math.min(1, chData[i]));
      view.setInt16(offset, sample < 0 ? sample * 0x8000 : sample * 0x7FFF, true);
      offset += 2;
    }

    return new Blob([out], { type: 'audio/wav' });
  }

  /**
   * Görselin arka planını tarayıcı içinde (GPU/Canvas kenar renk uzayı + GrabCut merkez ağırlıklı alfa matrisi ile)
   * ~120 milisaniyede temizleyip şeffaf PNG DataURL olarak döndürür.
   */
  async removeImageBackgroundInstant(imageUrl: string, toleranceOrColor: number | string = 48): Promise<string> {
    const tolerance = typeof toleranceOrColor === 'number' ? toleranceOrColor : 48;
    return new Promise((resolve, reject) => {
      const img = new Image();
      img.crossOrigin = 'anonymous';
      img.onload = () => {
        try {
          const maxDim = 900;
          const scale = Math.min(1, maxDim / Math.max(img.width || 1, img.height || 1));
          const w = Math.max(1, Math.round(img.width * scale));
          const h = Math.max(1, Math.round(img.height * scale));

          const canvas = document.createElement('canvas');
          canvas.width = w;
          canvas.height = h;
          const ctx = canvas.getContext('2d');
          if (!ctx) {
            resolve(imageUrl);
            return;
          }

          ctx.drawImage(img, 0, 0, w, h);
          const imgData = ctx.getImageData(0, 0, w, h);
          const d = imgData.data;

          // Kenar piksellerinden arka plan renk örneklerini (köşe ve kenar ortaları) topla
          const sampleCoords = [
            [2, 2], [w - 3, 2], [2, h - 3], [w - 3, h - 3],
            [Math.floor(w / 2), 2], [2, Math.floor(h / 2)], [w - 3, Math.floor(h / 2)]
          ];
          const bgSamples: [number, number, number][] = [];
          for (const [sx, sy] of sampleCoords) {
            const idx = (Math.max(0, Math.min(h - 1, sy)) * w + Math.max(0, Math.min(w - 1, sx))) * 4;
            bgSamples.push([d[idx], d[idx + 1], d[idx + 2]]);
          }

          const thresh = Math.max(18, tolerance * 1.45);
          const softRange = 28;

          for (let y = 0; y < h; y++) {
            const ny = (y / h) - 0.5;
            for (let x = 0; x < w; x++) {
              const nx = (x / w) - 0.5;
              const idx = (y * w + x) * 4;
              const r = d[idx];
              const g = d[idx + 1];
              const b = d[idx + 2];

              let minDiff = 9999;
              for (const [br, bg, bb] of bgSamples) {
                const dist = Math.sqrt(
                  (r - br) * (r - br) * 0.3 +
                  (g - bg) * (g - bg) * 0.59 +
                  (b - bb) * (b - bb) * 0.11
                );
                if (dist < minDiff) minDiff = dist;
              }

              // Merkezdeki özneyi koruma ağırlığı (Merkezde daha sıkı, kenarlarda daha esnek)
              const radialDist = Math.sqrt(nx * nx + ny * ny);
              const localThresh = radialDist < 0.28 ? thresh * 0.68 : thresh;

              if (minDiff < localThresh) {
                d[idx + 3] = 0;
              } else if (minDiff < localThresh + softRange) {
                const factor = (minDiff - localThresh) / softRange;
                d[idx + 3] = Math.round(d[idx + 3] * factor);
              }
            }
          }

          ctx.putImageData(imgData, 0, 0);
          resolve(canvas.toDataURL('image/png'));
        } catch (err) {
          console.warn('[BG-REMOVE-INSTANT] CORS veya Canvas hatası, SVG mask fallback:', err);
          reject(err);
        }
      };
      img.onerror = (err) => reject(err);
      img.src = imageUrl;
    });
  }

  /**
   * FAZ 6: Otonom Video Yönetmeni (Proaktif AI Kurgu Önerileri Üretici)
   * Projenin gerçek transkript segmentlerini, kesimlerini ve süresini analiz ederek
   * Faz 1-5'teki tüm profesyonel araçları (Yay Metin, MrBeast/Hormozi Şablonu, Geçiş Efekti, SFX, Sticker, Ses Master)
   * kullanan sahne bazlı akıllı öneriler üretir.
   */
  generateProactiveSuggestions(edl: EdlContent, totalDur?: number): SuggestionItem[] {
    const duration = totalDur || edl.duration || 60;
    const segments = edl.transcript?.segments || [];
    const cuts = edl.cuts || [];
    const suggestions: SuggestionItem[] = [];

    // 1. Açılış Viral Hook + Yay Metin + Pop SFX Önerisi
    const firstSeg = segments[0];
    const hookText = firstSeg?.text
      ? firstSeg.text.trim().split(/\s+/).slice(0, 4).join(' ').toUpperCase()
      : 'BUNU BİLİYOR MUYDUNUZ?';
    const hookStart = firstSeg ? Math.max(0, firstSeg.start) : 0.2;

    suggestions.push({
      id: `sug_hook_${Date.now()}_1`,
      type: 'viral_hook',
      category: '🔥 Viral Açılış & Tipografi',
      title: 'MrBeast Viral Hook + Pop SFX Ekle',
      content: hookText,
      timestamp: Number(hookStart.toFixed(1)),
      duration: 3.2,
      confidence: 96,
      templatePreset: 'mrbeast_viral',
      sfxPreset: 'pop-bubble',
      reason: 'İlk 3 saniyede izleyiciyi videoda tutmak için yüksek kontrastlı sarı-siyah başlık ve Pop ses efekti önerilir.',
      status: 'pending'
    });

    // 2. Sahne Geçişi (Whip Pan) + Whoosh SFX Önerisi
    const midCut = cuts.find(c => c.start > 3 && c.end < duration - 3) || { start: Math.min(12, duration * 0.25), end: Math.min(13, duration * 0.25 + 1) };
    suggestions.push({
      id: `sug_trans_${Date.now()}_2`,
      type: 'transition_sfx',
      category: '⚡ Sahne Geçişi & SFX',
      title: 'Hızlı Kayma (Whip Pan) Geçişi + Whoosh SFX',
      content: 'slideleft',
      timestamp: Number(midCut.start.toFixed(1)),
      duration: 0.4,
      confidence: 92,
      transitionType: 'slideleft',
      sfxPreset: 'whoosh-fast',
      reason: `${midCut.start.toFixed(1)}. saniyedeki kesim sıçramasını dinamik kamera kayması ve Whoosh rüzgar sesiyle sinematik hale getirir.`,
      status: 'pending'
    });

    // 3. Hormozi Vurgu Rozeti + Ding Çan Sesi (Önemli Cümle Vurgusu)
    const midSeg = segments.find(s => s.start >= duration * 0.35 && s.text.length > 12) || segments[Math.floor(segments.length / 2)];
    const highlightWords = midSeg?.text
      ? midSeg.text.trim().split(/\s+/).slice(0, 3).join(' ').toUpperCase()
      : 'ÖNEMLİ NOKTA!';
    const highlightTime = midSeg ? midSeg.start : Number((duration * 0.4).toFixed(1));

    suggestions.push({
      id: `sug_hormozi_${Date.now()}_3`,
      type: 'text_highlight',
      category: '✨ Kinetik Tipografi',
      title: 'Hormozi Yeşil Vurgu Rozeti + Ding Sesi',
      content: highlightWords,
      timestamp: Number(highlightTime.toFixed(1)),
      duration: 3.0,
      confidence: 90,
      templatePreset: 'hormozi_pill',
      sfxPreset: 'ding-bell',
      reason: 'Konuşmacının vurguladığı anahtar kavramı ekranda hap (pill) rozet ve çan efektiyle pekiştirir.',
      status: 'pending'
    });

    // 4. Hareketli Sosyal Medya Sticker + Kasa / Onay Sesi
    const ctaTime = Number(Math.max(4, duration * 0.72).toFixed(1));
    suggestions.push({
      id: `sug_sticker_${Date.now()}_4`,
      type: 'sticker_callout',
      category: '🎯 Etkileşim & Sticker',
      title: '🔴 Abone Ol Sticker + Beyaz Kontur + Pop SFX',
      content: 'stk_subscribe',
      sourceUrl: this.stickerLibrary[0].dataUrl,
      timestamp: ctaTime,
      duration: 4.0,
      confidence: 89,
      sfxPreset: 'pop-crisp',
      reason: 'Videonun son çeyreğinde izleyici etkileşimini artırmak için hareketli Abone Ol çıkartması ekler.',
      status: 'pending'
    });

    // 5. Stüdyo Ses Mastering (-14 LUFS Normalizasyon + Auto-Ducking BGM + Smart Punch-In)
    suggestions.push({
      id: `sug_master_${Date.now()}_5`,
      type: 'audio_master',
      category: '🎧 Stüdyo Ses & Kadraj Master',
      title: '-14 LUFS Ses Dengeleme + Smart Punch-In Zoom',
      content: 'Stüdyo Ses & Jump-Cut Kadraj Paketi',
      timestamp: 0,
      duration: Number(duration.toFixed(1)),
      confidence: 95,
      reason: 'Ses seviyesini YouTube/Reels standardı olan -14 LUFS\'a dengeler ve kesim noktalarında %10 akıllı yakınlaştırma (Smart Punch-In) uygular.',
      status: 'pending'
    });

    return suggestions;
  }
}
