import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { ProjectService } from '../../core/services/project.service';
import { ProjectCreateDto, ProjectListDto, VideoFormati } from '../../core/models/project.model';
import { NavbarComponent } from '../../shared/components/navbar/navbar.component';
import { StatusBadgeComponent } from '../../shared/components/status-badge/status-badge.component';

@Component({
  selector: 'app-project-list',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule, NavbarComponent, StatusBadgeComponent],
  template: `
    <app-navbar></app-navbar>

    <main class="max-w-7xl mx-auto px-6 py-8">
      <!-- Header Banner -->
      <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
        <div>
          <h1 class="text-3xl font-display font-extrabold text-white tracking-tight">Projelerim</h1>
          <p class="text-slate-400 text-sm mt-1">Yapay zeka ile düzenlenen videolarınız ve kurgu projeleriniz.</p>
        </div>

        <button 
          (click)="showCreateModal.set(true)"
          class="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-brand-blue to-brand-indigo hover:from-blue-600 hover:to-indigo-600 text-white font-medium text-sm shadow-glow-sm hover:shadow-glow-md transition-all active:scale-95">
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M12 4v16m8-8H4" />
          </svg>
          Yeni Proje Oluştur
        </button>
      </div>

      <!-- Loading State -->
      <div *ngIf="loading()" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 animate-pulse">
        <div *ngFor="let i of [1,2,3]" class="h-48 rounded-2xl bg-slate-800/40 border border-slate-700/30"></div>
      </div>

      <!-- Empty State -->
      <div *ngIf="!loading() && projects().length === 0" class="text-center py-20 glass-panel rounded-2xl border border-slate-800/60 p-8">
        <div class="w-16 h-16 rounded-2xl bg-brand-indigo/10 border border-brand-indigo/30 flex items-center justify-center mx-auto mb-4 text-brand-cyan">
          <svg class="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
          </svg>
        </div>
        <h3 class="text-lg font-bold text-white mb-2">Henüz Bir Projeniz Yok</h3>
        <p class="text-slate-400 text-sm max-w-md mx-auto mb-6">Ham videonuzu yükleyip yapay zeka ile otomatik kurgulamak için ilk projenizi hemen oluşturun.</p>
        <button 
          (click)="showCreateModal.set(true)"
          class="px-5 py-2.5 rounded-xl bg-brand-blue hover:bg-blue-600 text-white font-medium text-sm transition-all shadow-glow-sm">
          İlk Projeyi Başlat
        </button>
      </div>

      <!-- Projects Grid -->
      <div *ngIf="!loading() && projects().length > 0" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <div 
          *ngFor="let p of projects()"
          (click)="navigateToProject(p.id)"
          class="glass-panel glass-panel-hover rounded-2xl p-6 cursor-pointer relative group flex flex-col justify-between">
          
          <div>
            <div class="flex items-start justify-between gap-3 mb-3">
              <span class="px-2.5 py-1 rounded-md text-xs font-semibold bg-dark-700 text-slate-300 border border-slate-600/40">
                {{ formatName(p.videoFormati) }}
              </span>
              <app-status-badge [status]="p.durum"></app-status-badge>
            </div>

            <h3 class="text-lg font-bold text-white group-hover:text-brand-cyan transition-colors mb-1 line-clamp-1">
              {{ p.ad }}
            </h3>
            <p class="text-slate-400 text-xs line-clamp-2 mb-4">
              {{ p.aciklama || 'Açıklama belirtilmedi.' }}
            </p>
          </div>

          <div class="pt-4 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-500">
            <span>{{ p.olusturulmaTarihi | date:'dd.MM.yyyy HH:mm' }}</span>
            <div class="flex items-center gap-2">
              <button 
                (click)="deleteProject($event, p.id)"
                title="Projeyi Sil"
                class="p-1.5 rounded-lg text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 transition-colors">
                <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
              <span class="text-brand-cyan group-hover:translate-x-1 transition-transform inline-flex items-center font-medium">
                Aç →
              </span>
            </div>
          </div>
        </div>
      </div>
    </main>

    <!-- Create Project Modal -->
    <div *ngIf="showCreateModal()" class="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
      <div class="glass-panel w-full max-w-lg rounded-2xl p-6 border border-slate-700/80 shadow-2xl animate-fade-in">
        <div class="flex items-center justify-between mb-6">
          <h2 class="text-xl font-bold text-white">Yeni Kurgu Projesi</h2>
          <button (click)="showCreateModal.set(false)" class="text-slate-400 hover:text-white p-1 rounded-lg">
            <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <form (ngSubmit)="submitCreate()">
          <div class="space-y-4">
            <div>
              <label class="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">Proje Adı *</label>
              <input 
                type="text" 
                [(ngModel)]="newProject.ad" 
                name="ad"
                required
                placeholder="Örn: Psikiyatri Dersi - Tevekkül Kurgusu"
                class="w-full px-4 py-2.5 rounded-xl bg-dark-800 border border-slate-700 text-white placeholder-slate-500 focus:outline-none focus:border-brand-blue focus:ring-1 focus:ring-brand-blue text-sm transition-all" />
            </div>

            <div>
              <label class="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">Açıklama</label>
              <textarea 
                [(ngModel)]="newProject.aciklama" 
                name="aciklama"
                rows="3"
                placeholder="Proje hakkında notlar..."
                class="w-full px-4 py-2 rounded-xl bg-dark-800 border border-slate-700 text-white placeholder-slate-500 focus:outline-none focus:border-brand-blue focus:ring-1 focus:ring-brand-blue text-sm transition-all"></textarea>
            </div>

            <div>
              <label class="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">Hedef Video Formatı</label>
              <div class="grid grid-cols-3 gap-3">
                <button 
                  type="button"
                  (click)="newProject.videoFormati = VideoFormati.Yatay_16_9"
                  [ngClass]="newProject.videoFormati === VideoFormati.Yatay_16_9 ? 'border-brand-blue bg-brand-blue/10 text-brand-cyan' : 'border-slate-700 bg-dark-800 text-slate-400'"
                  class="p-3 rounded-xl border flex flex-col items-center gap-1.5 text-xs font-medium transition-all">
                  <div class="w-8 h-5 border-2 border-current rounded-sm"></div>
                  16:9 Yatay
                </button>
                <button 
                  type="button"
                  (click)="newProject.videoFormati = VideoFormati.Dikey_9_16"
                  [ngClass]="newProject.videoFormati === VideoFormati.Dikey_9_16 ? 'border-brand-blue bg-brand-blue/10 text-brand-cyan' : 'border-slate-700 bg-dark-800 text-slate-400'"
                  class="p-3 rounded-xl border flex flex-col items-center gap-1.5 text-xs font-medium transition-all">
                  <div class="w-5 h-8 border-2 border-current rounded-sm"></div>
                  9:16 Dikey (Reels)
                </button>
                <button 
                  type="button"
                  (click)="newProject.videoFormati = VideoFormati.Kare_1_1"
                  [ngClass]="newProject.videoFormati === VideoFormati.Kare_1_1 ? 'border-brand-blue bg-brand-blue/10 text-brand-cyan' : 'border-slate-700 bg-dark-800 text-slate-400'"
                  class="p-3 rounded-xl border flex flex-col items-center gap-1.5 text-xs font-medium transition-all">
                  <div class="w-6 h-6 border-2 border-current rounded-sm"></div>
                  1:1 Kare
                </button>
              </div>
            </div>

            <!-- Toggles -->
            <div class="pt-2 space-y-3">
              <label class="flex items-center gap-3 cursor-pointer">
                <input type="checkbox" [(ngModel)]="newProject.gestureCommandsEnabled" name="gesture" class="w-4 h-4 rounded text-brand-blue bg-dark-800 border-slate-700 focus:ring-brand-blue">
                <span class="text-sm text-slate-300">El Hareketi Komutlarını Aktif Et (Thumbs Down = Cut)</span>
              </label>
              <label class="flex items-center gap-3 cursor-pointer">
                <input type="checkbox" [(ngModel)]="newProject.audioEnhancementEnabled" name="audio" class="w-4 h-4 rounded text-brand-blue bg-dark-800 border-slate-700 focus:ring-brand-blue">
                <span class="text-sm text-slate-300">Otomatik Ses İyileştirme (Gürültü ve Yankı Temizleme)</span>
              </label>
            </div>
          </div>

          <div class="flex items-center justify-end gap-3 mt-8">
            <button 
              type="button"
              (click)="showCreateModal.set(false)"
              class="px-4 py-2.5 rounded-xl text-slate-400 hover:text-white text-sm font-medium transition-colors">
              İptal
            </button>
            <button 
              type="submit"
              [disabled]="!newProject.ad.trim() || creating()"
              class="px-6 py-2.5 rounded-xl bg-gradient-to-r from-brand-blue to-brand-indigo hover:from-blue-600 hover:to-indigo-600 text-white font-medium text-sm shadow-glow-sm disabled:opacity-50 disabled:cursor-not-allowed transition-all">
              {{ creating() ? 'Oluşturuluyor...' : 'Projeyi Başlat' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  `
})
export class ProjectListComponent implements OnInit {
  private projectService = inject(ProjectService);
  private router = inject(Router);

