import { Component, OnInit, OnDestroy, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { filter, Subscription } from 'rxjs';
import { HttpEventType } from '@angular/common/http';
import { ProjectService } from '../../core/services/project.service';
import { VideoService } from '../../core/services/video.service';
import { TemplateService } from '../../core/services/template.service';
import { SignalrService } from '../../core/services/signalr.service';
import { ProjectDetailDto, ProjectDurumu, VideoFormati } from '../../core/models/project.model';
import { TemplateDto } from '../../core/models/template.model';
import { NavbarComponent } from '../../shared/components/navbar/navbar.component';
import { StatusBadgeComponent } from '../../shared/components/status-badge/status-badge.component';
import { ProgressBarComponent } from '../../shared/components/progress-bar/progress-bar.component';

@Component({
  selector: 'app-project-detail',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule, NavbarComponent, StatusBadgeComponent, ProgressBarComponent],
  template: `
    <app-navbar [projectTitle]="project()?.ad"></app-navbar>

    <main class="max-w-6xl mx-auto px-6 py-8" *ngIf="project()">
      <!-- Header -->
      <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
        <div>
          <div class="flex items-center gap-3 mb-2">
            <h1 class="text-3xl font-display font-extrabold text-white tracking-tight">{{ project()?.ad }}</h1>
            <app-status-badge [status]="project()!.durum"></app-status-badge>
          </div>
          <p class="text-slate-400 text-sm">{{ project()?.aciklama || 'Açıklama girilmedi.' }}</p>
        </div>

        <div class="flex items-center gap-3">
          <!-- Editöre Git Butonu (Analiz tamamlandıysa veya EDL varsa aktif) -->
          <button 
            *ngIf="canGoToEditor()"
            (click)="goToEditor()"
            class="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-600 hover:to-teal-700 text-white font-bold text-sm shadow-glow-sm hover:shadow-glow-md transition-all active:scale-95 animate-pulse-subtle">
            <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
            </svg>
            Editör & Timeline'a Git →
          </button>
        </div>
      </div>

      <!-- Live Analysis Progress (SignalR) -->
      <div *ngIf="isAnalyzing()" class="mb-8 p-6 rounded-2xl glass-panel border border-brand-cyan/30 shadow-glow-sm animate-fade-in">
        <h3 class="text-base font-bold text-white mb-2 flex items-center gap-2">
          <span class="w-2.5 h-2.5 rounded-full bg-brand-cyan animate-ping"></span>
          Yapay Zeka Video Analiz Hattı Çalışıyor
        </h3>
        <p class="text-xs text-slate-400 mb-4">Whisper transkripsiyon, jump-cut sessizlik tespiti, el hareketleri ve yüz takibi yürütülüyor...</p>
        
        <app-progress-bar 
          [percentage]="analysisPercentage()" 
          [label]="analysisStageMessage()">
        </app-progress-bar>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <!-- Sol Panel: Video Yükleme Alanı -->
        <div class="lg:col-span-2 space-y-6">
          <div class="glass-panel rounded-2xl p-6 border border-slate-800">
            <h2 class="text-lg font-bold text-white mb-4 flex items-center gap-2">
              <svg class="w-5 h-5 text-brand-cyan" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
              Kaynak Video
            </h2>

            <!-- Video Yüklü Değilse Drag & Drop -->
            <div 
              *ngIf="!project()?.hasVideo && !uploading()"
              (dragover)="onDragOver($event)"
              (dragleave)="onDragLeave($event)"
              (drop)="onFileDrop($event)"
              [ngClass]="isDragging ? 'border-brand-blue bg-brand-blue/10 scale-[1.01]' : 'border-slate-700 hover:border-slate-500 bg-dark-800/40'"
              class="border-2 border-dashed rounded-2xl p-12 text-center cursor-pointer transition-all duration-200">
              
              <input type="file" #fileInput (change)="onFileSelected($event)" accept="video/mp4,video/quicktime,video/x-matroska" class="hidden" />
              
              <div class="w-16 h-16 rounded-2xl bg-brand-indigo/10 border border-brand-indigo/30 flex items-center justify-center mx-auto mb-4 text-brand-cyan">
                <svg class="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>

              <h3 class="text-base font-bold text-white mb-1">Ham Videoyu Buraya Sürükleyin</h3>
              <p class="text-xs text-slate-400 mb-4">MP4, MOV veya MKV (Azami 2 GB)</p>
              
              <button 
                type="button"
                (click)="fileInput.click()"
                class="px-5 py-2.5 rounded-xl bg-brand-blue hover:bg-blue-600 text-white font-medium text-xs transition-all shadow-glow-sm">
                Dosya Seç
              </button>
            </div>

            <!-- Uploading State -->
            <div *ngIf="uploading()" class="p-8 rounded-2xl bg-dark-800/60 border border-slate-700 text-center">
              <h4 class="text-sm font-semibold text-white mb-2">Video MinIO Bulut Depolamaya Yükleniyor...</h4>
              <app-progress-bar [percentage]="uploadPercentage()" label="Yükleme İlerlemesi"></app-progress-bar>
            </div>

            <!-- Video Yüklü İse Bilgi Kartı -->
            <div *ngIf="project()?.hasVideo && !uploading()" class="p-5 rounded-xl bg-dark-800 border border-slate-700/80 flex items-center justify-between">
              <div class="flex items-center gap-3">
                <div class="w-10 h-10 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
                  <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                  </svg>
                </div>
                <div>
                  <h4 class="text-sm font-bold text-white">Video Başarıyla Yüklendi</h4>
                  <p class="text-xs text-slate-400">Analiz tamamlandı ve EDL karar listesi oluşturuldu.</p>
                </div>
              </div>

              <button 
                (click)="reUpload(fileInput)" 
                class="text-xs text-slate-400 hover:text-white px-3 py-1.5 rounded-lg border border-slate-700 hover:bg-slate-700 transition-colors">
                Videoyu Değiştir
              </button>
              <input type="file" #fileInput (change)="onFileSelected($event)" accept="video/mp4,video/quicktime,video/x-matroska" class="hidden" />
            </div>
          </div>

          <!-- Format ve Kadraj Ayarı -->
          <div class="glass-panel rounded-2xl p-6 border border-slate-800">
            <h2 class="text-lg font-bold text-white mb-4">Çıktı Formatı</h2>
            <div class="grid grid-cols-3 gap-4">
              <button 
                type="button"
                (click)="updateFormat(VideoFormati.Yatay_16_9)"
                [ngClass]="project()?.videoFormati === VideoFormati.Yatay_16_9 ? 'border-brand-blue bg-brand-blue/10 text-brand-cyan shadow-glow-sm' : 'border-slate-800 bg-dark-800 text-slate-400 hover:border-slate-700'"
                class="p-4 rounded-xl border flex flex-col items-center gap-2 transition-all">
                <div class="w-10 h-6 border-2 border-current rounded-sm"></div>
                <span class="text-xs font-bold">16:9 Yatay</span>
                <span class="text-[10px] text-slate-500">YouTube / TV</span>
              </button>

              <button 
                type="button"
                (click)="updateFormat(VideoFormati.Dikey_9_16)"
                [ngClass]="project()?.videoFormati === VideoFormati.Dikey_9_16 ? 'border-brand-blue bg-brand-blue/10 text-brand-cyan shadow-glow-sm' : 'border-slate-800 bg-dark-800 text-slate-400 hover:border-slate-700'"
                class="p-4 rounded-xl border flex flex-col items-center gap-2 transition-all">
                <div class="w-6 h-10 border-2 border-current rounded-sm"></div>
                <span class="text-xs font-bold">9:16 Dikey</span>
                <span class="text-[10px] text-slate-500">Reels / Shorts</span>
              </button>

              <button 
                type="button"
                (click)="updateFormat(VideoFormati.Kare_1_1)"
                [ngClass]="project()?.videoFormati === VideoFormati.Kare_1_1 ? 'border-brand-blue bg-brand-blue/10 text-brand-cyan shadow-glow-sm' : 'border-slate-800 bg-dark-800 text-slate-400 hover:border-slate-700'"
                class="p-4 rounded-xl border flex flex-col items-center gap-2 transition-all">
                <div class="w-8 h-8 border-2 border-current rounded-sm"></div>
                <span class="text-xs font-bold">1:1 Kare</span>
                <span class="text-[10px] text-slate-500">Instagram Feed</span>
              </button>
            </div>
          </div>
        </div>

        <!-- Sağ Panel: Şablon Seçimi & Bilgiler -->
        <div class="space-y-6">
          <div class="glass-panel rounded-2xl p-6 border border-slate-800">
            <h2 class="text-lg font-bold text-white mb-4">Kurgu Şablonu</h2>
            <p class="text-xs text-slate-400 mb-4">Otomatik alt bant, kurumsal logo ve altyazı stilleri.</p>

            <div class="space-y-3">
              <div 
                *ngFor="let tpl of templates()"
                (click)="selectTemplate(tpl.id)"
                [ngClass]="project()?.templateId === tpl.id ? 'border-brand-blue bg-brand-blue/10 shadow-glow-sm' : 'border-slate-800 bg-dark-800 hover:border-slate-700'"
                class="p-4 rounded-xl border cursor-pointer transition-all flex items-start justify-between">
                <div>
                  <h4 class="text-sm font-bold text-white">{{ tpl.ad }}</h4>
                  <p class="text-xs text-slate-400 mt-0.5">{{ tpl.aciklama || 'Standart kurumsal şablon.' }}</p>
                </div>
                <span *ngIf="project()?.templateId === tpl.id" class="w-2.5 h-2.5 rounded-full bg-brand-cyan shadow-glow-sm"></span>
              </div>
            </div>
          </div>

          <!-- Ayarlar Özeti -->
          <div class="glass-panel rounded-2xl p-6 border border-slate-800 text-xs space-y-3">
            <h3 class="font-bold text-white uppercase tracking-wider text-[11px]">Pipeline Özellikleri</h3>
            <div class="flex justify-between items-center text-slate-300">
              <span>El Hareketi Komutları:</span>
              <span class="font-semibold text-emerald-400">{{ project()?.gestureCommandsEnabled ? 'Aktif' : 'Pasif' }}</span>
            </div>
            <div class="flex justify-between items-center text-slate-300">
              <span>Ses İyileştirme (Denoise):</span>
              <span class="font-semibold text-emerald-400">{{ project()?.audioEnhancementEnabled ? 'Aktif' : 'Pasif' }}</span>
            </div>
          </div>
        </div>
      </div>
    </main>
  `
})
export class ProjectDetailComponent implements OnInit, OnDestroy {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private projectService = inject(ProjectService);
  private videoService = inject(VideoService);
  private templateService = inject(TemplateService);
  private signalr = inject(SignalrService);

