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
  category: 'animated' | 'social' | 'arrows' | 'emoji' | 'badges' | 'effects';
  preview: string;
  dataUrl: string;
  dataUri?: string;
  isAnimated?: boolean;
  tags?: string[];
}

export interface TransitionLibraryItem {
  type: EdlTransition['type'];
  name: string;
  category: 'Temel' | 'Kamera / Whip' | 'Işık / Flaş' | 'Dijital & Maske' | 'Perde & Bölme' | 'Sinematik & Özel';
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
  private loadedFonts = new Set<string>([
    'Inter', 'Montserrat', 'Poppins', 'Bebas Neue', 'Anton', 'Cinzel', 'Outfit', 'JetBrains Mono'
  ]);

  readonly fontCategories = [
    { id: 'Viral & Başlık', label: '🔥 Viral & Başlık (25)' },
    { id: 'Modern Sans', label: '✨ Modern Sans (25)' },
    { id: 'Sinematik & Serif', label: '🎬 Sinematik & Serif (20)' },
    { id: 'El Yazısı & Fırça', label: '✍️ El Yazısı & Fırça (20)' },
    { id: 'Siber & Kod', label: '💻 Siber & Kod (15)' }
  ];

  // 1. 105 KATEGORİZE GOOGLE FONT KÜTÜPHANESİ (DİNAMİK CSS YÜKLEYİCİ DESTEKLİ)
  readonly fonts: StudioFontOption[] = [
    // Viral & Başlık (25)
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
    { name: 'Black Ops One (Askeri/Aksiyon)', family: 'Black Ops One', category: 'Viral & Başlık' },
    { name: 'Bungee (Kalın Dikkat)', family: 'Bungee', category: 'Viral & Başlık' },
    { name: 'Teko (Yüksek Dar)', family: 'Teko', category: 'Viral & Başlık' },
    { name: 'Staatliches (Manşet)', family: 'Staatliches', category: 'Viral & Başlık' },
    { name: 'Alfa Slab One (Ağır Blok)', family: 'Alfa Slab One', category: 'Viral & Başlık' },
    { name: 'Fjalla One (Kuvvetli)', family: 'Fjalla One', category: 'Viral & Başlık' },
    { name: 'Secular One', family: 'Secular One', category: 'Viral & Başlık' },
    { name: 'Russo One (E-Spor)', family: 'Russo One', category: 'Viral & Başlık' },
    { name: 'Ultra (Poster Slab)', family: 'Ultra', category: 'Viral & Başlık' },
    { name: 'Changa One', family: 'Changa One', category: 'Viral & Başlık' },
    { name: 'Bowlby One SC', family: 'Bowlby One SC', category: 'Viral & Başlık' },
    { name: 'Lilita One (Oyun Başlığı)', family: 'Lilita One', category: 'Viral & Başlık' },
    { name: 'Paytone One', family: 'Paytone One', category: 'Viral & Başlık' },
    { name: 'Francois One', family: 'Francois One', category: 'Viral & Başlık' },

    // Modern Sans (25)
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
    { name: 'Rubik', family: 'Rubik', category: 'Modern Sans' },
    { name: 'Work Sans', family: 'Work Sans', category: 'Modern Sans' },
    { name: 'Nunito', family: 'Nunito', category: 'Modern Sans' },
    { name: 'Raleway', family: 'Raleway', category: 'Modern Sans' },
    { name: 'Quicksand', family: 'Quicksand', category: 'Modern Sans' },
    { name: 'Kanit', family: 'Kanit', category: 'Modern Sans' },
    { name: 'Barlow', family: 'Barlow', category: 'Modern Sans' },
    { name: 'Mulish', family: 'Mulish', category: 'Modern Sans' },
    { name: 'Figtree', family: 'Figtree', category: 'Modern Sans' },
    { name: 'Sora', family: 'Sora', category: 'Modern Sans' },
    { name: 'Albert Sans', family: 'Albert Sans', category: 'Modern Sans' },
    { name: 'Exo 2', family: 'Exo 2', category: 'Modern Sans' },
    { name: 'Cabin', family: 'Cabin', category: 'Modern Sans' },
    { name: 'Josefin Sans', family: 'Josefin Sans', category: 'Modern Sans' },
    { name: 'Karla', family: 'Karla', category: 'Modern Sans' },

    // Sinematik & Serif (20)
    { name: 'Cinzel (Sinematik Fragman)', family: 'Cinzel', category: 'Sinematik & Serif' },
    { name: 'Playfair Display (Lüks)', family: 'Playfair Display', category: 'Sinematik & Serif' },
    { name: 'Bodoni Moda (Vogue)', family: 'Bodoni Moda', category: 'Sinematik & Serif' },
    { name: 'Cormorant Garamond', family: 'Cormorant Garamond', category: 'Sinematik & Serif' },
    { name: 'Merriweather', family: 'Merriweather', category: 'Sinematik & Serif' },
    { name: 'Lora (Belgesel)', family: 'Lora', category: 'Sinematik & Serif' },
    { name: 'Abril Fatface (Editoryal)', family: 'Abril Fatface', category: 'Sinematik & Serif' },
    { name: 'Yeseva One', family: 'Yeseva One', category: 'Sinematik & Serif' },
    { name: 'DM Serif Display', family: 'DM Serif Display', category: 'Sinematik & Serif' },
    { name: 'Prata (Moda)', family: 'Prata', category: 'Sinematik & Serif' },
    { name: 'Marcellus (Antik/Destan)', family: 'Marcellus', category: 'Sinematik & Serif' },
    { name: 'Philosopher', family: 'Philosopher', category: 'Sinematik & Serif' },
    { name: 'Spectral', family: 'Spectral', category: 'Sinematik & Serif' },
    { name: 'Crimson Text', family: 'Crimson Text', category: 'Sinematik & Serif' },
    { name: 'EB Garamond', family: 'EB Garamond', category: 'Sinematik & Serif' },
    { name: 'Libre Baskerville', family: 'Libre Baskerville', category: 'Sinematik & Serif' },
    { name: 'Bitter', family: 'Bitter', category: 'Sinematik & Serif' },
    { name: 'Vollkorn', family: 'Vollkorn', category: 'Sinematik & Serif' },
    { name: 'Fraunces', family: 'Fraunces', category: 'Sinematik & Serif' },
    { name: 'Rozha One', family: 'Rozha One', category: 'Sinematik & Serif' },

    // El Yazısı & Fırça (20)
    { name: 'Permanent Marker (Keçeli Kalem)', family: 'Permanent Marker', category: 'El Yazısı & Fırça' },
    { name: 'Caveat (Doğal Not)', family: 'Caveat', category: 'El Yazısı & Fırça' },
    { name: 'Pacifico (Retro Script)', family: 'Pacifico', category: 'El Yazısı & Fırça' },
    { name: 'Dancing Script', family: 'Dancing Script', category: 'El Yazısı & Fırça' },
    { name: 'Satisfy', family: 'Satisfy', category: 'El Yazısı & Fırça' },
    { name: 'Shadows Into Light', family: 'Shadows Into Light', category: 'El Yazısı & Fırça' },
    { name: 'Kaushan Script (Fırça)', family: 'Kaushan Script', category: 'El Yazısı & Fırça' },
    { name: 'Great Vibes (Kaligrafi)', family: 'Great Vibes', category: 'El Yazısı & Fırça' },
    { name: 'Sacramento (İmza)', family: 'Sacramento', category: 'El Yazısı & Fırça' },
    { name: 'Amatic SC (İnce El Çizimi)', family: 'Amatic SC', category: 'El Yazısı & Fırça' },
    { name: 'Courgette', family: 'Courgette', category: 'El Yazısı & Fırça' },
    { name: 'Indie Flower', family: 'Indie Flower', category: 'El Yazısı & Fırça' },
    { name: 'Patrick Hand', family: 'Patrick Hand', category: 'El Yazısı & Fırça' },
    { name: 'Gloria Hallelujah', family: 'Gloria Hallelujah', category: 'El Yazısı & Fırça' },
    { name: 'Kalam', family: 'Kalam', category: 'El Yazısı & Fırça' },
    { name: 'Lobster (Kalın Script)', family: 'Lobster', category: 'El Yazısı & Fırça' },
    { name: 'Yellowtail', family: 'Yellowtail', category: 'El Yazısı & Fırça' },
    { name: 'Cookie', family: 'Cookie', category: 'El Yazısı & Fırça' },
    { name: 'Allura', family: 'Allura', category: 'El Yazısı & Fırça' },
    { name: 'Handlee', family: 'Handlee', category: 'El Yazısı & Fırça' },

    // Siber & Kod (15)
    { name: 'Orbitron (Sci-Fi / Cyber)', family: 'Orbitron', category: 'Siber & Kod' },
    { name: 'Chakra Petch (Gaming)', family: 'Chakra Petch', category: 'Siber & Kod' },
    { name: 'Press Start 2P (8-Bit Retro)', family: 'Press Start 2P', category: 'Siber & Kod' },
    { name: 'JetBrains Mono (Kod/Daktilo)', family: 'JetBrains Mono', category: 'Siber & Kod' },
    { name: 'Fira Code', family: 'Fira Code', category: 'Siber & Kod' },
    { name: 'Audiowide (Synthwave)', family: 'Audiowide', category: 'Siber & Kod' },
    { name: 'Rajdhani (HUD / Taktik)', family: 'Rajdhani', category: 'Siber & Kod' },
    { name: 'Oxanium (Mecha)', family: 'Oxanium', category: 'Siber & Kod' },
    { name: 'Silkscreen (Piksel)', family: 'Silkscreen', category: 'Siber & Kod' },
    { name: 'VT323 (CRT Terminal)', family: 'VT323', category: 'Siber & Kod' },
    { name: 'Share Tech Mono', family: 'Share Tech Mono', category: 'Siber & Kod' },
    { name: 'Space Mono', family: 'Space Mono', category: 'Siber & Kod' },
    { name: 'Electrolize', family: 'Electrolize', category: 'Siber & Kod' },
    { name: 'Michroma (Geniş Sci-Fi)', family: 'Michroma', category: 'Siber & Kod' },
    { name: 'Wallpoet (Stencil Cyber)', family: 'Wallpoet', category: 'Siber & Kod' }
  ];

