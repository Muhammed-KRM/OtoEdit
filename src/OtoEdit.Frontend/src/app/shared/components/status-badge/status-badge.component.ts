import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ProjectDurumu } from '../../../core/models/project.model';
import { RenderDurumu } from '../../../core/models/render.model';

@Component({
  selector: 'app-status-badge',
  standalone: true,
  imports: [CommonModule],
  template: `
    <span [ngClass]="badgeClass" class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium transition-all">
      <span [ngClass]="dotClass" class="w-1.5 h-1.5 rounded-full animate-pulse"></span>
      {{ label }}
    </span>
  `
})
export class StatusBadgeComponent {
  @Input() status: ProjectDurumu | RenderDurumu | string = '';
  @Input() isRender = false;

  get label(): string {
    if (this.isRender) {
      switch (this.status) {
        case RenderDurumu.Kuyrukta: return 'Kuyrukta';
        case RenderDurumu.RenderEdiliyor: return 'Render Ediliyor';
        case RenderDurumu.Tamamlandi: return 'Tamamlandı';
        case RenderDurumu.Hata: return 'Hata';
        default: return 'Bilinmiyor';
      }
    }

    switch (this.status) {
      case ProjectDurumu.Taslak: return 'Taslak';
      case ProjectDurumu.VideoYuklendi: return 'Video Yüklendi';
      case ProjectDurumu.AnalizEdiliyor: return 'Analiz Ediliyor';
      case ProjectDurumu.AnalizTamamlandi: return 'Analiz Hazır';
      case ProjectDurumu.RenderEdiliyor: return 'Render Ediliyor';
      case ProjectDurumu.Tamamlandi: return 'Tamamlandı';
      case ProjectDurumu.Hata: return 'Hata';
      default: return 'Bilinmiyor';
    }
  }

  get badgeClass(): string {
    if (this.status === ProjectDurumu.Tamamlandi || (this.isRender && this.status === RenderDurumu.Tamamlandi)) {
      return 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20';
    }
    if (this.status === ProjectDurumu.AnalizEdiliyor || this.status === ProjectDurumu.RenderEdiliyor) {
      return 'bg-blue-500/10 text-blue-400 border border-blue-500/20';
    }
    if (this.status === ProjectDurumu.AnalizTamamlandi) {
      return 'bg-purple-500/10 text-purple-400 border border-purple-500/20';
    }
    if (this.status === ProjectDurumu.Hata || (this.isRender && this.status === RenderDurumu.Hata)) {
      return 'bg-rose-500/10 text-rose-400 border border-rose-500/20';
    }
    return 'bg-slate-500/10 text-slate-400 border border-slate-500/20';
  }

  get dotClass(): string {
    if (this.status === ProjectDurumu.Tamamlandi || (this.isRender && this.status === RenderDurumu.Tamamlandi)) {
      return 'bg-emerald-400';
    }
    if (this.status === ProjectDurumu.AnalizEdiliyor || this.status === ProjectDurumu.RenderEdiliyor) {
      return 'bg-blue-400';
    }
    if (this.status === ProjectDurumu.AnalizTamamlandi) {
      return 'bg-purple-400';
    }
    if (this.status === ProjectDurumu.Hata || (this.isRender && this.status === RenderDurumu.Hata)) {
      return 'bg-rose-400';
    }
    return 'bg-slate-400';
  }
}