  readonly project = signal<ProjectDetailDto | null>(null);
  readonly templates = signal<TemplateDto[]>([]);
  readonly uploading = signal<boolean>(false);
  readonly uploadPercentage = signal<number>(0);
  readonly analysisPercentage = signal<number>(0);
  readonly analysisStageMessage = signal<string>('Analiz başlıyor...');
  readonly isAnalyzing = signal<boolean>(false);
  readonly VideoFormati = VideoFormati;

  isDragging = false;
  private sub = new Subscription();

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.loadProject(id);
      this.loadTemplates();
      this.setupSignalR(id);
    }
  }

  ngOnDestroy(): void {
    const id = this.project()?.id;
    if (id) {
      this.signalr.leaveProjectGroup(id);
    }
    this.sub.unsubscribe();
  }

  private loadProject(id: string): void {
    this.projectService.getById(id).subscribe({
      next: (p) => {
        this.project.set(p);
        if (p.durum === ProjectDurumu.AnalizEdiliyor) {
          this.isAnalyzing.set(true);
        }
      },
      error: (err) => console.error('Proje detayı yüklenemedi:', err)
    });
  }

  private loadTemplates(): void {
    this.templateService.getAll().subscribe({
      next: (list) => this.templates.set(list),
      error: (err) => console.error('Şablonlar yüklenemedi:', err)
    });
  }

  private setupSignalR(projectId: string): void {
    this.signalr.joinProjectGroup(projectId);

    // Canlı Analiz İlerlemesi
    this.sub.add(
      this.signalr.analysisCompleted$
        .pipe(filter(e => e.projectId === projectId))
        .subscribe(() => {
          this.isAnalyzing.set(false);
          this.analysisPercentage.set(100);
          this.loadProject(projectId);
        })
    );

    // İlerleme yüzdesi güncellemesi
    // SignalR'dan currentAnalysisProgress değiştiğinde
    // Angular effect or template direct binding handles it
  }

  canGoToEditor(): boolean {
    const p = this.project();
    if (!p) return false;
    return p.hasEdl || p.durum === ProjectDurumu.AnalizTamamlandi || p.durum === ProjectDurumu.RenderEdiliyor || p.durum === ProjectDurumu.Tamamlandi;
  }

  goToEditor(): void {
    const id = this.project()?.id;
    if (id) {
      this.router.navigate(['/project', id, 'editor']);
    }
  }

  onDragOver(e: DragEvent): void {
    e.preventDefault();
    this.isDragging = true;
  }

  onDragLeave(e: DragEvent): void {
    e.preventDefault();
    this.isDragging = false;
  }

  onFileDrop(e: DragEvent): void {
    e.preventDefault();
    this.isDragging = false;
    if (e.dataTransfer?.files.length) {
      this.uploadFile(e.dataTransfer.files[0]);
    }
  }

  onFileSelected(e: Event): void {
    const input = e.target as HTMLInputElement;
    if (input.files?.length) {
      this.uploadFile(input.files[0]);
    }
  }

  reUpload(input: HTMLInputElement): void {
    input.click();
  }

  private uploadFile(file: File): void {
    const p = this.project();
    if (!p) return;

    this.uploading.set(true);
    this.uploadPercentage.set(0);

    this.videoService.uploadVideo(p.id, file).subscribe({
      next: (event) => {
        if (event.type === HttpEventType.UploadProgress && event.total) {
          this.uploadPercentage.set(Math.round((100 * event.loaded) / event.total));
        } else if (event.type === HttpEventType.Response) {
          this.uploading.set(false);
          this.isAnalyzing.set(true);
          this.loadProject(p.id);
        }
      },
      error: (err) => {
        this.uploading.set(false);
        alert('Video yüklenirken hata oluştu: ' + (err.error?.detail || err.message));
      }
    });
  }

  updateFormat(format: VideoFormati): void {
    const p = this.project();
    if (!p) return;

    this.projectService.update(p.id, {
      ad: p.ad,
      videoFormati: format
    }).subscribe({
      next: (updated) => this.project.set(updated),
      error: (err) => alert('Format güncellenemedi: ' + err.message)
    });
  }

  selectTemplate(templateId: string): void {
    const p = this.project();
    if (!p) return;

    this.projectService.update(p.id, {
      ad: p.ad,
      templateId
    }).subscribe({
      next: (updated) => this.project.set(updated),
      error: (err) => alert('Şablon güncellenemedi: ' + err.message)
    });
  }
}
