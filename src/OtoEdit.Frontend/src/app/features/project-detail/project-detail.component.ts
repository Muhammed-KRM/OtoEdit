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
          <!-- Editöre Git Butonu (Analiz tamamlandıysa veya video yüklüyse her zaman erişilebilir) -->
          <button 
            *ngIf="canGoToEditor()"
            (click)="goToEditor()"
            class="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-600 hover:to-teal-700 text-white font-bold text-sm shadow-glow-sm hover:shadow-glow-md transition-all active:scale-95">
            <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
            </svg>
            Editör & Timeline'a Git →
          </button>
        </div>
      </div>

      <!-- Live Analysis Progress (SignalR) -->
      <div *ngIf="isAnalyzing()" class="mb-8 p-6 rounded-2xl glass-panel border border-brand-cyan/30 shadow-glow-sm animate-fade-in">
        <div class="flex items-center justify-between gap-4 mb-2">
          <h3 class="text-base font-bold text-white flex items-center gap-2">
            <span class="w-2.5 h-2.5 rounded-full bg-brand-cyan animate-ping"></span>
            Yapay Zeka Video Analiz Hattı Çalışıyor
          </h3>
          <button
            type="button"
            (click)="goToEditor()"
            class="text-xs px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-brand-cyan border border-brand-cyan/30 font-semibold transition-all">
            Beklemeden Editöre Geç →
          </button>
        </div>
        <p class="text-xs text-slate-400 mb-4">Seçtiğiniz akıllı kurgu adımları yürütülüyor...</p>
        
        <app-progress-bar 
          [percentage]="analysisPercentage()" 
          [label]="analysisStageMessage()">
        </app-progress-bar>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <!-- Sol Panel: Hızlı Modlar, Pipeline Tikleri & Video Yükleme Alanı -->
        <div class="lg:col-span-2 space-y-6">
          <!-- 1. HIZLI KURGU SENARYOSU (4 PRESET MODU) + BİRLEŞTİRİLMİŞ TİKLER -->
          <div class="glass-panel rounded-2xl p-6 border border-slate-800 space-y-4">
            <div class="flex flex-wrap items-center justify-between gap-2">
              <div>
                <h3 class="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
                  <span class="w-2 h-2 rounded-full bg-brand-cyan shadow-glow-sm"></span>
                  1. Kurgu Senaryosu & Yapay Zeka Görevlerini Seçin
                </h3>
                <p class="text-xs text-slate-400 mt-0.5">Videoyu yüklemeden önce hazır bir senaryo seçin veya aşağıdaki kutucukları özelleştirin:</p>
              </div>
              <div class="flex items-center gap-2">
                <button
                  type="button"
                  (click)="applyPresetMode('direct')"
                  class="text-[11px] px-2.5 py-1 rounded-lg bg-emerald-500/15 hover:bg-emerald-500/25 text-emerald-300 border border-emerald-500/30 font-semibold transition-all">
                  ⚡ Tüm Tikleri Kaldır (Direkt Editör)
                </button>
                <button
                  type="button"
                  (click)="applyPresetMode('full')"
                  class="text-[11px] px-2.5 py-1 rounded-lg bg-brand-blue/15 hover:bg-brand-blue/25 text-brand-cyan border border-brand-blue/30 font-semibold transition-all">
                  🎬 Tümünü Seç
                </button>
              </div>
            </div>

            <!-- 4 Hazır Senaryo Kartı -->
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
              <!-- Mod 1: Direkt Editöre Geç (0 Saniye) -->
              <button
                type="button"
                (click)="applyPresetMode('direct')"
                [ngClass]="activePresetMode() === 'direct' ? 'border-emerald-500 bg-emerald-500/15 shadow-glow-sm' : 'border-slate-700/70 bg-dark-800/70 hover:border-slate-600'"
                class="p-3.5 rounded-xl border text-left transition-all flex items-start gap-3">
                <span class="text-xl leading-none mt-0.5">⚡</span>
                <div>
                  <div class="text-xs font-extrabold text-white flex items-center gap-1.5">
                    Direkt Editöre Geç
                    <span class="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-mono">0sn Bekleme</span>
                  </div>
                  <div class="text-[11px] text-slate-400 mt-0.5">Hiçbir otomatik kesim yapmadan videoyu anında Timeline'da açar.</div>
                </div>
              </button>

              <!-- Mod 2: Kesilmiş Videoyu Kurgula & Zenginleştir -->
              <button
                type="button"
                (click)="applyPresetMode('enrich')"
                [ngClass]="activePresetMode() === 'enrich' ? 'border-amber-500 bg-amber-500/15 shadow-glow-sm' : 'border-slate-700/70 bg-dark-800/70 hover:border-slate-600'"
                class="p-3.5 rounded-xl border text-left transition-all flex items-start gap-3">
                <span class="text-xl leading-none mt-0.5">✨</span>
                <div>
                  <div class="text-xs font-extrabold text-white flex items-center gap-1.5">
                    Kesilmiş Videoyu Kurgula
                    <span class="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 font-mono">Oto-Zenginleştir</span>
                  </div>
                  <div class="text-[11px] text-slate-400 mt-0.5">Videoyu kesmez; otomatik Başlık, Vurgu Yazısı, Emoji, Geçiş, SFX ve B-Roll ekler!</div>
                </div>
              </button>

              <!-- Mod 3: Sadece Otomatik Kes & Altyazı -->
              <button
                type="button"
                (click)="applyPresetMode('cut_sub')"
                [ngClass]="activePresetMode() === 'cut_sub' ? 'border-brand-blue bg-brand-blue/15 shadow-glow-sm' : 'border-slate-700/70 bg-dark-800/70 hover:border-slate-600'"
                class="p-3.5 rounded-xl border text-left transition-all flex items-start gap-3">
                <span class="text-xl leading-none mt-0.5">✂️</span>
                <div>
                  <div class="text-xs font-extrabold text-white">Sadece Kes & Altyazı Ekle</div>
                  <div class="text-[11px] text-slate-400 mt-0.5">Sessizlikleri/tekrarları temizler ve dinamik kelime altyazısı oluşturur.</div>
                </div>
              </button>

              <!-- Mod 4: Tam Otonom Yönetmen -->
              <button
                type="button"
                (click)="applyPresetMode('full')"
                [ngClass]="activePresetMode() === 'full' ? 'border-purple-500 bg-purple-500/15 shadow-glow-sm' : 'border-slate-700/70 bg-dark-800/70 hover:border-slate-600'"
                class="p-3.5 rounded-xl border text-left transition-all flex items-start gap-3">
                <span class="text-xl leading-none mt-0.5">🎬</span>
                <div>
                  <div class="text-xs font-extrabold text-white">Tam Otonom Yönetmen (Tümü)</div>
                  <div class="text-[11px] text-slate-400 mt-0.5">Jump-cut, Retake, Altyazı, B-Roll, Otonom Kurgu ve Ses temizliğini birlikte yapar.</div>
                </div>
              </button>
            </div>

            <!-- Direkt Editör Modu Bilgi Bandı -->
            <div *ngIf="isDirectEditorMode()" class="p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-xs text-emerald-200 flex items-center gap-3">
              <span class="text-lg">🚀</span>
              <div>
                <b>Direkt Editör Modu Aktif:</b> Hiçbir kutucuk seçili olmadığı için video yüklendiği anda <b>hiçbir işlem beklenmeden 0 saniyede</b> doğrudan Editör ekranına geçilecektir. İhtiyaç duyduğunuz AI özelliklerini (Altyazı, Otonom Kurgu, Kesim) daha sonra editör içinden tek tıkla çalıştırabilirsiniz.
              </div>
            </div>

            <!-- 7 Birleştirilmiş Pipeline Kutucuğu -->
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-2.5 pt-2 border-t border-slate-800/80">
              <!-- 1. Jump-Cut -->
              <label class="flex items-start gap-3 p-3 rounded-xl bg-dark-800/80 border border-slate-700/60 cursor-pointer hover:border-brand-blue/50 transition-all">
                <input type="checkbox" [(ngModel)]="autoJumpcut" class="mt-0.5 w-4 h-4 rounded text-brand-blue bg-dark-900 border-slate-600 focus:ring-brand-blue" />
                <div>
                  <div class="text-xs font-bold text-white">✂️ Otomatik Jump-Cut</div>
                  <div class="text-[11px] text-slate-400">Sessiz duraksamaları ve nefes boşluklarını keser</div>
                </div>
              </label>

              <!-- 2. Akıllı Retake -->
              <label class="flex items-start gap-3 p-3 rounded-xl bg-dark-800/80 border border-slate-700/60 cursor-pointer hover:border-brand-blue/50 transition-all">
                <input type="checkbox" [(ngModel)]="autoRetake" class="mt-0.5 w-4 h-4 rounded text-brand-blue bg-dark-900 border-slate-600 focus:ring-brand-blue" />
                <div>
                  <div class="text-xs font-bold text-white">🔁 Akıllı Hatalı Tekrar (Retake)</div>
                  <div class="text-[11px] text-slate-400">Takılmaları ve tekrar edilen cümleleri temizler</div>
                </div>
              </label>

              <!-- 3. Dinamik Altyazı -->
              <label class="flex items-start gap-3 p-3 rounded-xl bg-dark-800/80 border border-slate-700/60 cursor-pointer hover:border-brand-blue/50 transition-all">
                <input type="checkbox" [(ngModel)]="autoSubtitles" class="mt-0.5 w-4 h-4 rounded text-brand-blue bg-dark-900 border-slate-600 focus:ring-brand-blue" />
                <div>
                  <div class="text-xs font-bold text-white">💬 Dinamik Kelime Altyazısı</div>
                  <div class="text-[11px] text-slate-400">Whisper AI ile kelime bazlı senkron altyazı üretir</div>
                </div>
              </label>

              <!-- 4. Otonom Yönetmen Kurgusu (AutoDirectorComposer) -->
              <label class="flex items-start gap-3 p-3 rounded-xl bg-dark-800/80 border border-amber-500/40 cursor-pointer hover:border-amber-400 transition-all">
                <input type="checkbox" [(ngModel)]="autoDirectorEnabled" class="mt-0.5 w-4 h-4 rounded text-amber-500 bg-dark-900 border-slate-600 focus:ring-amber-500" />
                <div>
                  <div class="text-xs font-bold text-amber-300">✨ Otonom Yönetmen Kurgusu</div>
                  <div class="text-[11px] text-slate-400">Viral başlık, vurgu yazıları, hareketli emoji, geçiş ve SFX ekler</div>
                </div>
              </label>

              <!-- 5. Oto B-Roll -->
              <label class="flex items-start gap-3 p-3 rounded-xl bg-dark-800/80 border border-slate-700/60 cursor-pointer hover:border-brand-blue/50 transition-all">
                <input type="checkbox" [(ngModel)]="autoBroll" class="mt-0.5 w-4 h-4 rounded text-brand-blue bg-dark-900 border-slate-600 focus:ring-brand-blue" />
                <div>
                  <div class="text-xs font-bold text-white">🖼️ Oto Görsel / B-Roll Yerleştir</div>
                  <div class="text-[11px] text-slate-400">Önemli cümlelere telifsiz stok görsel/video ekler</div>
                </div>
              </label>

              <!-- 6. Ses İyileştirme -->
              <label class="flex items-start gap-3 p-3 rounded-xl bg-dark-800/80 border border-slate-700/60 cursor-pointer hover:border-brand-blue/50 transition-all">
                <input type="checkbox" [(ngModel)]="audioEnhancementEnabled" class="mt-0.5 w-4 h-4 rounded text-brand-blue bg-dark-900 border-slate-600 focus:ring-brand-blue" />
                <div>
                  <div class="text-xs font-bold text-white">🎙️ Stüdyo Ses İyileştirme</div>
                  <div class="text-[11px] text-slate-400">Dip gürültüsünü temizler ve ses seviyesini dengeler</div>
                </div>
              </label>

              <!-- 7. El Hareketi Komutları -->
              <label class="flex items-start gap-3 p-3 rounded-xl bg-dark-800/80 border border-slate-700/60 cursor-pointer hover:border-brand-blue/50 transition-all sm:col-span-2">
                <input type="checkbox" [(ngModel)]="gestureCommandsEnabled" class="mt-0.5 w-4 h-4 rounded text-brand-blue bg-dark-900 border-slate-600 focus:ring-brand-blue" />
                <div>
                  <div class="text-xs font-bold text-white">✋ El Hareketi Komutları (MediaPipe Gesture)</div>
                  <div class="text-[11px] text-slate-400">Kameraya başparmak aşağı (Thumbs Down) yaptığınız hatalı kısımları otomatik keser</div>
                </div>
              </label>
            </div>
          </div>

          <!-- 2. KAYNAK VİDEO YÜKLEME ALANI -->
          <div class="glass-panel rounded-2xl p-6 border border-slate-800">
            <h2 class="text-lg font-bold text-white mb-4 flex items-center gap-2">
              <svg class="w-5 h-5 text-brand-cyan" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
              2. Kaynak Videoyu Yükleyin
            </h2>

            <!-- Video Yüklü Değilse Drag & Drop -->
            <div 
              *ngIf="!project()?.hasVideo && !uploading()"
              (dragover)="onDragOver($event)"
              (dragleave)="onDragLeave($event)"
              (drop)="onFileDrop($event)"
              [ngClass]="isDragging ? 'border-brand-blue bg-brand-blue/10 scale-[1.01]' : 'border-slate-700 hover:border-slate-500 bg-dark-800/40'"
              class="border-2 border-dashed rounded-2xl p-10 text-center cursor-pointer transition-all duration-200">
              
              <input type="file" #fileInput (change)="onFileSelected($event)" accept="video/mp4,video/quicktime,video/x-matroska,video/webm" class="hidden" />
              
              <div class="w-16 h-16 rounded-2xl bg-brand-indigo/10 border border-brand-indigo/30 flex items-center justify-center mx-auto mb-4 text-brand-cyan">
                <svg class="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>

              <h3 class="text-base font-bold text-white mb-1">
                {{ isDirectEditorMode() ? 'Videoyu Sürükleyin → Anında Editörde Açılacak (0sn)' : 'Videoyu Buraya Sürükleyin veya Seçin' }}
              </h3>
              <p class="text-xs text-slate-400 mb-4">MP4, MOV, WEBM veya MKV (Azami 50 GB)</p>
              
              <button 
                type="button"
                (click)="fileInput.click()"
                class="px-5 py-2.5 rounded-xl bg-brand-blue hover:bg-blue-600 text-white font-medium text-xs transition-all shadow-glow-sm">
                Video Dosyası Seç
              </button>
            </div>

            <!-- Uploading State -->
            <div *ngIf="uploading()" class="p-8 rounded-2xl bg-dark-800/60 border border-slate-700 text-center">
              <h4 class="text-sm font-semibold text-white mb-2">Video Yükleniyor...</h4>
              <app-progress-bar [percentage]="uploadPercentage()" label="Yükleme İlerlemesi"></app-progress-bar>
            </div>

            <!-- Video Yüklü İse Bilgi Kartı -->
            <div *ngIf="project()?.hasVideo && !uploading()" class="p-5 rounded-xl bg-dark-800 border border-slate-700/80 flex flex-wrap items-center justify-between gap-3">
              <div class="flex items-center gap-3">
                <div class="w-10 h-10 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
                  <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                  </svg>
                </div>
                <div>
                  <h4 class="text-sm font-bold text-white">Video Yüklendi ve Kurguya Hazır</h4>
                  <p class="text-xs text-slate-400">İsterseniz doğrudan editöre geçebilir veya seçili kutucuklarla yeniden analiz başlatabilirsiniz.</p>
                </div>
              </div>

              <div class="flex items-center gap-2">
                <button
                  *ngIf="!isDirectEditorMode()"
                  type="button"
                  (click)="triggerReanalyzeWithSelectedFlags()"
                  class="text-xs text-amber-300 hover:text-white px-3 py-1.5 rounded-lg border border-amber-500/40 bg-amber-500/10 hover:bg-amber-500/25 transition-colors font-semibold">
                  ✨ Seçili Tiklerle Yeniden Kurgula
                </button>
                <button 
                  type="button"
                  (click)="reUpload(fileInput)" 
                  class="text-xs text-slate-400 hover:text-white px-3 py-1.5 rounded-lg border border-slate-700 hover:bg-slate-700 transition-colors">
                  Videoyu Değiştir
                </button>
              </div>
              <input type="file" #fileInput (change)="onFileSelected($event)" accept="video/mp4,video/quicktime,video/x-matroska,video/webm" class="hidden" />
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

          <!-- Aktif Seçim Özeti -->
          <div class="glass-panel rounded-2xl p-6 border border-slate-800 text-xs space-y-2.5">
            <h3 class="font-bold text-white uppercase tracking-wider text-[11px] mb-2">Seçili Kurgu Özeti</h3>
            <div class="flex justify-between items-center text-slate-300">
              <span>Senaryo Modu:</span>
              <span class="font-bold text-brand-cyan">
                {{ activePresetMode() === 'direct' ? '⚡ Direkt Editör (0sn)' :
                   activePresetMode() === 'enrich' ? '✨ Kesilmiş Videoyu Kurgula' :
                   activePresetMode() === 'cut_sub' ? '✂️ Kes & Altyazı' :
                   activePresetMode() === 'full' ? '🎬 Tam Otonom Yönetmen' : '⚙️ Özel Seçim' }}
              </span>
            </div>
            <div class="flex justify-between items-center text-slate-300">
              <span>Otomatik Jump-Cut:</span>
              <span [ngClass]="autoJumpcut ? 'text-emerald-400 font-semibold' : 'text-slate-500'">{{ autoJumpcut ? 'Aktif' : 'Kapalı' }}</span>
            </div>
            <div class="flex justify-between items-center text-slate-300">
              <span>Hatalı Tekrar (Retake):</span>
              <span [ngClass]="autoRetake ? 'text-emerald-400 font-semibold' : 'text-slate-500'">{{ autoRetake ? 'Aktif' : 'Kapalı' }}</span>
            </div>
            <div class="flex justify-between items-center text-slate-300">
              <span>Dinamik Altyazı:</span>
              <span [ngClass]="autoSubtitles ? 'text-emerald-400 font-semibold' : 'text-slate-500'">{{ autoSubtitles ? 'Aktif' : 'Kapalı' }}</span>
            </div>
            <div class="flex justify-between items-center text-slate-300">
              <span>Otonom Yönetmen (Yazı/Emoji/SFX):</span>
              <span [ngClass]="autoDirectorEnabled ? 'text-amber-400 font-semibold' : 'text-slate-500'">{{ autoDirectorEnabled ? 'Aktif' : 'Kapalı' }}</span>
            </div>
            <div class="flex justify-between items-center text-slate-300">
              <span>Stok Görsel (B-Roll):</span>
              <span [ngClass]="autoBroll ? 'text-emerald-400 font-semibold' : 'text-slate-500'">{{ autoBroll ? 'Aktif' : 'Kapalı' }}</span>
            </div>
            <div class="flex justify-between items-center text-slate-300">
              <span>Ses İyileştirme:</span>
              <span [ngClass]="audioEnhancementEnabled ? 'text-emerald-400 font-semibold' : 'text-slate-500'">{{ audioEnhancementEnabled ? 'Aktif' : 'Kapalı' }}</span>
            </div>
            <div class="flex justify-between items-center text-slate-300">
              <span>El Hareketi Komutu:</span>
              <span [ngClass]="gestureCommandsEnabled ? 'text-emerald-400 font-semibold' : 'text-slate-500'">{{ gestureCommandsEnabled ? 'Aktif' : 'Kapalı' }}</span>
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

  // Birleştirilmiş 7 Akıllı Yönetmen Tercihi
  autoJumpcut = true;
  autoRetake = true;
  autoBroll = true;
  autoSubtitles = true;
  autoDirectorEnabled = true;
  audioEnhancementEnabled = false;
  gestureCommandsEnabled = false;

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

  isDirectEditorMode(): boolean {
    return !this.autoJumpcut &&
           !this.autoRetake &&
           !this.autoBroll &&
           !this.autoSubtitles &&
           !this.autoDirectorEnabled &&
           !this.audioEnhancementEnabled &&
           !this.gestureCommandsEnabled;
  }

  activePresetMode(): 'direct' | 'enrich' | 'cut_sub' | 'full' | 'custom' {
    if (this.isDirectEditorMode()) return 'direct';
    if (!this.autoJumpcut && !this.autoRetake && this.autoSubtitles && this.autoDirectorEnabled && this.autoBroll) return 'enrich';
    if (this.autoJumpcut && this.autoRetake && this.autoSubtitles && !this.autoBroll && !this.autoDirectorEnabled) return 'cut_sub';
    if (this.autoJumpcut && this.autoRetake && this.autoSubtitles && this.autoBroll && this.autoDirectorEnabled) return 'full';
    return 'custom';
  }

  applyPresetMode(mode: 'direct' | 'enrich' | 'cut_sub' | 'full'): void {
    if (mode === 'direct') {
      this.autoJumpcut = false;
      this.autoRetake = false;
      this.autoBroll = false;
      this.autoSubtitles = false;
      this.autoDirectorEnabled = false;
      this.audioEnhancementEnabled = false;
      this.gestureCommandsEnabled = false;
    } else if (mode === 'enrich') {
      // Kesilmiş hazır videoyu bozmadan (kesmeden) üstüne yazı, hareketli emoji, geçiş, SFX ve B-Roll ekler
      this.autoJumpcut = false;
      this.autoRetake = false;
      this.autoSubtitles = true;
      this.autoDirectorEnabled = true;
      this.autoBroll = true;
      this.audioEnhancementEnabled = false;
      this.gestureCommandsEnabled = false;
    } else if (mode === 'cut_sub') {
      this.autoJumpcut = true;
      this.autoRetake = true;
      this.autoSubtitles = true;
      this.autoDirectorEnabled = false;
      this.autoBroll = false;
      this.audioEnhancementEnabled = true;
      this.gestureCommandsEnabled = false;
    } else if (mode === 'full') {
      this.autoJumpcut = true;
      this.autoRetake = true;
      this.autoSubtitles = true;
      this.autoDirectorEnabled = true;
      this.autoBroll = true;
      this.audioEnhancementEnabled = true;
      this.gestureCommandsEnabled = true;
    }
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

    this.sub.add(
      this.signalr.analysisCompleted$
        .pipe(filter(e => String(e.projectId).toLowerCase() === String(projectId).toLowerCase()))
        .subscribe(() => {
          this.isAnalyzing.set(false);
          this.analysisPercentage.set(100);
          this.loadProject(projectId);
        })
    );

    this.sub.add(
      this.signalr.analysisProgress$
        .pipe(filter(e => String(e.projectId).toLowerCase() === String(projectId).toLowerCase()))
        .subscribe((e) => {
          this.isAnalyzing.set(true);
          if (typeof e.yuzde === 'number') {
            this.analysisPercentage.set(e.yuzde);
          }
          if (e.mesaj) {
            this.analysisStageMessage.set(e.mesaj);
          } else if (e.asama) {
            this.analysisStageMessage.set(`${e.asama} aşaması yürütülüyor...`);
          }
        })
    );

    this.sub.add(
      this.signalr.pipelineError$
        .pipe(filter(e => String(e.projectId).toLowerCase() === String(projectId).toLowerCase()))
        .subscribe((err) => {
          this.isAnalyzing.set(false);
          this.analysisStageMessage.set(`Hata oluştu: ${err.hataMesaji}`);
        })
    );
  }

  canGoToEditor(): boolean {
    const p = this.project();
    if (!p) return false;
    return p.hasEdl || p.hasVideo || p.durum === ProjectDurumu.AnalizTamamlandi || p.durum === ProjectDurumu.RenderEdiliyor || p.durum === ProjectDurumu.Tamamlandi;
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

  triggerReanalyzeWithSelectedFlags(): void {
    const p = this.project();
    if (!p) return;
    this.isAnalyzing.set(true);
    this.analysisPercentage.set(5);
    this.analysisStageMessage.set('Seçili AI kurgu adımları başlatılıyor...');
    this.videoService.reanalyzeProject(p.id, {
      autoJumpcut: this.autoJumpcut,
      autoRetake: this.autoRetake,
      autoBroll: this.autoBroll,
      autoSubtitles: this.autoSubtitles,
      audioEnhancementEnabled: this.audioEnhancementEnabled,
      gestureCommandsEnabled: this.gestureCommandsEnabled,
      autoDirectorEnabled: this.autoDirectorEnabled
    }).subscribe({
      next: () => {},
      error: (err) => {
        this.isAnalyzing.set(false);
        alert('Yeniden analiz başlatılamadı: ' + (err.error?.detail || err.message));
      }
    });
  }

  private uploadFile(file: File): void {
    const p = this.project();
    if (!p) return;

    const directMode = this.isDirectEditorMode();
    this.uploading.set(true);
    this.uploadPercentage.set(0);

    this.videoService.uploadVideo(p.id, file, {
      autoJumpcut: this.autoJumpcut,
      autoRetake: this.autoRetake,
      autoBroll: this.autoBroll,
      autoSubtitles: this.autoSubtitles,
      audioEnhancementEnabled: this.audioEnhancementEnabled,
      gestureCommandsEnabled: this.gestureCommandsEnabled,
      autoDirectorEnabled: this.autoDirectorEnabled,
      directToEditor: directMode
    }).subscribe({
      next: (event) => {
        if (event.type === HttpEventType.UploadProgress && event.total) {
          this.uploadPercentage.set(Math.round((100 * event.loaded) / event.total));
        } else if (event.type === HttpEventType.Response) {
          this.uploading.set(false);
          if (directMode) {
            // Hiçbir kutucuk seçili değilse 0 saniye bekleme ile doğrudan Editöre geç!
            this.router.navigate(['/project', p.id, 'editor']);
            return;
          }
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