  /**
   * Seçilen Google Font'u tarayıcıda ilk kez kullanıldığında dinamik olarak <link> ile yükler.
   */
  ensureFontLoaded(fontFamily?: string): void {
    if (!fontFamily || typeof document === 'undefined') return;
    const clean = fontFamily.trim();
    if (!clean || this.loadedFonts.has(clean)) return;
    this.loadedFonts.add(clean);

    const id = `gf-${clean.toLowerCase().replace(/[^a-z0-9]+/g, '-')}`;
    if (document.getElementById(id)) return;

    const link = document.createElement('link');
    link.id = id;
    link.rel = 'stylesheet';
    const encoded = encodeURIComponent(clean).replace(/%20/g, '+');
    link.href = `https://fonts.googleapis.com/css2?family=${encoded}:ital,wght@0,400;0,700;0,900;1,400;1,700&display=swap`;
    document.head.appendChild(link);
  }

  // 2. 16 HAZIR VİRAL METİN ŞABLONU (CAPCUT & PHOTOSHOP PRESETS)
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
      previewStyle: 'font-family: Pacifico; color: #F9A8D4; text-shadow: 0 2px 6px rgba(0,0,0,0.8);',
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
    },
    {
      id: 'fire_explosion',
      name: 'Alevli Aksiyon Başlık',
      badge: '🔥 Alev',
      previewBg: 'linear-gradient(135deg, #7c2d12, #090d16)',
      previewStyle: 'font-family: Russo One; color: #F97316; -webkit-text-stroke: 2px #000;',
      props: {
        font: 'Russo One',
        fontSize: 62,
        color: '#FACC15',
        fillType: 'gradient',
        gradientStart: '#FEF08A',
        gradientEnd: '#EA580C',
        gradientAngle: 180,
        strokeColor: '#000000',
        strokeWidth: 5,
        outerStrokeColor: '#DC2626',
        outerStrokeWidth: 4,
        glowEnabled: true,
        glowColor: '#F97316',
        glowRadius: 14,
        boxStyle: 'none',
        allCaps: true,
        animation: 'zoom-crash',
        loopAnimation: 'shake'
      }
    },
    {
      id: 'tiktok_modern_clean',
      name: 'TikTok Beyaz Kontur',
      badge: '📱 TikTok',
      previewBg: 'linear-gradient(135deg, #1e293b, #090d16)',
      previewStyle: 'font-family: Plus Jakarta Sans; font-weight: 800; color: #FFF; -webkit-text-stroke: 2px #000;',
      props: {
        font: 'Plus Jakarta Sans',
        fontSize: 50,
        fontWeight: 900,
        color: '#FFFFFF',
        fillType: 'solid',
        strokeColor: '#000000',
        strokeWidth: 5,
        shadowColor: '#000000',
        shadowDistance: 4,
        shadowBlur: 4,
        boxStyle: 'none',
        allCaps: false,
        animation: 'pop-up',
        exitAnimation: 'fade'
      }
    }
  ];

  // 3. 76 KATEGORİZE STÜDYO SES EFEKTİ (SFX) KÜTÜPHANESİ (WEB AUDIO API SENTEZLEYİCİ İLE %100 ÇEVRİMDIŞI & 0ms GECİKME)
  readonly sfxLibrary: SfxLibraryItem[] = [
    // --- WHOOSH / GEÇİŞ (14) ---
    { id: 'whoosh-fast', name: 'Whoosh Hızlı Geçiş', category: 'whoosh', icon: '💨', duration: 0.42, synthPreset: 'whoosh-fast', description: 'Hızlı sahne ve yazı geçişleri için rüzgar efekti', peaks: [0.1, 0.3, 0.7, 0.95, 1.0, 0.85, 0.5, 0.2, 0.05] },
    { id: 'swoosh-deep', name: 'Swoosh Derin Sinematik', category: 'whoosh', icon: '🌪️', duration: 0.75, synthPreset: 'swoosh-deep', description: 'Ağır kamera dönüşleri ve Whip Pan için derin geçiş', peaks: [0.05, 0.2, 0.5, 0.8, 0.95, 0.9, 0.7, 0.4, 0.15, 0.05] },
    { id: 'whoosh-air', name: 'Hafif Hava Geçişi (Airy)', category: 'whoosh', icon: '🍃', duration: 0.38, synthPreset: 'whoosh-fast', description: 'Yumuşak B-Roll ve metin belirmesi için hava geçişi', peaks: [0.1, 0.4, 0.8, 0.9, 0.6, 0.3, 0.1] },
    { id: 'whoosh-whip', name: 'Kırbaç Kamera (Whip Pan)', category: 'whoosh', icon: '⚡', duration: 0.30, synthPreset: 'whoosh-fast', description: 'Çok hızlı sağa/sola kamera savrulma sesi', peaks: [0.2, 0.8, 1.0, 0.7, 0.2] },
    { id: 'whoosh-flames', name: 'Ateşli Geçiş (Fire Whoosh)', category: 'whoosh', icon: '🔥', duration: 0.85, synthPreset: 'swoosh-deep', description: 'Alevli ve sıcak frekanslı geçiş rüzgarı', peaks: [0.1, 0.3, 0.75, 1.0, 0.9, 0.7, 0.4, 0.15] },
    { id: 'whoosh-cyber', name: 'Siber Lazer Geçiş', category: 'whoosh', icon: '🛸', duration: 0.45, synthPreset: 'digital-glitch', description: 'Fütüristik ve teknoloji videoları için siber geçiş', peaks: [0.2, 0.6, 1.0, 0.85, 0.5, 0.2] },
    { id: 'whoosh-reverse', name: 'Ters Vakum (Reverse Suck)', category: 'whoosh', icon: '🌀', duration: 0.65, synthPreset: 'tension-riser', description: 'Kesim noktasına doğru vakumlayarak çeken geçiş', peaks: [0.05, 0.15, 0.3, 0.55, 0.8, 1.0, 0.2] },
    { id: 'whoosh-double', name: 'Çiftli Rüzgar (Double Swish)', category: 'whoosh', icon: '🎐', duration: 0.55, synthPreset: 'whoosh-fast', description: 'İki aşamalı hızlı hareket efekti', peaks: [0.3, 0.9, 0.3, 1.0, 0.4, 0.1] },
    { id: 'whoosh-heavy', name: 'Ağır Metalik Swoosh', category: 'whoosh', icon: '⚔️', duration: 0.70, synthPreset: 'swoosh-deep', description: 'Kılıç/metal tınılı keskin geçiş', peaks: [0.1, 0.5, 1.0, 0.85, 0.6, 0.3, 0.1] },
    { id: 'whoosh-zoom-in', name: 'Hızlı Zoom Yakınlaşma', category: 'whoosh', icon: '🔍', duration: 0.48, synthPreset: 'whoosh-fast', description: 'Jump-cut ve Punch-in zoom geçiş sesi', peaks: [0.1, 0.3, 0.7, 1.0, 0.6, 0.2] },
    { id: 'whoosh-zoom-out', name: 'Hızlı Zoom Uzaklaşma', category: 'whoosh', icon: '🔭', duration: 0.48, synthPreset: 'swoosh-deep', description: 'Geniş açıya dönüş geçiş sesi', peaks: [0.8, 1.0, 0.7, 0.4, 0.2, 0.05] },
    { id: 'whoosh-cloth', name: 'Kumaş / El Hareketi (Foley)', category: 'whoosh', icon: '🧥', duration: 0.32, synthPreset: 'whoosh-fast', description: 'Doğal vlog geçişleri için organik kumaş sesi', peaks: [0.2, 0.7, 0.9, 0.5, 0.15] },
    { id: 'whoosh-bass', name: 'Sub-Bass Geçiş Dalgası', category: 'whoosh', icon: '🌊', duration: 0.80, synthPreset: 'sub-bass-drop', description: 'Derin bas destekli ağır sahne değişimi', peaks: [0.2, 0.6, 1.0, 0.9, 0.7, 0.4, 0.1] },
    { id: 'whoosh-sparkle', name: 'Sihirli Parıltı Geçişi', category: 'whoosh', icon: '✨', duration: 0.60, synthPreset: 'success-chime', description: 'Parlak kristal tınılı sihirli geçiş', peaks: [0.3, 0.7, 1.0, 0.8, 0.5, 0.2] },

    // --- POP / METİN & STICKER BELİRME (12) ---
    { id: 'pop-bubble', name: 'Pop Baloncuk (Metin/Sticker)', category: 'pop', icon: '🫧', duration: 0.25, synthPreset: 'pop-bubble', description: 'Ekrana yazı veya çıkartma geldiğinde çıkan klasik Pop sesi', peaks: [0.2, 0.95, 1.0, 0.6, 0.2, 0.05] },
    { id: 'pop-crisp', name: 'Pop Keskin Vurgu', category: 'pop', icon: '✨', duration: 0.22, synthPreset: 'pop-crisp', description: 'Kısa ve net bildirim/rozet belirmesi', peaks: [0.4, 1.0, 0.8, 0.3, 0.05] },
    { id: 'pop-cork', name: 'Mantar Tıpa Patlaması', category: 'pop', icon: '🍾', duration: 0.28, synthPreset: 'pop-bubble', description: 'Tok ve eğlenceli şişe mantarı pop sesi', peaks: [0.3, 1.0, 0.7, 0.3, 0.1] },
    { id: 'pop-waterdrop', name: 'Su Damlası (Bloop)', category: 'pop', icon: '💧', duration: 0.30, synthPreset: 'pop-bubble', description: 'Organik su damlası rezonansı', peaks: [0.2, 0.9, 1.0, 0.5, 0.15] },
    { id: 'pop-finger-snap', name: 'Parmak Şıklatma (Snap)', category: 'pop', icon: '🫰', duration: 0.20, synthPreset: 'pop-crisp', description: 'Anlık değişim ve vurgu için parmak şıklatma', peaks: [1.0, 0.7, 0.25, 0.05] },
    { id: 'pop-plop', name: 'Yumuşak Plop (Emoji)', category: 'pop', icon: '🎈', duration: 0.26, synthPreset: 'pop-bubble', description: 'Animasyonlu emojiler için tatlı plop sesi', peaks: [0.3, 0.95, 0.8, 0.3, 0.05] },
    { id: 'pop-double', name: 'Çiftli Pop-Pop', category: 'pop', icon: '🍒', duration: 0.36, synthPreset: 'pop-crisp', description: 'İki kelimeli başlıklar için ardışık çift pop', peaks: [0.9, 0.2, 1.0, 0.3, 0.05] },
    { id: 'pop-suction', name: 'Vakum Pop (Vantuz)', category: 'pop', icon: '🪠', duration: 0.28, synthPreset: 'pop-bubble', description: 'Ekrana yapışan çıkartmalar için vakum sesi', peaks: [0.2, 0.8, 1.0, 0.4, 0.1] },
    { id: 'pop-wood', name: 'Ahşap Tokmak Tıkırtısı', category: 'pop', icon: '🪵', duration: 0.22, synthPreset: 'pop-crisp', description: 'Minimalist ve modern bilgi kartı sesi', peaks: [0.9, 0.6, 0.2, 0.05] },
    { id: 'pop-glass', name: 'Kristal Cam Dokunuşu', category: 'pop', icon: '🥂', duration: 0.40, synthPreset: 'ding-bell', description: 'Zarif ve parlak cam tınısı', peaks: [1.0, 0.8, 0.5, 0.25, 0.1] },
    { id: 'pop-rubber', name: 'Elastik Yaylanma (Bounce)', category: 'pop', icon: '🏀', duration: 0.35, synthPreset: 'pop-bubble', description: 'Bounce animasyonlu yazılar için elastik ses', peaks: [0.4, 1.0, 0.7, 0.5, 0.2] },
    { id: 'pop-card-flip', name: 'Kart Çevirme (Card Flip)', category: 'pop', icon: '🃏', duration: 0.25, synthPreset: 'camera-shutter', description: '3D dönen metin ve görseller için kart sesi', peaks: [0.7, 1.0, 0.4, 0.1] },

    // --- CINEMATIC / DARBE & GERİLİM (16) ---
    { id: 'sub-bass-drop', name: 'Sub Bass Drop (808 Boom)', category: 'cinematic', icon: '💣', duration: 1.40, synthPreset: 'sub-bass-drop', description: 'Dramatik anlar ve büyük başlıklar için derin bas patlaması', peaks: [1.0, 0.95, 0.9, 0.82, 0.75, 0.65, 0.5, 0.35, 0.2, 0.1] },
    { id: 'cinematic-hit', name: 'Sinematik Darbe (Impact Hit)', category: 'cinematic', icon: '🔨', duration: 1.10, synthPreset: 'cinematic-hit', description: 'Fragman tarzı güçlü metalik/orkestral vuruş', peaks: [1.0, 0.98, 0.85, 0.65, 0.45, 0.3, 0.15, 0.05] },
    { id: 'tension-riser', name: 'Gerilim Yükseltici (Riser)', category: 'cinematic', icon: '📈', duration: 1.50, synthPreset: 'tension-riser', description: 'Sürpriz veya kesim öncesi yükselen gerilim sesi', peaks: [0.05, 0.12, 0.22, 0.35, 0.5, 0.68, 0.85, 0.98, 1.0, 0.2] },
    { id: 'digital-glitch', name: 'Dijital Glitch / Parazit', category: 'cinematic', icon: '⚡', duration: 0.45, synthPreset: 'digital-glitch', description: 'Glitch geçişleri ve siber metinler için dijital bozulma', peaks: [0.9, 0.3, 1.0, 0.2, 0.85, 0.95, 0.4, 0.8] },
    { id: 'inception-braam', name: 'Fragman Borusu (Braaam)', category: 'cinematic', icon: '📯', duration: 1.60, synthPreset: 'sub-bass-drop', description: 'Hans Zimmer tarzı devasa sinematik bakır/bas kükremesi', peaks: [0.6, 0.95, 1.0, 0.95, 0.85, 0.7, 0.5, 0.25] },
    { id: 'thud-punch', name: 'Tok Yumruk / Çarpma (Punch)', category: 'cinematic', icon: '🥊', duration: 0.38, synthPreset: 'cinematic-hit', description: 'Zoom-crash ve ekran sarsıntısı için sert darbe', peaks: [1.0, 0.85, 0.4, 0.1] },
    { id: 'metal-slam', name: 'Demir Kapı Kapanışı (Slam)', category: 'cinematic', icon: '🚪', duration: 0.95, synthPreset: 'cinematic-hit', description: 'Yankılı ağır metal çarpma efekti', peaks: [1.0, 0.9, 0.7, 0.5, 0.35, 0.2, 0.1] },
    { id: 'thunder-crack', name: 'Yıldırım & Gök Gürültüsü', category: 'cinematic', icon: '🌩️', duration: 1.45, synthPreset: 'sub-bass-drop', description: 'Şok edici açıklamalar için yıldırım düşmesi', peaks: [1.0, 0.8, 0.9, 0.6, 0.45, 0.3, 0.15] },
    { id: 'explosion-heavy', name: 'Büyük Patlama (Explosion)', category: 'cinematic', icon: '💥', duration: 1.50, synthPreset: 'sub-bass-drop', description: 'Aksiyon ve oyun videoları için patlama efekti', peaks: [1.0, 0.95, 0.85, 0.7, 0.55, 0.4, 0.2, 0.1] },
    { id: 'glass-shatter', name: 'Cam Kırılması (Shatter)', category: 'cinematic', icon: '🪟', duration: 0.80, synthPreset: 'digital-glitch', description: 'Ezber bozan anlar için tuzla buz olan cam sesi', peaks: [1.0, 0.9, 0.75, 0.5, 0.3, 0.1] },
    { id: 'heartbeat-tense', name: 'Gerilim Kalp Atışı', category: 'cinematic', icon: '🫀', duration: 1.20, synthPreset: 'sub-bass-drop', description: 'Heyecanlı bekleyiş anları için derin kalp atışı', peaks: [0.9, 0.2, 1.0, 0.1, 0.85, 0.2, 0.95, 0.1] },
    { id: 'clock-ticking', name: 'Hızlı Saat Tik-Tak (Süre)', category: 'cinematic', icon: '⏱️', duration: 1.00, synthPreset: 'keyboard-typing', description: 'Zaman sınırı ve geri sayım gerilimi', peaks: [0.9, 0.1, 0.8, 0.1, 0.9, 0.1, 0.85, 0.1] },
    { id: 'horror-stinger', name: 'Korku / Şok Stinger', category: 'cinematic', icon: '👻', duration: 0.90, synthPreset: 'tension-riser', description: 'Ani farkındalık ve korku vurgusu', peaks: [0.95, 1.0, 0.85, 0.6, 0.35, 0.1] },
    { id: 'tape-stop', name: 'Kaset Durdurma (Tape Stop)', category: 'cinematic', icon: '📼', duration: 0.60, synthPreset: 'record-scratch', description: 'Müziği ve akışı yavaşlatarak durduran efekt', peaks: [0.9, 0.85, 0.75, 0.6, 0.4, 0.15] },
    { id: 'cyber-powerdown', name: 'Sistem Kapanışı (Power Down)', category: 'cinematic', icon: '🔌', duration: 0.80, synthPreset: 'sub-bass-drop', description: 'Enerji kesilmesi ve kapanış efekti', peaks: [0.9, 0.8, 0.65, 0.5, 0.3, 0.1] },
    { id: 'drone-dark', name: 'Karanlık Atmosfer Drone', category: 'cinematic', icon: '🌑', duration: 1.80, synthPreset: 'swoosh-deep', description: 'Gizemli hikayeler için arka plan gerilim dokusu', peaks: [0.3, 0.6, 0.8, 0.85, 0.8, 0.7, 0.4, 0.2] },

    // --- UI / BİLDİRİM & TEKNOLOJİ (16) ---
    { id: 'ding-bell', name: 'Ding Parlak Çan', category: 'ui', icon: '🔔', duration: 0.90, synthPreset: 'ding-bell', description: 'Önemli fikir, ipucu veya doğru cevap çanı', peaks: [1.0, 0.9, 0.75, 0.6, 0.45, 0.3, 0.2, 0.1, 0.05] },
    { id: 'cash-register', name: 'Kasa / Para Sesi (Ka-Ching)', category: 'ui', icon: '💰', duration: 0.80, synthPreset: 'cash-register', description: 'Fiyat, kazanç ve finans vurguları için kasa çanı', peaks: [0.9, 0.4, 1.0, 0.85, 0.6, 0.4, 0.2, 0.1] },
    { id: 'camera-shutter', name: 'Kamera Deklanşör (Shutter)', category: 'ui', icon: '📸', duration: 0.35, synthPreset: 'camera-shutter', description: 'Fotoğraf/ekran görüntüsü ve dondurulmuş kare efekti', peaks: [0.95, 0.3, 0.85, 0.2, 0.05] },
    { id: 'keyboard-typing', name: 'Mekanik Klavye (Daktilo)', category: 'ui', icon: '⌨️', duration: 0.85, synthPreset: 'keyboard-typing', description: 'Daktilo animasyonlu yazılar için tuş tıkırtısı', peaks: [0.8, 0.2, 0.9, 0.15, 0.75, 0.2, 0.85, 0.1, 0.9, 0.2] },
    { id: 'mouse-click', name: 'Çift Fare Tıklaması', category: 'ui', icon: '🖱️', duration: 0.30, synthPreset: 'mouse-click', description: 'Buton, abone ol ve UI etkileşim sesi', peaks: [0.9, 0.1, 0.95, 0.1] },
    { id: 'success-chime', name: 'Başarı / Seviye Atlama', category: 'ui', icon: '🏆', duration: 0.80, synthPreset: 'success-chime', description: 'Olumlu sonuç ve onay akoru', peaks: [0.6, 0.75, 0.9, 1.0, 0.85, 0.6, 0.3, 0.1] },
    { id: 'ios-notification', name: 'Akıllı Telefon Bildirimi', category: 'ui', icon: '📱', duration: 0.55, synthPreset: 'ding-bell', description: 'Mesaj ve sosyal medya bildirimi sesi', peaks: [0.8, 1.0, 0.7, 0.4, 0.1] },
    { id: 'message-sent', name: 'Mesaj Gönderildi (Swoosh)', category: 'ui', icon: '💬', duration: 0.35, synthPreset: 'pop-crisp', description: 'Sohbet balonu çıkma efekti', peaks: [0.3, 0.8, 1.0, 0.4, 0.1] },
    { id: 'marker-pen', name: 'Fosforlu Kalem Çizimi', category: 'ui', icon: '🖍️', duration: 0.50, synthPreset: 'whoosh-fast', description: 'Alt çizgi ve fosforlu vurgu sesi', peaks: [0.4, 0.8, 0.9, 0.7, 0.3] },
    { id: 'page-turn', name: 'Sayfa Çevirme (Page Flip)', category: 'ui', icon: '📄', duration: 0.42, synthPreset: 'whoosh-fast', description: 'Yeni bölüme veya konuya geçiş sesi', peaks: [0.2, 0.75, 0.95, 0.5, 0.15] },
    { id: 'scanner-beep', name: 'Barkod / Lazer Tarama', category: 'ui', icon: '📟', duration: 0.30, synthPreset: 'ding-bell', description: 'Analiz ve veri okuma bip sesi', peaks: [0.95, 0.95, 0.8, 0.1] },
    { id: 'hud-telemetry', name: 'Bilimkurgu HUD Verisi', category: 'ui', icon: '📡', duration: 0.60, synthPreset: 'keyboard-typing', description: 'Dijital ekran ve veri akışı tıkırtısı', peaks: [0.7, 0.3, 0.9, 0.2, 0.8, 0.4, 0.9] },
    { id: 'apple-pay-confirm', name: 'Modern Onay Tınısı (Pay)', category: 'ui', icon: '✅', duration: 0.65, synthPreset: 'success-chime', description: 'Premium çift notalı doğrulama sesi', peaks: [0.7, 0.5, 1.0, 0.8, 0.4, 0.1] },
    { id: 'alarm-siren', name: 'Uyarı / Alarm Sireni', category: 'ui', icon: '🚨', duration: 0.90, synthPreset: 'error-buzzer', description: 'Kritik hata veya önemli uyarı alarmı', peaks: [0.9, 0.5, 0.95, 0.5, 0.9, 0.4] },
    { id: 'coin-drop', name: 'Metal Para Düşmesi', category: 'ui', icon: '🪙', duration: 0.60, synthPreset: 'cash-register', description: 'Bozuk para / altın çınlaması', peaks: [1.0, 0.6, 0.85, 0.5, 0.7, 0.3, 0.1] },
    { id: 'unlock-latch', name: 'Kilit Açılma (Unlock)', category: 'ui', icon: '🔓', duration: 0.35, synthPreset: 'camera-shutter', description: 'Gizli bilgi veya ipucu açılma mekanizması', peaks: [0.8, 0.2, 1.0, 0.3] },

    // --- FUNNY / KOMEDİ, MEME & OYUN (18) ---
    { id: 'record-scratch', name: 'Plak Durma (Record Scratch)', category: 'funny', icon: '💿', duration: 0.65, synthPreset: 'record-scratch', description: 'Beklenmedik veya komik kesimler için plak cızırtısı', peaks: [0.7, 0.95, 0.6, 1.0, 0.8, 0.4, 0.1] },
    { id: 'error-buzzer', name: 'Yanlış Cevap (Buzzer)', category: 'funny', icon: '❌', duration: 0.60, synthPreset: 'error-buzzer', description: 'Hatalı hamle veya mizahi ret sesi', peaks: [0.9, 0.95, 0.9, 0.85, 0.8, 0.2] },
    { id: 'vine-boom', name: 'Meme Boom (Vine Thud)', category: 'funny', icon: '🗿', duration: 1.10, synthPreset: 'sub-bass-drop', description: 'Şüpheli bakış ve komik zoom anları için klasik Meme Boom', peaks: [1.0, 0.95, 0.85, 0.65, 0.4, 0.2, 0.05] },
    { id: 'cartoon-boing', name: 'Çizgi Film Yay (Boing)', category: 'funny', icon: '弹簧', duration: 0.55, synthPreset: 'pop-bubble', description: 'Zıplama ve komik şaşkınlık yay sesi', peaks: [0.9, 0.7, 0.85, 0.6, 0.7, 0.4, 0.2] },
    { id: 'sad-trombone', name: 'Üzgün Trombon (Fail)', category: 'funny', icon: '🎺', duration: 1.30, synthPreset: 'error-buzzer', description: 'Başarısızlık ve hayal kırıklığı anları (Wah-Wah-Wah)', peaks: [0.8, 0.7, 0.85, 0.6, 0.9, 0.5, 0.4, 0.2] },
    { id: 'comedy-rimshot', name: 'Espri Davulu (Ba-Dum-Tss)', category: 'funny', icon: '🥁', duration: 0.85, synthPreset: 'camera-shutter', description: 'Soğuk espri sonrası bateri vuruşu', peaks: [0.8, 0.2, 0.9, 0.3, 1.0, 0.6, 0.2] },
    { id: 'clown-horn', name: 'Palyaço Kornası (Honk)', category: 'funny', icon: '🤡', duration: 0.45, synthPreset: 'error-buzzer', description: 'Komik sansür veya hata kornası', peaks: [0.9, 0.3, 0.95, 0.2] },
    { id: 'duck-quack', name: 'Ördek Vaklaması (Quack)', category: 'funny', icon: '🦆', duration: 0.35, synthPreset: 'pop-bubble', description: 'Komik geçiş ve sansür efekti', peaks: [0.95, 0.8, 0.4, 0.1] },
    { id: 'censorship-beep', name: 'TV Sansür Bip (1000Hz)', category: 'funny', icon: '🤬', duration: 0.50, synthPreset: 'ding-bell', description: 'Küfür veya sürpriz kelime gizleme bip sesi', peaks: [0.95, 0.95, 0.95, 0.95, 0.95] },
    { id: 'slide-whistle-up', name: 'Kayar Düdük Yukarı', category: 'funny', icon: '📈', duration: 0.60, synthPreset: 'tension-riser', description: 'Komik yükseliş veya büyüme efekti', peaks: [0.3, 0.5, 0.7, 0.9, 1.0] },
    { id: 'slide-whistle-down', name: 'Kayar Düdük Aşağı', category: 'funny', icon: '📉', duration: 0.60, synthPreset: 'swoosh-deep', description: 'Komik düşüş veya küçülme efekti', peaks: [1.0, 0.8, 0.6, 0.4, 0.2] },
    { id: 'retro-coin-8bit', name: '8-Bit Mario Altın Sesi', category: 'funny', icon: '👾', duration: 0.45, synthPreset: 'cash-register', description: 'Retro oyun puan kazanma sesi', peaks: [0.8, 1.0, 0.9, 0.6, 0.2] },
    { id: 'retro-jump-8bit', name: '8-Bit Arcade Zıplama', category: 'funny', icon: '🕹️', duration: 0.35, synthPreset: 'pop-bubble', description: 'Retro platform oyunu zıplama efekti', peaks: [0.4, 0.7, 0.9, 1.0, 0.5] },
    { id: 'retro-laser-8bit', name: '8-Bit Uzay Lazeri (Pew)', category: 'funny', icon: '🔫', duration: 0.32, synthPreset: 'digital-glitch', description: 'Retro lazer ateşleme efekti', peaks: [1.0, 0.8, 0.5, 0.2] },
    { id: 'retro-powerup', name: '8-Bit Güçlenme (Power-Up)', category: 'funny', icon: '🍄', duration: 0.75, synthPreset: 'success-chime', description: 'Hızlı arpejli seviye ve güç artışı', peaks: [0.5, 0.7, 0.85, 0.95, 1.0, 0.8] },
    { id: 'crowd-applause', name: 'Stüdyo Alkış & Tezahürat', category: 'funny', icon: '👏', duration: 1.50, synthPreset: 'whoosh-fast', description: 'Başarı anları için coşkulu alkış efekti', peaks: [0.4, 0.8, 0.95, 1.0, 0.9, 0.75, 0.5, 0.2] },
    { id: 'cricket-awkward', name: 'Cırcır Böceği (Soğuk Sessizlik)', category: 'funny', icon: '🦗', duration: 1.20, synthPreset: 'keyboard-typing', description: 'Kimsenin gülmediği garip sessizlik anı', peaks: [0.7, 0.1, 0.7, 0.1, 0.7, 0.1, 0.7] },
    { id: 'anime-wow', name: 'Parlak Anime Şaşkınlık', category: 'funny', icon: '🤩', duration: 0.85, synthPreset: 'success-chime', description: 'Etkileyici ve parlak anlar için ışıltılı akor', peaks: [0.8, 1.0, 0.9, 0.7, 0.4, 0.15] }
  ];

  // 4. 45 FFMPEG XFADE VİDEO VE SAHNE GEÇİŞ EFEKTİ (8 KATEGORİ, %100 RENDER MOTORU UYUMLU)
  readonly transitionLibrary: TransitionLibraryItem[] = [
    // --- Temel (8) ---
    { type: 'fade', name: 'Yumuşak Geçiş (Dissolve)', category: 'Temel', icon: '🌫️', defaultDuration: 0.5, recommendedSfx: 'whoosh-air' },
    { type: 'fadeblack', name: 'Siyaha Kararma (Dip to Black)', category: 'Temel', icon: '⬛', defaultDuration: 0.6, recommendedSfx: 'swoosh-deep' },
    { type: 'fadegrays', name: 'Griye Geçiş (Monochrome)', category: 'Temel', icon: '🩶', defaultDuration: 0.55, recommendedSfx: 'whoosh-air' },
    { type: 'dissolve', name: 'Kumlanma Çözülme (Dissolve)', category: 'Temel', icon: '✨', defaultDuration: 0.5, recommendedSfx: 'whoosh-sparkle' },
    { type: 'distance', name: 'Derinlik / Renk Mesafesi', category: 'Temel', icon: '🌌', defaultDuration: 0.5, recommendedSfx: 'swoosh-deep' },
    { type: 'hblur', name: 'Yatay Hareket Bulanıklığı (Motion Blur)', category: 'Temel', icon: '💨', defaultDuration: 0.4, recommendedSfx: 'whoosh-fast' },
    { type: 'wipeleft', name: 'Sola Perde Silme (Wipe Left)', category: 'Temel', icon: '◧', defaultDuration: 0.45, recommendedSfx: 'whoosh-fast' },
    { type: 'wiperight', name: 'Sağa Perde Silme (Wipe Right)', category: 'Temel', icon: '◨', defaultDuration: 0.45, recommendedSfx: 'whoosh-fast' },

    // --- Kamera / Whip (12) ---
    { type: 'slideleft', name: 'Hızlı Sola Kayma (Whip Left)', category: 'Kamera / Whip', icon: '⏪', defaultDuration: 0.35, recommendedSfx: 'whoosh-whip' },
    { type: 'slideright', name: 'Hızlı Sağa Kayma (Whip Right)', category: 'Kamera / Whip', icon: '⏩', defaultDuration: 0.35, recommendedSfx: 'whoosh-whip' },
    { type: 'slideup', name: 'Yukarı Savrulma (Whip Up)', category: 'Kamera / Whip', icon: '⏫', defaultDuration: 0.4, recommendedSfx: 'whoosh-fast' },
    { type: 'slidedown', name: 'Aşağı Savrulma (Whip Down)', category: 'Kamera / Whip', icon: '⏬', defaultDuration: 0.4, recommendedSfx: 'whoosh-fast' },
    { type: 'smoothleft', name: 'Elastik Sola Kayma (Smooth Left)', category: 'Kamera / Whip', icon: '⬅️', defaultDuration: 0.45, recommendedSfx: 'whoosh-fast' },
    { type: 'smoothright', name: 'Elastik Sağa Kayma (Smooth Right)', category: 'Kamera / Whip', icon: '➡️', defaultDuration: 0.45, recommendedSfx: 'whoosh-fast' },
    { type: 'smoothup', name: 'Elastik Yukarı (Smooth Up)', category: 'Kamera / Whip', icon: '⬆️', defaultDuration: 0.45, recommendedSfx: 'whoosh-fast' },
    { type: 'smoothdown', name: 'Elastik Aşağı (Smooth Down)', category: 'Kamera / Whip', icon: '⬇️', defaultDuration: 0.45, recommendedSfx: 'whoosh-fast' },
    { type: 'zoomin', name: 'Yakınlaşarak Çarpma (Zoom Crash)', category: 'Kamera / Whip', icon: '🔍', defaultDuration: 0.4, recommendedSfx: 'sub-bass-drop' },
    { type: 'squeezeh', name: 'Yatay Sıkıştırma (Squeeze H)', category: 'Kamera / Whip', icon: '↔️', defaultDuration: 0.4, recommendedSfx: 'whoosh-whip' },
    { type: 'squeezev', name: 'Dikey Sıkıştırma (Squeeze V)', category: 'Kamera / Whip', icon: '↕️', defaultDuration: 0.4, recommendedSfx: 'whoosh-whip' },
    { type: 'radial', name: 'Dairesel Saat Taraması (Radial)', category: 'Kamera / Whip', icon: '🧭', defaultDuration: 0.5, recommendedSfx: 'whoosh-fast' },

    // --- Işık / Flaş & Rüzgar (5) ---
    { type: 'fadewhite', name: 'Beyaz Flaş Patlaması (Flash)', category: 'Işık / Flaş', icon: '⚡', defaultDuration: 0.35, recommendedSfx: 'camera-shutter' },
    { type: 'hlwind', name: 'Sola Rüzgar Çizgileri (Wind Left)', category: 'Işık / Flaş', icon: '🌬️', defaultDuration: 0.4, recommendedSfx: 'whoosh-fast' },
    { type: 'hrwind', name: 'Sağa Rüzgar Çizgileri (Wind Right)', category: 'Işık / Flaş', icon: '🌪️', defaultDuration: 0.4, recommendedSfx: 'whoosh-fast' },
    { type: 'vuwind', name: 'Yukarı Rüzgar Akışı (Wind Up)', category: 'Işık / Flaş', icon: '☄️', defaultDuration: 0.4, recommendedSfx: 'whoosh-fast' },
    { type: 'vdwind', name: 'Aşağı Rüzgar Akışı (Wind Down)', category: 'Işık / Flaş', icon: '🌧️', defaultDuration: 0.4, recommendedSfx: 'whoosh-fast' },

    // --- Dijital & Maske (10) ---
    { type: 'circleopen', name: 'Dairesel Açılış (Iris Open)', category: 'Dijital & Maske', icon: '⭕', defaultDuration: 0.5, recommendedSfx: 'pop-bubble' },
    { type: 'circleclose', name: 'Dairesel Kapanış (Iris Close)', category: 'Dijital & Maske', icon: '🎯', defaultDuration: 0.5, recommendedSfx: 'swoosh-deep' },
    { type: 'circlecrop', name: 'Dairesel Odak Kırpma (Circle Crop)', category: 'Dijital & Maske', icon: '🔘', defaultDuration: 0.5, recommendedSfx: 'whoosh-zoom-in' },
    { type: 'rectcrop', name: 'Sinematik Kutu Açılış (Rect Crop)', category: 'Dijital & Maske', icon: '🔲', defaultDuration: 0.5, recommendedSfx: 'whoosh-fast' },
    { type: 'pixelize', name: 'Dijital Pikselleşme (Mosaic)', category: 'Dijital & Maske', icon: '🟦', defaultDuration: 0.45, recommendedSfx: 'digital-glitch' },
    { type: 'hlslice', name: 'Glitch Sol Dilimleme (Slice L)', category: 'Dijital & Maske', icon: '📺', defaultDuration: 0.35, recommendedSfx: 'digital-glitch' },
    { type: 'hrslice', name: 'Glitch Sağ Dilimleme (Slice R)', category: 'Dijital & Maske', icon: '📟', defaultDuration: 0.35, recommendedSfx: 'digital-glitch' },
    { type: 'vuslice', name: 'Glitch Dikey Dilim Yukarı', category: 'Dijital & Maske', icon: '📊', defaultDuration: 0.35, recommendedSfx: 'digital-glitch' },
    { type: 'vdslice', name: 'Glitch Dikey Dilim Aşağı', category: 'Dijital & Maske', icon: '📉', defaultDuration: 0.35, recommendedSfx: 'digital-glitch' },
    { type: 'vertopen', name: 'Dikey Sahne Perdesi Açılış', category: 'Dijital & Maske', icon: '🎭', defaultDuration: 0.5, recommendedSfx: 'whoosh-fast' },

    // --- Perde & Bölme (10) ---
    { type: 'vertclose', name: 'Dikey Sahne Perdesi Kapanış', category: 'Perde & Bölme', icon: '🚪', defaultDuration: 0.5, recommendedSfx: 'metal-slam' },
    { type: 'horzopen', name: 'Sinema Barı Açılış (Horz Open)', category: 'Perde & Bölme', icon: '🎬', defaultDuration: 0.5, recommendedSfx: 'whoosh-fast' },
    { type: 'horzclose', name: 'Sinema Barı Kapanış (Horz Close)', category: 'Perde & Bölme', icon: '🎞️', defaultDuration: 0.5, recommendedSfx: 'swoosh-deep' },
    { type: 'wipeup', name: 'Yukarı Perde Silme', category: 'Perde & Bölme', icon: '⬆️', defaultDuration: 0.45, recommendedSfx: 'whoosh-fast' },
    { type: 'wipedown', name: 'Aşağı Perde Silme', category: 'Perde & Bölme', icon: '⬇️', defaultDuration: 0.45, recommendedSfx: 'whoosh-fast' },
    { type: 'diagtl', name: 'Çapraz Sol-Üst Perde (Diag TL)', category: 'Perde & Bölme', icon: '↖️', defaultDuration: 0.45, recommendedSfx: 'whoosh-fast' },
    { type: 'diagtr', name: 'Çapraz Sağ-Üst Perde (Diag TR)', category: 'Perde & Bölme', icon: '↗️', defaultDuration: 0.45, recommendedSfx: 'whoosh-fast' },
    { type: 'diagbl', name: 'Çapraz Sol-Alt Perde (Diag BL)', category: 'Perde & Bölme', icon: '↙️', defaultDuration: 0.45, recommendedSfx: 'whoosh-fast' },
    { type: 'diagbr', name: 'Çapraz Sağ-Alt Perde (Diag BR)', category: 'Perde & Bölme', icon: '↘️', defaultDuration: 0.45, recommendedSfx: 'whoosh-fast' },
    { type: 'coverleft', name: 'Üzerini Örterek Kayma (Cover)', category: 'Perde & Bölme', icon: '🃏', defaultDuration: 0.4, recommendedSfx: 'pop-card-flip' }
  ];

  // 5. ZENGİN ANİMASYONLU EMOJİ (GOOGLE NOTO GIF) + 3D/VEKTÖR ÇIKARTMA PAKETİ + CANLI 200.000+ ICONIFY ARAMA
  readonly stickerLibrary: StickerLibraryItem[] = [
    // --- GOOGLE NOTO HAREKETLİ (ANIMATED GIF) EMOJİLER (24) ---
    { id: 'anim_fire', name: '🔥 Hareketli Alev (Trend)', category: 'animated', preview: '🔥 CANLI', isAnimated: true, dataUrl: 'https://fonts.gstatic.com/s/e/notoemoji/latest/1f525/512.gif' },
    { id: 'anim_rocket', name: '🚀 Hareketli Roket', category: 'animated', preview: '🚀 CANLI', isAnimated: true, dataUrl: 'https://fonts.gstatic.com/s/e/notoemoji/latest/1f680/512.gif' },
    { id: 'anim_mindblown', name: '🤯 Beyin Patlaması (Şok)', category: 'animated', preview: '🤯 CANLI', isAnimated: true, dataUrl: 'https://fonts.gstatic.com/s/e/notoemoji/latest/1f92f/512.gif' },
    { id: 'anim_idea', name: '💡 Parlayan Ampul (Fikir)', category: 'animated', preview: '💡 CANLI', isAnimated: true, dataUrl: 'https://fonts.gstatic.com/s/e/notoemoji/latest/1f4a1/512.gif' },
    { id: 'anim_zap', name: '⚡ Çakan Şimşek (Enerji)', category: 'animated', preview: '⚡ CANLI', isAnimated: true, dataUrl: 'https://fonts.gstatic.com/s/e/notoemoji/latest/26a1/512.gif' },
    { id: 'anim_target', name: '🎯 Tam İsabet (Dart)', category: 'animated', preview: '🎯 CANLI', isAnimated: true, dataUrl: 'https://fonts.gstatic.com/s/e/notoemoji/latest/1f3af/512.gif' },
    { id: 'anim_100', name: '💯 Yüzde Yüz (Tam Puan)', category: 'animated', preview: '💯 CANLI', isAnimated: true, dataUrl: 'https://fonts.gstatic.com/s/e/notoemoji/latest/1f4af/512.gif' },
    { id: 'anim_joy', name: '😂 Gözyaşlarıyla Gülen', category: 'animated', preview: '😂 CANLI', isAnimated: true, dataUrl: 'https://fonts.gstatic.com/s/e/notoemoji/latest/1f602/512.gif' },
    { id: 'anim_star_eyes', name: '🤩 Yıldız Gözlü Hayran', category: 'animated', preview: '🤩 CANLI', isAnimated: true, dataUrl: 'https://fonts.gstatic.com/s/e/notoemoji/latest/1f929/512.gif' },
    { id: 'anim_clap', name: '👏 Hareketli Alkış', category: 'animated', preview: '👏 CANLI', isAnimated: true, dataUrl: 'https://fonts.gstatic.com/s/e/notoemoji/latest/1f44f/512.gif' },
    { id: 'anim_money_wings', name: '💸 Uçan Para', category: 'animated', preview: '💸 CANLI', isAnimated: true, dataUrl: 'https://fonts.gstatic.com/s/e/notoemoji/latest/1f4b8/512.gif' },
    { id: 'anim_gem', name: '💎 Parlayan Elmas', category: 'animated', preview: '💎 CANLI', isAnimated: true, dataUrl: 'https://fonts.gstatic.com/s/e/notoemoji/latest/1f48e/512.gif' },
    { id: 'anim_trophy', name: '🏆 Şampiyonluk Kupası', category: 'animated', preview: '🏆 CANLI', isAnimated: true, dataUrl: 'https://fonts.gstatic.com/s/e/notoemoji/latest/1f3c6/512.gif' },
    { id: 'anim_party', name: '🎉 Konfeti Kutlama', category: 'animated', preview: '🎉 CANLI', isAnimated: true, dataUrl: 'https://fonts.gstatic.com/s/e/notoemoji/latest/1f389/512.gif' },
    { id: 'anim_eyes', name: '👀 Meraklı Gözler', category: 'animated', preview: '👀 CANLI', isAnimated: true, dataUrl: 'https://fonts.gstatic.com/s/e/notoemoji/latest/1f440/512.gif' },
    { id: 'anim_thinking', name: '🤔 Düşünen Yüz', category: 'animated', preview: '🤔 CANLI', isAnimated: true, dataUrl: 'https://fonts.gstatic.com/s/e/notoemoji/latest/1f914/512.gif' },
    { id: 'anim_scream', name: '😱 Çığlık / Korku', category: 'animated', preview: '😱 CANLI', isAnimated: true, dataUrl: 'https://fonts.gstatic.com/s/e/notoemoji/latest/1f631/512.gif' },
    { id: 'anim_heart_fire', name: '❤️‍🔥 Alevli Kalp', category: 'animated', preview: '❤️‍🔥 CANLI', isAnimated: true, dataUrl: 'https://fonts.gstatic.com/s/e/notoemoji/latest/2764_fe0f_200d_1f525/512.gif' },
    { id: 'anim_thumbsup', name: '👍 Süper / Onay', category: 'animated', preview: '👍 CANLI', isAnimated: true, dataUrl: 'https://fonts.gstatic.com/s/e/notoemoji/latest/1f44d/512.gif' },
    { id: 'anim_warning', name: '⚠️ Dikkat / Uyarı', category: 'animated', preview: '⚠️ CANLI', isAnimated: true, dataUrl: 'https://fonts.gstatic.com/s/e/notoemoji/latest/26a0_fe0f/512.gif' },
    { id: 'anim_alarm', name: '🚨 Polis / Acil Siren', category: 'animated', preview: '🚨 CANLI', isAnimated: true, dataUrl: 'https://fonts.gstatic.com/s/e/notoemoji/latest/1f6a8/512.gif' },
    { id: 'anim_check', name: '✅ Yeşil Onay Tiki', category: 'animated', preview: '✅ CANLI', isAnimated: true, dataUrl: 'https://fonts.gstatic.com/s/e/notoemoji/latest/2705/512.gif' },
    { id: 'anim_cross', name: '❌ Kırmızı Çarpı', category: 'animated', preview: '❌ CANLI', isAnimated: true, dataUrl: 'https://fonts.gstatic.com/s/e/notoemoji/latest/274c/512.gif' },
    { id: 'anim_Sparkles', name: '✨ Sihirli Yıldızlar', category: 'animated', preview: '✨ CANLI', isAnimated: true, dataUrl: 'https://fonts.gstatic.com/s/e/notoemoji/latest/2728/512.gif' },

    // --- SOSYAL MEDYA & CTA ROZETLERİ (8) ---
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
      id: 'stk_follow_ig',
      name: '📸 Takip Et (Gradyan)',
      category: 'social',
      preview: '📸 TAKİP ET',
      dataUrl: this.svgToDataUrl(`<svg xmlns="http://www.w3.org/2000/svg" width="340" height="110" viewBox="0 0 340 110"><defs><linearGradient id="ig" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="#f59e0b"/><stop offset="50%" stop-color="#ec4899"/><stop offset="100%" stop-color="#8b5cf6"/></linearGradient></defs><rect x="12" y="12" width="316" height="82" rx="41" fill="url(#ig)" stroke="#ffffff" stroke-width="5"/><text x="64" y="67" font-size="38">📸</text><text x="195" y="65" font-family="Arial, sans-serif" font-weight="900" font-size="32" fill="#ffffff" text-anchor="middle" letter-spacing="2">TAKİP ET</text></svg>`)
    },
    {
      id: 'stk_comment',
      name: '💬 Yorum Yap Rozeti',
      category: 'social',
      preview: '💬 YORUM YAP',
      dataUrl: this.svgToDataUrl(`<svg xmlns="http://www.w3.org/2000/svg" width="350" height="110" viewBox="0 0 350 110"><rect x="12" y="12" width="326" height="82" rx="41" fill="#10b981" stroke="#ffffff" stroke-width="5"/><text x="62" y="67" font-size="38">💬</text><text x="200" y="65" font-family="Arial, sans-serif" font-weight="900" font-size="30" fill="#ffffff" text-anchor="middle" letter-spacing="1.5">YORUM YAP</text></svg>`)
    },
    {
      id: 'stk_link_bio',
      name: '🔗 Link Açıklamada',
      category: 'social',
      preview: '🔗 LİNK BİO',
      dataUrl: this.svgToDataUrl(`<svg xmlns="http://www.w3.org/2000/svg" width="360" height="110" viewBox="0 0 360 110"><rect x="12" y="12" width="336" height="82" rx="20" fill="#0f172a" stroke="#38bdf8" stroke-width="5"/><text x="58" y="67" font-size="36">🔗</text><text x="202" y="65" font-family="Arial, sans-serif" font-weight="900" font-size="28" fill="#38bdf8" text-anchor="middle" letter-spacing="1.5">LİNK AÇIKLAMADA</text></svg>`)
    },
    {
      id: 'stk_live_badge',
      name: '🔴 CANLI YAYIN Rozeti',
      category: 'badges',
      preview: '🔴 CANLI',
      dataUrl: this.svgToDataUrl(`<svg xmlns="http://www.w3.org/2000/svg" width="260" height="96" viewBox="0 0 260 96"><rect x="8" y="8" width="244" height="80" rx="16" fill="#dc2626" stroke="#ffffff" stroke-width="4"/><circle cx="52" cy="48" r="14" fill="#ffffff"/><text x="150" y="60" font-family="Arial, sans-serif" font-weight="900" font-size="34" fill="#ffffff" text-anchor="middle" letter-spacing="3">CANLI</text></svg>`)
    },
    {
      id: 'stk_new_badge',
      name: '⚡ YENİ / NEW Rozeti',
      category: 'badges',
      preview: '⚡ YENİ',
      dataUrl: this.svgToDataUrl(`<svg xmlns="http://www.w3.org/2000/svg" width="240" height="96" viewBox="0 0 240 96"><rect x="8" y="8" width="224" height="80" rx="40" fill="#facc15" stroke="#000000" stroke-width="6"/><text x="120" y="61" font-family="Arial, sans-serif" font-weight="900" font-size="36" fill="#000000" text-anchor="middle" letter-spacing="3">⚡ YENİ</text></svg>`)
    },
    {
      id: 'stk_vs_badge',
      name: '⚔️ VS Karşılaştırma',
      category: 'badges',
      preview: '⚔️ VS',
      dataUrl: this.svgToDataUrl(`<svg xmlns="http://www.w3.org/2000/svg" width="220" height="220" viewBox="0 0 220 220"><circle cx="110" cy="110" r="92" fill="#0f172a" stroke="#f97316" stroke-width="10"/><text x="110" y="136" font-family="Impact, Arial, sans-serif" font-weight="900" font-size="84" fill="#facc15" text-anchor="middle">VS</text></svg>`)
    },

    // --- OKLAR & İŞARETÇİLER (6) ---
    {
      id: 'stk_arrow_red',
      name: '↘ Kırmızı Vurgu Oku',
      category: 'arrows',
      preview: '↘ VURGU OKU',
      dataUrl: this.svgToDataUrl(`<svg xmlns="http://www.w3.org/2000/svg" width="240" height="240" viewBox="0 0 240 240"><path d="M35 35 L165 165 M165 165 L95 165 M165 165 L165 95" stroke="#ffffff" stroke-width="30" stroke-linecap="round" stroke-linejoin="round" fill="none"/><path d="M35 35 L165 165 M165 165 L95 165 M165 165 L165 95" stroke="#ef4444" stroke-width="20" stroke-linecap="round" stroke-linejoin="round" fill="none"/></svg>`)
    },
    {
      id: 'stk_arrow_curved',
      name: '↪ Kıvrımlı Neon Sarı Ok',
      category: 'arrows',
      preview: '↪ KIVRIMLI OK',
      dataUrl: this.svgToDataUrl(`<svg xmlns="http://www.w3.org/2000/svg" width="260" height="220" viewBox="0 0 260 220"><path d="M30 180 Q 40 40 200 60 M200 60 L155 30 M200 60 L160 100" stroke="#000000" stroke-width="24" stroke-linecap="round" stroke-linejoin="round" fill="none"/><path d="M30 180 Q 40 40 200 60 M200 60 L155 30 M200 60 L160 100" stroke="#facc15" stroke-width="14" stroke-linecap="round" stroke-linejoin="round" fill="none"/></svg>`)
    },
    {
      id: 'stk_circle_callout',
      name: '⭕ El Çizimi Kırmızı Daire',
      category: 'arrows',
      preview: '⭕ DAİRE VURGU',
      dataUrl: this.svgToDataUrl(`<svg xmlns="http://www.w3.org/2000/svg" width="280" height="200" viewBox="0 0 280 200"><ellipse cx="140" cy="100" rx="118" ry="74" fill="none" stroke="#ffffff" stroke-width="16" stroke-dasharray="600 40" stroke-linecap="round" transform="rotate(-6 140 100)"/><ellipse cx="140" cy="100" rx="118" ry="74" fill="none" stroke="#ef4444" stroke-width="10" stroke-dasharray="600 40" stroke-linecap="round" transform="rotate(-6 140 100)"/></svg>`)
    },
    {
      id: 'stk_underline_brush',
      name: '〰️ Fırça Alt Çizgi Vurgusu',
      category: 'arrows',
      preview: '〰️ ALT ÇİZGİ',
      dataUrl: this.svgToDataUrl(`<svg xmlns="http://www.w3.org/2000/svg" width="360" height="90" viewBox="0 0 360 90"><path d="M20 55 Q 180 20 340 50" stroke="#000" stroke-width="22" stroke-linecap="round" fill="none"/><path d="M20 55 Q 180 20 340 50" stroke="#22d3ee" stroke-width="14" stroke-linecap="round" fill="none"/></svg>`)
    },
    {
      id: 'stk_ comic_boom',
      name: '💥 Çizgi Roman BOOM!',
      category: 'effects',
      preview: '💥 BOOM!',
      dataUrl: this.svgToDataUrl(`<svg xmlns="http://www.w3.org/2000/svg" width="320" height="240" viewBox="0 0 320 240"><polygon points="160,10 195,65 265,30 240,95 305,125 240,155 265,215 190,185 160,230 130,185 55,215 80,155 15,125 80,95 55,30 125,65" fill="#ef4444" stroke="#000" stroke-width="8"/><polygon points="160,28 188,75 245,48 225,100 280,125 225,150 245,198 185,172 160,210 135,172 75,198 95,150 40,125 95,100 75,48 132,75" fill="#facc15"/><text x="160" y="142" font-family="Impact, Arial, sans-serif" font-weight="900" font-size="56" fill="#000" text-anchor="middle" transform="rotate(-6 160 125)">BOOM!</text></svg>`)
    },
    {
      id: 'stk_comic_wow',
      name: '⚡ Çizgi Roman WOW!',
      category: 'effects',
      preview: '⚡ WOW!',
      dataUrl: this.svgToDataUrl(`<svg xmlns="http://www.w3.org/2000/svg" width="320" height="240" viewBox="0 0 320 240"><polygon points="160,12 200,70 275,40 245,105 305,140 235,165 255,220 185,190 150,230 120,185 50,210 75,150 15,115 85,90 65,30 130,65" fill="#ec4899" stroke="#000" stroke-width="8"/><text x="160" y="144" font-family="Impact, Arial, sans-serif" font-weight="900" font-size="62" fill="#ffffff" stroke="#000" stroke-width="3" text-anchor="middle" transform="rotate(5 160 125)">WOW!</text></svg>`)
    },

    // --- KLASİK YÜKSEK ÇÖZÜNÜRLÜKLÜ EMOJİ ROZETLERİ (6) ---
    { id: 'stk_fire', name: '🔥 Alev Rozeti', category: 'emoji', preview: '🔥', dataUrl: this.emojiToDataUrl('🔥') },
    { id: 'stk_rocket', name: '🚀 Roket Rozeti', category: 'emoji', preview: '🚀', dataUrl: this.emojiToDataUrl('🚀') },
    { id: 'stk_mindblown', name: '🤯 Şok Rozeti', category: 'emoji', preview: '🤯', dataUrl: this.emojiToDataUrl('🤯') },
    { id: 'stk_money', name: '💰 Para Rozeti', category: 'emoji', preview: '💰', dataUrl: this.emojiToDataUrl('💰') },
    { id: 'stk_idea', name: '💡 Fikir Rozeti', category: 'emoji', preview: '💡', dataUrl: this.emojiToDataUrl('💡') },
    { id: 'stk_crown', name: '👑 Kral Tacı', category: 'badges', preview: '👑', dataUrl: this.emojiToDataUrl('👑') }
  ];

  /**
   * Iconify 200.000+ Açık Kaynak Vektör Sticker & İkon Motoru araması.
   * Türkçe anahtar kelimeleri otomatik İngilizce ikon terimleriyle zenginleştirir.
   */
  async searchIconifyStickers(query: string): Promise<StickerLibraryItem[]> {
    const q = (query || '').trim().toLowerCase();
    if (!q) return [];

    const trMap: Record<string, string> = {
      'ateş': 'fire flame',
      'alev': 'fire flame',
      'ok': 'arrow',
      'kalp': 'heart love',
      'para': 'money cash dollar coin',
      'yıldız': 'star sparkle',
      'roket': 'rocket',
      'kral': 'crown king',
      'taç': 'crown',
      'oyun': 'gamepad gaming',
      'müzik': 'music note audio',
      'kamera': 'camera video',
      'uyarı': 'warning alert',
      'onay': 'check verified',
      'tik': 'check tick',
      'çarpı': 'close cross error',
      'youtube': 'youtube',
      'instagram': 'instagram',
      'tiktok': 'tiktok',
      'abone': 'bell subscribe',
      'zil': 'bell notification',
      'şimşek': 'lightning bolt zap',
      'fikir': 'lightbulb idea',
      'ampul': 'lightbulb',
      'hediye': 'gift present',
      'araba': 'car racing',
      'kupa': 'trophy award',
      'elmas': 'diamond gem',
      'gülümseme': 'smile emoji',
      'korku': 'skull ghost',
      'patlama': 'explosion boom'
    };

    const mappedQuery = trMap[q] || q;
    try {
      const url = `https://api.iconify.design/search?query=${encodeURIComponent(mappedQuery)}&limit=36`;
      const resp = await fetch(url);
      if (!resp.ok) return [];
      const data = await resp.json();
      const icons: string[] = Array.isArray(data?.icons) ? data.icons : [];
      return icons.map((iconFull, idx) => {
        const [prefix, name] = iconFull.split(':');
        const svgUrl = `https://api.iconify.design/${prefix}/${name}.svg?height=256`;
        return {
          id: `iconify_${prefix}_${name}_${idx}`,
          name: `${name.replace(/-/g, ' ')} (${prefix})`,
          category: 'effects',
          preview: name.slice(0, 12).toUpperCase(),
          dataUrl: svgUrl
        };
      });
    } catch (err) {
      console.warn('[ICONIFY-SEARCH] Arama hatası:', err);
      return [];
    }
  }

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

  private audioElementCache = new Map<string, HTMLAudioElement>();

  /**
   * Gerçek Stüdyo Ses Efektini (/assets/sfx/{presetId}.wav veya özel ses URL'si) çalar.
   */
  playSfxPreset(presetId: string, volume = 0.85, customUrl?: string): void {
    try {
      const cleanId = (presetId || 'whoosh-fast').trim();
      const targetUrl =
        customUrl && (customUrl.startsWith('http') || customUrl.startsWith('/assets/') || customUrl.startsWith('/api/'))
          ? customUrl
          : `/assets/sfx/${cleanId}.wav`;

      let baseAudio = this.audioElementCache.get(targetUrl);
      if (!baseAudio) {
        baseAudio = new Audio(targetUrl);
        baseAudio.preload = 'auto';
        this.audioElementCache.set(targetUrl, baseAudio);
      }

      const clone = baseAudio.cloneNode(true) as HTMLAudioElement;
      clone.volume = Math.max(0, Math.min(1.0, volume));
      clone.currentTime = 0;
      clone.play().catch(() => {
        // Yedek WebAudio geri dönüşü
        const ctx = this.getAudioContext();
        const buffer = this.getOrCreateSfxBuffer(ctx, cleanId);
        const source = ctx.createBufferSource();
        source.buffer = buffer;
        const gain = ctx.createGain();
        gain.gain.value = Math.max(0, Math.min(2.0, volume));
        source.connect(gain);
        gain.connect(ctx.destination);
        source.start(0);
      });
    } catch (err) {
      console.warn('[STUDIO-SFX] Ses çalınamadı:', err);
    }
  }

  playSynthesizedSfx(presetId: string, volume = 0.85, customUrl?: string): void {
    this.playSfxPreset(presetId, volume, customUrl);
  }

  generateSfxWavDataUri(presetId: string, _duration?: number): string {
    const cleanId = (presetId || 'whoosh-fast').trim();
    return `/assets/sfx/${cleanId}.wav`;
  }

  /**
   * SFX presetinin gerçek stüdyo WAV dosya yolunu döndürür.
   */
  getSfxDataUrl(presetId: string): string {
    const cleanId = (presetId || 'whoosh-fast').trim();
    return `/assets/sfx/${cleanId}.wav`;
  }

  private getOrCreateSfxBuffer(ctx: AudioContext, presetId: string): AudioBuffer {
    const existing = this.sfxBufferCache.get(presetId);
    if (existing) return existing;

    const sr = ctx.sampleRate || 44100;
    const item = this.sfxLibrary.find(s => s.id === presetId || s.synthPreset === presetId);
    const synthFamily = item?.synthPreset || presetId;
    const duration = item ? item.duration : 0.5;
    const length = Math.max(1024, Math.floor(sr * duration));
    const buffer = ctx.createBuffer(1, length, sr);
    const data = buffer.getChannelData(0);

    // Her presetId için deterministik frekans varyasyonu (aynı ailedeki efektlerin bile kendine has tınısı olması için)
    let hash = 0;
    for (let c = 0; c < presetId.length; c++) {
      hash = ((hash << 5) - hash + presetId.charCodeAt(c)) | 0;
    }
    const pitchMod = 0.85 + ((Math.abs(hash) % 35) / 100);

    for (let i = 0; i < length; i++) {
      const t = i / sr;
      const norm = i / length;

      switch (synthFamily) {
        case 'whoosh-fast':
        case 'swoosh-deep': {
          const env = Math.sin(Math.PI * norm) ** 1.8;
          const baseFreq = (synthFamily === 'whoosh-fast' ? 180 + 900 * Math.sin(Math.PI * norm) : 90 + 420 * Math.sin(Math.PI * norm)) * pitchMod;
          const noise = (Math.random() * 2 - 1) * 0.55;
          const tone = Math.sin(2 * Math.PI * baseFreq * t) * 0.45;
          data[i] = (noise + tone) * env;
          break;
        }
        case 'pop-bubble':
        case 'pop-crisp': {
          const env = Math.exp(-t * 22);
          const fStart = (synthFamily === 'pop-bubble' ? 220 : 380) * pitchMod;
          const fEnd = (synthFamily === 'pop-bubble' ? 880 : 1200) * pitchMod;
          const freq = fStart + (fEnd - fStart) * Math.min(1, t * 14);
          data[i] = Math.sin(2 * Math.PI * freq * t) * env * 0.9;
          break;
        }
        case 'ding-bell':
        case 'cash-register': {
          const env = Math.exp(-t * 4.5);
          const f1 = (synthFamily === 'cash-register' && t > 0.12 ? 2093 : 1318.5) * pitchMod;
          const f2 = f1 * 2.0;
          data[i] = (Math.sin(2 * Math.PI * f1 * t) * 0.65 + Math.sin(2 * Math.PI * f2 * t) * 0.35) * env;
          break;
        }
        case 'sub-bass-drop':
        case 'cinematic-hit': {
          const env = Math.exp(-t * 3.2);
          const freq = (130 * Math.exp(-t * 2.4) + 32) * pitchMod;
          const punch = t < 0.04 ? (Math.random() * 2 - 1) * (1 - t / 0.04) * 0.7 : 0;
          data[i] = (Math.sin(2 * Math.PI * freq * t) * 0.85 + punch) * env;
          break;
        }
        case 'tension-riser': {
          const env = norm ** 2.2 * (norm > 0.92 ? (1 - norm) / 0.08 : 1);
          const freq = (140 + 1200 * (norm ** 2)) * pitchMod;
          const noise = (Math.random() * 2 - 1) * 0.35;
          data[i] = (Math.sin(2 * Math.PI * freq * t) * 0.65 + noise) * env;
          break;
        }
        case 'camera-shutter':
        case 'mouse-click':
        case 'keyboard-typing': {
          const clickPeriod = synthFamily === 'keyboard-typing' ? 0.14 : 0.12;
          const localT = t % clickPeriod;
          const env = Math.exp(-localT * 65);
          data[i] = (Math.random() * 2 - 1) * env * 0.9;
          break;
        }
        case 'digital-glitch':
        case 'record-scratch': {
          const step = Math.floor(t * 45);
          const freq = (180 + ((step * 397) % 1400)) * pitchMod;
          const sq = Math.sin(2 * Math.PI * freq * t) >= 0 ? 0.6 : -0.6;
          data[i] = (sq + (Math.random() * 2 - 1) * 0.3) * (1 - norm * 0.4);
          break;
        }
        case 'success-chime': {
          const notes = [523.25, 659.25, 783.99, 1046.5];
          const idx = Math.min(notes.length - 1, Math.floor(norm * notes.length));
          const env = Math.exp(-(t % 0.2) * 6);
          data[i] = Math.sin(2 * Math.PI * notes[idx] * pitchMod * t) * env * 0.8;
          break;
        }
        default: {
          const env = 1 - norm * 0.5;
          data[i] = (Math.sin(2 * Math.PI * 145 * pitchMod * t) >= 0 ? 0.5 : -0.5) * env;
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
   * Görselin arka planını tarayıcı içinde ~120 milisaniyede temizleyip şeffaf PNG DataURL olarak döndürür.
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
          console.warn('[BG-REMOVE-INSTANT] CORS veya Canvas hatası:', err);
          reject(err);
        }
      };
      img.onerror = (err) => reject(err);
      img.src = imageUrl;
    });
  }

  /**
   * FAZ D: Otonom Kurgu & Zenginleştirme Motoru (AutoDirectorComposer - Frontend 1-Tık)
   * Önceden kesilmiş veya ham bir videoya tek tıkla:
   * - Açılış Viral Hook Başlığı (T2)
   * - Önemli anlara Vurgu Yazıları (T2)
   * - Hareketli Google Noto Emoji Çıkartmaları (T3)
   * - Kesim sınırlarına Sahne Geçişleri (Transitions)
   * - Senkronize Stüdyo Ses Efektleri (SFX)
   * yerleştirir.
   */
  composeAutoDirectorTimeline(edl: EdlContent, totalDur?: number): {
    overlays: OverlayItem[];
    transitions: EdlTransition[];
    sfxClips: EdlSfxClip[];
  } {
    const duration = Math.max(8, totalDur || edl.duration || 60);
    const segments = edl.transcript?.segments || [];
    const cuts = edl.cuts || [];
    const now = Date.now();

    const overlays: OverlayItem[] = [];
    const transitions: EdlTransition[] = [];
    const sfxClips: EdlSfxClip[] = [];

    // 1. Açılış Viral Hook Başlığı (0.3s - 3.5s, T2)
    const firstSeg = segments[0];
    const hookWords = firstSeg?.text
      ? firstSeg.text.trim().split(/\s+/).slice(0, 4).join(' ').toUpperCase()
      : 'DİKKAT! BUNU İZLEYİN 🔥';
    const hookStart = Number(Math.max(0.2, firstSeg ? firstSeg.start : 0.3).toFixed(2));
    const hookDur = Math.min(3.2, Math.max(2.0, duration * 0.15));

    overlays.push({
      id: `ad_hook_${now}`,
      type: 'text',
      content: hookWords,
      timestamp: hookStart,
      duration: Number(hookDur.toFixed(2)),
      trackId: 2,
      positionX: 50,
      positionY: 22,
      scale: 1,
      ...this.textPresets[0].props,
      action: 'add'
    });

    sfxClips.push({
      id: `ad_sfx_hook_${now}`,
      name: 'Pop Baloncuk (Hook)',
      category: 'pop',
      presetId: 'pop-bubble',
      synthPreset: 'pop-bubble',
      start: hookStart,
      duration: 0.25,
      volume: 0.85,
      peaks: [0.2, 0.95, 1.0, 0.6, 0.2],
      action: 'add'
    });

    // 2. Periyodik Vurgu Başlıkları (T2) + Hareketli Emojiler (T3)
    const step = Math.max(12, Math.min(25, duration / 4));
    const animatedEmojis = [
      'https://fonts.gstatic.com/s/e/notoemoji/latest/1f525/512.gif',
      'https://fonts.gstatic.com/s/e/notoemoji/latest/1f4a1/512.gif',
      'https://fonts.gstatic.com/s/e/notoemoji/latest/1f680/512.gif',
      'https://fonts.gstatic.com/s/e/notoemoji/latest/26a1/512.gif',
      'https://fonts.gstatic.com/s/e/notoemoji/latest/1f3af/512.gif',
      'https://fonts.gstatic.com/s/e/notoemoji/latest/1f4af/512.gif'
    ];
    const presetPool = [this.textPresets[1], this.textPresets[2], this.textPresets[3], this.textPresets[7]];
    const fallbackPhrases = ['ÖNEMLİ NOKTA ⚡', 'KRİTİK DETAY 💡', 'SONUÇ MUHTEŞEM 🚀', 'BUNU UNUTMAYIN 🎯'];

    let idx = 0;
    for (let t = Math.max(5.5, step * 0.7); t < duration - 4.0 && idx < 6; t += step) {
      const matchSeg = segments.find(s => Math.abs(s.start - t) < step * 0.45 && s.text.trim().length > 6);
      const phrase = matchSeg
        ? matchSeg.text.trim().split(/\s+/).slice(0, 3).join(' ').toUpperCase()
        : fallbackPhrases[idx % fallbackPhrases.length];
      const stamp = Number((matchSeg ? matchSeg.start : t).toFixed(2));
      const preset = presetPool[idx % presetPool.length];

      overlays.push({
        id: `ad_txt_${now}_${idx}`,
        type: 'text',
        content: phrase,
        timestamp: stamp,
        duration: 2.8,
        trackId: 2,
        positionX: 50,
        positionY: idx % 2 === 0 ? 20 : 78,
        scale: 1,
        ...preset.props,
        action: 'add'
      });

      // Hareketli Emoji Çıkartması (T3)
      overlays.push({
        id: `ad_stk_${now}_${idx}`,
        type: 'image',
        content: 'Hareketli Emoji',
        source: animatedEmojis[idx % animatedEmojis.length],
        timestamp: Number((stamp + 0.15).toFixed(2)),
        duration: 2.6,
        trackId: 3,
        positionX: idx % 2 === 0 ? 82 : 18,
        positionY: 26,
        scale: 0.75,
        animation: 'pop-up',
        exitAnimation: 'scale-out',
        loopAnimation: 'float',
        action: 'add'
      });

      sfxClips.push({
        id: `ad_sfx_hl_${now}_${idx}`,
        name: idx % 2 === 0 ? 'Ding Parlak Çan' : 'Whoosh Hızlı Geçiş',
        category: idx % 2 === 0 ? 'ui' : 'whoosh',
        presetId: idx % 2 === 0 ? 'ding-bell' : 'whoosh-fast',
        synthPreset: idx % 2 === 0 ? 'ding-bell' : 'whoosh-fast',
        start: stamp,
        duration: idx % 2 === 0 ? 0.8 : 0.42,
        volume: 0.75,
        peaks: [0.3, 0.9, 1.0, 0.7, 0.3],
        action: 'add'
      });

      idx++;
    }

    // 3. Kesim Sınırlarına (veya 3 ana noktaya) Sahne Geçişleri
    const transTypes: EdlTransition['type'][] = ['slideleft', 'zoomin', 'fadewhite', 'smoothright', 'circleopen'];
    const validCuts = cuts.filter(c => c.start > 2.5 && c.end < duration - 2.5);
    const maxTrans = Math.min(5, Math.max(1, validCuts.length));
    for (let i = 0; i < maxTrans; i++) {
      const cutItem = validCuts[Math.floor((i * validCuts.length) / maxTrans)];
      const boundary = cutItem ? Number(cutItem.end.toFixed(2)) : Number(((i + 1) * (duration / (maxTrans + 1))).toFixed(2));
      const tType = transTypes[i % transTypes.length];
      transitions.push({
        id: `ad_tr_${now}_${i}`,
        boundarySourceTime: boundary,
        boundaryTime: boundary,
        type: tType,
        duration: 0.4,
        autoSfxId: 'whoosh-fast',
        action: 'add'
      });
    }

    return { overlays, transitions, sfxClips };
  }

  /**
   * FAZ 6: Otonom Video Yönetmeni (Proaktif AI Kurgu Önerileri Üretici)
   */
  generateProactiveSuggestions(edl: EdlContent, totalDur?: number): SuggestionItem[] {
    const duration = totalDur || edl.duration || 60;
    const segments = edl.transcript?.segments || [];
    const cuts = edl.cuts || [];
    const suggestions: SuggestionItem[] = [];

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

    const ctaTime = Number(Math.max(4, duration * 0.72).toFixed(1));
    suggestions.push({
      id: `sug_sticker_${Date.now()}_4`,
      type: 'sticker_callout',
      category: '🎯 Etkileşim & Sticker',
      title: '🔥 Hareketli Alev Emoji + Pop SFX',
      content: 'anim_fire',
      sourceUrl: this.stickerLibrary[0].dataUrl,
      timestamp: ctaTime,
      duration: 4.0,
      confidence: 89,
      sfxPreset: 'pop-crisp',
      reason: 'Videonun son çeyreğinde izleyici etkileşimini artırmak için hareketli Noto Emoji çıkartması ekler.',
      status: 'pending'
    });

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
