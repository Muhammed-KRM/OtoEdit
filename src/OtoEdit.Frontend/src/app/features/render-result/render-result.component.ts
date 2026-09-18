import { Component, OnInit, OnDestroy, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { filter, Subscription } from 'rxjs';
import { RenderService } from '../../core/services/render.service';
import { SignalrService } from '../../core/services/signalr.service';
import { RenderDurumu, RenderStatusDto } from '../../core/models/render.model';
import { NavbarComponent } from '../../shared/components/navbar/navbar.component';
import { StatusBadgeComponent } from '../../shared/components/status-badge/status-badge.component';
import { ProgressBarComponent } from '../../shared/components/progress-bar/progress-bar.component';

@Component({
  selector: 'app-render-result',
  standalone: true,
  imports: [CommonModule, RouterLink, NavbarComponent, StatusBadgeComponent, ProgressBarComponent],
  template: `
    <app-navbar></app-navbar>

    <main class="max-w-4xl mx-auto px-6 py-12">
      <!-- Durum Başlığı -->
      <div class="text-center mb-8">
        <h1 class="text-3xl font-display font-extrabold text-white tracking-tight mb-2">Video Dışa Aktarma (Render)</h1>
        <p class="text-slate-400 text-sm">FFmpeg donanım hızlandırmalı motor ile kurgulanmış nihai videonuz hazırlanıyor.</p>
      </div>

      <!-- Render Devam Ediyor Durumu -->
      <div *ngIf="isRendering()" class="glass-panel rounded-2xl p-8 border border-brand-cyan/40 shadow-glow-md text-center space-y-6 animate-fade-in">
        <div class="w-16 h-16 rounded-2xl bg-brand-blue/10 border border-brand-blue/30 flex items-center justify-center mx-auto text-brand-cyan">
          <svg class="w-8 h-8 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
        </div>

        <div>
          <h3 class="text-lg font-bold text-white mb-1">Videonuz İşleniyor...</h3>
          <p class="text-xs text-slate-400">Tüm kesimler, altyazılar ve görseller videoya kalıcı olarak işleniyor.</p>
        </div>

        <app-progress-bar [percentage]="renderPercentage()" label="Render İlerlemesi"></app-progress-bar>
      </div>

      <!-- Render Tamamlandı Durumu -->
      <div *ngIf="isCompleted()" class="space-y-6 animate-fade-in">
        <!-- Başarı Banner -->
        <div class="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-between">
          <div class="flex items-center gap-3">
            <div class="w-9 h-9 rounded-lg bg-emerald-500/20 text-emerald-400 flex items-center justify-center font-bold">
              ✓
            </div>
            <div>
              <h4 class="text-sm font-bold text-white">Render Başarıyla Tamamlandı!</h4>
              <p class="text-xs text-slate-400">Videonuz indirilmeye ve paylaşılmaya hazır.</p>
            </div>
          </div>

          <a 
            *ngIf="downloadUrl()"
            [href]="downloadUrl()"
            download="otoedit_render.mp4"
            target="_blank"
            class="px-5 py-2.5 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-600 hover:to-teal-700 text-white font-bold text-xs shadow-glow-sm hover:shadow-glow-md transition-all active:scale-95 flex items-center gap-2">
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            Nihai Videoyu İndir
          </a>
        </div>

        <!-- Video Player Önizleme -->
        <div class="relative bg-black rounded-2xl overflow-hidden shadow-2xl border border-slate-800 flex items-center justify-center min-h-[380px] max-h-[540px]">
          <video 
            *ngIf="downloadUrl()"
            [src]="downloadUrl()"
            class="w-full h-full object-contain max-h-[520px]"
            controls
            autoplay>
          </video>
        </div>

        <!-- Eylemler -->
        <div class="flex items-center justify-between pt-4">
          <a [routerLink]="['/project', projectId, 'editor']" class="text-xs text-slate-400 hover:text-white flex items-center gap-1 transition-colors">
            ← Editöre Geri Dön
          </a>

          <a [routerLink]="['/']" class="text-xs text-brand-cyan hover:underline">
            Tüm Projelerime Git →
          </a>
        </div>
      </div>

      <!-- Hata Durumu -->
      <div *ngIf="isFailed()" class="glass-panel rounded-2xl p-8 border border-rose-500/40 text-center space-y-4">
        <div class="w-16 h-16 rounded-2xl bg-rose-500/10 border border-rose-500/30 flex items-center justify-center mx-auto text-rose-400 text-2xl font-bold">
          ✕
        </div>
        <h3 class="text-lg font-bold text-white">Render Sırasında Hata Oluştu</h3>
        <p class="text-xs text-rose-300 max-w-md mx-auto">{{ renderStatus()?.hataMesaji || 'Bilinmeyen bir hata nedeniyle işlem tamamlanamadı.' }}</p>
        <button (click)="retryRender()" class="px-5 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-white text-xs font-semibold">
          Yeniden Dene
        </button>
      </div>
    </main>
  `
})
export class RenderResultComponent implements OnInit, OnDestroy {
  private route = inject(ActivatedRoute);
  private renderService = inject(RenderService);
  private signalr = inject(SignalrService);

  projectId = '';
  renderJobId = '';

  readonly renderStatus = signal<RenderStatusDto | null>(null);
  readonly renderPercentage = signal<number>(20);
  readonly downloadUrl = signal<string>('');

  private sub = new Subscription();

  ngOnInit(): void {
    this.projectId = this.route.snapshot.paramMap.get('id') || '';
    this.renderJobId = this.route.snapshot.paramMap.get('renderJobId') || '';

    if (this.projectId && this.renderJobId) {
      this.checkStatus();
      this.setupSignalR();
    }
  }

  ngOnDestroy(): void {
    if (this.projectId) {
      this.signalr.leaveProjectGroup(this.projectId);
    }
    this.sub.unsubscribe();
  }

  private checkStatus(): void {
    this.renderService.getRenderStatus(this.projectId, this.renderJobId).subscribe({
      next: (status) => {
        this.renderStatus.set(status);
        if (status.durum === RenderDurumu.Tamamlandi) {
          this.fetchDownloadUrl();
        }
      },
      error: (err) => console.error('Render durumu okunamadı:', err)
    });
  }

  private fetchDownloadUrl(): void {
    this.renderService.getDownloadUrl(this.projectId, this.renderJobId).subscribe({
      next: (res) => this.downloadUrl.set(res.downloadUrl),
      error: (err) => console.error('İndirme URL alınamadı:', err)
    });
  }

  private setupSignalR(): void {
    this.signalr.joinProjectGroup(this.projectId);

    // Canlı render tamamlanma bildirimi
    this.sub.add(
      this.signalr.renderCompleted$
        .pipe(filter(e => e.renderJobId === this.renderJobId))
        .subscribe((e) => {
          this.renderPercentage.set(100);
          this.checkStatus();
        })
    );
  }

  isRendering(): boolean {
    const s = this.renderStatus()?.durum;
    return s === RenderDurumu.Kuyrukta || s === RenderDurumu.RenderEdiliyor;
  }

  isCompleted(): boolean {
    return this.renderStatus()?.durum === RenderDurumu.Tamamlandi;
  }

  isFailed(): boolean {
    return this.renderStatus()?.durum === RenderDurumu.Hata;
  }

  retryRender(): void {
    this.renderService.requestRender(this.projectId).subscribe({
      next: (res) => {
        this.renderJobId = res.renderJobId;
        this.renderStatus.set(res);
        this.renderPercentage.set(10);
      }
    });
  }
}
