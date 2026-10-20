import {
  Directive,
  ElementRef,
  Input,
  OnChanges,
  OnDestroy,
  OnInit,
  SimpleChanges,
  NgZone,
  inject
} from '@angular/core';

/**
 * CapCut & Premiere Pro Stili Çok Çözünürlüklü (Zoom LOD),
 * Ayrık Dikey Çubuk (Bar) ve Desibel Renk Kodlu Ses Dalga Formu Çizici.
 */
@Directive({
  selector: 'canvas[appClipWaveform]',
  standalone: true
})
export class ClipWaveformDirective implements OnInit, OnChanges, OnDestroy {
  @Input() peaks: number[] | null = null;
  @Input() clipStart = 0;
  @Input() clipEnd = 0;
  @Input() totalDuration = 1;
  @Input() isCut = false;
  @Input() zoom = 1;
  @Input() trackHeight = 56;

  private readonly el = inject(ElementRef<HTMLCanvasElement>);
  private readonly ngZone = inject(NgZone);
  private resizeObserver: ResizeObserver | null = null;
  private rafId: number | null = null;

  ngOnInit(): void {
    this.ngZone.runOutsideAngular(() => {
      if (typeof ResizeObserver !== 'undefined') {
        this.resizeObserver = new ResizeObserver(() => {
          this.scheduleDraw();
        });
        const parent = this.el.nativeElement.parentElement || this.el.nativeElement;
        this.resizeObserver.observe(parent);
      }
      this.scheduleDraw();
    });
  }

  ngOnChanges(_changes: SimpleChanges): void {
    this.scheduleDraw();
  }

  ngOnDestroy(): void {
    if (this.resizeObserver) {
      this.resizeObserver.disconnect();
      this.resizeObserver = null;
    }
    if (this.rafId !== null) {
      cancelAnimationFrame(this.rafId);
      this.rafId = null;
    }
  }

  private scheduleDraw(): void {
    if (this.rafId !== null) {
      cancelAnimationFrame(this.rafId);
    }
    this.ngZone.runOutsideAngular(() => {
      this.rafId = requestAnimationFrame(() => {
        this.rafId = null;
        this.drawWaveform();
      });
    });
  }

  private drawWaveform(): void {
    const canvas = this.el.nativeElement;
    if (!canvas) return;

    const parent = canvas.parentElement;
    const cssWidth = parent ? parent.clientWidth : canvas.clientWidth;
    const cssHeight = parent ? parent.clientHeight : canvas.clientHeight;

    if (cssWidth <= 1 || cssHeight <= 4) {
      return;
    }

    const dpr = Math.min(2, window.devicePixelRatio || 1);
    const targetW = Math.round(cssWidth * dpr);
    const targetH = Math.round(cssHeight * dpr);

    if (canvas.width !== targetW || canvas.height !== targetH) {
      canvas.width = targetW;
      canvas.height = targetH;
    }

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, cssWidth, cssHeight);

    const allPeaks = this.peaks;
    const totalDur = Math.max(0.1, this.totalDuration);
    const startSec = Math.max(0, this.clipStart);
    const endSec = Math.max(startSec + 0.01, this.clipEnd);

    // Çubuk (Bar) Geometrisi: 2px çubuk + 1px boşluk = 3px adım
    const barWidth = 2;
    const barGap = 1;
    const step = barWidth + barGap;
    const numBars = Math.max(1, Math.floor(cssWidth / step));

    const bottomY = cssHeight - 1;
    // Üstteki klip etiketiyle çakışmaması için hafif tavan payı bırak, tüm yüksekliği verimli kullan
    const maxBarHeight = Math.max(8, cssHeight - 10);

    if (!allPeaks || allPeaks.length === 0) {
      // Veri henüz yüklenirken ince referans taban çizgisi
      ctx.fillStyle = 'rgba(148, 163, 184, 0.18)';
      for (let b = 0; b < numBars; b++) {
        ctx.fillRect(b * step, bottomY - 2, barWidth, 2);
      }
      return;
    }

    const nPeaks = allPeaks.length;
    // Klibin kendi zaman sınırlarına [startSec, endSec] karşılık gelen tam kayan noktalı indeks aralığı
    const clipStartIdxFloat = Math.max(0, Math.min(nPeaks - 0.001, (startSec / totalDur) * nPeaks));
    const clipEndIdxFloat = Math.max(clipStartIdxFloat + 0.001, Math.min(nPeaks, (endSec / totalDur) * nPeaks));
    const clipIdxSpan = clipEndIdxFloat - clipStartIdxFloat;