  readonly projects = signal<ProjectListDto[]>([]);
  readonly loading = signal<boolean>(true);
  readonly showCreateModal = signal<boolean>(false);
  readonly creating = signal<boolean>(false);
  readonly VideoFormati = VideoFormati;

  newProject: ProjectCreateDto & { ad: string } = {
    ad: '',
    aciklama: '',
    videoFormati: VideoFormati.Yatay_16_9,
    gestureCommandsEnabled: true,
    audioEnhancementEnabled: true
  };

  ngOnInit(): void {
    this.loadProjects();
  }

  loadProjects(): void {
    this.loading.set(true);
    this.projectService.getAll().subscribe({
      next: (list) => {
        this.projects.set(list);
        this.loading.set(false);
      },
      error: (err) => {
        console.error('Projeler yüklenemedi:', err);
        this.loading.set(false);
      }
    });
  }

  formatName(format: VideoFormati): string {
    switch (format) {
      case VideoFormati.Yatay_16_9: return '16:9 Yatay';
      case VideoFormati.Dikey_9_16: return '9:16 Reels';
      case VideoFormati.Kare_1_1: return '1:1 Kare';
      default: return '16:9';
    }
  }

  navigateToProject(id: string): void {
    this.router.navigate(['/project', id]);
  }

  deleteProject(e: Event, id: string): void {
    e.stopPropagation();
    if (confirm('Bu projeyi ve ilişkili tüm kurguları silmek istediğinizden emin misiniz?')) {
      this.projectService.delete(id).subscribe({
        next: () => {
          this.projects.update(list => list.filter(p => p.id !== id));
        },
        error: (err) => alert('Proje silinemedi: ' + err.message)
      });
    }
  }

  submitCreate(): void {
    if (!this.newProject.ad.trim()) return;
    this.creating.set(true);

    this.projectService.create(this.newProject).subscribe({
      next: (res) => {
        this.creating.set(false);
        this.showCreateModal.set(false);
        this.router.navigate(['/project', res.id]);
      },
      error: (err) => {
        this.creating.set(false);
        alert('Proje oluşturulurken hata oluştu: ' + (err.error?.detail || err.message));
      }
    });
  }
}
