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
  category?: 'trend' | 'social' | 'news' | 'cinematic' | 'gaming' | 'vlog' | 'academic';
  sampleText?: string;
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
  sourceUrl?: string;
  creator?: string;
  license?: string;
  isOnline?: boolean;
}

export interface StickerLibraryItem {
  id: string;
  name: string;
  category: 'animated' | 'fluent3d' | 'social' | 'arrows' | 'emoji' | 'badges' | 'effects' | 'giphy';
  preview: string;
  dataUrl: string;
  dataUri?: string;
  isAnimated?: boolean;
  tags?: string[];
}

export interface TransitionLibraryItem {
  type: EdlTransition['type'];
  name: string;
  category: 'Trend' | 'Temel' | 'Kamera / Whip' | 'Işık / Flaş' | 'Bulanıklık' | 'Dijital & Maske' | 'Perde & Bölme' | '3D & Shader' | 'Sinematik & Özel';
  icon: string;
  defaultDuration: number;
  recommendedSfx: string;
  description?: string;
}

export interface OnlineStockImageItem {
  id: string;
  title: string;
  thumb: string;
  url: string;
  source: string;
  creator?: string;
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
    { name: 'Wallpoet (Stencil Cyber)', family: 'Wallpoet', category: 'Siber & Kod' },
    { name: 'Rubik Glitch (Bozuk Siber)', family: 'Rubik Glitch', category: 'Siber & Kod' },
    { name: 'Rubik Wet Paint (Sprey)', family: 'Rubik Wet Paint', category: 'Viral & Başlık' },
    { name: 'Bungee Shade (3D Gölgeli)', family: 'Bungee Shade', category: 'Viral & Başlık' },
    { name: 'Rampart One (3D Blok)', family: 'Rampart One', category: 'Viral & Başlık' },
    { name: 'Monoton (Neon Çizgi)', family: 'Monoton', category: 'Siber & Kod' },
    { name: 'Creepster (Korku / Cadılar Bayramı)', family: 'Creepster', category: 'Viral & Başlık' },
    { name: 'Nosifer (Damla Korku)', family: 'Nosifer', category: 'Viral & Başlık' },
    { name: 'Special Elite (Eski Daktilo)', family: 'Special Elite', category: 'Siber & Kod' },
    { name: 'Courier Prime (Senaryo)', family: 'Courier Prime', category: 'Siber & Kod' },
    { name: 'IBM Plex Mono', family: 'IBM Plex Mono', category: 'Siber & Kod' },
    { name: 'Bricolage Grotesque', family: 'Bricolage Grotesque', category: 'Modern Sans' },
    { name: 'Archivo', family: 'Archivo', category: 'Modern Sans' },
    { name: 'Unbounded (Geniş Fütüristik)', family: 'Unbounded', category: 'Viral & Başlık' },
    { name: 'Dela Gothic One (Ultra Kalın)', family: 'Dela Gothic One', category: 'Viral & Başlık' },
    { name: 'Climate Crisis', family: 'Climate Crisis', category: 'Viral & Başlık' },
    { name: 'Instrument Serif', family: 'Instrument Serif', category: 'Sinematik & Serif' },
    { name: 'Young Serif', family: 'Young Serif', category: 'Sinematik & Serif' },
    { name: 'Noto Serif Display', family: 'Noto Serif Display', category: 'Sinematik & Serif' },
    { name: 'Fredoka (Yuvarlak Pop)', family: 'Fredoka', category: 'Modern Sans' },
    { name: 'Comfortaa', family: 'Comfortaa', category: 'Modern Sans' }
  ];

  /**
   * Seçilen Google Font'u tarayıcıda ilk kez kullanıldığında dinamik olarak <link> ile yükler.
   * Türkçe (latin-ext) karakter setini eksiksiz içerir.
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
    link.href = `https://fonts.googleapis.com/css2?family=${encoded}:ital,wght@0,400;0,700;0,900;1,400;1,700&subset=latin,latin-ext&display=swap`;
    document.head.appendChild(link);
  }

  /**
   * Google Fonts üzerindeki 1.600+ yazı tipinden herhangi birini canlı olarak kütüphaneye ekler ve yükler.
   */
  addCustomGoogleFont(familyName: string, category: StudioFontOption['category'] = 'Modern Sans'): StudioFontOption | null {
    const clean = (familyName || '').trim();
    if (!clean) return null;
    this.ensureFontLoaded(clean);
    const existing = this.fonts.find(f => f.family.toLowerCase() === clean.toLowerCase());
    if (existing) return existing;
    const newFont: StudioFontOption = {
      name: `${clean} (Google Fonts)`,
      family: clean,
      category
    };
    this.fonts.unshift(newFont);
    return newFont;
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
    },
    // --- YENİ CAPCUT TREND ŞABLONLARI (Görsel 2'deki CapCut Metin Şablonları) ---
    {
      id: 'capcut_subscribe_btn',
      name: '🔔 SUBSCRIBE / ABONE OL',
      badge: '🔴 Sosyal',
      category: 'social',
      sampleText: '🔔 ABONE OL',
      previewBg: 'linear-gradient(135deg, #450a0a, #090d16)',
      previewStyle: 'font-family: Montserrat; font-weight: 900; color: #FFF; background: #DC2626; padding: 3px 12px; border-radius: 999px; box-shadow: 0 4px 12px rgba(220,38,38,0.6);',
      props: {
        font: 'Montserrat',
        fontSize: 48,
        fontWeight: 900,
        color: '#FFFFFF',
        fillType: 'solid',
        strokeWidth: 0,
        boxStyle: 'pill',
        boxBgColor: '#DC2626',
        boxPadding: 18,
        allCaps: true,
        letterSpacing: 2,
        animation: 'pop-up',
        exitAnimation: 'scale-out',
        loopAnimation: 'pulse'
      }
    },
    {
      id: 'capcut_chapter_end',
      name: '🎬 Chapter End / Bölüm Sonu',
      badge: '🎬 Sinematik',
      category: 'cinematic',
      sampleText: 'BÖLÜM SONU',
      previewBg: 'linear-gradient(135deg, #090d16, #1e293b)',
      previewStyle: 'font-family: "Playfair Display"; font-style: italic; font-weight: 900; color: #F8FAFC; -webkit-text-stroke: 1.5px #000; text-shadow: 0 4px 10px #000;',
      props: {
        font: 'Playfair Display',
        fontSize: 58,
        italic: true,
        color: '#F8FAFC',
        fillType: 'solid',
        strokeColor: '#000000',
        strokeWidth: 4,
        shadowColor: '#000000',
        shadowDistance: 6,
        shadowBlur: 8,
        boxStyle: 'none',
        allCaps: false,
        letterSpacing: 2,
        animation: 'blur-in',
        exitAnimation: 'fade'
      }
    },
    {
      id: 'capcut_live_breaking_news',
      name: '📺 LIVE BREAKING NEWS',
      badge: '📺 Haber',
      category: 'news',
      sampleText: '🔴 SON DAKİKA HABER',
      previewBg: 'linear-gradient(135deg, #1e3a8a, #450a0a)',
      previewStyle: 'font-family: Oswald; font-weight: 800; color: #FFF; background: #1D4ED8; border: 2px solid #EF4444; padding: 2px 10px; border-radius: 4px;',
      props: {
        font: 'Oswald',
        fontSize: 48,
        color: '#FFFFFF',
        fillType: 'solid',
        strokeColor: '#EF4444',
        strokeWidth: 2,
        boxStyle: 'badge',
        boxBgColor: '#1E3A8A',
        boxPadding: 16,
        borderRadius: 8,
        allCaps: true,
        letterSpacing: 2,
        animation: 'slide-right',
        exitAnimation: 'slide-left'
      }
    },
    {
      id: 'capcut_cloud_3d',
      name: '☁️ CLOUD Kabartma Glow',
      badge: '☁️ Trend',
      category: 'trend',
      sampleText: 'CLOUD',
      previewBg: 'linear-gradient(135deg, #0f172a, #1e1b4b)',
      previewStyle: 'font-family: "Titan One"; color: #090d16; -webkit-text-stroke: 2px #FFF; filter: drop-shadow(0 0 8px #FFF);',
      props: {
        font: 'Titan One',
        fontSize: 64,
        color: '#0F172A',
        fillType: 'solid',
        strokeColor: '#FFFFFF',
        strokeWidth: 6,
        glowEnabled: true,
        glowColor: '#FFFFFF',
        glowRadius: 18,
        boxStyle: 'none',
        allCaps: true,
        letterSpacing: 3,
        animation: 'bounce',
        loopAnimation: 'float'
      }
    },
    {
      id: 'capcut_angel_metallic',
      name: '🪽 ANGEL Gümüş Gotik',
      badge: '🪽 Estetik',
      category: 'cinematic',
      sampleText: 'ANGEL',
      previewBg: 'linear-gradient(135deg, #18181b, #09090b)',
      previewStyle: 'font-family: Cinzel; font-weight: 900; color: #E2E8F0; text-shadow: 0 0 12px rgba(255,255,255,0.7);',
      props: {
        font: 'Cinzel',
        fontSize: 62,
        color: '#F8FAFC',
        fillType: 'gradient',
        gradientStart: '#FFFFFF',
        gradientEnd: '#64748B',
        gradientAngle: 180,
        strokeColor: '#090D16',
        strokeWidth: 3,
        glowEnabled: true,
        glowColor: '#CBD5E1',
        glowRadius: 14,
        boxStyle: 'none',
        allCaps: true,
        letterSpacing: 5,
        animation: 'blur-in',
        exitAnimation: 'fade'
      }
    },
    {
      id: 'capcut_location_pin',
      name: '📍 LOCATION Konum Kartı',
      badge: '📍 Konum',
      category: 'vlog',
      sampleText: '📍 İSTANBUL, TÜRKİYE',
      previewBg: 'linear-gradient(135deg, #090d16, #1e293b)',
      previewStyle: 'font-family: Montserrat; font-weight: 800; color: #FFF; border-left: 3px solid #EF4444; padding-left: 8px;',
      props: {
        font: 'Montserrat',
        fontSize: 44,
        fontWeight: 900,
        color: '#FFFFFF',
        fillType: 'solid',
        strokeColor: '#000000',
        strokeWidth: 3,
        boxStyle: 'rounded',
        boxBgColor: 'rgba(15, 23, 42, 0.85)',
        boxPadding: 14,
        borderRadius: 10,
        allCaps: true,
        letterSpacing: 2,
        animation: 'slide-up',
        exitAnimation: 'fade'
      }
    },
    {
      id: 'capcut_like_follow_share',
      name: '❤️ LIKE • + FOLLOW • ↗ SHARE',
      badge: '📱 TikTok',
      category: 'social',
      sampleText: '❤️ BEĞEN • + TAKİP ET',
      previewBg: 'linear-gradient(135deg, #090d16, #31102f)',
      previewStyle: 'font-family: Outfit; font-weight: 800; color: #FFF; background: #000; border: 1.5px solid #22D3EE; text-shadow: 1px 1px 0 #EC4899; padding: 2px 10px; border-radius: 999px;',
      props: {
        font: 'Outfit',
        fontSize: 44,
        color: '#FFFFFF',
        fillType: 'solid',
        strokeColor: '#EC4899',
        strokeWidth: 2,
        outerStrokeColor: '#22D3EE',
        outerStrokeWidth: 2,
        boxStyle: 'pill',
        boxBgColor: 'rgba(0, 0, 0, 0.90)',
        boxPadding: 16,
        allCaps: true,
        letterSpacing: 2,
        animation: 'pop-up',
        loopAnimation: 'pulse'
      }
    },
    {
      id: 'capcut_whatsapp_call',
      name: '📞 CALL NOW / İletişim Rozeti',
      badge: '📞 Çağrı',
      category: 'social',
      sampleText: '📞 HEMEN ARA',
      previewBg: 'linear-gradient(135deg, #064e3b, #090d16)',
      previewStyle: 'font-family: Poppins; font-weight: 800; color: #FFF; background: #16A34A; padding: 3px 12px; border-radius: 999px;',
      props: {
        font: 'Poppins',
        fontSize: 46,
        color: '#FFFFFF',
        fillType: 'solid',
        strokeWidth: 0,
        boxStyle: 'pill',
        boxBgColor: '#16A34A',
        boxPadding: 18,
        allCaps: true,
        letterSpacing: 1,
        animation: 'bounce',
        loopAnimation: 'wiggle'
      }
    },
    {
      id: 'capcut_live_stream_moments',
      name: '🎮 Live Stream Best Moments',
      badge: '🎮 Yayın',
      category: 'gaming',
      sampleText: 'EN İYİ ANLAR',
      previewBg: 'linear-gradient(135deg, #1e293b, #090d16)',
      previewStyle: 'font-family: "Chakra Petch"; font-weight: 800; color: #090d16; background: #FFF; border: 2px solid #F59E0B; padding: 2px 8px;',
      props: {
        font: 'Chakra Petch',
        fontSize: 48,
        color: '#0F172A',
        fillType: 'solid',
        strokeColor: '#F59E0B',
        strokeWidth: 2,
        boxStyle: 'badge',
        boxBgColor: '#FFFFFF',
        boxPadding: 14,
        borderRadius: 6,
        allCaps: true,
        letterSpacing: 1,
        animation: 'zoom-crash',
        exitAnimation: 'fade'
      }
    },
    {
      id: 'capcut_thanks_watching',
      name: '✨ Thanks For Watching',
      badge: '✨ Kapanış',
      category: 'vlog',
      sampleText: 'İZLEDİĞİNİZ İÇİN TEŞEKKÜRLER',
      previewBg: 'linear-gradient(135deg, #1e1b4b, #090d16)',
      previewStyle: 'font-family: "Luckiest Guy"; color: #BAE6FD; -webkit-text-stroke: 2px #1E3A8A;',
      props: {
        font: 'Luckiest Guy',
        fontSize: 56,
        color: '#BAE6FD',
        fillType: 'gradient',
        gradientStart: '#FFFFFF',
        gradientEnd: '#38BDF8',
        gradientAngle: 180,
        strokeColor: '#1E3A8A',
        strokeWidth: 6,
        boxStyle: 'none',
        allCaps: true,
        letterSpacing: 2,
        animation: 'bounce',
        loopAnimation: 'float'
      }
    },
    {
      id: 'capcut_today_story',
      name: '🌈 TODAY STORY Renkli Pop',
      badge: '🌈 Hikaye',
      category: 'vlog',
      sampleText: 'GÜNÜN HİKAYESİ',
      previewBg: 'linear-gradient(135deg, #3b0764, #0f172a)',
      previewStyle: 'font-family: Fredoka; font-weight: 900; color: #F43F5E; -webkit-text-stroke: 1.5px #FFF; text-shadow: 2px 2px 0 #38BDF8;',
      props: {
        font: 'Fredoka',
        fontSize: 56,
        color: '#F43F5E',
        fillType: 'gradient',
        gradientStart: '#FACC15',
        gradientEnd: '#EC4899',
        gradientAngle: 90,
        strokeColor: '#FFFFFF',
        strokeWidth: 5,
        outerStrokeColor: '#0F172A',
        outerStrokeWidth: 4,
        boxStyle: 'none',
        allCaps: true,
        animation: 'pop-up',
        loopAnimation: 'wiggle'
      }
    },
    {
      id: 'capcut_academic_concept',
      name: '⚖️ Akademik / Belgesel Kartı',
      badge: '⚖️ Akademik',
      category: 'academic',
      sampleText: 'TEKVİNÎ ŞERİAT',
      previewBg: 'linear-gradient(135deg, #0f172a, #020617)',
      previewStyle: 'font-family: Montserrat; font-weight: 800; color: #F8FAFC; background: rgba(15,23,42,0.92); border: 1px solid #38BDF8; padding: 3px 10px; border-radius: 8px;',
      props: {
        font: 'Montserrat',
        fontSize: 56,
        fontWeight: 800,
        color: '#F8FAFC',
        fillType: 'solid',
        strokeColor: '#020617',
        strokeWidth: 3,
        boxStyle: 'rounded',
        boxBgColor: '#0F172A',
        boxPadding: 16,
        borderRadius: 12,
        allCaps: true,
        letterSpacing: 1,
        animation: 'slide-up',
        exitAnimation: 'fade'
      }
    },
    {
      id: 'capcut_enjoy_life_serif',
      name: '🌿 Enjoy Your Life Minimal',
      badge: '🌿 Minimal',
      category: 'cinematic',
      sampleText: 'Hayatın Ritmini Yakala.',
      previewBg: 'linear-gradient(135deg, #1c1917, #090d16)',
      previewStyle: 'font-family: "Cormorant Garamond"; font-weight: 700; color: #F5F5F4; letter-spacing: 1px;',
      props: {
        font: 'Cormorant Garamond',
        fontSize: 54,
        color: '#F5F5F4',
        fillType: 'solid',
        strokeColor: '#000000',
        strokeWidth: 2,
        shadowColor: '#000000',
        shadowDistance: 4,
        shadowBlur: 6,
        boxStyle: 'none',
        allCaps: false,
        letterSpacing: 2,
        animation: 'fade',
        exitAnimation: 'fade'
      }
    },
    {
      id: 'capcut_ultimas_noticias',
      name: '📰 Manşet Çerçeve Kutu',
      badge: '📰 Manşet',
      category: 'news',
      sampleText: 'ÖZEL DOSYA',
      previewBg: 'linear-gradient(135deg, #0c4a6e, #090d16)',
      previewStyle: 'font-family: "Archivo Black"; color: #FFF; background: #0284C7; padding: 3px 10px; border-left: 4px solid #FACC15;',
      props: {
        font: 'Archivo Black',
        fontSize: 50,
        color: '#FFFFFF',
        fillType: 'solid',
        strokeColor: '#0F172A',
        strokeWidth: 3,
        boxStyle: 'rounded',
        boxBgColor: '#0369A1',
        boxPadding: 16,
        borderRadius: 8,
        allCaps: true,
        letterSpacing: 1,
        animation: 'slide-left',
        exitAnimation: 'fade'
      }
    },
    {
      id: 'capcut_glitch_horror',
      name: '👻 Korku / Glitch Başlık',
      badge: '👻 Korku',
      category: 'gaming',
      sampleText: 'KARANLIK SIR',
      previewBg: 'linear-gradient(135deg, #3f000b, #090d16)',
      previewStyle: 'font-family: Creepster; color: #EF4444; text-shadow: 0 0 10px #7F1D1D;',
      props: {
        font: 'Creepster',
        fontSize: 64,
        color: '#EF4444',
        fillType: 'solid',
        strokeColor: '#000000',
        strokeWidth: 5,
        glowEnabled: true,
        glowColor: '#DC2626',
        glowRadius: 16,
        boxStyle: 'none',
        allCaps: true,
        letterSpacing: 3,
        animation: 'glitch',
        loopAnimation: 'shake'
      }
    }
  ];

  // 3. 76 KATEGORİZE STÜDYO SES EFEKTİ (SFX) KÜTÜPHANESİ (WEB AUDIO API SENTEZLEYİCİ İLE %100 ÇEVRİMDIŞI & 0ms GECİKME)
  readonly sfxLibrary: SfxLibraryItem[] = [
    // --- WHOOSH / GEÇİŞ (14) ---
    { id: 'whoosh-fast', name: 'Swish Whoosh (Large 794558)', category: 'whoosh', icon: '💨', duration: 0.81, synthPreset: 'capcut-swish-large', description: 'Orijinal CapCut Swish Whoosh (Large 794558) kaydırmalı geçiş sesi', peaks: [0.28, 0.94, 0.88, 0.43, 0.45, 0.12, 0.04, 0.01] },
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

    // --- UI / BİLDİRİM & TEKNOLOJİ (18) ---
    { id: 'ding-bright', name: 'Ding Parlak Çan (Tın)', category: 'ui', icon: '🔔', duration: 0.90, synthPreset: 'ding-bright', description: 'Kişi ve eser tanıtım kartları için kristal tın sesi', peaks: [1.0, 0.9, 0.75, 0.6, 0.45, 0.3, 0.2, 0.1, 0.05] },
    { id: 'ding-bell', name: 'Ding Parlak Çan', category: 'ui', icon: '🔔', duration: 0.90, synthPreset: 'ding-bell', description: 'Önemli fikir, ipucu veya doğru cevap çanı', peaks: [1.0, 0.9, 0.75, 0.6, 0.45, 0.3, 0.2, 0.1, 0.05] },
    { id: 'cash-register', name: 'Kasa / Para Sesi (Ka-Ching)', category: 'ui', icon: '💰', duration: 0.80, synthPreset: 'cash-register', description: 'Fiyat, kazanç ve finans vurguları için kasa çanı', peaks: [0.9, 0.4, 1.0, 0.85, 0.6, 0.4, 0.2, 0.1] },
    { id: 'camera-shutter', name: 'Kamera Deklanşör (Shutter)', category: 'ui', icon: '📸', duration: 0.35, synthPreset: 'camera-shutter', description: 'Fotoğraf/ekran görüntüsü ve dondurulmuş kare efekti', peaks: [0.95, 0.3, 0.85, 0.2, 0.05] },
    { id: 'keyboard-type', name: 'Mekanik Klavye (Sıralama)', category: 'ui', icon: '⌨️', duration: 0.45, synthPreset: 'keyboard-type', description: 'Alt alta sıralanan liste maddeleri için daktilo/klavye sesi', peaks: [0.85, 0.2, 0.95, 0.15, 0.80, 0.2, 0.90, 0.1] },
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
    { id: 'anime-wow', name: 'Parlak Anime Şaşkınlık', category: 'funny', icon: '🤩', duration: 0.85, synthPreset: 'success-chime', description: 'Etkileyici ve parlak anlar için ışıltılı akor', peaks: [0.8, 1.0, 0.9, 0.7, 0.4, 0.15] },

    // --- CAPCUT REVAÇTA, ASMR, MAKİNELER & ISLIK (24 YENİ SES EFEKTİ — Görsel 1) ---
    { id: 'capcut-swish-large', name: 'Swish Whoosh (Large 794558)', category: 'whoosh', icon: '🌪️', duration: 0.81, synthPreset: 'capcut-swish-large', description: 'Orijinal CapCut Swish Whoosh (Large 794558) eğitim ve kaydırmalı sahne geçişi', peaks: [0.28, 0.94, 0.88, 0.43, 0.45, 0.12, 0.04, 0.01] },
    { id: 'canon-50d-shutter', name: 'Canon 50D DSLR Shutter Click', category: 'ui', icon: '📷', duration: 0.40, synthPreset: 'camera-shutter', description: 'CapCut Revaçta: Gerçekçi DSLR ayna ve deklanşör sesi', peaks: [0.95, 0.25, 1.0, 0.35, 0.1] },
    { id: 'stinger-camera-shut', name: 'Stinger Camera Shutter Flash', category: 'ui', icon: '📸', duration: 0.50, synthPreset: 'camera-shutter', description: 'CapCut Revaçta: Flaş dolumlu keskin fotoğraf çekim sesi', peaks: [1.0, 0.6, 0.9, 0.5, 0.2] },
    { id: 'click-small-button', name: 'Click (Small Button Sound)', category: 'ui', icon: '🔘', duration: 0.18, synthPreset: 'mouse-click', description: 'CapCut Revaçta: Küçük mekanik buton tıklama sesi', peaks: [1.0, 0.3, 0.8, 0.1] },
    { id: 'realistic-keyboard-rapid', name: 'Realistic Keyboard Typing (Rapid)', category: 'ui', icon: '⌨️', duration: 1.10, synthPreset: 'keyboard-typing', description: 'CapCut Revaçta: Hızlı mekanik klavye yazım serisi', peaks: [0.9, 0.2, 0.85, 0.15, 0.95, 0.2, 0.8, 0.1, 0.9, 0.25, 0.85] },
    { id: 'whistle-wolf-up', name: 'Hayranlık Islığı (Whistle)', category: 'funny', icon: '😗', duration: 0.85, synthPreset: 'tension-riser', description: 'Islık Sesleri: Şaşkınlık ve beğeni ıslığı', peaks: [0.3, 0.8, 0.95, 0.4, 0.9, 1.0, 0.5] },
    { id: 'whistle-referee', name: 'Hakem Düdüğü (Faul / Dur)', category: 'funny', icon: '⚽', duration: 0.55, synthPreset: 'ding-bright', description: 'Islık Sesleri: Keskin hakem uyarı düdüğü', peaks: [0.95, 1.0, 0.95, 0.9, 0.3] },
    { id: 'asmr-page-whisper', name: 'ASMR Kitap Sayfası Hışırtısı', category: 'foley', icon: '📖', duration: 0.65, synthPreset: 'whoosh-fast', description: 'ASMR & Foley: Yakın mikrofon kağıt ve sayfa dokusu', peaks: [0.2, 0.5, 0.75, 0.6, 0.3, 0.1] },
    { id: 'asmr-mechanical-switch', name: 'ASMR Blue Switch Tuş Sesi', category: 'foley', icon: '🎛️', duration: 0.32, synthPreset: 'keyboard-type', description: 'ASMR & Foley: Tok mekanik switch tıklaması', peaks: [0.95, 0.2, 0.85, 0.1] },
    { id: 'asmr-coffee-pour', name: 'ASMR Sıcak Kahve & Buz', category: 'ambience', icon: '☕', duration: 1.20, synthPreset: 'pop-bubble', description: 'Vlog & ASMR: Rahatlatıcı içecek doldurma dokusu', peaks: [0.3, 0.6, 0.5, 0.7, 0.6, 0.4, 0.2] },
    { id: 'machine-film-projector', name: 'Eski 8mm Film Projektörü', category: 'foley', icon: '📽️', duration: 1.10, synthPreset: 'keyboard-typing', description: 'Makineler: Nostaljik sinema makarası dönüş sesi', peaks: [0.6, 0.3, 0.65, 0.3, 0.6, 0.3, 0.65, 0.3] },
    { id: 'machine-vhs-insert', name: 'VHS Kaset Takma & Sarma', category: 'foley', icon: '📼', duration: 0.85, synthPreset: 'camera-shutter', description: 'Makineler: Retro kaset mekanizması sesi', peaks: [0.8, 0.4, 0.95, 0.6, 0.3] },
    { id: 'machine-printer-matrix', name: 'Adli Daktilo / Matris Yazıcı', category: 'foley', icon: '🖨️', duration: 0.90, synthPreset: 'keyboard-typing', description: 'Makineler: Belge ve kanun maddesi yazdırma sesi', peaks: [0.85, 0.4, 0.9, 0.35, 0.85, 0.4, 0.9] },
    { id: 'gavel-court-hammer', name: 'Mahkeme Hakim Tokmağı (Gavel)', category: 'impact', icon: '⚖️', duration: 0.65, synthPreset: 'cinematic-hit', description: 'Hukuk & Belgesel: Tok ahşap mahkeme karar tokmağı', peaks: [1.0, 0.3, 0.95, 0.4, 0.15] },
    { id: 'stamp-seal-thud', name: 'Resmi Mühür Basma (Stamp)', category: 'impact', icon: '🔏', duration: 0.42, synthPreset: 'cinematic-hit', description: 'Belgesel & Kanun: Kağıda sert mühür vurma sesi', peaks: [0.95, 0.8, 0.3, 0.05] },
    { id: 'sword-unsheathe', name: 'Tarihi Kılıç Çekme (Metal)', category: 'cinematic', icon: '🗡️', duration: 0.75, synthPreset: 'ding-bright', description: 'Tarih & Destan: Keskin metalik kılıç sıyırma tınısı', peaks: [0.4, 0.9, 1.0, 0.75, 0.4, 0.15] },
    { id: 'deep-gong-oriental', name: 'Tarihi Kubbe / Gong Rezonansı', category: 'cinematic', icon: '🕌', duration: 1.65, synthPreset: 'sub-bass-drop', description: 'Derin ve mistik bölüm başlangıcı rezonansı', peaks: [1.0, 0.95, 0.85, 0.72, 0.58, 0.42, 0.25, 0.1] },
    { id: 'game-level-complete', name: 'Oyun Görev Tamamlandı', category: 'musical', icon: '🎮', duration: 0.95, synthPreset: 'success-chime', description: 'Oyun: Parlak zafer ve görev başarısı fanfarı', peaks: [0.7, 0.85, 0.95, 1.0, 0.9, 0.6, 0.2] },
    { id: 'game-hit-damage', name: 'Oyun Hasar / Can Kaybı (Oof)', category: 'funny', icon: '💔', duration: 0.38, synthPreset: 'error-buzzer', description: 'Oyun: Hızlı darbe ve puan kaybı efekti', peaks: [1.0, 0.75, 0.35, 0.1] },
    { id: 'variety-spring-pop', name: 'Çeşitlilik Şovu Komik Vurgu', category: 'funny', icon: '🎪', duration: 0.50, synthPreset: 'pop-bubble', description: 'Çeşitlilik Şovu: TV şovu tarzı neşeli balon vurgusu', peaks: [0.4, 1.0, 0.8, 0.5, 0.2] }
  ];

  // 4. 45 FFMPEG XFADE VİDEO VE SAHNE GEÇİŞ EFEKTİ (8 KATEGORİ, %100 RENDER MOTORU UYUMLU)
  readonly transitionLibrary: TransitionLibraryItem[] = [
    // --- Temel (8) ---
    { type: 'fade', name: 'Yumuşak Geçiş (Dissolve)', category: 'Temel', icon: '🌫️', defaultDuration: 0.5, recommendedSfx: 'whoosh-air' },
    { type: 'fadeblack', name: 'Siyaha Kararma (Dip to Black)', category: 'Temel', icon: '⬛', defaultDuration: 0.6, recommendedSfx: 'swoosh-deep' },
    { type: 'fadegrays', name: 'Griye Geçiş (Monochrome)', category: 'Temel', icon: '🩶', defaultDuration: 0.55, recommendedSfx: 'whoosh-air' },
    { type: 'dissolve', name: 'Kumlanma Çözülme (Dissolve)', category: 'Temel', icon: '✨', defaultDuration: 0.5, recommendedSfx: 'whoosh-sparkle' },
    { type: 'distance', name: 'Derinlik / Renk Mesafesi', category: 'Temel', icon: '🌌', defaultDuration: 0.5, recommendedSfx: 'swoosh-deep' },
    { type: 'hblur', name: 'Yatay Hareket Bulanıklığı (Motion Blur)', category: 'Temel', icon: '💨', defaultDuration: 0.4, recommendedSfx: 'capcut-swish-large' },
    { type: 'wipeleft', name: 'Sola Perde Silme (Wipe Left)', category: 'Temel', icon: '◧', defaultDuration: 0.45, recommendedSfx: 'capcut-swish-large' },
    { type: 'wiperight', name: 'Sağa Perde Silme (Wipe Right)', category: 'Temel', icon: '◨', defaultDuration: 0.45, recommendedSfx: 'capcut-swish-large' },

    // --- Kamera / Whip (12) ---
    { type: 'slideleft', name: 'Hızlı Sola Kayma (Whip Left)', category: 'Kamera / Whip', icon: '⏪', defaultDuration: 0.35, recommendedSfx: 'capcut-swish-large' },
    { type: 'slideright', name: 'Hızlı Sağa Kayma (Whip Right)', category: 'Kamera / Whip', icon: '⏩', defaultDuration: 0.35, recommendedSfx: 'capcut-swish-large' },
    { type: 'slideup', name: 'Yukarı Savrulma (Whip Up)', category: 'Kamera / Whip', icon: '⏫', defaultDuration: 0.4, recommendedSfx: 'capcut-swish-large' },
    { type: 'slidedown', name: 'Aşağı Savrulma (Whip Down)', category: 'Kamera / Whip', icon: '⏬', defaultDuration: 0.4, recommendedSfx: 'capcut-swish-large' },
    { type: 'smoothleft', name: 'Elastik Sola Kayma (Smooth Left)', category: 'Kamera / Whip', icon: '⬅️', defaultDuration: 0.45, recommendedSfx: 'capcut-swish-large' },
    { type: 'smoothright', name: 'Elastik Sağa Kayma (Smooth Right)', category: 'Kamera / Whip', icon: '➡️', defaultDuration: 0.45, recommendedSfx: 'capcut-swish-large' },
    { type: 'smoothup', name: 'Elastik Yukarı (Smooth Up)', category: 'Kamera / Whip', icon: '⬆️', defaultDuration: 0.45, recommendedSfx: 'capcut-swish-large' },
    { type: 'smoothdown', name: 'Elastik Aşağı (Smooth Down)', category: 'Kamera / Whip', icon: '⬇️', defaultDuration: 0.45, recommendedSfx: 'capcut-swish-large' },
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
    { type: 'coverleft', name: 'Üzerini Örterek Kayma (Cover)', category: 'Perde & Bölme', icon: '🃏', defaultDuration: 0.4, recommendedSfx: 'pop-card-flip' },

    // --- CAPCUT TREND & GL-TRANSITIONS SHADER GEÇİŞLERİ (22 YENİ — Görsel 3 & 4) ---
    { type: 'smoothleft', name: 'Sol Kaydırma (CapCut Sol / Swish Whoosh 794558)', category: 'Trend', icon: '⬅️', defaultDuration: 0.45, recommendedSfx: 'capcut-swish-large', description: 'Konu bitimi ve açıklama öncesi standart sola kaydırmalı geçiş (Swish Whoosh Large 794558)' },
    { type: 'diagbl', name: 'Sol Alt Kayma (CapCut Sol Alt)', category: 'Trend', icon: '↙️', defaultDuration: 0.45, recommendedSfx: 'capcut-swish-large', description: 'Sol alt köşeye doğru diyagonal kaydırmalı geçiş' },
    { type: 'solarflash', name: 'Güneş Flaşı (Solar Flash)', category: 'Işık / Flaş', icon: '☀️', defaultDuration: 0.40, recommendedSfx: 'whoosh-flames', description: 'CapCut Trend: Sıcak güneş parlaması ile sahne geçişi' },
    { type: 'snowflash', name: 'Karlı Flaş (White Strobe)', category: 'Işık / Flaş', icon: '❄️', defaultDuration: 0.35, recommendedSfx: 'camera-shutter', description: 'CapCut Trend: Parlak beyaz flaş patlaması' },
    { type: 'zoommorph', name: 'Yakın Plan Morf (Zoom Morph)', category: 'Trend', icon: '🔭', defaultDuration: 0.45, recommendedSfx: 'whoosh-zoom-in', description: 'CapCut Trend: Merkeze hızla yakınlaşarak yeni sahneye morf olma' },
    { type: 'vortexblur', name: 'Sisli Girdap (Vortex Blur)', category: 'Bulanıklık', icon: '🌀', defaultDuration: 0.50, recommendedSfx: 'swoosh-deep', description: 'CapCut Trend: Bulanık girdap hareketiyle yumuşak geçiş' },
    { type: 'pagecurl', name: 'Uçan Kağıt / Sayfa Çevirme', category: '3D & Shader', icon: '📄', defaultDuration: 0.50, recommendedSfx: 'page-turn', description: 'GL-Transitions PageCurl: Kitap sayfası çevrilir gibi geçiş' },
    { type: 'irisglow', name: 'Işıltı Çemberi (Iris Glow)', category: 'Trend', icon: '💫', defaultDuration: 0.50, recommendedSfx: 'whoosh-sparkle', description: 'CapCut Trend: Merkezden dışa doğru genişleyen dairesel ışıltı' },
    { type: 'burnportal', name: 'Yanmış Portal (Burn Transition)', category: 'Trend', icon: '🔥', defaultDuration: 0.55, recommendedSfx: 'whoosh-flames', description: 'GL-Transitions Burn: Renk ve ışık yanmasıyla sahne açılışı' },
    { type: 'blurayscan', name: 'Blu-ray Lazer Tarama', category: 'Dijital & Maske', icon: '💿', defaultDuration: 0.40, recommendedSfx: 'whoosh-cyber', description: 'CapCut Trend: Yatay optik tarama çizgileriyle geçiş' },
    { type: 'zoomsnap', name: 'Zoom Snap (Anlık Vurgu)', category: 'Trend', icon: '⚡', defaultDuration: 0.35, recommendedSfx: 'thud-punch', description: 'CapCut Trend: Hızlı zoom ve darbe ile keskin geçiş' },
    { type: 'reelroll', name: 'Renkli Makara (Film Roll)', category: 'Kamera / Whip', icon: '🎞️', defaultDuration: 0.45, recommendedSfx: 'machine-film-projector', description: 'CapCut Trend: Sinema film şeridi gibi dikey makara kayması' },
    { type: 'clouddissolve', name: 'Bulutlar (Dreamy Dissolve)', category: 'Bulanıklık', icon: '☁️', defaultDuration: 0.55, recommendedSfx: 'whoosh-air', description: 'CapCut Trend: Yumuşak bulut dokusuyla eriyerek geçiş' },
    { type: 'cubespin', name: '3D Küp Dönüşü (GL Cube)', category: '3D & Shader', icon: '🧊', defaultDuration: 0.50, recommendedSfx: 'whoosh-whip', description: 'GL-Transitions Cube: 3 boyutlu küp yüzeyi döndürme geçişi' },
    { type: 'doorway', name: '3D Kapı Açılışı (GL Doorway)', category: '3D & Shader', icon: '🚪', defaultDuration: 0.55, recommendedSfx: 'swoosh-deep', description: 'GL-Transitions Doorway: İki yana açılan 3D kapı geçişi' },
    { type: 'glitchmemories', name: 'Glitch Anılar (GL Glitch)', category: 'Dijital & Maske', icon: '👾', defaultDuration: 0.40, recommendedSfx: 'digital-glitch', description: 'GL-Transitions GlitchMemories: RGB kaymalı dijital bozulma' },
    { type: 'directionalwarp', name: 'Esnek Bükülme (Directional Warp)', category: 'Bulanıklık', icon: '🌊', defaultDuration: 0.45, recommendedSfx: 'whoosh-fast', description: 'GL-Transitions DirectionalWarp: Sola doğru elastik piksel bükülmesi' },
    { type: 'pinwheel', name: 'Rüzgar Gülü (GL Pinwheel)', category: '3D & Shader', icon: '🎡', defaultDuration: 0.50, recommendedSfx: 'whoosh-fast', description: 'GL-Transitions Pinwheel: Dönen pervane kanatlarıyla geçiş' },
    { type: 'windowblinds', name: 'Panjur Perde (Window Blinds)', category: 'Perde & Bölme', icon: '🪟', defaultDuration: 0.45, recommendedSfx: 'whoosh-fast', description: 'GL-Transitions WindowBlinds: Yatay şerit panjur açılışı' },
    { type: 'hexagonalize', name: 'Altıgen Petek (Hexagonalize)', category: '3D & Shader', icon: '🐝', defaultDuration: 0.50, recommendedSfx: 'whoosh-cyber', description: 'GL-Transitions Hexagonalize: Altıgen mozaik petek dönüşümü' },
    { type: 'luminancemelt', name: 'Işık Erimesi (Luminance Melt)', category: 'Işık / Flaş', icon: '🕯️', defaultDuration: 0.55, recommendedSfx: 'swoosh-deep', description: 'GL-Transitions LuminanceMelt: Parlak piksellerin aşağı akarak erimesi' }
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
    { id: 'stk_crown', name: '👑 Kral Tacı', category: 'badges', preview: '👑', dataUrl: this.emojiToDataUrl('👑') },

    // --- YENİ GOOGLE NOTO HAREKETLİ GIF & MICROSOFT FLUENT 3D ANİMASYONLU EMOJİLER (Görsel 5) ---
    { id: 'anim_chefkiss', name: '👨‍🍳 Mükemmel (Chef Kiss)', category: 'animated', preview: '👨‍🍳 CANLI', isAnimated: true, dataUrl: 'https://fonts.gstatic.com/s/e/notoemoji/latest/1f90c/512.gif' },
    { id: 'anim_rofl', name: '🤣 Kahkaha Криzi (ROFL)', category: 'animated', preview: '🤣 CANLI', isAnimated: true, dataUrl: 'https://fonts.gstatic.com/s/e/notoemoji/latest/1f923/512.gif' },
    { id: 'anim_butterfly', name: '🦋 Hareketli Kelebek', category: 'animated', preview: '🦋 CANLI', isAnimated: true, dataUrl: 'https://fonts.gstatic.com/s/e/notoemoji/latest/1f98b/512.gif' },
    { id: 'anim_ghost', name: '👻 Sevimli Hayalet', category: 'animated', preview: '👻 CANLI', isAnimated: true, dataUrl: 'https://fonts.gstatic.com/s/e/notoemoji/latest/1f47b/512.gif' },
    { id: 'anim_pumpkin', name: '🎃 Cadılar Bayramı Kabak', category: 'animated', preview: '🎃 CANLI', isAnimated: true, dataUrl: 'https://fonts.gstatic.com/s/e/notoemoji/latest/1f383/512.gif' },
    { id: 'anim_snowman', name: '⛄ Kardan Adam', category: 'animated', preview: '⛄ CANLI', isAnimated: true, dataUrl: 'https://fonts.gstatic.com/s/e/notoemoji/latest/26c4/512.gif' },
    { id: 'anim_cat_wry', name: '😼 Şaşkın Kedi (Cat Meme)', category: 'animated', preview: '😼 CANLI', isAnimated: true, dataUrl: 'https://fonts.gstatic.com/s/e/notoemoji/latest/1f63c/512.gif' },
    { id: 'anim_bell', name: '🔔 Bildirim Zili', category: 'animated', preview: '🔔 CANLI', isAnimated: true, dataUrl: 'https://fonts.gstatic.com/s/e/notoemoji/latest/1f514/512.gif' },
    { id: 'anim_scales', name: '⚖️ Adalet Terazisi', category: 'animated', preview: '⚖️ CANLI', isAnimated: true, dataUrl: 'https://fonts.gstatic.com/s/e/notoemoji/latest/2696_fe0f/512.gif' },
    { id: 'anim_books', name: '📚 Kitaplar / Külliyat', category: 'animated', preview: '📚 CANLI', isAnimated: true, dataUrl: 'https://fonts.gstatic.com/s/e/notoemoji/latest/1f4da/512.gif' },
    { id: 'anim_graduation', name: '🎓 Akademik Kep', category: 'animated', preview: '🎓 CANLI', isAnimated: true, dataUrl: 'https://fonts.gstatic.com/s/e/notoemoji/latest/1f393/512.gif' },
    { id: 'anim_muscle', name: '💪 Güç / Azim', category: 'animated', preview: '💪 CANLI', isAnimated: true, dataUrl: 'https://fonts.gstatic.com/s/e/notoemoji/latest/1f4aa/512.gif' },

    // --- CAPCUT ÖZEL ÇIKARTMALARI (Görsel 5: Sayaç, Abone Ol El Tıklama, Sansür Mozaik, Kırmızı Ok, Daire) ---
    {
      id: 'stk_cinema_countdown',
      name: '⏱️ Sinema Geri Sayım (4-3-2-1)',
      category: 'effects',
      preview: '⏱️ SAYAÇ 4',
      dataUrl: this.svgToDataUrl(`<svg xmlns="http://www.w3.org/2000/svg" width="260" height="260" viewBox="0 0 260 260"><circle cx="130" cy="130" r="118" fill="#1e293b" stroke="#e2e8f0" stroke-width="6"/><circle cx="130" cy="130" r="92" fill="none" stroke="#94a3b8" stroke-width="4" stroke-dasharray="14 8"/><line x1="10" y1="130" x2="250" y2="130" stroke="#cbd5e1" stroke-width="3"/><line x1="130" y1="10" x2="130" y2="250" stroke="#cbd5e1" stroke-width="3"/><text x="130" y="168" font-family="Arial, sans-serif" font-weight="900" font-size="120" fill="#ffffff" text-anchor="middle">4</text></svg>`)
    },
    {
      id: 'stk_subscribe_hand_click',
      name: '👆 SUBSCRIBE + El Tıklama',
      category: 'social',
      preview: '👆 SUBSCRIBE',
      dataUrl: this.svgToDataUrl(`<svg xmlns="http://www.w3.org/2000/svg" width="380" height="140" viewBox="0 0 380 140"><rect x="16" y="20" width="280" height="74" rx="14" fill="#dc2626" stroke="#ffffff" stroke-width="4"/><text x="156" y="68" font-family="Arial, sans-serif" font-weight="900" font-size="32" fill="#ffffff" text-anchor="middle" letter-spacing="2">SUBSCRIBE</text><circle cx="332" cy="57" r="28" fill="#334155" stroke="#fff" stroke-width="3"/><text x="332" y="68" font-size="28" text-anchor="middle">🔔</text><text x="80" y="122" font-size="48">👆</text></svg>`)
    },
    {
      id: 'stk_like_follow_3d',
      name: '❤️ LIKE / FOLLOW 3D Bar',
      category: 'social',
      preview: '❤️ LIKE/FOLLOW',
      dataUrl: this.svgToDataUrl(`<svg xmlns="http://www.w3.org/2000/svg" width="360" height="130" viewBox="0 0 360 130"><polygon points="30,25 330,25 310,65 50,65" fill="#ef4444" stroke="#fff" stroke-width="3"/><polygon points="50,65 310,65 330,105 30,105" fill="#2563eb" stroke="#fff" stroke-width="3"/><text x="180" y="53" font-family="Arial, sans-serif" font-weight="900" font-size="26" fill="#fff" text-anchor="middle" letter-spacing="3">LIKE</text><text x="180" y="94" font-family="Arial, sans-serif" font-weight="900" font-size="26" fill="#fff" text-anchor="middle" letter-spacing="3">FOLLOW</text></svg>`)
    },
    {
      id: 'stk_pixel_censor_bar',
      name: '🟦 Sansür Mozaik Barı (Censor)',
      category: 'effects',
      preview: '🟦 SANSÜR',
      dataUrl: this.svgToDataUrl(`<svg xmlns="http://www.w3.org/2000/svg" width="360" height="100" viewBox="0 0 360 100"><rect x="0" y="10" width="45" height="40" fill="#cbd5e1"/><rect x="45" y="10" width="45" height="40" fill="#475569"/><rect x="90" y="10" width="45" height="40" fill="#94a3b8"/><rect x="135" y="10" width="45" height="40" fill="#1e293b"/><rect x="180" y="10" width="45" height="40" fill="#e2e8f0"/><rect x="225" y="10" width="45" height="40" fill="#64748b"/><rect x="270" y="10" width="45" height="40" fill="#334155"/><rect x="315" y="10" width="45" height="40" fill="#f8fafc"/><rect x="0" y="50" width="45" height="40" fill="#334155"/><rect x="45" y="50" width="45" height="40" fill="#f1f5f9"/><rect x="90" y="50" width="45" height="40" fill="#1e293b"/><rect x="135" y="50" width="45" height="40" fill="#cbd5e1"/><rect x="180" y="50" width="45" height="40" fill="#475569"/><rect x="225" y="50" width="45" height="40" fill="#94a3b8"/><rect x="270" y="50" width="45" height="40" fill="#e2e8f0"/><rect x="315" y="50" width="45" height="40" fill="#64748b"/></svg>`)
    },
    {
      id: 'stk_arrow_down_bold',
      name: '⬇️ Kırmızı Kalın Aşağı Ok',
      category: 'arrows',
      preview: '⬇️ AŞAĞI OK',
      dataUrl: this.svgToDataUrl(`<svg xmlns="http://www.w3.org/2000/svg" width="220" height="260" viewBox="0 0 220 260"><path d="M110 20 L110 190 M45 140 L110 215 L175 140" stroke="#ffffff" stroke-width="34" stroke-linecap="round" stroke-linejoin="round" fill="none"/><path d="M110 20 L110 190 M45 140 L110 215 L175 140" stroke="#ef4444" stroke-width="22" stroke-linecap="round" stroke-linejoin="round" fill="none"/></svg>`)
    },
    {
      id: 'stk_loading_spinner',
      name: '🔄 Yükleniyor Halkası (Loading)',
      category: 'effects',
      preview: '🔄 LOADING',
      dataUrl: this.svgToDataUrl(`<svg xmlns="http://www.w3.org/2000/svg" width="240" height="240" viewBox="0 0 240 240"><circle cx="120" cy="120" r="84" fill="none" stroke="#ffffff" stroke-width="18" stroke-dasharray="320 180" stroke-linecap="round"/><circle cx="120" cy="120" r="84" fill="none" stroke="#38bdf8" stroke-width="10" stroke-dasharray="320 180" stroke-linecap="round"/></svg>`)
    }
  ];

  private notoEmojiCatalogCache: Array<{ codepoint: string; tags: string[]; category: string }> | null = null;

  /**
   * Çoklu Açık Kaynak Sticker & GIF Arama Motoru:
   * 1. GIPHY v1 Transparent Stickers & GIFs API (CORS: *, Sıfır Kurulum)
   * 2. Google Noto 881 Hareketli Emoji Kataloğu (512x512 Şeffaf GIF)
   * 3. Iconify 200.000+ Vektör Çıkartma & İkon API
   */
  async searchIconifyStickers(query: string, sourceMode: 'all' | 'giphy_stickers' | 'giphy_gifs' | 'noto_animated' | 'iconify' = 'all'): Promise<StickerLibraryItem[]> {
    const q = (query || '').trim().toLowerCase();
    if (!q) return [];

    const trMap: Record<string, string> = {
      'ateş': 'fire flame',
      'alev': 'fire flame',
      'ok': 'arrow point',
      'ok işareti': 'arrow point here',
      'daire': 'circle highlight ring',
      'kalp': 'heart love',
      'para': 'money cash dollar coin',
      'yıldız': 'star sparkle',
      'roket': 'rocket launch',
      'kral': 'crown king',
      'taç': 'crown',
      'oyun': 'gamepad gaming',
      'müzik': 'music note audio',
      'kamera': 'camera video',
      'uyarı': 'warning alert',
      'onay': 'check verified yes',
      'tik': 'check tick',
      'çarpı': 'close cross error no',
      'youtube': 'youtube subscribe',
      'instagram': 'instagram follow',
      'tiktok': 'tiktok',
      'abone': 'subscribe bell button',
      'abone ol': 'subscribe button bell',
      'zil': 'bell notification',
      'şimşek': 'lightning bolt zap',
      'fikir': 'lightbulb idea',
      'ampul': 'lightbulb',
      'hediye': 'gift present',
      'araba': 'car racing',
      'kupa': 'trophy award winner',
      'elmas': 'diamond gem',
      'gülümseme': 'smile laugh emoji',
      'komik': 'funny laugh lol cat',
      'kedi': 'funny cat meme',
      'alkış': 'clap applause bravo',
      'şaşkın': 'shocked wow mindblown',
      'korku': 'skull ghost scary',
      'patlama': 'explosion boom',
      'hukuk': 'justice scales law gavel',
      'adalet': 'justice scales court',
      'kitap': 'book reading library',
      'sayaç': 'countdown timer'
    };

    const mappedQuery = trMap[q] || q;
    const results: StickerLibraryItem[] = [];
    const giphyKey = 'GlVGYHkr3WSBnllca54iNt0yFbjz7L65';

    const tasks: Promise<void>[] = [];

    // 1. GIPHY Şeffaf Hareketli Stickerlar (veya GIF'ler)
    if (sourceMode === 'all' || sourceMode === 'giphy_stickers' || sourceMode === 'giphy_gifs') {
      const endpoint = sourceMode === 'giphy_gifs' ? 'gifs' : 'stickers';
      const limit = sourceMode === 'all' ? 16 : 30;
      tasks.push(
        fetch(`https://api.giphy.com/v1/${endpoint}/search?api_key=${giphyKey}&q=${encodeURIComponent(mappedQuery)}&limit=${limit}&rating=g&lang=tr`)
          .then(r => (r.ok ? r.json() : null))
          .then(data => {
            const list = Array.isArray(data?.data) ? data.data : [];
            for (const item of list) {
              const gifUrl = item?.images?.original?.url || item?.images?.fixed_height?.url;
              const previewUrl = item?.images?.fixed_height?.url || gifUrl;
              if (!gifUrl) continue;
              results.push({
                id: `giphy_${item.id}`,
                name: (item.title || mappedQuery).replace(/Sticker|GIF/gi, '').trim() || 'Hareketli GIF',
                category: 'animated',
                preview: 'GIF',
                isAnimated: true,
                dataUrl: gifUrl,
                dataUri: previewUrl
              });
            }
          })
          .catch(() => {})
      );
    }

    // 2. Google Noto 881 Hareketli Emoji Kataloğu
    if (sourceMode === 'all' || sourceMode === 'noto_animated') {
      tasks.push(
        this.searchNotoAnimatedEmojis(mappedQuery, sourceMode === 'noto_animated' ? 30 : 10)
          .then(items => {
            results.push(...items);
          })
          .catch(() => {})
      );
    }

    // 3. Iconify 200.000+ Vektör Sticker & İkon Motoru
    if (sourceMode === 'all' || sourceMode === 'iconify') {
      const limit = sourceMode === 'iconify' ? 36 : 16;
      tasks.push(
        fetch(`https://api.iconify.design/search?query=${encodeURIComponent(mappedQuery)}&limit=${limit}`)
          .then(r => (r.ok ? r.json() : null))
          .then(data => {
            const icons: string[] = Array.isArray(data?.icons) ? data.icons : [];
            for (let idx = 0; idx < icons.length; idx++) {
              const [prefix, name] = icons[idx].split(':');
              const svgUrl = `https://api.iconify.design/${prefix}/${name}.svg?height=256`;
              results.push({
                id: `iconify_${prefix}_${name}_${idx}`,
                name: `${name.replace(/-/g, ' ')} (${prefix})`,
                category: 'effects',
                preview: name.slice(0, 12).toUpperCase(),
                dataUrl: svgUrl
              });
            }
          })
          .catch(() => {})
      );
    }

    await Promise.allSettled(tasks);
    return results;
  }

  /**
   * Google Noto 881 Hareketli Emoji resmi JSON kataloğunda arama yapar.
   */
  async searchNotoAnimatedEmojis(query: string, limit = 18): Promise<StickerLibraryItem[]> {
    try {
      if (!this.notoEmojiCatalogCache) {
        const resp = await fetch('https://googlefonts.github.io/noto-emoji-animation/data/api.json');
        if (resp.ok) {
          const data = await resp.json();
          const rawIcons = Array.isArray(data?.icons) ? data.icons : [];
          this.notoEmojiCatalogCache = rawIcons.map((ic: any) => ({
            codepoint: String(ic.codepoint || ''),
            tags: Array.isArray(ic.tags) ? ic.tags.map((t: string) => t.replace(/:/g, '').toLowerCase()) : [],
            category: Array.isArray(ic.categories) && ic.categories[0] ? String(ic.categories[0]) : ''
          }));
        } else {
          this.notoEmojiCatalogCache = [];
        }
      }
      const tokens = query.toLowerCase().split(/\s+/).filter(Boolean);
      const matched = (this.notoEmojiCatalogCache || []).filter(item =>
        tokens.some(tok => item.tags.some(tag => tag.includes(tok)))
      );
      return matched.slice(0, limit).map(item => ({
        id: `noto_anim_${item.codepoint}`,
        name: `✨ ${item.tags[0] || item.codepoint} (Noto GIF)`,
        category: 'animated',
        preview: 'GIF',
        isAnimated: true,
        dataUrl: `https://fonts.gstatic.com/s/e/notoemoji/latest/${item.codepoint}/512.gif`
      }));
    } catch {
      return [];
    }
  }

  /**
   * Canlı Çevrimiçi Ses Efekti (SFX) Arama Motoru:
   * Openverse Audio API (Freesound CC0/CC-BY HQ MP3) + Wikimedia Commons Audio API üzerinden
   * sıfır API anahtarıyla binlerce gerçek ses efektini arar ve anında önizleme/indirme sağlar.
   */
  async searchOnlineSfx(query: string): Promise<SfxLibraryItem[]> {
    const q = (query || '').trim().toLowerCase();
    if (!q) return [];

    const trSfxMap: Record<string, string> = {
      'geçiş': 'whoosh transition swish',
      'kaydırma': 'whoosh swipe',
      'rüzgar': 'whoosh wind swoosh',
      'klavye': 'keyboard typing mechanical',
      'daktilo': 'typewriter typing',
      'yazı': 'typing keyboard',
      'tıklama': 'mouse click button',
      'buton': 'button click ui',
      'çan': 'bell ding chime',
      'zil': 'bell ring notification',
      'tın': 'bell ding crystal chime',
      'patlama': 'explosion boom blast',
      'darbe': 'cinematic hit impact punch',
      'yumruk': 'punch hit thud',
      'kamera': 'camera shutter click flash',
      'fotoğraf': 'camera shutter',
      'alkış': 'applause clapping crowd',
      'gülme': 'laugh funny',
      'kahkaha': 'laughter crowd',
      'komik': 'cartoon boing funny pop',
      'ıslık': 'whistle',
      'kalp': 'heartbeat pulse',
      'saat': 'clock ticking timer',
      'alarm': 'alarm siren alert',
      'korku': 'horror suspense jumpscare',
      'para': 'cash register coin money',
      'kasa': 'cash register cha ching',
      'su': 'water drop splash',
      'sayfa': 'page turn paper flip',
      'mühür': 'stamp thud gavel',
      'mahkeme': 'gavel court hammer',
      'oyun': 'arcade retro 8bit powerup'
    };

    const mappedQuery = trSfxMap[q] || q;
    const results: SfxLibraryItem[] = [];

    const openverseTask = fetch(
      `https://api.openverse.org/v1/audio/?q=${encodeURIComponent(mappedQuery)}&length=shortest&page_size=18`
    )
      .then(r => (r.ok ? r.json() : null))
      .then(data => {
        const items = Array.isArray(data?.results) ? data.results : [];
        for (const item of items) {
          const audioUrl = String(item?.url || '');
          if (!audioUrl || !audioUrl.startsWith('http')) continue;
          const durSec = item.duration ? Math.max(0.3, Math.min(12.0, Number(item.duration) / 1000)) : 1.5;
          results.push({
            id: `ov_sfx_${item.id}`,
            name: String(item.title || mappedQuery).slice(0, 42),
            category: 'ui',
            icon: '🌐',
            duration: Number(durSec.toFixed(2)),
            synthPreset: 'whoosh-fast',
            description: `${item.source || 'Freesound'} • ${item.creator || 'CC0'} (${(item.license || 'cc0').toUpperCase()})`,
            peaks: [0.25, 0.75, 1.0, 0.85, 0.6, 0.35, 0.15],
            sourceUrl: audioUrl,
            creator: String(item.creator || 'Freesound'),
            license: String(item.license || 'CC0'),
            isOnline: true
          });
        }
      })
      .catch(() => {});

    const wikiTask = fetch(
      `https://commons.wikimedia.org/w/api.php?action=query&generator=search&gsrsearch=${encodeURIComponent('filetype:audio sound effect ' + mappedQuery)}&gsrnamespace=6&gsrlimit=12&prop=imageinfo&iiprop=url|size|mime|duration&format=json&origin=*`
    )
      .then(r => (r.ok ? r.json() : null))
      .then(data => {
        const pages = data?.query?.pages ? Object.values(data.query.pages) : [];
        for (const p of pages as any[]) {
          const ii = Array.isArray(p?.imageinfo) ? p.imageinfo[0] : null;
          const url = String(ii?.url || '');
          const dur = Number(ii?.duration || 1.5);
          if (!url || dur > 15.0 || dur <= 0.05) continue;
          const cleanTitle = String(p?.title || '')
            .replace(/^File:/i, '')
            .replace(/\.(ogg|oga|mp3|wav|flac)$/i, '')
            .replace(/[_-]+/g, ' ');
          results.push({
            id: `wiki_sfx_${p.pageid}`,
            name: cleanTitle.slice(0, 42),
            category: 'ui',
            icon: '🔊',
            duration: Number(Math.max(0.25, dur).toFixed(2)),
            synthPreset: 'whoosh-fast',
            description: 'Wikimedia Commons • Açık Lisanslı Stüdyo Sesi',
            peaks: [0.3, 0.8, 0.95, 0.7, 0.4, 0.15],
            sourceUrl: url,
            creator: 'Wikimedia Commons',
            license: 'CC',
            isOnline: true
          });
        }
      })
      .catch(() => {});

    await Promise.allSettled([openverseTask, wikiTask]);
    return results;
  }

  /**
   * Canlı Çevrimiçi Ücretsiz Stok Görsel / B-Roll Arama Motoru (Openverse + Wikimedia Commons).
   */
  async searchOnlineStockImages(query: string): Promise<OnlineStockImageItem[]> {
    const q = (query || '').trim();
    if (!q) return [];
    const results: OnlineStockImageItem[] = [];

    const openverseTask = fetch(
      `https://api.openverse.org/v1/images/?q=${encodeURIComponent(q)}&page_size=16&aspect_ratio=wide`
    )
      .then(r => (r.ok ? r.json() : null))
      .then(data => {
        const items = Array.isArray(data?.results) ? data.results : [];
        for (const item of items) {
          if (!item?.url) continue;
          results.push({
            id: `ov_img_${item.id}`,
            title: String(item.title || q).slice(0, 40),
            thumb: String(item.thumbnail || item.url),
            url: String(item.url),
            source: String(item.source || 'Openverse'),
            creator: String(item.creator || '')
          });
        }
      })
      .catch(() => {});

    const wikiTask = fetch(
      `https://commons.wikimedia.org/w/api.php?action=query&generator=search&gsrsearch=${encodeURIComponent('filetype:bitmap ' + q)}&gsrnamespace=6&gsrlimit=12&prop=imageinfo&iiprop=url&iiurlwidth=640&format=json&origin=*`
    )
      .then(r => (r.ok ? r.json() : null))
      .then(data => {
        const pages = data?.query?.pages ? Object.values(data.query.pages) : [];
        for (const p of pages as any[]) {
          const ii = Array.isArray(p?.imageinfo) ? p.imageinfo[0] : null;
          const thumb = String(ii?.thumburl || ii?.url || '');
          const full = String(ii?.url || thumb);
          if (!thumb) continue;
          const cleanTitle = String(p?.title || q).replace(/^File:/i, '').replace(/\.[a-z0-9]+$/i, '').replace(/_/g, ' ');
          results.push({
            id: `wiki_img_${p.pageid}`,
            title: cleanTitle.slice(0, 40),
            thumb,
            url: thumb,
            source: 'Wikimedia'
          });
        }
      })
      .catch(() => {});

    await Promise.allSettled([openverseTask, wikiTask]);
    return results;
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
      const rawId = (presetId || 'capcut-swish-large').trim();
      const wavIdMap: Record<string, string> = {
        'keyboard-type': 'keyboard-typing',
        'keyboard': 'keyboard-typing',
        'ding': 'ding-bright',
        'pop': 'pop-bubble',
        'whoosh': 'capcut-swish-large',
        'whoosh-fast': 'capcut-swish-large',
        'swish': 'capcut-swish-large',
        'capcut-swish-large': 'capcut-swish-large'
      };
      const cleanId = wavIdMap[rawId] || rawId;
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
        case 'ding-bright':
        case 'ding-bell':
        case 'cash-register': {
          const env = Math.exp(-t * 4.5);
          const f1 = (synthFamily === 'cash-register' && t > 0.12 ? 2093 : 1567.98) * pitchMod;
          const f2 = f1 * 2.0;
          const f3 = f1 * 3.0;
          data[i] = (
            Math.sin(2 * Math.PI * f1 * t) * 0.60 +
            Math.sin(2 * Math.PI * f2 * t) * 0.28 +
            Math.sin(2 * Math.PI * f3 * t) * 0.12 * Math.exp(-t * 8.0)
          ) * env;
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
        case 'mouse-click': {
          const clickPeriod = 0.12;
          const localT = t % clickPeriod;
          const env = Math.exp(-localT * 65);
          data[i] = (Math.random() * 2 - 1) * env * 0.9;
          break;
        }
        case 'keyboard-type':
        case 'keyboard-typing': {
          const strokeTimes = [0.0, 0.075, 0.145, 0.225, 0.31, 0.39, 0.48, 0.57, 0.66, 0.75];
          let sampleVal = 0;
          for (let k = 0; k < strokeTimes.length; k++) {
            const dt = t - strokeTimes[k];
            if (dt >= 0 && dt < 0.068) {
              const clickFreq = (2400 + ((k * 317) % 700)) * pitchMod;
              const thockFreq = (420 + ((k * 131) % 160)) * pitchMod;
              const clickEnv = Math.exp(-dt * 175);
              const thockEnv = Math.exp(-dt * 58);
              const clickWave = Math.sin(2 * Math.PI * clickFreq * dt) * clickEnv * 0.45;
              const thockWave = Math.sin(2 * Math.PI * thockFreq * dt) * thockEnv * 0.40;
              const burstNoise = (Math.random() * 2 - 1) * Math.exp(-dt * 115) * 0.30;
              sampleVal += (clickWave + thockWave + burstNoise);
            }
          }
          data[i] = Math.max(-0.95, Math.min(0.95, sampleVal));
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
   * Türkçe cümleden ASLA kelime veya tamlama ortasından bölünmeyen,
   * bağlaç/edat/yarım fiil ile bitmeyen tam ve anlamlı bir kavramsal başlık çıkarır.
   */
  extractSemanticTurkishPhrase(rawText: string, maxChars = 34): string {
    if (!rawText || !rawText.trim()) return '';
    const trimmed = rawText.trim().replace(/\s+/g, ' ');
    if (
      trimmed.length <= maxChars + 4 &&
      (/^(\d+\.|PROF\.|DR\.|HZ\.|İMAM\b|MD\.)/i.test(trimmed) ||
        (trimmed.includes(':') && trimmed.split(/\s+/).length <= 6) ||
        (trimmed.includes('&') && trimmed.split(/\s+/).length <= 6) ||
        (trimmed.includes('(') && trimmed.includes(')') && trimmed.split(/\s+/).length <= 6))
    ) {
      return trimmed.slice(0, maxChars + 4).toLocaleUpperCase('tr-TR');
    }

    const clauses = trimmed.split(/[!?;:—–]+|(?<!\d)(?<!Prof)(?<!Dr)(?<!Hz)(?<!Md)\.(?!\w)/i);
    const clause = clauses.find(c => c.trim().length >= 6) || trimmed;
    const cleaned = clause.replace(/[^\w\sğüşıöçĞÜŞİÖÇ0-9/'():&\-]/g, ' ').trim();
    const words = cleaned.split(/\s+/).filter(w => w.length > 1 || /^\d+$/.test(w));
    if (!words.length) return '';

    const fillers = new Set([
      'arkadaşlar', 'şimdi', 'bakın', 'tabii', 'elbette', 'burada',
      'dolayısıyla', 'öncelikle', 'mesela', 'örneğin', 'aslında', 'peki',
      'evet', 'bugün', 'bugünkü', 'dersimizde', 've', 'ama', 'fakat',
      'ancak', 'çünkü', 'yani', 'işte', 'hatta', 'bir', 'bu', 'şu',
      'ayrıntılı', 'özellikle'
    ]);
    while (words.length > 2 && fillers.has(words[0].replace(/[.,:;]/g, '').toLocaleLowerCase('tr-TR'))) {
      words.shift();
    }

    const danglingStopwords = new Set([
      've', 'veya', 'ile', 'için', 'gibi', 'kadar', 'göre', 'karşı',
      'ama', 'fakat', 'ancak', 'çünkü', 'dolayısıyla', 'ise', 'de', 'da', 'ki',
      'bu', 'şu', 'bir', 'her', 'en', 'çok', 'daha', 'hiç', 'olarak', 'olan',
      'olup', 'olduğu', 'olur', 'olmaz', 'vardır', 'yoktur', 'değildir', 'demektir',
      'düşü', 'düşünün', 'düşünelim', 'bakalım', 'görüyoruz', 'eden', 'edilen',
      'intikal', 'uğrardı', 'şekilde', 'anlamda', 'çevresinde', 'kapsamında',
      'üzerinde', 'içerisinde', 'hakkında', 'tarafından', 'arasında'
    ]);

    const selected: string[] = [];
    for (const w of words.slice(0, 5)) {
      const candidate = [...selected, w].join(' ');
      if (candidate.length <= maxChars) {
        selected.push(w);
      } else {
        break;
      }
    }
    if (!selected.length) selected.push(words[0].slice(0, maxChars));

    while (
      selected.length > 1 &&
      danglingStopwords.has(selected[selected.length - 1].replace(/[.,:;]/g, '').toLocaleLowerCase('tr-TR'))
    ) {
      selected.pop();
    }

    // Tamlayan eki ("Kanununun" -> "Kanunu") düzeltmesi
    const lastIdx = selected.length - 1;
    const lastLower = selected[lastIdx].toLocaleLowerCase('tr-TR');
    for (const suf of ['unun', 'ünün', 'ının', 'inin', 'nun', 'nün', 'nın', 'nin']) {
      if (lastLower.endsWith(suf) && selected[lastIdx].length - suf.length >= 3) {
        const cutLen = suf.length === 4 ? 3 : suf.length;
        selected[lastIdx] = selected[lastIdx].slice(0, selected[lastIdx].length - cutLen);
        break;
      }
    }

    while (
      selected.length > 1 &&
      danglingStopwords.has(selected[selected.length - 1].replace(/[.,:;]/g, '').toLocaleLowerCase('tr-TR'))
    ) {
      selected.pop();
    }

    return selected.join(' ').toLocaleUpperCase('tr-TR');
  }

  /**
   * Transkriptin içeriğinden kilitli ThemeProfile seçer (Akademik/Felsefe/Hukuk, Kurumsal, Teknoloji, Vlog).
   */
  private detectLockedThemeProfile(segments: Array<{ text: string }>): {
    id: 'academic_lecture' | 'corporate_explainer' | 'tech_review' | 'energetic_vlog';
    fontFamily: string;
    fontSize: number;
    textColor: string;
    accentColor: string;
    strokeWidth: number;
    boxStyle: OverlayItem['boxStyle'];
    boxBgColor: string;
    borderRadius: number;
    boxPadding: number;
    animation: OverlayItem['animation'];
    exitAnimation: OverlayItem['exitAnimation'];
    allowStickers: boolean;
    minGapSec: number;
    allowedTransitions: EdlTransition['type'][];
    contextualImages: Array<{ url: string; label: string; keywords: RegExp }>;
  } {
    const fullText = segments.map(s => s.text || '').join(' ').toLocaleLowerCase('tr-TR');
    const isAcademic = /(kanun|mahkeme|dava|hukuk|madde|fıkra|mevzuat|ders|fakülte|teori|kavram|tarih|felsefe|delil|şeriat|kelam|fıkıh|gazali|aristoteles|anayasa|yargı)/.test(fullText);
    const isCorporate = /(şirket|yatırım|bütçe|strateji|müşteri|finans|kurumsal|yönetim|rapor|bilanço)/.test(fullText);
    const isTech = /(yazılım|algoritma|yapay zeka|uygulama|donanım|sunucu|teknoloji|kod|veri)/.test(fullText);

    if (isAcademic) {
      return {
        id: 'academic_lecture',
        fontFamily: 'Montserrat',
        fontSize: 36,
        textColor: '#FFFFFF',
        accentColor: '#FACC15',
        strokeWidth: 4,
        boxStyle: 'none',
        boxBgColor: 'rgba(15, 23, 42, 0.0)',
        borderRadius: 0,
        boxPadding: 0,
        animation: 'pop-up',
        exitAnimation: 'fade',
        allowStickers: false,
        minGapSec: 14,
        allowedTransitions: ['smoothleft', 'slideleft', 'wipeleft', 'fade'],
        contextualImages: []
      };
    }

    if (isCorporate) {
      return {
        id: 'corporate_explainer',
        fontFamily: 'Inter',
        fontSize: 44,
        textColor: '#FFFFFF',
        accentColor: '#10B981',
        strokeWidth: 4,
        boxStyle: 'rounded',
        boxBgColor: 'rgba(17, 24, 39, 0.88)',
        borderRadius: 16,
        boxPadding: 16,
        animation: 'slide-up',
        exitAnimation: 'fade',
        allowStickers: false,
        minGapSec: 18,
        allowedTransitions: ['smoothleft', 'slideleft', 'wipeleft', 'fade'],
        contextualImages: []
      };
    }

    if (isTech) {
      return {
        id: 'tech_review',
        fontFamily: 'Inter',
        fontSize: 44,
        textColor: '#F9FAFB',
        accentColor: '#06B6D4',
        strokeWidth: 4,
        boxStyle: 'rounded',
        boxBgColor: 'rgba(9, 13, 22, 0.86)',
        borderRadius: 16,
        boxPadding: 16,
        animation: 'slide-left',
        exitAnimation: 'fade',
        allowStickers: false,
        minGapSec: 15,
        allowedTransitions: ['smoothleft', 'slideleft', 'wipeleft', 'fade'],
        contextualImages: []
      };
    }

    return {
      id: 'energetic_vlog',
      fontFamily: 'Montserrat',
      fontSize: 48,
      textColor: '#FFFFFF',
      accentColor: '#00E676',
      strokeWidth: 5,
      boxStyle: 'none',
      boxBgColor: 'rgba(17, 17, 17, 0.0)',
      borderRadius: 0,
      boxPadding: 0,
      animation: 'pop-up',
      exitAnimation: 'fade',
      allowStickers: true,
      minGapSec: 12,
      allowedTransitions: ['smoothleft', 'slideleft', 'wipeleft', 'fade'],
      contextualImages: []
    };
  }

  /**
   * 5 Aşamalı Multimodal Otonom Yönetmen (AutoDirectorComposer V2 - Frontend):
   * 1. Transkriptten kilitli ThemeProfile seçer (Akademik/Hukuk dersinde rastgele font ve emoji yasağı!)
   * 2. Videonun tamamını (00:00 -> son saniye) orantılı Bölümlere (Chapters) ayırır (idx < 6 sınırı kaldırıldı)
   * 3. Konuşmacı yüzü (X=50%, Y=28%) ve altyazı kuşağına (Y ∈ [70%, 92%]) ASLA çarpmayan SafeZone köşelerini kullanır
   * 4. Bölüm içi anlamlı Türkçe kavram başlıkları (T2) ve bağlamsal konu görselleri (T3) yerleştirir
   * 5. Yalnızca görsel olaylara bağlı zarif mikro-SFX (vol: 0.18) ve cümle sınırına mıknatıslanmış geçişler üretir.
   */
  composeAutoDirectorTimeline(edl: EdlContent, totalDur?: number): {
    overlays: OverlayItem[];
    transitions: EdlTransition[];
    sfxClips: EdlSfxClip[];
  } {
    const duration = Math.max(8, totalDur || edl.duration || 60);
    const segments = edl.transcript?.segments || [];
    const rawCuts = (edl.cuts || []).slice().sort((a, b) => a.start - b.start);
    const now = Date.now();

    // 0. Kesilmeyen (Keep) aralıkları ve Sequence Time dönüşüm haritasını oluştur
    const mergedCuts: Array<{ start: number; end: number }> = [];
    for (const c of rawCuts) {
      const s = Math.max(0, Number(c.start || 0));
      const e = Math.min(duration, Number(c.end || 0));
      if (e <= s) continue;
      if (mergedCuts.length > 0 && s <= mergedCuts[mergedCuts.length - 1].end + 0.05) {
        mergedCuts[mergedCuts.length - 1].end = Math.max(mergedCuts[mergedCuts.length - 1].end, e);
      } else {
        mergedCuts.push({ start: s, end: e });
      }
    }

    const keepIntervals: Array<{ rawStart: number; rawEnd: number; seqStart: number; seqEnd: number; dur: number }> = [];
    let cursor = 0;
    let seqCursor = 0;
    for (const c of mergedCuts) {
      if (c.start > cursor + 0.15) {
        const d = c.start - cursor;
        keepIntervals.push({ rawStart: cursor, rawEnd: c.start, seqStart: seqCursor, seqEnd: seqCursor + d, dur: d });
        seqCursor += d;
      }
      cursor = Math.max(cursor, c.end);
    }
    if (cursor < duration - 0.15 || keepIntervals.length === 0) {
      const startR = keepIntervals.length === 0 ? 0 : cursor;
      const d = Math.max(1, duration - startR);
      keepIntervals.push({ rawStart: startR, rawEnd: startR + d, seqStart: seqCursor, seqEnd: seqCursor + d, dur: d });
      seqCursor += d;
    }
    const seqDuration = Math.max(4, seqCursor);

    const isRawInCut = (rawT: number): boolean =>
      mergedCuts.some(c => rawT >= c.start - 0.05 && rawT <= c.end + 0.05);

    const rawToSeq = (rawT: number): number => {
      for (const k of keepIntervals) {
        if (rawT >= k.rawStart - 0.05 && rawT <= k.rawEnd + 0.05) {
          return Math.max(k.seqStart, Math.min(k.seqEnd, k.seqStart + (rawT - k.rawStart)));
        }
        if (rawT < k.rawStart) {
          return k.seqStart;
        }
      }
      return seqDuration;
    };

    const seqToRaw = (seqT: number): number => {
      const clamped = Math.max(0, Math.min(seqDuration, seqT));
      for (const k of keepIntervals) {
        if (clamped >= k.seqStart && clamped <= k.seqEnd + 0.001) {
          return k.rawStart + (clamped - k.seqStart);
        }
      }
      const last = keepIntervals[keepIntervals.length - 1];
      return last ? last.rawStart : clamped;
    };

    const keepSegments = segments.filter(s => {
      const mid = (s.start + s.end) * 0.5;
      return !isRawInCut(mid) && s.text && s.text.trim().length > 2;
    });

    const theme = this.detectLockedThemeProfile(keepSegments.length ? keepSegments : segments);
    const overlays: OverlayItem[] = [];
    const transitions: EdlTransition[] = [];
    const sfxClips: EdlSfxClip[] = [];

    // SafeZone Köşe Yuvaları (Konuşmacının X=50%, Y=28% merkez yüzüne ve Y=85% altyazısına ASLA çarpmaz!)
    const safeTextSlots = [
      { x: 16, y: 18 }, // Sol Üst Sütun 1
      { x: 84, y: 18 }, // Sağ Üst Sütun 1
      { x: 16, y: 27.5 }, // Sol Üst Sütun 2
      { x: 84, y: 27.5 }  // Sağ Üst Sütun 2
    ];
    const safeImageSlots = [
      { x: 82, y: 28 }, // Sağ Üst Görsel Kartı
      { x: 18, y: 28 }  // Sol Üst Görsel Kartı
    ];

    // Videonun tamamını (00:00 -> seqDuration) kapsayan Bölüm Orantılı (Chapter-Proportional) Planlama
    const targetChapterLen = seqDuration >= 240 ? 135 : Math.max(20, seqDuration / 3);
    const chapterCount = Math.max(2, Math.min(16, Math.round(seqDuration / targetChapterLen)));
    const chapterDuration = seqDuration / chapterCount;

    let lastOverlaySeqEnd = -999;
    let lastSfxSeqStart = -999;
    let imageCardCounter = 0;

    for (let chIdx = 0; chIdx < chapterCount; chIdx++) {
      const chSeqStart = chIdx * chapterDuration;
      const chSeqEnd = (chIdx + 1) * chapterDuration;
      const chSegs = keepSegments.filter(s => {
        const st = rawToSeq(s.start);
        return st >= chSeqStart - 0.5 && st < chSeqEnd + 0.5;
      });

      // 1. Bölüm Sınırı Geçişi (Cümle başlangıcına mıknatıslanmış, kesimsiz 1 kliplik videolarda da V1'i böler!)
      if (chIdx > 0) {
        const boundarySeq = chSegs.length > 0 ? rawToSeq(chSegs[0].start) : chSeqStart;
        const boundaryRaw = Number(seqToRaw(boundarySeq).toFixed(2));
        if (boundaryRaw > 4.0 && boundaryRaw < duration - 4.0) {
          const tType = theme.allowedTransitions[(chIdx - 1) % theme.allowedTransitions.length];
          transitions.push({
            id: `ad_tr_${now}_${chIdx}`,
            boundarySourceTime: boundaryRaw,
            boundaryTime: boundaryRaw,
            type: tType,
            duration: 0.45,
            autoSfxId: 'capcut-swish-large',
            action: 'add'
          });
        }
      }

      if (!chSegs.length) continue;

      // 2. Bölüm İçi Kurgu Olayları (Bölüm başına 2-3 anlamlı olay)
      const eventsInChapter = Math.max(2, Math.min(3, Math.floor(chapterDuration / theme.minGapSec) + 1));
      const stepInChapter = chapterDuration / (eventsInChapter + 0.5);

      for (let eIdx = 0; eIdx < eventsInChapter; eIdx++) {
        const targetSeq = chSeqStart + stepInChapter * (eIdx + 0.35);
        const matchSeg =
          chSegs.find(s => rawToSeq(s.start) >= targetSeq - stepInChapter * 0.4 && s.text.trim().length >= 14) ||
          chSegs[Math.min(chSegs.length - 1, eIdx)];
        if (!matchSeg) continue;

        const itemSeqStamp = Number(Math.max(0.3, rawToSeq(matchSeg.start)).toFixed(2));
        if (itemSeqStamp - lastOverlaySeqEnd < theme.minGapSec * 0.65) continue;

        const itemRawStamp = Number(seqToRaw(itemSeqStamp).toFixed(2));
        const itemDur = Number(Math.min(3.8, Math.max(2.2, seqDuration - itemSeqStamp - 0.4)).toFixed(2));
        const phrase = this.extractSemanticTurkishPhrase(matchSeg.text, 32);
        if (!phrase || phrase.length < 3) continue;

        const textSlot = safeTextSlots[(chIdx + eIdx) % safeTextSlots.length];

        // Her bölümün 2. olayında (eIdx === 1) bağlamsal konu görseli kartı (T3) + kavram başlığı (T2)
        if (eIdx === 1 && theme.contextualImages.length > 0) {
          const matchedImg =
            theme.contextualImages.find(ci => ci.keywords.test(matchSeg.text)) ||
            theme.contextualImages[imageCardCounter % theme.contextualImages.length];
          const imgSlot = safeImageSlots[imageCardCounter % safeImageSlots.length];
          imageCardCounter++;

          overlays.push({
            id: `ad_img_${now}_${chIdx}_${eIdx}`,
            type: 'image',
            content: `${phrase} — ${matchedImg.label}`,
            source: matchedImg.url,
            timestamp: itemRawStamp,
            seqTimestamp: itemSeqStamp,
            duration: itemDur,
            trackId: 3,
            positionX: imgSlot.x,
            positionY: imgSlot.y,
            scale: 0.95,
            maskShape: 'rounded',
            borderRadius: 18,
            dropShadow: true,
            shadowBlur: 18,
            animation: 'fade',
            exitAnimation: 'fade',
            action: 'add'
          });
        } else {
          // Kilitli Tema Stiliyle Kavramsal Başlık Kartı (T2)
          overlays.push({
            id: `ad_txt_${now}_${chIdx}_${eIdx}`,
            type: 'text',
            content: phrase,
            timestamp: itemRawStamp,
            seqTimestamp: itemSeqStamp,
            duration: itemDur,
            trackId: 2,
            positionX: textSlot.x,
            positionY: textSlot.y,
            scale: 1,
            font: theme.fontFamily,
            fontSize: theme.fontSize,
            fontWeight: 800,
            color: eIdx === 0 ? theme.accentColor : theme.textColor,
            fillType: 'solid',
            strokeColor: '#000000',
            strokeWidth: theme.strokeWidth,
            boxStyle: theme.boxStyle,
            boxBgColor: theme.boxBgColor,
            boxPadding: theme.boxPadding,
            borderRadius: theme.borderRadius,
            allCaps: true,
            animation: theme.animation,
            exitAnimation: theme.exitAnimation,
            loopAnimation: 'none',
            action: 'add'
          });
        }

        // Yalnızca eğlence/vlog temasında izin veriliyorsa ve ilk bölümde 1 adet vurgu çıkartması
        if (theme.allowStickers && chIdx < 2 && eIdx === 0) {
          overlays.push({
            id: `ad_stk_${now}_${chIdx}`,
            type: 'image',
            content: 'Vurgu Çıkartması',
            source: 'https://fonts.gstatic.com/s/e/notoemoji/latest/1f525/512.gif',
            timestamp: itemRawStamp,
            seqTimestamp: itemSeqStamp,
            duration: 2.4,
            trackId: 3,
            positionX: textSlot.x > 50 ? 22 : 78,
            positionY: 24,
            scale: 0.75,
            animation: 'pop-up',
            exitAnimation: 'scale-out',
            action: 'add'
          });
        }

        // Olaya Bağlı Zarif Mikro-SFX (Metronom döngüsü yok, ses seviyesi: 0.18-0.22)
        if (itemSeqStamp - lastSfxSeqStart >= 14) {
          const sfxPresetId = eIdx === 0 ? 'capcut-swish-large' : 'pop-crisp';
          const sfxDur = eIdx === 0 ? 0.81 : 0.25;
          sfxClips.push({
            id: `ad_sfx_${now}_${chIdx}_${eIdx}`,
            name: eIdx === 0 ? 'Swish Whoosh (Large 794558)' : 'Kavram Kartı Efekti',
            title: eIdx === 0 ? 'Swish Whoosh (Large 794558)' : 'Kavram Kartı Efekti',
            category: eIdx === 0 ? 'whoosh' : 'pop',
            presetId: sfxPresetId,
            synthPreset: sfxPresetId,
            sourceUrl: this.generateSfxWavDataUri(sfxPresetId, sfxDur),
            start: itemRawStamp,
            duration: sfxDur,
            volume: eIdx === 0 ? 0.22 : 0.18,
            peaks: eIdx === 0 ? [0.28, 0.94, 0.88, 0.43, 0.45, 0.12, 0.04, 0.01] : [0.2, 0.7, 0.9, 0.5, 0.15],
            action: 'add'
          });
          lastSfxSeqStart = itemSeqStamp;
        }

        lastOverlaySeqEnd = itemSeqStamp + itemDur;
      }
    }

    // Eğer gerçek kesim sınırları varsa ve henüz geçiş eklenmemişse kesim sınırlarını da değerlendir
    if (transitions.length === 0 && keepIntervals.length > 1) {
      const maxTrans = Math.min(6, keepIntervals.length - 1);
      for (let i = 1; i <= maxTrans; i++) {
        const boundary = Number(keepIntervals[i].rawStart.toFixed(2));
        const tType = theme.allowedTransitions[(i - 1) % theme.allowedTransitions.length];
        transitions.push({
          id: `ad_tr_cut_${now}_${i}`,
          boundarySourceTime: boundary,
          boundaryTime: boundary,
          type: tType,
          duration: 0.45,
          autoSfxId: 'capcut-swish-large',
          action: 'add'
        });
      }
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

    const isRawInCut = (rawT: number): boolean =>
      cuts.some(c => rawT >= c.start - 0.05 && rawT <= c.end + 0.05);
    const keepSegments = segments.filter(s => !isRawInCut((s.start + s.end) * 0.5) && s.text && s.text.trim().length > 2);

    const firstSeg = keepSegments[0] || segments[0];
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

    const midCut = cuts.find(c => c.start > 2 && c.end < duration - 2) || { start: Math.min(12, duration * 0.25), end: Math.min(13, duration * 0.25 + 1) };
    suggestions.push({
      id: `sug_trans_${Date.now()}_2`,
      type: 'transition_sfx',
      category: '⚡ Sahne Geçişi & SFX',
      title: 'Hızlı Kayma (Whip Pan) Geçişi + Whoosh SFX',
      content: 'slideleft',
      timestamp: Number(midCut.end.toFixed(1)),
      duration: 0.4,
      confidence: 92,
      transitionType: 'slideleft',
      sfxPreset: 'whoosh-fast',
      reason: `${midCut.end.toFixed(1)}. saniyedeki kesim sıçramasını dinamik kamera kayması ve Whoosh rüzgar sesiyle sinematik hale getirir.`,
      status: 'pending'
    });

    const midSeg = keepSegments.find(s => s.start >= duration * 0.3 && s.text.length > 10) || keepSegments[Math.floor(keepSegments.length / 2)] || segments[Math.floor(segments.length / 2)];
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

    const lateSeg = keepSegments[Math.max(0, keepSegments.length - 2)] || keepSegments[keepSegments.length - 1];
    const ctaTime = Number((lateSeg ? lateSeg.start : Math.max(4, duration * 0.72)).toFixed(1));
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
      title: '-14 LUFS Ses Dengeleme',
      content: 'Stüdyo Ses Dengeleme Paketi',
      timestamp: 0,
      duration: Number(duration.toFixed(1)),
      confidence: 95,
      reason: 'Ses seviyesini YouTube/Reels/TikTok yayın standardı olan -14 LUFS seviyesine dengeler.',
      status: 'pending'
    });

    return suggestions;
  }
}