    for (let b = 0; b < numBars; b++) {
      const f0 = clipStartIdxFloat + (b / numBars) * clipIdxSpan;
      const f1 = clipStartIdxFloat + ((b + 1) / numBars) * clipIdxSpan;

      let peakVal = 0;
      let rmsVal = 0;

      if (f1 - f0 >= 1.0) {
        // Birden fazla örnek bu 2px çubuğa düşüyor (Uzak/Orta Zoom - Multi-Resolution Özetleme)
        const i0 = Math.max(0, Math.min(nPeaks - 1, Math.floor(f0)));
        const i1 = Math.max(i0, Math.min(nPeaks - 1, Math.ceil(f1) - 1));
        let maxV = 0;
        let sumSq = 0;
        let count = 0;
        for (let k = i0; k <= i1; k++) {
          const v = allPeaks[k] || 0;
          if (v > maxV) maxV = v;
          sumSq += v * v;
          count++;
        }
        const rms = count > 0 ? Math.sqrt(sumSq / count) : maxV;
        peakVal = maxV;
        rmsVal = rms;
      } else {
        // Çok yüksek Zoom (Örnekler arası alt-milisaniye doğrusal enterpolasyon - Üçgen/Sıfıra düşme hatasını %100 önler)
        const centerF = (f0 + f1) * 0.5;
        const i0 = Math.max(0, Math.min(nPeaks - 1, Math.floor(centerF)));
        const i1 = Math.min(nPeaks - 1, i0 + 1);
        const frac = Math.max(0, Math.min(1, centerF - i0));
        const v0 = allPeaks[i0] || 0;
        const v1 = allPeaks[i1] || 0;
        peakVal = v0 + (v1 - v0) * frac;
        rmsVal = peakVal * 0.82;
      }

      // Algısal seviye (0.0 .. 1.0)
      const level = Math.max(0, Math.min(1, 0.72 * peakVal + 0.28 * rmsVal));
      const x = b * step;

      // Tam sessizlik durumu (< 0.018): Sadece 1.5px taban izi çiz
      if (level < 0.018) {
        ctx.fillStyle = this.isCut ? 'rgba(244, 63, 94, 0.20)' : 'rgba(148, 163, 184, 0.22)';
        ctx.fillRect(x, bottomY - 1.5, barWidth, 1.5);
        continue;
      }

      // Ses varsa yüksekliği hesapla (En ufak fısıltı bile en az 3px görünür çubuk üretir)
      const barH = Math.max(3, Math.min(maxBarHeight, Math.round(level * maxBarHeight)));
      const topY = bottomY - barH;

      // CapCut & Premiere Pro Desibel Seviye Renklendirmesi
      let bodyColor: string;
      let capColor: string;

      if (this.isCut) {
        // Kesilen (Silinen/Retake/Sessizlik) Klipler için Koyu/Açık Mercan Tonları
        if (level >= 0.75) {
          bodyColor = 'rgba(244, 63, 94, 0.85)';
          capColor = '#fda4af';
        } else if (level >= 0.35) {
          bodyColor = 'rgba(251, 113, 133, 0.65)';
          capColor = '#fb7185';
        } else {
          bodyColor = 'rgba(253, 164, 175, 0.45)';
          capColor = '#fecdd3';
        }
      } else {
        // Aktif Konuşma Klipleri için Seviye (dBFS) Renk Paleti:
        // 1) Peak / Çok Yüksek (>= 0.82): Kırmızı / Mercan
        // 2) Yüksek Vurgu (0.60 - 0.82): Kehribar / Altın Sarısı
        // 3) Normal Konuşma (0.25 - 0.60): Zümrüt Yeşili
        // 4) Fısıltı / Nefes / Kısık Ses (0.018 - 0.25): Canlı Turkuaz / Mavi
        if (level >= 0.82) {
          bodyColor = '#ef4444'; // Peak Red
          capColor = '#fecdd3';  // Bright Rose Cap
        } else if (level >= 0.60) {
          bodyColor = '#f59e0b'; // Amber / Gold
          capColor = '#fde047';  // Bright Yellow Cap
        } else if (level >= 0.25) {
          bodyColor = '#10b981'; // CapCut Emerald Green
          capColor = '#6ee7b7';  // Mint Cap
        } else {
          bodyColor = '#06b6d4'; // Whisper Cyan / Turquoise
          capColor = '#7dd3fc';  // Sky Blue Cap
        }
      }

      // Ana çubuk gövdesi
      ctx.fillStyle = bodyColor;
      ctx.fillRect(x, topY, barWidth, barH);

      // Eğer çubuk yüksekse (>= 6px), alt/orta RMS gövdesini ve en üst 2px Peak ucunu vurgula
      if (barH >= 6) {
        ctx.fillStyle = capColor;
        ctx.fillRect(x, topY, barWidth, 2);
      }
    }
  }
}
