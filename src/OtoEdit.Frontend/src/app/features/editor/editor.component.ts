import { Component, OnInit, OnDestroy, inject, signal, computed, ViewChild, ElementRef, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { Subscription } from 'rxjs';
import { ProjectService } from '../../core/services/project.service';
import { VideoService } from '../../core/services/video.service';
import { EdlService } from '../../core/services/edl.service';
import { ChatService } from '../../core/services/chat.service';
import { RenderService } from '../../core/services/render.service';
import { AssetService } from '../../core/services/asset.service';
import { SignalrService } from '../../core/services/signalr.service';
import { ProjectDetailDto } from '../../core/models/project.model';
import { DiagnosticsService } from '../../core/services/diagnostics.service';
import { VideoDetailDto } from '../../core/models/video.model';
import { CutItem, EdlContent, EdlDto, EdlPatchDto, OverlayItem, OverlayKeyframe, EdlTransition, EdlSfxClip, SubtitleStyleConfig, BackgroundMusicConfig, ColorGradingConfig, SuggestionItem, TranscriptSegment, TranscriptWord } from '../../core/models/edl.model';
import { ChatMessageDto, FormFieldDto } from '../../core/models/chat.model';
import { ProjectAssetDto } from '../../core/models/asset.model';
import { NavbarComponent } from '../../shared/components/navbar/navbar.component';
import { DurationPipe } from '../../shared/pipes/duration.pipe';
import { ClipWaveformDirective } from './clip-waveform.directive';
import { StudioEngineService, StudioFontOption, FontOption, TextTemplatePreset, SfxLibraryItem, StickerLibraryItem, TransitionLibraryItem } from './studio-engine.service';
import { environment } from '../../../environments/environment';

export interface ContextMenuState {
  visible: boolean;
  x: number;
  y: number;
  type: 'clip' | 'overlay' | 'timeline';
  targetClip?: any;
  targetOverlay?: OverlayItem;
  seekTime?: number;
}

@Component({
  selector: 'app-editor',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule, NavbarComponent, DurationPipe, ClipWaveformDirective],
  template: `
    <app-navbar [projectTitle]="project()?.ad"></app-navbar>

    <main class="h-[calc(100vh-65px)] flex flex-col bg-dark-950 text-slate-100 overflow-hidden select-none" (click)="closeContextMenu()">
      <!-- Üst Bar: Navigasyon, EDL Durumu, Hızlı Bilgi ve Render -->
      <header class="h-11 px-5 bg-dark-900/95 border-b border-slate-800 flex items-center justify-between shrink-0 z-20">
        <div class="flex items-center gap-4">
          <a [routerLink]="['/project', projectId]" class="text-xs text-slate-400 hover:text-white flex items-center gap-1.5 transition-colors font-medium">
            <span>←</span>
            <span>Detaya Dön</span>
          </a>
          <div class="h-4 w-px bg-slate-800"></div>
          <div class="flex items-center gap-2">
            <span class="w-2 h-2 rounded-full bg-brand-cyan shadow-glow-sm animate-pulse"></span>
            <span class="text-xs font-bold text-white tracking-wide">Canlı EDL Simülasyonu</span>
            <span class="text-[10px] px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-mono">Render Bekletmez</span>
          </div>
        </div>

        <div class="flex items-center gap-3">
          <!-- Kısayol İpuçları Butonu -->
          <div class="relative group">
            <button type="button" class="px-2.5 py-1 rounded-lg bg-dark-800 hover:bg-slate-700 text-slate-300 border border-slate-700 text-xs flex items-center gap-1.5 transition-colors">
              <span>⌨️</span>
              <span class="text-[11px] font-semibold">Kısayollar</span>
            </button>
            <!-- Popover -->
            <div class="absolute right-0 top-full mt-2 w-72 p-3 bg-dark-900/98 backdrop-blur-xl border border-slate-700 rounded-xl shadow-2xl opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-50 text-[11px] space-y-1.5">
              <div class="font-bold text-brand-cyan border-b border-slate-800 pb-1 flex items-center justify-between">
                <span>🎬 CapCut / NLE Kısayolları</span>
                <span class="text-[9px] text-slate-500">Hızlı Tuşlar</span>
              </div>
              <div class="flex justify-between"><span class="text-slate-400">Oynat / Duraklat:</span> <kbd class="px-1 bg-dark-800 border border-slate-700 rounded font-mono">Space</kbd></div>
              <div class="flex justify-between"><span class="text-slate-400">İmleçten Böl:</span> <kbd class="px-1 bg-dark-800 border border-slate-700 rounded font-mono">B</kbd></div>
              <div class="flex justify-between"><span class="text-amber-300 font-semibold">Soldakini Kırp & Birleştir:</span> <kbd class="px-1 bg-dark-800 border border-amber-400/50 text-amber-300 rounded font-mono font-bold">V</kbd></div>
              <div class="flex justify-between"><span class="text-slate-400">Sil (Klip / Katman):</span> <kbd class="px-1 bg-dark-800 border border-slate-700 rounded font-mono">Del</kbd></div>
              <div class="flex justify-between"><span class="text-slate-400">Katmanı Çoğalt:</span> <kbd class="px-1 bg-dark-800 border border-slate-700 rounded font-mono">Ctrl+D</kbd></div>
              <div class="flex justify-between"><span class="text-slate-400">Klipleri Birleştir:</span> <kbd class="px-1 bg-dark-800 border border-slate-700 rounded font-mono">M</kbd></div>
              <div class="flex justify-between"><span class="text-slate-400">Geri / İleri:</span> <kbd class="px-1 bg-dark-800 border border-slate-700 rounded font-mono">Ctrl+Z / Ctrl+Y</kbd></div>
              <div class="flex justify-between"><span class="text-slate-400">Timeline Yakınlaş:</span> <kbd class="px-1 bg-dark-800 border border-slate-700 rounded font-mono">Ctrl + Tekerlek</kbd></div>
              <div class="flex justify-between"><span class="text-slate-400">Yatay Kaydır:</span> <kbd class="px-1 bg-dark-800 border border-slate-700 rounded font-mono">Shift + Tekerlek</kbd></div>
              <div class="flex justify-between"><span class="text-slate-400">Bağlam Menüsü:</span> <span class="text-brand-yellow font-medium">Sağ Tık</span></div>
            </div>
          </div>

          <!-- Render / Dışa Aktar Butonu -->
          <button 
            (click)="requestExport()"
            [disabled]="rendering()"
            class="px-4 py-1.5 rounded-xl bg-gradient-to-r from-brand-blue via-brand-indigo to-brand-purple hover:from-blue-600 hover:to-purple-600 text-white font-bold text-xs shadow-glow-sm hover:shadow-glow-purple transition-all active:scale-95 flex items-center gap-2 cursor-pointer">
            <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
            </svg>
            {{ rendering() ? 'Kuyruğa Alınıyor...' : 'Nihai Videoyu Render Et' }}
          </button>
        </div>
      </header>

      <!-- Üst Alan: 3 Panelli Grid (Sol Kütüphane + Orta Video Monitör + Sağ Inspector) -->
      <div class="h-[56%] min-h-0 flex flex-row overflow-hidden border-b border-slate-800">
        
        <!-- 1. SOL PANEL: Medya, AI Kurgu Sohbeti, Transkript & Katman Listesi -->
        <aside class="w-[310px] xl:w-[350px] shrink-0 flex flex-col border-r border-slate-800 bg-dark-950 overflow-hidden">
          <!-- Sekme Butonları -->
          <div class="flex border-b border-slate-800 bg-dark-900/90 shrink-0">
            <button 
              (click)="activeTab.set('media')"
              [ngClass]="activeTab() === 'media' ? 'text-brand-cyan border-brand-cyan bg-dark-950 font-bold' : 'text-slate-400 hover:text-slate-200 border-transparent'"
              class="flex-1 py-2.5 text-[10px] border-b-2 transition-all flex items-center justify-center gap-1 cursor-pointer" title="Medya, Sticker & GIF">
              <span>📁</span>
              <span>Medya</span>
            </button>
            <button 
              (click)="activeTab.set('sfx')"
              [ngClass]="activeTab() === 'sfx' ? 'text-emerald-400 border-emerald-400 bg-dark-950 font-bold' : 'text-slate-400 hover:text-slate-200 border-transparent'"
              class="flex-1 py-2.5 text-[10px] border-b-2 transition-all flex items-center justify-center gap-1 cursor-pointer" title="Ses Efektleri (SFX) & Ses Mastering">
              <span>🔊</span>
              <span>SFX</span>
            </button>
            <button 
              (click)="activeTab.set('chat')"
              [ngClass]="activeTab() === 'chat' ? 'text-brand-cyan border-brand-cyan bg-dark-950 font-bold' : 'text-slate-400 hover:text-slate-200 border-transparent'"
              class="flex-1 py-2.5 text-[10px] border-b-2 transition-all flex items-center justify-center gap-1 cursor-pointer" title="Otonom AI Yönetmen & Sohbet">
              <span>🤖</span>
              <span>AI Kurgu</span>
            </button>
            <button 
              (click)="activeTab.set('transcript')"
              [ngClass]="activeTab() === 'transcript' ? 'text-brand-cyan border-brand-cyan bg-dark-950 font-bold' : 'text-slate-400 hover:text-slate-200 border-transparent'"
              class="flex-1 py-2.5 text-[10px] border-b-2 transition-all flex items-center justify-center gap-1 cursor-pointer" title="Transkript & Altyazı">
              <span>📝</span>
              <span>Metin</span>
            </button>
            <button 
              (click)="activeTab.set('overlays')"
              [ngClass]="activeTab() === 'overlays' ? 'text-brand-cyan border-brand-cyan bg-dark-950 font-bold' : 'text-slate-400 hover:text-slate-200 border-transparent'"
              class="flex-1 py-2.5 text-[10px] border-b-2 transition-all flex items-center justify-center gap-1 cursor-pointer" title="Katman Listesi">
              <span>🥞</span>
              <span>({{ activeEdl()?.overlays?.length || 0 }})</span>
            </button>
          </div>

          <!-- Sekme 1: Medya Kütüphanesi & Yükleme -->
          <div *ngIf="activeTab() === 'media'" class="flex-1 p-3.5 overflow-y-auto space-y-3">
            <div class="flex items-center justify-between">
              <span class="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Proje Varlıkları</span>
              <span class="text-[10px] font-mono text-brand-cyan">{{ assets().length }} Dosya</span>
            </div>

            <input #assetFileInput type="file" (change)="onAssetFileSelected($event)" accept="image/*,video/*,audio/*" class="hidden" />

            <div 
              (click)="triggerAssetUpload()"
              (dragover)="onAssetDragOver($event)"
              (dragleave)="onAssetDragLeave($event)"
              (drop)="onAssetDrop($event)"
              [ngClass]="isDragOver() ? 'border-brand-cyan bg-brand-cyan/10 scale-[1.02]' : 'border-slate-700 hover:border-slate-500 bg-dark-900/60'"
              class="p-4 rounded-xl border-2 border-dashed text-center space-y-1.5 cursor-pointer transition-all duration-150">
              <div *ngIf="isUploadingAsset()" class="py-2 flex flex-col items-center gap-2">
                <div class="w-5 h-5 border-2 border-brand-cyan border-t-transparent rounded-full animate-spin"></div>
                <span class="text-xs text-brand-cyan font-bold">Yükleniyor...</span>
              </div>
              <div *ngIf="!isUploadingAsset()">
                <span class="text-2xl block mb-1">📤</span>
                <p class="text-xs text-slate-200 font-medium">
                  <span class="text-brand-cyan font-bold">Dosya Seçin</span> veya buraya sürükleyin
                </p>
                <p class="text-[9px] text-slate-500">PNG, JPG, MP4, MP3 (Maks 50MB)</p>
              </div>
            </div>

            <!-- Yüklenen Dosyalar -->
            <div *ngIf="assets().length > 0" class="space-y-1.5 pt-1">
              <div class="grid grid-cols-2 gap-2">
                <div 
                  *ngFor="let asset of assets()"
                  class="aspect-video bg-dark-900 border border-slate-700/80 rounded-lg overflow-hidden relative group hover:border-brand-cyan transition-all">
                  <img *ngIf="asset.mimeTuru.startsWith('image/')" [src]="asset.url" [alt]="asset.dosyaAdi" class="w-full h-full object-cover" />
                  <div *ngIf="!asset.mimeTuru.startsWith('image/')" class="w-full h-full flex flex-col items-center justify-center bg-dark-800 p-1 text-center">
                    <span class="text-lg">{{ asset.mimeTuru.startsWith('audio/') ? '🎵' : '🎬' }}</span>
                    <span class="text-[8px] text-slate-300 truncate w-full mt-1">{{ asset.dosyaAdi }}</span>
                  </div>

                  <!-- Hover Kontrolleri -->
                  <div class="absolute inset-0 bg-dark-950/85 opacity-0 group-hover:opacity-100 transition-opacity flex flex-col items-center justify-center gap-1 p-1">
                    <button 
                      *ngIf="selectedOverlay()?.type === 'image'"
                      (click)="$event.stopPropagation(); assignAssetToSelectedOverlay(asset)"
                      class="px-2 py-0.5 bg-purple-600 hover:bg-purple-500 text-white font-bold text-[9px] rounded w-full">
                      🎯 Seçiliye Ata
                    </button>
                    <button 
                      (click)="$event.stopPropagation(); addAssetOverlay(asset)"
                      class="px-2 py-0.5 bg-brand-cyan hover:bg-cyan-400 text-slate-950 font-bold text-[9px] rounded w-full">
                      + Katman Ekle
                    </button>
                    <button 
                      (click)="$event.stopPropagation(); deleteAsset(asset.id)"
                      class="px-2 py-0.5 bg-rose-600/20 hover:bg-rose-600/40 text-rose-300 text-[8px] rounded w-full">
                      Sil
                    </button>
                  </div>
                  <div class="absolute bottom-0 inset-x-0 bg-black/60 backdrop-blur-xs px-1 py-0.5 truncate text-[8px] text-slate-300">
                    {{ asset.dosyaAdi }}
                  </div>
                </div>
              </div>
            </div>

            <!-- FAZ 5: Çıkartmalar (Stickers), Hareketli GIF & 3D Emoji Stüdyosu -->
            <div class="pt-2 border-t border-slate-800/80 space-y-2">
              <div class="flex items-center justify-between">
                <span class="text-[10px] font-bold text-amber-400 uppercase tracking-wider">✨ Çıkartmalar, Emoji & GIF</span>
                <span class="text-[9px] text-slate-400 font-mono">Tek Tıkla Ekle</span>
              </div>

              <!-- Çıkartma & Emoji Izgarası -->
              <div class="grid grid-cols-3 gap-1.5 max-h-40 overflow-y-auto pr-1">
                <button
                  type="button"
                  *ngFor="let stk of studioEngine.stickerLibrary"
                  (click)="addStickerOverlay(stk)"
                  class="p-2 rounded-lg bg-dark-900 border border-slate-800 hover:border-amber-400/70 hover:bg-dark-800 flex flex-col items-center justify-center gap-1 transition-all cursor-pointer group"
                  [title]="stk.name + ' Ekle'">
                  <img [src]="stk.dataUrl" [alt]="stk.name" class="h-7 object-contain group-hover:scale-110 transition-transform" />
                  <span class="text-[8px] text-slate-300 truncate w-full text-center font-medium">{{ stk.name }}</span>
                </button>
              </div>

              <!-- Özel Hareketli GIF / Sticker URL Ekle -->
              <div class="flex gap-1.5 pt-1">
                <input
                  type="text"
                  #gifUrlInput
                  placeholder="Hareketli GIF / WebP / PNG URL'si yapıştır..."
                  class="flex-1 bg-dark-900 border border-slate-700 rounded-lg px-2 py-1 text-[10px] text-white placeholder-slate-500 focus:border-amber-400 outline-none" />
                <button
                  type="button"
                  (click)="gifUrlInput.value && addImageOverlayFromUrl(gifUrlInput.value, 'Hareketli GIF'); gifUrlInput.value = ''"
                  class="px-2.5 py-1 bg-amber-500 hover:bg-amber-400 text-slate-950 rounded-lg text-[10px] font-bold cursor-pointer shrink-0">
                  + GIF
                </button>
              </div>
            </div>

            <!-- Zengin B-Roll Stok Kütüphanesi -->
            <div class="pt-2 border-t border-slate-800/80 space-y-2">
              <span class="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">B-Roll Stok Kütüphanesi</span>
              
              <!-- Kategori Seçici Çipler -->
              <div class="flex items-center gap-1 overflow-x-auto pb-1 text-[9px] no-scrollbar">
                <button 
                  type="button" 
                  *ngFor="let cat of stockCategories" 
                  (click)="selectedStockCategory.set(cat.id)" 
                  [ngClass]="selectedStockCategory() === cat.id ? 'bg-brand-cyan text-slate-950 font-bold' : 'bg-dark-800 text-slate-400 hover:text-white'" 
                  class="px-2 py-0.8 rounded-full border border-slate-700 whitespace-nowrap cursor-pointer transition-colors">
                  {{ cat.name }}
                </button>
              </div>

              <!-- Görsel Izgarası -->
              <div class="grid grid-cols-2 gap-2 max-h-48 overflow-y-auto pr-1">
                <div *ngFor="let img of currentCategoryImages()" class="aspect-video bg-dark-800 border border-slate-700 rounded overflow-hidden relative group hover:border-brand-cyan">
                  <img [src]="img.thumb" [alt]="img.title" class="w-full h-full object-cover" />
                  <div class="absolute inset-0 bg-dark-950/85 opacity-0 group-hover:opacity-100 transition-opacity flex flex-col items-center justify-center gap-1 p-1">
                    <span class="text-[9px] text-white font-bold truncate max-w-full text-center">{{ img.title }}</span>
                    <button (click)="$event.stopPropagation(); addImageOverlayFromUrl(img.url, img.title)" class="px-2 py-0.5 bg-brand-cyan text-slate-950 text-[9px] rounded font-bold w-full cursor-pointer hover:bg-cyan-400">+ Katmana Ekle</button>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Sekme 1.5 (FAZ 3): Stüdyo Ses Efektleri (SFX) & Ses Mastering -->
          <div *ngIf="activeTab() === 'sfx'" class="flex-1 p-3 overflow-y-auto space-y-3">
            <!-- Stüdyo Ses Mastering (-14 LUFS & Smart Punch-In) -->
            <div class="p-2.5 rounded-xl bg-gradient-to-br from-emerald-950/50 to-dark-900 border border-emerald-500/30 space-y-2">
              <div class="flex items-center justify-between">
                <span class="text-[10px] font-bold text-emerald-300 uppercase tracking-wider">🎧 Stüdyo Ses & Kurgu Master</span>
                <span class="text-[9px] px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-mono">Pro</span>
              </div>
              <div class="flex items-center justify-between text-xs">
                <div>
                  <span class="font-semibold text-slate-200 block text-[11px]">-14 LUFS Ses Normalizasyonu</span>
                  <span class="text-[9px] text-slate-400">YouTube / Reels yayın standardı</span>
                </div>
                <input type="checkbox" [checked]="normalizeAudio()" (change)="toggleNormalizeAudio($any($event.target).checked)" class="rounded accent-emerald-400 cursor-pointer w-4 h-4" />
              </div>
              <div class="flex items-center justify-between text-xs pt-1 border-t border-slate-800/70">
                <div>
                  <span class="font-semibold text-slate-200 block text-[11px]">🔍 Smart Punch-In Zoom</span>
                  <span class="text-[9px] text-slate-400">Jump-cut sıçramalarında %10 yakınlaş</span>
                </div>
                <input type="checkbox" [checked]="smartPunchIn()" (change)="toggleSmartPunchIn($any($event.target).checked)" class="rounded accent-emerald-400 cursor-pointer w-4 h-4" />
              </div>
            </div>

            <!-- SFX Kategori Filtresi -->
            <div class="space-y-1.5">
              <div class="flex items-center justify-between">
                <span class="text-[10px] font-bold text-slate-300 uppercase tracking-wider">🔊 Ses Efektleri Kütüphanesi ({{ filteredSfxLibrary().length }})</span>
                <button type="button" (click)="isBgmSelectorOpen.set(true)" class="text-[9px] text-violet-300 hover:underline cursor-pointer font-semibold">🎵 BGM Müzik</button>
              </div>
              <div class="flex items-center gap-1 overflow-x-auto pb-1 text-[9px] no-scrollbar">
                <button type="button" (click)="selectedSfxCategory.set('all')" [ngClass]="selectedSfxCategory() === 'all' ? 'bg-emerald-400 text-slate-950 font-bold' : 'bg-dark-800 text-slate-400'" class="px-2 py-0.5 rounded-full border border-slate-700 cursor-pointer">Tümü</button>
                <button type="button" (click)="selectedSfxCategory.set('whoosh')" [ngClass]="selectedSfxCategory() === 'whoosh' ? 'bg-emerald-400 text-slate-950 font-bold' : 'bg-dark-800 text-slate-400'" class="px-2 py-0.5 rounded-full border border-slate-700 cursor-pointer">💨 Geçiş</button>
                <button type="button" (click)="selectedSfxCategory.set('pop')" [ngClass]="selectedSfxCategory() === 'pop' ? 'bg-emerald-400 text-slate-950 font-bold' : 'bg-dark-800 text-slate-400'" class="px-2 py-0.5 rounded-full border border-slate-700 cursor-pointer">🫧 Pop</button>
                <button type="button" (click)="selectedSfxCategory.set('cinematic')" [ngClass]="selectedSfxCategory() === 'cinematic' ? 'bg-emerald-400 text-slate-950 font-bold' : 'bg-dark-800 text-slate-400'" class="px-2 py-0.5 rounded-full border border-slate-700 cursor-pointer">💣 Sinematik</button>
                <button type="button" (click)="selectedSfxCategory.set('ui')" [ngClass]="selectedSfxCategory() === 'ui' ? 'bg-emerald-400 text-slate-950 font-bold' : 'bg-dark-800 text-slate-400'" class="px-2 py-0.5 rounded-full border border-slate-700 cursor-pointer">🔔 Bildirim</button>
                <button type="button" (click)="selectedSfxCategory.set('funny')" [ngClass]="selectedSfxCategory() === 'funny' ? 'bg-emerald-400 text-slate-950 font-bold' : 'bg-dark-800 text-slate-400'" class="px-2 py-0.5 rounded-full border border-slate-700 cursor-pointer">💿 Mizah</button>
              </div>
            </div>

            <!-- SFX Kartları -->
            <div class="space-y-1.5">
              <div
                *ngFor="let sfx of filteredSfxLibrary()"
                class="p-2 rounded-xl bg-dark-900 border border-slate-800 hover:border-emerald-500/50 flex items-center justify-between gap-2 transition-all group">
                <div class="flex items-center gap-2 min-w-0">
                  <button
                    type="button"
                    (click)="previewSfxItem(sfx)"
                    class="w-7 h-7 rounded-lg bg-emerald-500/15 hover:bg-emerald-500 text-emerald-300 hover:text-slate-950 flex items-center justify-center text-xs shrink-0 transition-colors cursor-pointer"
                    title="Sesi Dinle">
                    ▶
                  </button>
                  <div class="min-w-0">
                    <div class="flex items-center gap-1.5">
                      <span class="text-xs">{{ sfx.icon }}</span>
                      <span class="text-[11px] font-bold text-slate-100 truncate">{{ sfx.name }}</span>
                      <span class="text-[9px] font-mono text-emerald-400">{{ sfx.duration }}s</span>
                    </div>
                    <p class="text-[9px] text-slate-400 truncate">{{ sfx.description }}</p>
                  </div>
                </div>
                <button
                  type="button"
                  (click)="addSfxToTimeline(sfx)"
                  class="px-2.5 py-1 rounded-lg bg-emerald-500/20 hover:bg-emerald-500 text-emerald-300 hover:text-slate-950 border border-emerald-500/40 text-[10px] font-bold shrink-0 cursor-pointer transition-colors"
                  title="İmlecin olduğu saniyeye (A2 Kanalına) ekle">
                  + Ekle
                </button>
              </div>
            </div>
          </div>

          <!-- Sekme 2: AI Kurgu Sohbeti & Otonom Video Yönetmeni (FAZ 6) -->
          <div *ngIf="activeTab() === 'chat'" class="flex-1 flex flex-col h-full overflow-hidden">
            <div #chatMessagesContainer class="flex-1 p-3 overflow-y-auto space-y-3">

              <!-- FAZ 6: OTONOM VİDEO YÖNETMENİ (PROAKTİF AI ÖNERİLERİ) -->
              <div class="p-3 rounded-xl bg-gradient-to-br from-indigo-950/70 via-dark-900 to-slate-950 border border-indigo-500/40 space-y-2.5 shadow-lg">
                <div class="flex items-center justify-between">
                  <div class="flex items-center gap-1.5">
                    <span class="text-sm">🎬</span>
                    <span class="text-[11px] font-extrabold text-indigo-300 uppercase tracking-wide">Otonom Video Yönetmeni</span>
                  </div>
                  <button
                    type="button"
                    (click)="generateAiDirectorSuggestions()"
                    class="px-2 py-0.5 rounded-md bg-brand-cyan/20 hover:bg-brand-cyan text-brand-cyan hover:text-slate-950 border border-brand-cyan/40 text-[9px] font-bold transition-colors cursor-pointer">
                    ✨ Sahneyi Analiz Et ({{ pendingSuggestions().length }})
                  </button>
                </div>
                <p class="text-[10px] text-slate-300 leading-snug">
                  Videonuzun konuşma vurgularına ve kesim noktalarına göre hazırlanan profesyonel kurgu önerileri:
                </p>

                <div *ngIf="pendingSuggestions().length === 0" class="p-2.5 rounded-lg bg-dark-950/80 border border-slate-800 text-center space-y-1.5">
                  <p class="text-[10px] text-slate-400">Bu proje için henüz aktif yönetmen önerisi üretilmedi.</p>
                  <button
                    type="button"
                    (click)="generateAiDirectorSuggestions()"
                    class="px-3 py-1.5 rounded-lg bg-gradient-to-r from-brand-cyan to-indigo-500 text-slate-950 font-extrabold text-[10px] shadow-glow-sm cursor-pointer">
                    🚀 5 Profesyonel Kurgu Önerisi Üret
                  </button>
                </div>

                <!-- Proaktif Öneri Kartları -->
                <div *ngIf="pendingSuggestions().length > 0" class="space-y-2 max-h-60 overflow-y-auto pr-0.5">
                  <div
                    *ngFor="let sug of pendingSuggestions()"
                    class="p-2.5 rounded-lg bg-dark-950/90 border border-slate-700/80 hover:border-brand-cyan/60 space-y-1.5 transition-all">
                    <div class="flex items-center justify-between gap-1">
                      <span class="text-[9px] px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-300 font-bold">{{ sug.category || '✨ AI Önerisi' }}</span>
                      <span class="text-[9px] font-mono text-brand-cyan font-bold cursor-pointer hover:underline" (click)="seekToTranscript(sug.timestamp)">
                        ⏱ {{ sug.timestamp }}s ({{ sug.duration }}s)
                      </span>
                    </div>
                    <p class="text-[11px] font-bold text-white">{{ sug.title }}</p>
                    <p class="text-[10px] text-slate-400 leading-snug">{{ sug.reason }}</p>
                    <div class="flex items-center gap-1.5 pt-1">
                      <button
                        type="button"
                        (click)="seekToTranscript(sug.timestamp)"
                        class="px-2 py-1 rounded bg-dark-800 hover:bg-slate-700 text-slate-300 text-[9px] font-semibold cursor-pointer">
                        👁️ Git
                      </button>
                      <button
                        type="button"
                        (click)="acceptSuggestion(sug)"
                        class="flex-1 py-1 rounded bg-emerald-500 hover:bg-emerald-400 text-slate-950 text-[10px] font-extrabold cursor-pointer shadow-sm">
                        ✓ Tek Tıkla Uygula
                      </button>
                      <button
                        type="button"
                        (click)="rejectSuggestion(sug)"
                        class="px-2 py-1 rounded bg-rose-500/20 hover:bg-rose-500/40 text-rose-300 text-[9px] font-bold cursor-pointer">
                        ✕
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              <div *ngIf="chatMessages().length === 0" class="text-center py-3 text-slate-500 text-xs">
                <p class="mb-2 font-medium">💡 Doğal dille kurgu komutu verin:</p>
                <div class="space-y-1.5 text-slate-300 text-[11px]">
                  <p class="p-2 rounded-lg bg-dark-900 border border-slate-800 cursor-pointer hover:border-brand-cyan/60 transition-colors" (click)="setPrompt('Girişteki sessizlikleri kes')">"Girişteki sessizlikleri kes"</p>
                  <p class="p-2 rounded-lg bg-dark-900 border border-slate-800 cursor-pointer hover:border-brand-cyan/60 transition-colors" (click)="setPrompt('10. saniyeye Kanala Abone Ol yazısı koy')">"10. saniyeye Kanala Abone Ol yazısı koy"</p>
                </div>
              </div>

              <div *ngFor="let msg of chatMessages()" [ngClass]="msg.rol === 'user' ? 'flex justify-end' : 'flex justify-start'">
                <div 
                  [ngClass]="msg.rol === 'user' ? 'bg-gradient-to-r from-brand-blue to-brand-indigo text-white rounded-2xl rounded-tr-none' : 'bg-dark-900 border border-slate-700/60 text-slate-200 rounded-2xl rounded-tl-none'"
                  class="max-w-[90%] p-3 text-xs shadow-md space-y-1.5">
                  <p class="leading-relaxed">{{ msg.mesaj }}</p>
                  
                  <div *ngIf="msg.patchDurumu === 'pending'" class="mt-2 flex gap-1.5">
                    <button (click)="previewPatch(msg)" [ngClass]="previewMessageId() === msg.id ? 'bg-sky-500/40 text-sky-300' : 'bg-sky-500/20 text-sky-400'" class="flex-1 py-1 text-[10px] hover:bg-sky-500/40 border border-sky-500/50 rounded font-bold">
                      {{ previewMessageId() === msg.id ? '👀 İzleniyor' : '🔍 Önizle' }}
                    </button>
                    <button (click)="applyPatch(msg)" class="flex-1 py-1 text-[10px] bg-emerald-500/20 hover:bg-emerald-500/40 text-emerald-400 border border-emerald-500/50 rounded font-bold">Onayla</button>
                    <button (click)="cancelPatch(msg)" class="flex-1 py-1 text-[10px] bg-rose-500/20 hover:bg-rose-500/40 text-rose-400 border border-rose-500/50 rounded font-bold">İptal</button>
                  </div>

                  <!-- Dinamik Clarification Formu -->
                  <div *ngIf="msg.patchDurumu === 'clarification' && msg.formFields" class="mt-2 p-2.5 bg-dark-950 border border-brand-cyan/40 rounded-xl space-y-2.5 shadow-lg">
                     <span class="text-[10px] text-brand-cyan font-bold uppercase tracking-wider block border-b border-slate-800 pb-1">
                       ⚙️ Katman Özelliklerini Belirleyin
                     </span>
                     <div *ngFor="let field of msg.formFields" class="space-y-1">
                        <label class="text-[10px] text-slate-300 font-medium flex justify-between">
                          <span>{{ field.label }}</span>
                          <span *ngIf="field.required" class="text-rose-400 text-[9px]">*Zorunlu</span>
                        </label>
                        <input *ngIf="field.type === 'text'" type="text" [ngModel]="msg.formData?.[field.id] || field.defaultValue" (ngModelChange)="updateFormData(msg, field.id, $event)" placeholder="Metin giriniz..." class="w-full bg-dark-900 border border-slate-700 rounded p-1.5 text-xs text-white outline-none" />
                        <input *ngIf="field.type === 'number'" type="number" [ngModel]="msg.formData?.[field.id] || field.defaultValue" (ngModelChange)="updateFormData(msg, field.id, $event)" class="w-full bg-dark-900 border border-slate-700 rounded p-1.5 text-xs text-white outline-none" />
                        
                        <!-- Renk Seçici -->
                        <div *ngIf="field.type === 'color'" class="space-y-1.5">
                          <div class="flex flex-wrap gap-1 items-center">
                            <button *ngFor="let c of colorPalette" type="button" (click)="updateFormData(msg, field.id, c)" [style.backgroundColor]="c" [ngClass]="(msg.formData?.[field.id] || field.defaultValue) === c ? 'ring-2 ring-brand-cyan scale-110' : 'opacity-80 hover:opacity-100'" class="w-5 h-5 rounded-full border border-white/20 transition-all"></button>
                          </div>
                          <div class="flex items-center gap-2 bg-dark-900 p-1 rounded border border-slate-700">
                            <input type="color" [ngModel]="msg.formData?.[field.id] || field.defaultValue || '#FACC15'" (ngModelChange)="updateFormData(msg, field.id, $event)" class="w-6 h-6 rounded cursor-pointer border-0 bg-transparent p-0" />
                            <input type="text" [ngModel]="msg.formData?.[field.id] || field.defaultValue || '#FACC15'" (ngModelChange)="updateFormData(msg, field.id, $event)" class="bg-transparent text-[11px] font-mono text-slate-200 outline-none w-16 uppercase font-semibold" maxlength="7" />
                          </div>
                        </div>

                        <!-- 16:9 Mini Stage Konum Seçici -->
                        <div *ngIf="field.type === 'position'" class="space-y-1">
                          <div (click)="onMiniStageClick($event, msg, field.id)" class="w-full aspect-video bg-black border border-slate-700 rounded relative overflow-hidden cursor-crosshair select-none">
                            <div class="absolute inset-0 grid grid-cols-3 grid-rows-3 pointer-events-none opacity-20">
                              <div class="border-r border-b border-slate-400"></div><div class="border-r border-b border-slate-400"></div><div class="border-b border-slate-400"></div>
                              <div class="border-r border-b border-slate-400"></div><div class="border-r border-b border-slate-400"></div><div class="border-b border-slate-400"></div>
                            </div>
                            <div class="absolute -translate-x-1/2 -translate-y-1/2 pointer-events-none flex flex-col items-center" [style.left.%]="getMarkerPosition(msg, field).x" [style.top.%]="getMarkerPosition(msg, field).y">
                              <div class="w-3 h-3 rounded-full bg-brand-cyan border-2 border-white animate-pulse"></div>
                            </div>
                          </div>
                        </div>

                        <select *ngIf="field.type === 'select'" [ngModel]="msg.formData?.[field.id] || field.defaultValue" (ngModelChange)="updateFormData(msg, field.id, $event)" class="w-full bg-dark-900 border border-slate-700 rounded p-1.5 text-xs text-white outline-none">
                          <option *ngFor="let opt of field.options" [value]="getOptValue(opt)">{{ getOptLabel(opt) }}</option>
                        </select>
                     </div>
                     <button (click)="submitForm(msg)" class="w-full py-1.5 bg-brand-cyan hover:bg-cyan-400 text-slate-950 font-bold rounded text-xs transition-all flex items-center justify-center gap-1">
                       <span>✨</span>
                       <span>Onayla ve Ekle</span>
                     </button>
                  </div>

                  <span class="text-[9px] opacity-60 block text-right">{{ msg.olusturulmaZamani | date:'HH:mm' }}</span>
                </div>
              </div>

              <div *ngIf="chatLoading()" class="flex items-center gap-2 text-slate-400 text-xs p-2">
                <span class="w-2 h-2 rounded-full bg-brand-cyan animate-ping"></span>
                <span>AI kararları işliyor...</span>
              </div>
            </div>

            <!-- Chat Gönderme Kutusu -->
            <div class="p-2.5 bg-dark-900 border-t border-slate-800">
              <form (ngSubmit)="sendChatMessage()" class="flex items-center gap-1.5">
                <input 
                  type="text" 
                  [(ngModel)]="userPrompt" 
                  name="prompt"
                  placeholder="Komut yazın (Enter)..."
                  [disabled]="chatLoading()"
                  class="flex-1 px-3 py-2 rounded-lg bg-dark-950 border border-slate-700 text-white placeholder-slate-500 focus:outline-none focus:border-brand-cyan text-xs transition-all" />
                <button 
                  type="submit"
                  [disabled]="!userPrompt.trim() || chatLoading()"
                  class="px-3.5 py-2 rounded-lg bg-brand-blue hover:bg-blue-600 text-white text-xs font-bold disabled:opacity-40 transition-all shadow-glow-sm">
                  Gönder
                </button>
              </form>
            </div>
          </div>

          <!-- Sekme 3: Transkript ve Tıklanabilir Metin Akışı -->
          <div *ngIf="activeTab() === 'transcript'" class="flex-1 p-3 overflow-y-auto space-y-2.5">
            <!-- Arama Kutusu -->
            <div class="sticky top-0 bg-dark-950 pb-1 z-10">
              <input 
                type="text" 
                [ngModel]="transcriptSearchQuery()" 
                (ngModelChange)="transcriptSearchQuery.set($event)"
                placeholder="Transkriptte kelime ara..."
                class="w-full bg-dark-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-white placeholder-slate-500 focus:border-brand-cyan outline-none" />
            </div>

            <div *ngIf="!filteredTranscriptSegments()?.length" class="text-center py-10 text-slate-500 text-xs">
              Transkript verisi bulunamadı veya eşleşen sonuç yok.
            </div>

            <div 
              *ngFor="let seg of filteredTranscriptSegments()"
              (click)="selectSubtitle(seg)"
              class="p-2 rounded-lg border cursor-pointer transition-all space-y-1 group"
              [ngClass]="isSelectedSubtitle(seg) ? 'border-brand-cyan bg-dark-800 ring-1 ring-brand-cyan shadow-glow-sm' : 'border-slate-800 bg-dark-900/60 hover:bg-dark-800 hover:border-brand-cyan/50'">
              <div class="flex items-center justify-between text-[10px] font-mono text-slate-400">
                <span class="text-brand-cyan font-bold group-hover:underline">⏱ {{ seg.start | duration }}</span>
                <span class="opacity-60">{{ (seg.end - seg.start).toFixed(1) }}s</span>
              </div>
              <p class="text-xs text-slate-200 leading-relaxed">{{ seg.text }}</p>
            </div>
          </div>

          <!-- Sekme 4: Katmanlar Listesi (Overlays) -->
          <div *ngIf="activeTab() === 'overlays'" class="flex-1 p-3 overflow-y-auto space-y-2">
            <div *ngIf="!activeEdl()?.overlays?.length" class="text-center py-10 text-slate-500 text-xs">
              Henüz eklenmiş katman bulunmuyor.
            </div>

            <div 
              *ngFor="let ov of activeEdl()?.overlays"
              (click)="selectOverlay(ov.id)"
              class="p-2.5 rounded-lg border flex items-start justify-between gap-2 cursor-pointer transition-all"
              [ngClass]="selectedOverlayId() === ov.id ? 'bg-dark-800 border-brand-cyan shadow-glow-sm' : 'bg-dark-900 border-slate-800 hover:bg-dark-850'">
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-1.5 mb-1">
                  <span [ngClass]="ov.type === 'text' ? 'bg-sky-500/20 text-sky-400' : 'bg-purple-500/20 text-purple-400'" class="px-1.5 py-0.5 rounded text-[9px] font-bold uppercase">
                    {{ ov.type }}
                  </span>
                  <span class="px-1.5 py-0.5 rounded text-[9px] font-mono font-bold bg-slate-800 text-brand-cyan">
                    T{{ ov.trackId || 1 }}
                  </span>
                  <span class="text-[10px] font-mono text-slate-400">{{ ov.timestamp | number:'1.1-1' }}s</span>
                </div>
                <p class="text-xs font-medium text-white truncate">{{ ov.content || ov.source || ov.id }}</p>
              </div>

              <div class="flex items-center gap-1 shrink-0">
                <button (click)="$event.stopPropagation(); bringOverlayForward(ov.id)" title="Öne Getir" class="text-slate-400 hover:text-white p-1 rounded text-xs">🔼</button>
                <button (click)="$event.stopPropagation(); sendOverlayBackward(ov.id)" title="Arkaya Gönder" class="text-slate-400 hover:text-white p-1 rounded text-xs">🔽</button>
                <button (click)="$event.stopPropagation(); removeOverlay(ov.id)" title="Sil" class="text-slate-500 hover:text-rose-400 p-1 rounded text-xs">✕</button>
              </div>
            </div>
          </div>
        </aside>

        <!-- 2. ORTA PANEL: Video Önizleme Monitörü + CapCut Oynatma Barı -->
        <section class="flex-1 flex flex-col bg-black/95 relative items-center justify-between p-3 min-w-0 overflow-hidden">
          <!-- Monitör Sahnesi Dış Çerçevesi -->
          <div class="relative w-full flex-1 max-w-[860px] bg-black rounded-xl overflow-hidden shadow-2xl border border-slate-800/80 flex items-center justify-center min-h-0">
            <!-- Canlı BGM Oynatıcı (E2: Auto-Ducking Destekli) -->
            <audio #bgmAudioPlayer *ngIf="bgmUrl()" [src]="bgmUrl()" loop preload="auto" class="hidden"></audio>

            <!-- Gerçek Silüet Sticker Konturu için SVG Morpholojik Filtre Tanımları -->
            <svg width="0" height="0" class="absolute pointer-events-none overflow-hidden" aria-hidden="true">
              <defs>
                <filter *ngFor="let ov of activeOverlays()" [attr.id]="'sticker-outline-' + ov.id" x="-30%" y="-30%" width="160%" height="160%">
                  <feMorphology in="SourceAlpha" operator="dilate" [attr.radius]="((ov.stickerBorderWidth || 6) * 0.45).toFixed(1)" result="dilated" />
                  <feFlood [attr.flood-color]="ov.stickerBorderColor || '#FFFFFF'" result="floodColor" />
                  <feComposite in="floodColor" in2="dilated" operator="in" result="outline" />
                  <feDropShadow dx="0" dy="4" stdDeviation="4" flood-color="rgba(0,0,0,0.55)" result="shadowedOutline" />
                  <feMerge>
                    <feMergeNode in="shadowedOutline" />
                    <feMergeNode in="outline" />
                    <feMergeNode in="SourceGraphic" />
                  </feMerge>
                </filter>
              </defs>
            </svg>

            <!-- Video En-Boy Oranına Kilitli Sahne (Video & Kaplamalar Birebir Kilitli) -->
            <div 
              style="container-type: inline-size; container-name: player;"
              class="relative flex items-center justify-center w-full max-h-[460px] shadow-2xl overflow-hidden"
              [style.aspectRatio]="videoAspectRatio()"
              [style.maxWidth]="'calc(460px * (' + videoAspectRatio() + '))'">
              
              <video 
                #videoPlayer
                [src]="videoUrl()"
                (timeupdate)="onTimeUpdate()"
                (seeked)="onVideoSeeked()"
                (loadedmetadata)="onMetadataLoaded()"
                (play)="onVideoPlay()"
                (pause)="onVideoPause()"
                [style.filter]="videoFilterStyle()"
                [style.transform]="videoPreviewTransform()"
                [style.opacity]="videoPreviewOpacity()"
                class="w-full h-full object-contain rounded pointer-events-auto transition-transform duration-150">
              </video>

              <!-- Canlı Sahne Geçiş Efekti (Transition Overlay) -->
              <div 
                *ngIf="activeTransitionEffect() as trEffect"
                class="absolute inset-0 pointer-events-none z-20 transition-all duration-75 flex items-center justify-center"
                [ngStyle]="trEffect.overlayStyle">
                <span *ngIf="trEffect.badge" class="px-2.5 py-1 rounded-full bg-black/75 border border-brand-cyan/40 text-[10px] font-bold text-brand-cyan shadow-lg">
                  ⚡ {{ trEffect.badge }}
                </span>
              </div>

              <!-- Dinamik Aktif Metin & Görsel Overlay Önizlemesi (Photoshop & CapCut Studio) -->
              <div 
                *ngFor="let ov of activeOverlays()" 
                (mousedown)="onCanvasDragStart($event, ov.id)"
                (click)="$event.stopPropagation(); selectOverlay(ov.id)"
                (contextmenu)="openOverlayContextMenu($event, ov)"
                [style.top]="getOverlayTop(ov)"
                [style.left]="getOverlayLeft(ov)"
                [style.zIndex]="getOverlayZIndex(ov)"
                [style.mixBlendMode]="ov.blendMode || 'normal'"
                class="absolute transition-none cursor-move hover:ring-2 hover:ring-brand-cyan rounded p-1 -translate-x-1/2 -translate-y-1/2 select-none"
                [ngClass]="[
                   selectedOverlayId() === ov.id ? 'ring-2 ring-brand-cyan shadow-glow-sm' : ''
                ]"
                [style.color]="ov.color || '#FFFFFF'"
                [style.backgroundColor]="ov.backgroundColor || 'transparent'"
                [style.fontFamily]="ov.font || 'Inter, sans-serif'">
                
                <div [ngClass]="getOverlayAnimationClass(ov)" [style.transform]="getOverlay3DTransform(ov)">
                
                <!-- 1A. Yay / Kavisli (Curved SVG TextPath) Metin Kaplaması -->
                <svg 
                  *ngIf="ov.type === 'text' && ov.curveBend && (ov.curveBend > 1 || ov.curveBend < -1)"
                  viewBox="0 0 560 220"
                  class="overflow-visible pointer-events-none block"
                  [style.width]="((ov.fontSize || 48) * 7.2 / 19.2) + 'cqi'"
                  [style.filter]="getTextOverlayFilter(ov)">
                  <defs>
                    <path [attr.id]="'curve-path-' + ov.id" [attr.d]="getCurvedTextPath(ov.curveBend)" fill="none" />
                    <linearGradient *ngIf="ov.fillType === 'gradient' || ov.fillType === 'radial'" [attr.id]="'grad-' + ov.id" x1="0%" y1="0%" x2="100%" y2="100%">
                      <stop offset="0%" [attr.stop-color]="ov.gradientStart || ov.color || '#FACC15'" />
                      <stop offset="100%" [attr.stop-color]="ov.gradientEnd || '#EF4444'" />
                    </linearGradient>
                  </defs>
                  <!-- Outer Stroke (Double Stroke) -->
                  <text 
                    *ngIf="ov.outerStrokeWidth && ov.outerStrokeWidth > 0"
                    [style.fontFamily]="ov.font || 'Montserrat'"
                    [attr.font-size]="ov.fontSize || 48"
                    font-weight="800"
                    [attr.letter-spacing]="ov.letterSpacing || 0"
                    fill="none"
                    [attr.stroke]="ov.outerStrokeColor || '#000000'"
                    [attr.stroke-width]="((ov.strokeWidth || 0) + (ov.outerStrokeWidth || 0)) * 1.6"
                    stroke-linejoin="round"
                    stroke-linecap="round">
                    <textPath [attr.href]="'#curve-path-' + ov.id" startOffset="50%" text-anchor="middle">
                      {{ ov.allCaps ? (ov.content || '').toUpperCase() : ov.content }}
                    </textPath>
                  </text>
                  <!-- Main Text + Primary Stroke -->
                  <text 
                    [style.fontFamily]="ov.font || 'Montserrat'"
                    [attr.font-size]="ov.fontSize || 48"
                    font-weight="800"
                    [attr.letter-spacing]="ov.letterSpacing || 0"
                    [attr.fill]="(ov.fillType === 'gradient' || ov.fillType === 'radial') ? 'url(#grad-' + ov.id + ')' : (ov.color || '#FFFFFF')"
                    [attr.stroke]="ov.strokeWidth ? (ov.strokeColor || '#000000') : 'none'"
                    [attr.stroke-width]="(ov.strokeWidth || 0) * 1.2"
                    stroke-linejoin="round"
                    paint-order="stroke fill">
                    <textPath [attr.href]="'#curve-path-' + ov.id" startOffset="50%" text-anchor="middle">
                      {{ ov.allCaps ? (ov.content || '').toUpperCase() : ov.content }}
                    </textPath>
                  </text>
                </svg>

                <!-- 1B. Normal & Photoshop Stil Metin Kaplaması (Gradient, Çift Kontur, Neon Glow, Pill/Marker) -->
                <span 
                  *ngIf="ov.type === 'text' && (!ov.curveBend || (ov.curveBend >= -1 && ov.curveBend <= 1))" 
                  class="font-bold whitespace-nowrap block transition-all"
                  [ngStyle]="getTextOverlayStyle(ov)">
                  {{ ov.allCaps ? (ov.content || '').toUpperCase() : ov.content }}
                </span>

                <!-- 2. Görsel / B-Roll / Sticker / GIF Kaplaması (Photoshop Adjustments + Real Silhouette Sticker + Shape Mask) -->
                <div 
                  *ngIf="ov.type === 'image'" 
                  class="relative group transition-transform duration-75"
                  [style.opacity]="(ov.opacity ?? 100) / 100">
                  <img 
                    *ngIf="ov.source" 
                    [src]="ov.source" 
                    [alt]="ov.content || 'Görsel'" 
                    class="pointer-events-none object-contain transition-all"
                    [ngClass]="[
                      ov.maskShape === 'circle' ? 'rounded-full aspect-square object-cover' : (ov.maskShape === 'rounded' ? 'rounded-2xl' : 'rounded-lg'),
                      (!ov.removeBg && !ov.stickerBorder && (!ov.maskShape || ov.maskShape === 'rect')) ? 'border border-brand-cyan/40 shadow-xl' : ''
                    ]"
                    [style.width]="(160 * (ov.scale || 1.0) / 8.6) + 'cqi'"
                    [style.filter]="getImageOverlayFilter(ov)"
                    [style.clipPath]="getImageClipPath(ov)"
                    style="height: auto; max-width: none;" />
                  
                  <div *ngIf="!ov.source" class="px-3 py-2 rounded-lg bg-dark-800/90 border border-brand-cyan/40 text-brand-cyan text-xs font-bold flex items-center gap-1.5">
                    <span>🖼️</span>
                    <span>{{ ov.content || 'B-Roll Görseli' }}</span>
                  </div>
                </div>
                </div>

                <!-- Keyframe Rozeti -->
                <span *ngIf="ov.keyframes && ov.keyframes.length > 0 && selectedOverlayId() === ov.id"
                      class="absolute -top-2.5 -left-2.5 px-1.5 py-0.2 rounded bg-amber-500 text-slate-950 font-black text-[8px] shadow z-30">
                  ◆ {{ ov.keyframes.length }} KF
                </span>

                <!-- Canvas Resize Handle -->
                <div *ngIf="selectedOverlayId() === ov.id"
                     (mousedown)="onCanvasResizeStart($event, ov.id)"
                     class="absolute -bottom-2 -right-2 w-5 h-5 bg-white border-2 border-brand-cyan rounded-full cursor-nwse-resize z-30 shadow-md hover:scale-125 transition-transform flex items-center justify-center">
                     <span class="text-[8px] text-brand-cyan font-bold">⤡</span>
                </div>
              </div>

              <!-- Canlı Taslak (Ghost Layer) -->
              <div 
                *ngIf="ghostPreview() as ghost" 
                class="absolute pointer-events-none z-30 -translate-x-1/2 -translate-y-1/2 select-none border-2 border-dashed border-brand-cyan bg-black/70 backdrop-blur-xs px-3 py-1.5 rounded-lg shadow-glow-sm"
                [style.left.%]="ghost.posX"
                [style.top.%]="ghost.posY"
                [style.color]="ghost.color"
                [style.fontFamily]="ghost.font">
                <span class="font-bold whitespace-nowrap block drop-shadow text-base">{{ ghost.text }}</span>
                <span class="absolute -top-3 -right-3 text-[8px] bg-brand-cyan text-slate-900 font-extrabold px-1 rounded">📍 Taslak</span>
              </div>

              <!-- TikTok / Reels / CapCut Karaoke Altyazı -->
              <div 
                *ngIf="showSubtitles() && currentSubtitleSegment() as seg" 
                (click)="$event.stopPropagation(); selectSubtitle(seg)"
                class="absolute left-1/2 -translate-x-1/2 z-25 max-w-[85%] text-center cursor-pointer select-none transition-all group"
                [style.bottom.%]="100 - subtitlePositionY()"
                [style.backgroundColor]="subtitlePreset() === 'opaque_banner' ? subtitleBgColor() : (subtitlePreset() === 'neon_glow' ? 'rgba(0,0,0,0.4)' : 'rgba(0,0,0,0.65)')"
                [style.padding.px]="subtitlePreset() === 'opaque_banner' ? subtitleBgPadding() : 8"
                [style.borderRadius.px]="subtitleBorderRadius()"
                [style.letterSpacing.px]="subtitleLetterSpacing()"
                [style.textTransform]="subtitleAllCaps() ? 'uppercase' : 'none'"
                [style.backdropFilter]="subtitlePreset() === 'opaque_banner' ? 'none' : 'blur(8px)'"
                [style.border]="subtitlePreset() === 'opaque_banner' ? '1px solid rgba(255,255,255,0.1)' : '1px solid rgba(255,255,255,0.08)'"
                [style.boxShadow]="subtitlePreset() === 'neon_glow' ? '0 0 25px ' + subtitleHighlightColor() + '40' : '0 10px 25px rgba(0,0,0,0.5)'"
                title="Altyazıyı Düzenlemek İçin Tıklayın">
                <div 
                  class="flex flex-wrap items-center justify-center gap-x-1.5 gap-y-0.5" 
                  [style.fontFamily]="subtitleFont()" 
                  [style.fontSize.px]="subtitleFontSize()"
                  [style.color]="subtitleColor()">
                  <ng-container *ngIf="seg.words && seg.words.length > 0; else plainText">
                    <span 
                      *ngFor="let w of seg.words"
                      class="transition-all duration-100 inline-block px-1 rounded"
                      [style.color]="isWordActive(w) ? subtitleHighlightColor() : subtitleColor()"
                      [style.textShadow]="subtitlePreset() === 'neon_glow' && isWordActive(w) ? '0 0 10px ' + subtitleHighlightColor() + ', 0 0 20px ' + subtitleStrokeColor() : (subtitlePreset() === 'cinematic_shadow' ? '0 2px 8px rgba(0,0,0,0.9)' : '0 2px 4px rgba(0,0,0,0.8)')"
                      [style.webkitTextStroke]="(subtitleStrokeWidth() > 0 ? (subtitleStrokeWidth() * 0.4) + 'px ' + subtitleStrokeColor() : 'none')"
                      [ngClass]="isWordActive(w) ? 'font-black scale-110 shadow-glow-sm' : 'font-semibold opacity-90'">
                      {{ subtitleAllCaps() ? w.word.toUpperCase() : w.word }}
                    </span>
                  </ng-container>
                  <ng-template #plainText>
                    <span 
                      class="font-bold drop-shadow" 
                      [style.color]="subtitleColor()"
                      [style.webkitTextStroke]="(subtitleStrokeWidth() > 0 ? (subtitleStrokeWidth() * 0.4) + 'px ' + subtitleStrokeColor() : 'none')">
                      {{ subtitleAllCaps() ? seg.text.toUpperCase() : seg.text }}
                    </span>
                  </ng-template>
                </div>
              </div>
            </div>
          </div>

          <!-- CapCut Stili Monitör Alt Kontrol / Transport Barı -->
          <div class="h-11 w-full max-w-[860px] bg-dark-900/90 border border-slate-800 rounded-xl px-4 flex items-center justify-between select-none shadow-lg mt-2 shrink-0">
            <!-- Sol: Zaman Göstergesi -->
            <div class="flex items-center gap-2.5 font-mono text-xs text-slate-400">
              <span class="text-white font-semibold">{{ currentTime() | duration }}</span>
              <span class="text-slate-600">/</span>
              <span>{{ totalDuration() | duration }}</span>
              <span class="text-brand-cyan font-bold text-[11px] ml-1.5 px-2 py-0.5 rounded bg-brand-cyan/10 border border-brand-cyan/20">
                Net: {{ visibleDuration() | duration }}
              </span>
            </div>

            <!-- Orta: Oynatma Kontrolleri -->
            <div class="flex items-center gap-3">
              <button 
                (click)="skipSeconds(-5)" 
                class="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-dark-800 transition-colors flex items-center gap-0.5 text-xs font-mono" 
                title="5 Saniye Geri">
                <span>⏮</span>
                <span class="text-[10px]">5s</span>
              </button>
              <button 
                (click)="togglePlayPause()" 
                class="w-9 h-9 rounded-full bg-brand-cyan hover:bg-cyan-400 text-slate-950 font-black flex items-center justify-center shadow-glow-sm hover:scale-105 active:scale-95 transition-all text-sm cursor-pointer"
                title="Oynat / Duraklat (Space)">
                <span>{{ isPlaying() ? '⏸' : '▶' }}</span>
              </button>
              <button 
                (click)="skipSeconds(5)" 
                class="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-dark-800 transition-colors flex items-center gap-0.5 text-xs font-mono" 
                title="5 Saniye İleri">
                <span class="text-[10px]">5s</span>
                <span>⏭</span>
              </button>
            </div>

            <!-- Sağ: Hız, Renk, Altyazı ve Tam Ekran -->
            <div class="flex items-center gap-2">
              <!-- Hız Kontrolü (0.5x, 0.75x, 1x, 1.25x, 1.5x, 2x) -->
              <button 
                type="button"
                (click)="cyclePlaybackSpeed()" 
                [ngClass]="playbackSpeed() !== 1.0 ? 'text-brand-cyan bg-brand-cyan/20 border-brand-cyan/40 font-bold' : 'text-slate-400 border-slate-700 bg-dark-800'"
                class="px-2 py-1 rounded border hover:border-slate-500 transition-colors flex items-center gap-1 text-[11px] font-mono cursor-pointer"
                title="Oynatma Hızını Değiştir (0.5x - 2.0x)">
                <span>⚡</span>
                <span>{{ playbackSpeed() }}x</span>
              </button>

              <!-- Renk Ayarları (Color Grading) -->
              <button 
                type="button"
                (click)="showColorModal.set(true)" 
                [ngClass]="isColorGraded() ? 'text-amber-400 bg-amber-500/20 border-amber-500/40 font-bold' : 'text-slate-400 border-slate-700 bg-dark-800'"
                class="px-2 py-1 rounded border hover:border-slate-500 transition-colors flex items-center gap-1 text-[11px] font-semibold cursor-pointer"
                title="Renk & Görüntü Ayarları (Parlaklık, Kontrast, Doygunluk, Sıcaklık)">
                <span>🎨</span>
                <span>Renk</span>
              </button>

              <button 
                (click)="toggleSubtitles()" 
                [ngClass]="showSubtitles() ? 'text-amber-300 bg-amber-400/20 border-amber-400/40' : 'text-slate-400 border-slate-700 bg-dark-800'"
                class="px-2.5 py-1 rounded border hover:border-slate-500 transition-colors flex items-center gap-1.5 text-[11px] font-semibold cursor-pointer"
                title="Altyazıyı Aç/Kapat (C)">
                <span>💬</span>
                <span>Altyazı</span>
              </button>
              <button 
                (click)="toggleFullscreen()" 
                class="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-dark-800 border border-slate-800 transition-colors text-xs cursor-pointer" 
                title="Tam Ekran Monitör">
                <span>⛶</span>
              </button>
            </div>
          </div>
        </section>

        <!-- 3. SAĞ PANEL: Context-Aware Inspector (CapCut / Premiere / Photoshop Studio) -->
        <aside class="w-[300px] xl:w-[345px] shrink-0 flex flex-col border-l border-slate-800 bg-dark-900 overflow-y-auto p-3.5 space-y-3.5">
          <!-- 1. Durum: Katman Seçili -->
          <div *ngIf="selectedOverlay()" class="space-y-3">
            <div class="flex items-center justify-between border-b border-slate-800 pb-2">
              <div class="flex items-center gap-1.5">
                <h3 class="text-xs font-bold text-slate-200 uppercase tracking-wider">Stüdyo Özellikleri</h3>
                <span [ngClass]="inspectorData.type === 'text' ? 'bg-sky-500/20 text-sky-400 border-sky-500/30' : 'bg-purple-500/20 text-purple-400 border-purple-500/30'" class="px-2 py-0.5 rounded text-[9px] font-bold uppercase border">
                  {{ inspectorData.type === 'text' ? 'T Tipografi' : '🖼️ Photoshop & AI' }}
                </span>
              </div>
              <button type="button" (click)="selectedOverlayId.set(null)" class="text-slate-500 hover:text-white text-xs px-1.5 py-0.5 rounded hover:bg-dark-800 cursor-pointer" title="Seçimi Kapat">✕</button>
            </div>

            <!-- Ortak: İçerik & Zamanlama -->
            <div class="space-y-2 p-2.5 bg-dark-950/70 rounded-xl border border-slate-800">
              <div class="space-y-1">
                <label class="text-[10px] text-slate-400 uppercase font-semibold">
                  {{ inspectorData.type === 'image' ? 'Görsel / Çıkartma Başlığı' : 'Metin İçeriği' }}
                </label>
                <textarea 
                  [(ngModel)]="inspectorData.content" 
                  (ngModelChange)="onInspectorChange()"
                  class="w-full bg-dark-900 border border-slate-700 rounded-lg p-2 text-xs text-white focus:border-brand-cyan focus:outline-none"
                  rows="2"></textarea>
              </div>
              <div class="grid grid-cols-2 gap-2">
                <div class="space-y-0.5">
                  <label class="text-[9px] text-slate-400 uppercase font-semibold">Başlangıç (sn)</label>
                  <input type="number" step="0.1" [(ngModel)]="inspectorData.timestamp" (ngModelChange)="onInspectorChange()" class="w-full bg-dark-900 border border-slate-700 rounded-lg p-1 text-xs text-white focus:border-brand-cyan font-mono" />
                </div>
                <div class="space-y-0.5">
                  <label class="text-[9px] text-slate-400 uppercase font-semibold">Süre (sn)</label>
                  <input type="number" step="0.1" [(ngModel)]="inspectorData.duration" (ngModelChange)="onInspectorChange()" class="w-full bg-dark-900 border border-slate-700 rounded-lg p-1 text-xs text-white focus:border-brand-cyan font-mono" />
                </div>
              </div>
            </div>

            <!-- ========================================================================= -->
            <!-- A. METİN STÜDYOSU (5 SEKMELİ CAPCUT / PHOTOSHOP TİPOGRAFİ MOTORU)         -->
            <!-- ========================================================================= -->
            <ng-container *ngIf="inspectorData.type === 'text'">
              <!-- 5 Sekmeli Bar -->
              <div class="grid grid-cols-5 gap-1 p-1 bg-dark-950 rounded-xl border border-slate-800 text-[9px] font-bold">
                <button type="button" (click)="textInspectorTab.set('style')" [ngClass]="textInspectorTab() === 'style' ? 'bg-brand-cyan text-slate-950 shadow' : 'text-slate-400 hover:text-white'" class="py-1.5 rounded-lg transition-all cursor-pointer">T Stil</button>
                <button type="button" (click)="textInspectorTab.set('presets')" [ngClass]="textInspectorTab() === 'presets' ? 'bg-brand-cyan text-slate-950 shadow' : 'text-slate-400 hover:text-white'" class="py-1.5 rounded-lg transition-all cursor-pointer">✨ Şablon</button>
                <button type="button" (click)="textInspectorTab.set('effects')" [ngClass]="textInspectorTab() === 'effects' ? 'bg-brand-cyan text-slate-950 shadow' : 'text-slate-400 hover:text-white'" class="py-1.5 rounded-lg transition-all cursor-pointer">🔥 Efekt</button>
                <button type="button" (click)="textInspectorTab.set('anim')" [ngClass]="textInspectorTab() === 'anim' ? 'bg-brand-cyan text-slate-950 shadow' : 'text-slate-400 hover:text-white'" class="py-1.5 rounded-lg transition-all cursor-pointer">🎬 Hareket</button>
                <button type="button" (click)="textInspectorTab.set('transform')" [ngClass]="textInspectorTab() === 'transform' ? 'bg-brand-cyan text-slate-950 shadow' : 'text-slate-400 hover:text-white'" class="py-1.5 rounded-lg transition-all cursor-pointer">📐 3D & Yay</button>
              </div>

              <!-- 1. T STİL SEKMESİ (35+ Font, Renk, Degrade, Kutu Rozet) -->
              <div *ngIf="textInspectorTab() === 'style'" class="space-y-3 p-2.5 bg-dark-950/70 rounded-xl border border-slate-800">
                <!-- Kategorili 35+ Google Font Seçici -->
                <div class="space-y-1">
                  <div class="flex items-center justify-between">
                    <label class="text-[10px] text-slate-400 uppercase font-semibold">Yazı Tipi (35+ Profesyonel Font)</label>
                    <span class="text-[9px] text-brand-cyan font-mono">{{ inspectorData.font }}</span>
                  </div>
                  <select [(ngModel)]="inspectorData.font" (ngModelChange)="onInspectorChange()" class="w-full bg-dark-900 border border-slate-700 rounded-lg p-1.5 text-xs text-white focus:border-brand-cyan outline-none">
                    <optgroup *ngFor="let cat of studio.fontCategories" [label]="cat.label">
                      <option *ngFor="let f of getFontsByCategory(cat.id)" [value]="f.family" [style.fontFamily]="f.family">
                        {{ f.name }}
                      </option>
                    </optgroup>
                  </select>
                </div>

                <!-- Boyut & Harf Aralığı -->
                <div class="grid grid-cols-2 gap-2">
                  <div class="space-y-1">
                    <div class="flex justify-between text-[9px] text-slate-400 font-semibold">
                      <span>Boyut</span>
                      <span class="text-brand-cyan font-mono">{{ inspectorData.fontSize || 48 }}px</span>
                    </div>
                    <input type="range" min="18" max="140" step="2" [(ngModel)]="inspectorData.fontSize" (ngModelChange)="onInspectorChange()" class="w-full accent-brand-cyan cursor-pointer" />
                  </div>
                  <div class="space-y-1">
                    <div class="flex justify-between text-[9px] text-slate-400 font-semibold">
                      <span>Harf Aralığı</span>
                      <span class="text-brand-cyan font-mono">{{ inspectorData.letterSpacing || 0 }}px</span>
                    </div>
                    <input type="range" min="-3" max="20" step="1" [(ngModel)]="inspectorData.letterSpacing" (ngModelChange)="onInspectorChange()" class="w-full accent-brand-cyan cursor-pointer" />
                  </div>
                </div>

                <!-- Dolgu Tipi: Düz Renk vs Degrade (Gradient) -->
                <div class="space-y-2 pt-1 border-t border-slate-800/70">
                  <div class="flex items-center justify-between">
                    <span class="text-[10px] text-slate-400 uppercase font-semibold">Renk & Degrade Dolgu</span>
                    <div class="flex gap-1">
                      <button type="button" (click)="inspectorData.fillType = 'solid'; onInspectorChange()" [ngClass]="(!inspectorData.fillType || inspectorData.fillType === 'solid') ? 'bg-brand-cyan text-slate-950 font-bold' : 'bg-dark-900 text-slate-400'" class="px-2 py-0.5 rounded text-[9px] border border-slate-700 cursor-pointer">Düz</button>
                      <button type="button" (click)="inspectorData.fillType = 'gradient'; onInspectorChange()" [ngClass]="inspectorData.fillType === 'gradient' ? 'bg-brand-cyan text-slate-950 font-bold' : 'bg-dark-900 text-slate-400'" class="px-2 py-0.5 rounded text-[9px] border border-slate-700 cursor-pointer">🌈 Degrade</button>
                    </div>
                  </div>

                  <div *ngIf="!inspectorData.fillType || inspectorData.fillType === 'solid'" class="flex items-center gap-2">
                    <input type="color" [(ngModel)]="inspectorData.color" (ngModelChange)="onInspectorChange()" class="w-8 h-7 rounded border border-slate-700 bg-transparent p-0 cursor-pointer" />
                    <input type="text" [(ngModel)]="inspectorData.color" (ngModelChange)="onInspectorChange()" class="flex-1 bg-dark-900 border border-slate-700 rounded-lg p-1 text-xs text-white font-mono" />
                    <label class="flex items-center gap-1.5 cursor-pointer text-[10px] text-slate-300">
                      <input type="checkbox" [(ngModel)]="inspectorData.allCaps" (ngModelChange)="onInspectorChange()" class="rounded accent-brand-cyan" />
                      <span>BÜYÜK</span>
                    </label>
                  </div>

                  <div *ngIf="inspectorData.fillType === 'gradient'" class="space-y-2 bg-dark-900/80 p-2 rounded-lg border border-slate-800">
                    <div class="grid grid-cols-2 gap-2">
                      <div class="space-y-0.5">
                        <span class="text-[9px] text-slate-400">Başlangıç Rengi</span>
                        <div class="flex items-center gap-1">
                          <input type="color" [(ngModel)]="inspectorData.gradientStart" (ngModelChange)="onInspectorChange()" class="w-6 h-6 rounded border border-slate-700 bg-transparent p-0 cursor-pointer" />
                          <input type="text" [(ngModel)]="inspectorData.gradientStart" (ngModelChange)="onInspectorChange()" class="w-full bg-dark-950 border border-slate-700 rounded p-1 text-[10px] text-white font-mono" />
                        </div>
                      </div>
                      <div class="space-y-0.5">
                        <span class="text-[9px] text-slate-400">Bitiş Rengi</span>
                        <div class="flex items-center gap-1">
                          <input type="color" [(ngModel)]="inspectorData.gradientEnd" (ngModelChange)="onInspectorChange()" class="w-6 h-6 rounded border border-slate-700 bg-transparent p-0 cursor-pointer" />
                          <input type="text" [(ngModel)]="inspectorData.gradientEnd" (ngModelChange)="onInspectorChange()" class="w-full bg-dark-950 border border-slate-700 rounded p-1 text-[10px] text-white font-mono" />
                        </div>
                      </div>
                    </div>
                    <div class="space-y-0.5">
                      <div class="flex justify-between text-[9px] text-slate-400">
                        <span>Degrade Açısı</span>
                        <span class="text-brand-cyan font-mono">{{ inspectorData.gradientAngle ?? 90 }}°</span>
                      </div>
                      <input type="range" min="0" max="360" step="15" [(ngModel)]="inspectorData.gradientAngle" (ngModelChange)="onInspectorChange()" class="w-full accent-brand-cyan cursor-pointer" />
                    </div>
                  </div>
                </div>

                <!-- Kutu / Banner / Fosforlu Kalem Rozet Stili -->
                <div class="space-y-2 pt-2 border-t border-slate-800/70">
                  <span class="text-[10px] text-slate-400 uppercase font-semibold block">🏷️ Arka Plan Kutu / Rozet</span>
                  <div class="grid grid-cols-5 gap-1">
                    <button type="button" (click)="inspectorData.boxStyle = 'none'; onInspectorChange()" [ngClass]="(!inspectorData.boxStyle || inspectorData.boxStyle === 'none') ? 'bg-brand-cyan text-slate-900 font-bold' : 'bg-dark-900 text-slate-400'" class="py-1 rounded text-[9px] border border-slate-700 cursor-pointer">Yok</button>
                    <button type="button" (click)="inspectorData.boxStyle = 'pill'; onInspectorChange()" [ngClass]="inspectorData.boxStyle === 'pill' ? 'bg-brand-cyan text-slate-900 font-bold' : 'bg-dark-900 text-slate-400'" class="py-1 rounded text-[9px] border border-slate-700 cursor-pointer">Pill</button>
                    <button type="button" (click)="inspectorData.boxStyle = 'rounded'; onInspectorChange()" [ngClass]="inspectorData.boxStyle === 'rounded' ? 'bg-brand-cyan text-slate-900 font-bold' : 'bg-dark-900 text-slate-400'" class="py-1 rounded text-[9px] border border-slate-700 cursor-pointer">Kutu</button>
                    <button type="button" (click)="inspectorData.boxStyle = 'badge'; onInspectorChange()" [ngClass]="inspectorData.boxStyle === 'badge' ? 'bg-brand-cyan text-slate-900 font-bold' : 'bg-dark-900 text-slate-400'" class="py-1 rounded text-[9px] border border-slate-700 cursor-pointer">Rozet</button>
                    <button type="button" (click)="inspectorData.boxStyle = 'highlight-marker'; onInspectorChange()" [ngClass]="inspectorData.boxStyle === 'highlight-marker' ? 'bg-brand-cyan text-slate-900 font-bold' : 'bg-dark-900 text-slate-400'" class="py-1 rounded text-[9px] border border-slate-700 cursor-pointer">Marker</button>
                  </div>
                  <div *ngIf="inspectorData.boxStyle && inspectorData.boxStyle !== 'none'" class="grid grid-cols-2 gap-2 pt-1">
                    <div class="space-y-0.5">
                      <label class="text-[9px] text-slate-400">Kutu Rengi</label>
                      <input type="color" [(ngModel)]="inspectorData.boxBgColor" (ngModelChange)="onInspectorChange()" class="w-full h-6 rounded bg-transparent border border-slate-700 p-0 cursor-pointer" />
                    </div>
                    <div class="space-y-0.5">
                      <label class="text-[9px] text-slate-400">Dolgu ({{ inspectorData.boxPadding || 14 }}px)</label>
                      <input type="range" min="4" max="36" step="2" [(ngModel)]="inspectorData.boxPadding" (ngModelChange)="onInspectorChange()" class="w-full accent-brand-cyan" />
                    </div>
                  </div>
                </div>
              </div>

              <!-- 2. ✨ ŞABLON SEKMESİ (12 Viral CapCut / Premiere Hazır Şablonu) -->
              <div *ngIf="textInspectorTab() === 'presets'" class="space-y-2 p-2.5 bg-dark-950/70 rounded-xl border border-slate-800 max-h-[340px] overflow-y-auto">
                <div class="flex items-center justify-between">
                  <span class="text-[10px] font-bold text-slate-300 uppercase">🔥 Viral Metin Şablonları (12 Preset)</span>
                  <span class="text-[9px] text-slate-500">Tek Tıkla Uygula</span>
                </div>
                <div class="grid grid-cols-2 gap-1.5">
                  <button
                    *ngFor="let preset of studio.textPresets"
                    type="button"
                    (click)="applyTextPreset(preset)"
                    class="p-2 rounded-xl border border-slate-800 hover:border-brand-cyan/60 text-left flex flex-col justify-between gap-1 transition-all cursor-pointer group overflow-hidden"
                    [style.background]="preset.previewBg">
                    <span class="text-[11px] font-black truncate drop-shadow" [style.color]="preset.props.color" [style.fontFamily]="preset.props.font">
                      {{ preset.name }}
                    </span>
                    <span class="text-[8px] px-1.5 py-0.5 rounded bg-black/50 text-slate-200 w-fit uppercase font-mono">
                      {{ preset.badge }}
                    </span>
                  </button>
                </div>
              </div>

              <!-- 3. 🔥 EFEKT SEKMESİ (Çift Kontur, Neon Glow, Yönlü Gölge) -->
              <div *ngIf="textInspectorTab() === 'effects'" class="space-y-3 p-2.5 bg-dark-950/70 rounded-xl border border-slate-800">
                <!-- 1. Ana Kontur (Inner Stroke) -->
                <div class="space-y-1">
                  <div class="flex items-center justify-between text-[10px]">
                    <span class="text-slate-300 font-bold">1. Ana Dış Kontur (Stroke)</span>
                    <span class="text-brand-cyan font-mono">{{ inspectorData.strokeWidth || 0 }}px</span>
                  </div>
                  <div class="flex items-center gap-2">
                    <input type="color" [(ngModel)]="inspectorData.strokeColor" (ngModelChange)="onInspectorChange()" class="w-7 h-6 rounded border border-slate-700 bg-transparent p-0 cursor-pointer shrink-0" />
                    <input type="range" min="0" max="12" step="1" [(ngModel)]="inspectorData.strokeWidth" (ngModelChange)="onInspectorChange()" class="flex-1 accent-brand-cyan cursor-pointer" />
                  </div>
                </div>

                <!-- 2. İkinci Kontur (Double Stroke) -->
                <div class="space-y-1 pt-2 border-t border-slate-800/70">
                  <div class="flex items-center justify-between text-[10px]">
                    <span class="text-slate-300 font-bold">2. Çift Kontur (Outer Stroke)</span>
                    <span class="text-amber-300 font-mono">{{ inspectorData.outerStrokeWidth || 0 }}px</span>
                  </div>
                  <div class="flex items-center gap-2">
                    <input type="color" [(ngModel)]="inspectorData.outerStrokeColor" (ngModelChange)="onInspectorChange()" class="w-7 h-6 rounded border border-slate-700 bg-transparent p-0 cursor-pointer shrink-0" />
                    <input type="range" min="0" max="14" step="1" [(ngModel)]="inspectorData.outerStrokeWidth" (ngModelChange)="onInspectorChange()" class="flex-1 accent-amber-400 cursor-pointer" />
                  </div>
                </div>

                <!-- 3. Neon Parıltı (Outer Glow) -->
                <div class="space-y-1.5 pt-2 border-t border-slate-800/70">
                  <div class="flex items-center justify-between">
                    <span class="text-[10px] text-slate-300 font-bold">🔮 Neon Dış Parıltı (Glow)</span>
                    <input type="checkbox" [(ngModel)]="inspectorData.glowEnabled" (ngModelChange)="onInspectorChange()" class="rounded accent-fuchsia-500 cursor-pointer" />
                  </div>
                  <div *ngIf="inspectorData.glowEnabled" class="flex items-center gap-2">
                    <input type="color" [(ngModel)]="inspectorData.glowColor" (ngModelChange)="onInspectorChange()" class="w-7 h-6 rounded border border-slate-700 bg-transparent p-0 cursor-pointer shrink-0" />
                    <input type="range" min="4" max="40" step="2" [(ngModel)]="inspectorData.glowRadius" (ngModelChange)="onInspectorChange()" class="flex-1 accent-fuchsia-400 cursor-pointer" />
                    <span class="text-[9px] font-mono text-fuchsia-300 w-7">{{ inspectorData.glowRadius || 16 }}px</span>
                  </div>
                </div>

                <!-- 4. Yönlü Gölge (Directional Drop Shadow) -->
                <div class="space-y-1.5 pt-2 border-t border-slate-800/70">
                  <div class="flex items-center justify-between text-[10px]">
                    <span class="text-slate-300 font-bold">🌑 Yönlü Gölge (Drop Shadow)</span>
                    <input type="color" [(ngModel)]="inspectorData.shadowColor" (ngModelChange)="onInspectorChange()" class="w-6 h-5 rounded border border-slate-700 bg-transparent p-0 cursor-pointer" />
                  </div>
                  <div class="grid grid-cols-3 gap-1.5 text-[9px] text-slate-400">
                    <div>
                      <span>Mesafe ({{ inspectorData.shadowDistance ?? 4 }})</span>
                      <input type="range" min="0" max="24" step="1" [(ngModel)]="inspectorData.shadowDistance" (ngModelChange)="onInspectorChange()" class="w-full accent-brand-cyan" />
                    </div>
                    <div>
                      <span>Açı ({{ inspectorData.shadowAngle ?? 45 }}°)</span>
                      <input type="range" min="0" max="360" step="15" [(ngModel)]="inspectorData.shadowAngle" (ngModelChange)="onInspectorChange()" class="w-full accent-brand-cyan" />
                    </div>
                    <div>
                      <span>Bulanık ({{ inspectorData.shadowBlur ?? 4 }})</span>
                      <input type="range" min="0" max="24" step="1" [(ngModel)]="inspectorData.shadowBlur" (ngModelChange)="onInspectorChange()" class="w-full accent-brand-cyan" />
                    </div>
                  </div>
                </div>
              </div>

              <!-- 4. 🎬 HAREKET & KEYFRAME SEKMESİ -->
              <div *ngIf="textInspectorTab() === 'anim'" class="space-y-3 p-2.5 bg-dark-950/70 rounded-xl border border-slate-800">
                <div class="grid grid-cols-2 gap-2">
                  <div class="space-y-1">
                    <label class="text-[9px] text-slate-400 uppercase font-semibold">Giriş Animasyonu</label>
                    <select [(ngModel)]="inspectorData.animation" (ngModelChange)="onInspectorChange()" class="w-full bg-dark-900 border border-slate-700 rounded-lg p-1.5 text-xs text-white outline-none">
                      <option value="none">Yok</option>
                      <option value="pop-up">💥 Pop-Up (Sıçrama)</option>
                      <option value="bounce">🏀 Elastic Bounce</option>
                      <option value="fade">✨ Yumuşak Belirme</option>
                      <option value="slide-up">⬆️ Aşağıdan Kayma</option>
                      <option value="slide-down">⬇️ Yukarıdan Kayma</option>
                      <option value="slide-left">⬅️ Sağdan Kayma</option>
                      <option value="slide-right">➡️ Soldan Kayma</option>
                      <option value="zoom-crash">🚀 Zoom Crash</option>
                      <option value="typewriter">⌨️ Daktilo</option>
                      <option value="blur-in">🌫️ Sinematik Odak</option>
                      <option value="glitch">⚡ Siber Glitch</option>
                    </select>
                  </div>
                  <div class="space-y-1">
                    <label class="text-[9px] text-slate-400 uppercase font-semibold">Çıkış Animasyonu</label>
                    <select [(ngModel)]="inspectorData.exitAnimation" (ngModelChange)="onInspectorChange()" class="w-full bg-dark-900 border border-slate-700 rounded-lg p-1.5 text-xs text-white outline-none">
                      <option value="none">Yok</option>
                      <option value="fade">Fade Out</option>
                      <option value="scale-out">Scale Out (Küçül)</option>
                      <option value="slide-down">Aşağı Kayarak Çık</option>
                    </select>
                  </div>
                </div>

                <!-- Sürekli Döngü (Loop) Animasyonu -->
                <div class="space-y-1">
                  <label class="text-[9px] text-slate-400 uppercase font-semibold">🔄 Sürekli Döngü (Loop) Efekti</label>
                  <select [(ngModel)]="inspectorData.loopAnimation" (ngModelChange)="onInspectorChange()" class="w-full bg-dark-900 border border-slate-700 rounded-lg p-1.5 text-xs text-white outline-none">
                    <option value="none">Sabit (Döngü Yok)</option>
                    <option value="pulse">💓 Kalp Atışı (Pulse)</option>
                    <option value="float">☁️ Havada Süzülme (Float)</option>
                    <option value="wiggle">🎸 Sallanma (Wiggle)</option>
                    <option value="shake">🔥 Deprem Titreme (Shake)</option>
                    <option value="neon-flicker">⚡ Neon Titreme (Flicker)</option>
                    <option value="pendulum">🕰️ Sarkaç (Pendulum)</option>
                  </select>
                </div>

                <!-- Keyframe (◆ Anahtar Kare) Sistemi -->
                <div class="p-2 bg-dark-900 rounded-lg border border-slate-800 space-y-2">
                  <div class="flex items-center justify-between">
                    <span class="text-[10px] font-bold text-amber-300 flex items-center gap-1">◆ Keyframe (Anahtar Kare)</span>
                    <button type="button" (click)="addKeyFrameToSelectedOverlay()" class="px-2 py-0.5 rounded bg-amber-500/20 hover:bg-amber-500/40 text-amber-300 border border-amber-500/40 text-[9px] font-bold cursor-pointer">
                      + ◆ Bu Ana Ekle
                    </button>
                  </div>
                  <p class="text-[9px] text-slate-400 leading-tight">
                    Farklı saniyelerde konum/boyut belirleyerek katmanı ekranda otomatik hareket ettirin.
                  </p>
                  <div *ngIf="inspectorData.keyframes && inspectorData.keyframes.length > 0" class="space-y-1 max-h-24 overflow-y-auto">
                    <div *ngFor="let kf of inspectorData.keyframes; let i = index" class="flex items-center justify-between text-[9px] bg-dark-950 px-2 py-1 rounded border border-slate-800 font-mono">
                      <span class="text-amber-300">◆ +{{ kf.timeOffset.toFixed(1) }}sn</span>
                      <span class="text-slate-400">X:{{ kf.x.toFixed(0) }}% Y:{{ kf.y.toFixed(0) }}%</span>
                      <button type="button" (click)="removeKeyframeFromSelectedOverlay(i)" class="text-rose-400 hover:text-rose-200 cursor-pointer">✕</button>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 5. 📐 3D & YAY (PHOTOSHOP WARP & PERSPECTIVE) SEKMESİ -->
              <div *ngIf="textInspectorTab() === 'transform'" class="space-y-3 p-2.5 bg-dark-950/70 rounded-xl border border-slate-800">
                <!-- Yay / Kavisli Metin (Curved Text Arc) -->
                <div class="space-y-1">
                  <div class="flex justify-between items-center text-[10px]">
                    <span class="text-slate-200 font-bold">🌈 Yay / Kavisli Yazı (Arc Bend)</span>
                    <span class="text-brand-cyan font-mono font-bold">{{ inspectorData.curveBend || 0 }}%</span>
                  </div>
                  <div class="flex items-center gap-2">
                    <input type="range" min="-100" max="100" step="5" [(ngModel)]="inspectorData.curveBend" (ngModelChange)="onInspectorChange()" class="flex-1 accent-brand-cyan cursor-pointer" />
                    <button type="button" (click)="inspectorData.curveBend = 0; onInspectorChange()" class="px-1.5 py-0.5 text-[9px] bg-dark-900 border border-slate-700 rounded text-slate-400 hover:text-white cursor-pointer">0</button>
                  </div>
                </div>

                <!-- 3D Perspektif (RotateX, RotateY, Rotation, SkewX) -->
                <div class="grid grid-cols-2 gap-2 pt-2 border-t border-slate-800/70 text-[9px] text-slate-400">
                  <div>
                    <div class="flex justify-between"><span>3D Eğim X</span><span class="text-brand-cyan font-mono">{{ inspectorData.rotateX || 0 }}°</span></div>
                    <input type="range" min="-60" max="60" step="5" [(ngModel)]="inspectorData.rotateX" (ngModelChange)="onInspectorChange()" class="w-full accent-brand-cyan" />
                  </div>
                  <div>
                    <div class="flex justify-between"><span>3D Dönüş Y</span><span class="text-brand-cyan font-mono">{{ inspectorData.rotateY || 0 }}°</span></div>
                    <input type="range" min="-60" max="60" step="5" [(ngModel)]="inspectorData.rotateY" (ngModelChange)="onInspectorChange()" class="w-full accent-brand-cyan" />
                  </div>
                  <div>
                    <div class="flex justify-between"><span>2D Döndür</span><span class="text-brand-cyan font-mono">{{ inspectorData.rotation || 0 }}°</span></div>
                    <input type="range" min="-180" max="180" step="5" [(ngModel)]="inspectorData.rotation" (ngModelChange)="onInspectorChange()" class="w-full accent-brand-cyan" />
                  </div>
                  <div>
                    <div class="flex justify-between"><span>İtalik Eğim (Skew)</span><span class="text-brand-cyan font-mono">{{ inspectorData.skewX || 0 }}°</span></div>
                    <input type="range" min="-35" max="35" step="5" [(ngModel)]="inspectorData.skewX" (ngModelChange)="onInspectorChange()" class="w-full accent-brand-cyan" />
                  </div>
                </div>

                <!-- X / Y Konum & Kanal -->
                <div class="grid grid-cols-2 gap-2 pt-2 border-t border-slate-800/70">
                  <div class="space-y-0.5">
                    <label class="text-[9px] text-slate-400 uppercase font-semibold">X Konum (%)</label>
                    <input type="number" step="0.5" [(ngModel)]="inspectorData.positionX" (ngModelChange)="onInspectorChange()" class="w-full bg-dark-900 border border-slate-700 rounded-lg p-1 text-xs text-white font-mono" />
                  </div>
                  <div class="space-y-0.5">
                    <label class="text-[9px] text-slate-400 uppercase font-semibold">Y Konum (%)</label>
                    <input type="number" step="0.5" [(ngModel)]="inspectorData.positionY" (ngModelChange)="onInspectorChange()" class="w-full bg-dark-900 border border-slate-700 rounded-lg p-1 text-xs text-white font-mono" />
                  </div>
                </div>
              </div>
            </ng-container>

            <!-- ========================================================================= -->
            <!-- B. GÖRSEL & AI STICKER STÜDYOSU (4 SEKMELİ PHOTOSHOP MOTORU)              -->
            <!-- ========================================================================= -->
            <ng-container *ngIf="inspectorData.type === 'image'">
              <!-- 4 Sekmeli Bar -->
              <div class="grid grid-cols-4 gap-1 p-1 bg-dark-950 rounded-xl border border-slate-800 text-[9px] font-bold">
                <button type="button" (click)="imageInspectorTab.set('ai')" [ngClass]="imageInspectorTab() === 'ai' ? 'bg-purple-500 text-white shadow' : 'text-slate-400 hover:text-white'" class="py-1.5 rounded-lg transition-all cursor-pointer">✂️ AI Sticker</button>
                <button type="button" (click)="imageInspectorTab.set('adjust')" [ngClass]="imageInspectorTab() === 'adjust' ? 'bg-purple-500 text-white shadow' : 'text-slate-400 hover:text-white'" class="py-1.5 rounded-lg transition-all cursor-pointer">🎨 Renk/Işık</button>
                <button type="button" (click)="imageInspectorTab.set('transform')" [ngClass]="imageInspectorTab() === 'transform' ? 'bg-purple-500 text-white shadow' : 'text-slate-400 hover:text-white'" class="py-1.5 rounded-lg transition-all cursor-pointer">📐 Boyut/3D</button>
                <button type="button" (click)="imageInspectorTab.set('anim')" [ngClass]="imageInspectorTab() === 'anim' ? 'bg-purple-500 text-white shadow' : 'text-slate-400 hover:text-white'" class="py-1.5 rounded-lg transition-all cursor-pointer">🎬 Hareket</button>
              </div>

              <!-- 1. ✂️ AI STICKER & MASKE SEKMESİ -->
              <div *ngIf="imageInspectorTab() === 'ai'" class="space-y-3 p-2.5 bg-dark-950/70 rounded-xl border border-slate-800">
                <!-- Canlı AI Arka Plan Kaldırma Butonu -->
                <div class="p-2.5 rounded-xl bg-gradient-to-br from-purple-950/60 to-indigo-950/40 border border-purple-500/40 space-y-2">
                  <div class="flex items-center justify-between">
                    <div>
                      <span class="text-xs font-bold text-white block">🪄 AI Arka Plan Kaldırıcı</span>
                      <span class="text-[9px] text-purple-200/80">Canlı önizlemede & renderda dekupe</span>
                    </div>
                    <input type="checkbox" [(ngModel)]="inspectorData.removeBg" (ngModelChange)="onInspectorChange()" class="rounded accent-purple-500 cursor-pointer" title="Render sırasında rembg AI kullan" />
                  </div>
                  <div class="flex gap-1.5">
                    <button
                      type="button"
                      [disabled]="isRemovingBgNow()"
                      (click)="removeBackgroundNow()"
                      class="flex-1 py-1.5 px-2 rounded-lg bg-purple-600 hover:bg-purple-500 text-white font-bold text-[10px] transition-all cursor-pointer shadow flex items-center justify-center gap-1 disabled:opacity-50">
                      <span>⚡</span>
                      <span>{{ isRemovingBgNow() ? 'Dekupe Ediliyor...' : 'Şimdi Arka Planı Sil (Canlı)' }}</span>
                    </button>
                    <button
                      *ngIf="inspectorData.originalSource"
                      type="button"
                      (click)="restoreOriginalBackground()"
                      class="px-2 py-1.5 rounded-lg bg-dark-800 hover:bg-slate-700 text-slate-300 text-[10px] border border-slate-700 cursor-pointer"
                      title="Orijinal Görsele Dön">
                      ↩
                    </button>
                  </div>
                </div>

                <!-- Gerçek Silüet Sticker Konturu -->
                <div class="space-y-1.5 pt-1 border-t border-slate-800/60">
                  <div class="flex items-center justify-between">
                    <span class="text-xs text-slate-200 font-semibold">🏷️ Silüet Sticker Konturu</span>
                    <input type="checkbox" [(ngModel)]="inspectorData.stickerBorder" (ngModelChange)="onInspectorChange()" class="rounded accent-brand-cyan cursor-pointer" />
                  </div>
                  <div *ngIf="inspectorData.stickerBorder" class="grid grid-cols-2 gap-2 pt-1">
                    <div class="space-y-0.5">
                      <span class="text-[9px] text-slate-400">Kalınlık ({{ inspectorData.stickerBorderWidth || 6 }}px)</span>
                      <input type="range" min="2" max="18" step="1" [(ngModel)]="inspectorData.stickerBorderWidth" (ngModelChange)="onInspectorChange()" class="w-full accent-brand-cyan" />
                    </div>
                    <div class="space-y-0.5">
                      <span class="text-[9px] text-slate-400">Kontur Rengi</span>
                      <input type="color" [(ngModel)]="inspectorData.stickerBorderColor" (ngModelChange)="onInspectorChange()" class="w-full h-6 rounded bg-transparent border border-slate-700 p-0 cursor-pointer" />
                    </div>
                  </div>
                </div>

                <!-- Kırpma / Şekil Maskesi (7 Geometrik Şekil) -->
                <div class="space-y-1.5 pt-1 border-t border-slate-800/60">
                  <span class="text-[10px] text-slate-400 uppercase font-semibold block">Kırpma / Şekil Maskesi</span>
                  <div class="grid grid-cols-4 gap-1">
                    <button type="button" (click)="inspectorData.maskShape = 'rect'; onInspectorChange()" [ngClass]="(!inspectorData.maskShape || inspectorData.maskShape === 'rect') ? 'bg-purple-500 text-white font-bold' : 'bg-dark-900 text-slate-400'" class="py-1 rounded text-[9px] border border-slate-700 cursor-pointer">Tam</button>
                    <button type="button" (click)="inspectorData.maskShape = 'rounded'; onInspectorChange()" [ngClass]="inspectorData.maskShape === 'rounded' ? 'bg-purple-500 text-white font-bold' : 'bg-dark-900 text-slate-400'" class="py-1 rounded text-[9px] border border-slate-700 cursor-pointer">Yuvarlak</button>
                    <button type="button" (click)="inspectorData.maskShape = 'circle'; onInspectorChange()" [ngClass]="inspectorData.maskShape === 'circle' ? 'bg-purple-500 text-white font-bold' : 'bg-dark-900 text-slate-400'" class="py-1 rounded text-[9px] border border-slate-700 cursor-pointer">Daire</button>
                    <button type="button" (click)="inspectorData.maskShape = 'star'; onInspectorChange()" [ngClass]="inspectorData.maskShape === 'star' ? 'bg-purple-500 text-white font-bold' : 'bg-dark-900 text-slate-400'" class="py-1 rounded text-[9px] border border-slate-700 cursor-pointer">⭐ Yıldız</button>
                    <button type="button" (click)="inspectorData.maskShape = 'heart'; onInspectorChange()" [ngClass]="inspectorData.maskShape === 'heart' ? 'bg-purple-500 text-white font-bold' : 'bg-dark-900 text-slate-400'" class="py-1 rounded text-[9px] border border-slate-700 cursor-pointer">❤️ Kalp</button>
                    <button type="button" (click)="inspectorData.maskShape = 'hexagon'; onInspectorChange()" [ngClass]="inspectorData.maskShape === 'hexagon' ? 'bg-purple-500 text-white font-bold' : 'bg-dark-900 text-slate-400'" class="py-1 rounded text-[9px] border border-slate-700 cursor-pointer">⬡ Altıgen</button>
                    <button type="button" (click)="inspectorData.maskShape = 'diamond'; onInspectorChange()" [ngClass]="inspectorData.maskShape === 'diamond' ? 'bg-purple-500 text-white font-bold' : 'bg-dark-900 text-slate-400'" class="py-1 rounded text-[9px] border border-slate-700 cursor-pointer">◆ Elmas</button>
                  </div>
                </div>

                <!-- Görsel URL -->
                <div class="space-y-1 pt-1 border-t border-slate-800/60">
                  <div class="flex items-center justify-between">
                    <label class="text-[9px] text-slate-400 uppercase font-semibold">Görsel / GIF URL</label>
                    <button type="button" (click)="activeTab.set('media')" class="text-[9px] font-bold text-brand-cyan hover:underline cursor-pointer">📁 Medyadan Seç</button>
                  </div>
                  <input type="text" [(ngModel)]="inspectorData.source" (ngModelChange)="onInspectorChange()" class="w-full bg-dark-900 border border-slate-700 rounded-lg p-1 text-[11px] text-white focus:border-brand-cyan focus:outline-none" placeholder="https://..." />
                </div>
              </div>

              <!-- 2. 🎨 PHOTOSHOP RENK & IŞIK SEKMESİ -->
              <div *ngIf="imageInspectorTab() === 'adjust'" class="space-y-2.5 p-2.5 bg-dark-950/70 rounded-xl border border-slate-800">
                <div class="flex items-center justify-between border-b border-slate-800 pb-1">
                  <span class="text-[10px] font-bold text-slate-300 uppercase">🎨 Katman Renk & Işık (Photoshop)</span>
                  <button type="button" (click)="resetImageAdjustments()" class="text-[9px] text-amber-400 hover:underline cursor-pointer">Sıfırla</button>
                </div>

                <div class="grid grid-cols-2 gap-2 text-[9px] text-slate-400">
                  <div>
                    <div class="flex justify-between"><span>☀️ Parlaklık</span><span class="text-purple-300 font-mono">{{ inspectorData.brightness || 0 }}</span></div>
                    <input type="range" min="-80" max="80" step="5" [(ngModel)]="inspectorData.brightness" (ngModelChange)="onInspectorChange()" class="w-full accent-purple-500" />
                  </div>
                  <div>
                    <div class="flex justify-between"><span>🌓 Kontrast</span><span class="text-purple-300 font-mono">{{ inspectorData.contrast || 0 }}</span></div>
                    <input type="range" min="-80" max="80" step="5" [(ngModel)]="inspectorData.contrast" (ngModelChange)="onInspectorChange()" class="w-full accent-purple-500" />
                  </div>
                  <div>
                    <div class="flex justify-between"><span>🌈 Doygunluk</span><span class="text-purple-300 font-mono">{{ inspectorData.saturation || 0 }}</span></div>
                    <input type="range" min="-100" max="100" step="5" [(ngModel)]="inspectorData.saturation" (ngModelChange)="onInspectorChange()" class="w-full accent-purple-500" />
                  </div>
                  <div>
                    <div class="flex justify-between"><span>🌡️ Sıcaklık</span><span class="text-purple-300 font-mono">{{ inspectorData.warmth || 0 }}</span></div>
                    <input type="range" min="-80" max="80" step="5" [(ngModel)]="inspectorData.warmth" (ngModelChange)="onInspectorChange()" class="w-full accent-purple-500" />
                  </div>
                  <div>
                    <div class="flex justify-between"><span>🎨 Ton (Hue)</span><span class="text-purple-300 font-mono">{{ inspectorData.hue || 0 }}°</span></div>
                    <input type="range" min="-180" max="180" step="10" [(ngModel)]="inspectorData.hue" (ngModelChange)="onInspectorChange()" class="w-full accent-purple-500" />
                  </div>
                  <div>
                    <div class="flex justify-between"><span>💧 Bulanıklık</span><span class="text-purple-300 font-mono">{{ inspectorData.blur || 0 }}px</span></div>
                    <input type="range" min="0" max="20" step="1" [(ngModel)]="inspectorData.blur" (ngModelChange)="onInspectorChange()" class="w-full accent-purple-500" />
                  </div>
                  <div>
                    <div class="flex justify-between"><span>🔪 Keskinlik</span><span class="text-purple-300 font-mono">{{ inspectorData.sharpen || 0 }}</span></div>
                    <input type="range" min="0" max="100" step="10" [(ngModel)]="inspectorData.sharpen" (ngModelChange)="onInspectorChange()" class="w-full accent-purple-500" />
                  </div>
                  <div>
                    <div class="flex justify-between"><span>👻 Opaklık</span><span class="text-purple-300 font-mono">%{{ inspectorData.opacity ?? 100 }}</span></div>
                    <input type="range" min="10" max="100" step="5" [(ngModel)]="inspectorData.opacity" (ngModelChange)="onInspectorChange()" class="w-full accent-purple-500" />
                  </div>
                </div>
              </div>

              <!-- 3. 📐 BOYUT, 3D & KARIŞIM MODU SEKMESİ -->
              <div *ngIf="imageInspectorTab() === 'transform'" class="space-y-3 p-2.5 bg-dark-950/70 rounded-xl border border-slate-800">
                <div class="grid grid-cols-2 gap-2 text-[9px] text-slate-400">
                  <div>
                    <div class="flex justify-between"><span>Ölçek (Scale)</span><span class="text-brand-cyan font-mono">{{ inspectorData.scale || 1.0 }}x</span></div>
                    <input type="range" min="0.2" max="3.0" step="0.05" [(ngModel)]="inspectorData.scale" (ngModelChange)="onInspectorChange()" class="w-full accent-brand-cyan" />
                  </div>
                  <div>
                    <div class="flex justify-between"><span>Döndür</span><span class="text-brand-cyan font-mono">{{ inspectorData.rotation || 0 }}°</span></div>
                    <input type="range" min="-180" max="180" step="5" [(ngModel)]="inspectorData.rotation" (ngModelChange)="onInspectorChange()" class="w-full accent-brand-cyan" />
                  </div>
                </div>

                <!-- Aynalama (Flip H / Flip V) & Karışım Modu -->
                <div class="grid grid-cols-2 gap-2 pt-1 border-t border-slate-800/60">
                  <button type="button" (click)="inspectorData.flipH = !inspectorData.flipH; onInspectorChange()" [ngClass]="inspectorData.flipH ? 'bg-purple-500/30 border-purple-400 text-purple-200 font-bold' : 'bg-dark-900 border-slate-700 text-slate-400'" class="py-1.5 rounded-lg border text-[10px] cursor-pointer">
                    ↔️ Yatay Çevir
                  </button>
                  <button type="button" (click)="inspectorData.flipV = !inspectorData.flipV; onInspectorChange()" [ngClass]="inspectorData.flipV ? 'bg-purple-500/30 border-purple-400 text-purple-200 font-bold' : 'bg-dark-900 border-slate-700 text-slate-400'" class="py-1.5 rounded-lg border text-[10px] cursor-pointer">
                    ↕️ Dikey Çevir
                  </button>
                </div>

                <div class="space-y-1">
                  <label class="text-[9px] text-slate-400 uppercase font-semibold">Karışım Modu (Blend Mode)</label>
                  <select [(ngModel)]="inspectorData.blendMode" (ngModelChange)="onInspectorChange()" class="w-full bg-dark-900 border border-slate-700 rounded-lg p-1.5 text-xs text-white outline-none">
                    <option value="normal">Normal</option>
                    <option value="screen">Screen (Işık Ekle)</option>
                    <option value="multiply">Multiply (Koyulaştır)</option>
                    <option value="overlay">Overlay (Kontrast)</option>
                  </select>
                </div>

                <!-- X / Y Konum -->
                <div class="grid grid-cols-2 gap-2 pt-1 border-t border-slate-800/60">
                  <div class="space-y-0.5">
                    <label class="text-[9px] text-slate-400 uppercase font-semibold">X Konum (%)</label>
                    <input type="number" step="0.5" [(ngModel)]="inspectorData.positionX" (ngModelChange)="onInspectorChange()" class="w-full bg-dark-900 border border-slate-700 rounded-lg p-1 text-xs text-white font-mono" />
                  </div>
                  <div class="space-y-0.5">
                    <label class="text-[9px] text-slate-400 uppercase font-semibold">Y Konum (%)</label>
                    <input type="number" step="0.5" [(ngModel)]="inspectorData.positionY" (ngModelChange)="onInspectorChange()" class="w-full bg-dark-900 border border-slate-700 rounded-lg p-1 text-xs text-white font-mono" />
                  </div>
                </div>
              </div>

              <!-- 4. 🎬 GÖRSEL HAREKET & KEYFRAME SEKMESİ -->
              <div *ngIf="imageInspectorTab() === 'anim'" class="space-y-3 p-2.5 bg-dark-950/70 rounded-xl border border-slate-800">
                <div class="grid grid-cols-2 gap-2">
                  <div class="space-y-1">
                    <label class="text-[9px] text-slate-400 uppercase font-semibold">Giriş</label>
                    <select [(ngModel)]="inspectorData.animation" (ngModelChange)="onInspectorChange()" class="w-full bg-dark-900 border border-slate-700 rounded-lg p-1.5 text-xs text-white outline-none">
                      <option value="none">Yok</option>
                      <option value="pop-up">💥 Pop-Up</option>
                      <option value="bounce">🏀 Bounce</option>
                      <option value="fade">✨ Fade In</option>
                      <option value="slide-up">⬆️ Slide Up</option>
                      <option value="slide-left">⬅️ Slide Left</option>
                      <option value="zoom-crash">🚀 Zoom Crash</option>
                    </select>
                  </div>
                  <div class="space-y-1">
                    <label class="text-[9px] text-slate-400 uppercase font-semibold">Döngü (Loop)</label>
                    <select [(ngModel)]="inspectorData.loopAnimation" (ngModelChange)="onInspectorChange()" class="w-full bg-dark-900 border border-slate-700 rounded-lg p-1.5 text-xs text-white outline-none">
                      <option value="none">Sabit</option>
                      <option value="pulse">💓 Pulse</option>
                      <option value="float">☁️ Float</option>
                      <option value="wiggle">🎸 Wiggle</option>
                      <option value="shake">🔥 Shake</option>
                      <option value="pendulum">🕰️ Pendulum</option>
                    </select>
                  </div>
                </div>

                <!-- Keyframe -->
                <div class="p-2 bg-dark-900 rounded-lg border border-slate-800 space-y-1.5">
                  <div class="flex items-center justify-between">
                    <span class="text-[10px] font-bold text-amber-300">◆ Keyframe Hareketi</span>
                    <button type="button" (click)="addKeyFrameToSelectedOverlay()" class="px-2 py-0.5 rounded bg-amber-500/20 hover:bg-amber-500/40 text-amber-300 border border-amber-500/40 text-[9px] font-bold cursor-pointer">
                      + ◆ Keyframe Ekle
                    </button>
                  </div>
                  <div *ngIf="inspectorData.keyframes && inspectorData.keyframes.length > 0" class="space-y-1 max-h-24 overflow-y-auto">
                    <div *ngFor="let kf of inspectorData.keyframes; let i = index" class="flex items-center justify-between text-[9px] bg-dark-950 px-2 py-1 rounded border border-slate-800 font-mono">
                      <span class="text-amber-300">◆ +{{ kf.timeOffset.toFixed(1) }}sn</span>
                      <span class="text-slate-400">X:{{ kf.x.toFixed(0) }}% Y:{{ kf.y.toFixed(0) }}%</span>
                      <button type="button" (click)="removeKeyframeFromSelectedOverlay(i)" class="text-rose-400 hover:text-rose-200 cursor-pointer">✕</button>
                    </div>
                  </div>
                </div>
              </div>
            </ng-container>

            <!-- Katman Sırası / Track Kanalı -->
            <div class="p-2 bg-dark-950 rounded-xl border border-slate-800 flex items-center justify-between">
              <span class="text-[10px] text-slate-400 uppercase font-semibold">🥞 Kanal:</span>
              <div class="flex items-center gap-1 flex-wrap">
                <button 
                  *ngFor="let t of overlayTrackNumbers()" 
                  type="button"
                  (click)="setOverlayTrack(selectedOverlayId()!, t)"
                  [ngClass]="(inspectorData.trackId || 1) === t ? 'bg-sky-500 text-white font-bold border-sky-400' : 'bg-dark-800 text-slate-400 hover:text-white border-slate-700'"
                  class="px-2 py-0.5 rounded text-[10px] border transition-all cursor-pointer font-mono">
                  T{{ t }}
                </button>
                <button type="button" (click)="addTrackLane()" class="px-1.5 py-0.5 rounded text-[10px] bg-dark-800 text-sky-400 border border-slate-700 font-semibold cursor-pointer">+</button>
              </div>
            </div>

            <!-- Kaydet / Çoğalt / Sil Butonları -->
            <div class="pt-1 border-t border-slate-800 flex flex-col gap-1.5">
              <button (click)="saveInspector()" class="w-full py-2 bg-brand-cyan hover:bg-cyan-400 text-slate-900 font-bold rounded-lg transition-colors shadow-glow-sm cursor-pointer text-xs">
                ✓ Katman Ayarlarını Kaydet
              </button>
              <div class="flex gap-2">
                <button (click)="duplicateOverlay(selectedOverlayId()!)" class="flex-1 py-1.5 bg-dark-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-lg text-xs font-semibold cursor-pointer">
                  Çoğalt (Ctrl+D)
                </button>
                <button (click)="removeOverlay(selectedOverlayId()!)" class="px-3 py-1.5 bg-rose-600/20 hover:bg-rose-600/40 text-rose-300 border border-rose-600/40 rounded-lg text-xs font-semibold cursor-pointer">
                  Sil (Del)
                </button>
              </div>
            </div>
          </div>

          <!-- 1.5. Durum: Altyazı Seçili -->
          <div *ngIf="!selectedOverlay() && selectedSubtitle()" class="space-y-4">
            <div class="flex items-center justify-between border-b border-slate-800 pb-2">
              <div class="flex items-center gap-2">
                <h3 class="text-xs font-bold text-slate-200 uppercase tracking-wider">Altyazı Özellikleri</h3>
                <span class="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-amber-500/20 text-amber-300 border border-amber-500/30">
                  Whisper Altyazı
                </span>
              </div>
              <button 
                type="button" 
                (click)="clearSubtitleSelection()" 
                class="text-slate-400 hover:text-white text-xs px-1.5 py-0.5 rounded hover:bg-dark-800"
                title="Seçimi Kapat">
                ✕
              </button>
            </div>

            <!-- Metin İçeriği -->
            <div class="space-y-1">
              <div class="flex items-center justify-between">
                <label class="text-[10px] text-slate-400 uppercase font-semibold">Altyazı Metni</label>
                <span class="text-[10px] text-slate-500 font-mono">{{ subtitleInspectorData.text.length || 0 }} kr</span>
              </div>
              <textarea 
                [(ngModel)]="subtitleInspectorData.text" 
                (ngModelChange)="onSubtitleTextChange()"
                class="w-full bg-dark-950 border border-slate-700 rounded-lg p-2 text-xs text-white focus:border-brand-cyan focus:outline-none focus:ring-1 focus:ring-brand-cyan leading-relaxed"
                rows="3"
                placeholder="Altyazı metnini girin..."></textarea>
            </div>

            <!-- Zamanlama (Başlangıç, Bitiş, Süre) -->
            <div class="p-3 bg-dark-950 rounded-xl border border-slate-800 space-y-2.5">
              <div class="flex items-center justify-between">
                <span class="text-[10px] text-slate-400 uppercase font-semibold">⏱ Zamanlama Ayarı</span>
                <span class="text-[10px] font-mono text-brand-cyan font-bold">
                  {{ subtitleInspectorData.duration }} sn
                </span>
              </div>

              <div class="grid grid-cols-2 gap-2">
                <div class="space-y-1">
                  <label class="text-[9px] text-slate-400 uppercase font-semibold">Başlangıç (sn)</label>
                  <input 
                    type="number" 
                    step="0.05" 
                    [(ngModel)]="subtitleInspectorData.start" 
                    (ngModelChange)="onSubtitleStartChange()"
                    class="w-full bg-dark-900 border border-slate-700 rounded-lg p-1.5 text-xs text-white focus:border-brand-cyan font-mono" />
                </div>
                <div class="space-y-1">
                  <label class="text-[9px] text-slate-400 uppercase font-semibold">Bitiş (sn)</label>
                  <input 
                    type="number" 
                    step="0.05" 
                    [(ngModel)]="subtitleInspectorData.end" 
                    (ngModelChange)="onSubtitleEndChange()"
                    class="w-full bg-dark-900 border border-slate-700 rounded-lg p-1.5 text-xs text-white focus:border-brand-cyan font-mono" />
                </div>
              </div>

              <div class="space-y-1">
                <div class="flex justify-between text-[9px] text-slate-400 uppercase font-semibold">
                  <span>Süre (sn)</span>
                  <span class="font-mono text-amber-300">{{ subtitleInspectorData.duration }}s</span>
                </div>
                <input 
                  type="number" 
                  step="0.1" 
                  min="0.1" 
                  [(ngModel)]="subtitleInspectorData.duration" 
                  (ngModelChange)="onSubtitleDurationChange()"
                  class="w-full bg-dark-900 border border-slate-700 rounded-lg p-1.5 text-xs text-white focus:border-brand-cyan font-mono" />
              </div>
            </div>

            <!-- Görünüm & Konum (Tüm Altyazılar İçin Canlı) -->
            <div class="space-y-3 p-3 bg-dark-950/70 rounded-xl border border-slate-800/80">
              <div class="flex items-center justify-between border-b border-slate-800 pb-1.5">
                <span class="text-[10px] text-slate-300 uppercase font-bold tracking-wider">🎨 Altyazı Stili & Şablonlar (CapCut)</span>
                <span class="text-[9px] text-brand-cyan font-mono font-bold">{{ subtitlePreset() }}</span>
              </div>

              <!-- Hazır Stil Preset Kartları -->
              <div class="space-y-1.5">
                <label class="text-[10px] text-slate-400 uppercase font-semibold">Hazır Şablonlar</label>
                <div class="grid grid-cols-2 gap-2">
                  <button 
                    type="button" 
                    (click)="applySubtitlePreset('tiktok_yellow')"
                    [ngClass]="subtitlePreset() === 'tiktok_yellow' ? 'border-amber-400 bg-amber-500/20 text-amber-300 ring-1 ring-amber-400/50' : 'border-slate-800 bg-dark-900/60 text-slate-400 hover:border-slate-700'"
                    class="p-2 rounded-lg border text-left flex flex-col gap-1 transition-all">
                    <span class="text-[11px] font-bold">⚡ TikTok Sarı</span>
                    <span class="text-[9px] text-slate-400 font-sans">Sarı Vurgulu & Konturlu</span>
                  </button>
                  <button 
                    type="button" 
                    (click)="applySubtitlePreset('cinematic_shadow')"
                    [ngClass]="subtitlePreset() === 'cinematic_shadow' ? 'border-sky-400 bg-sky-500/20 text-sky-300 ring-1 ring-sky-400/50' : 'border-slate-800 bg-dark-900/60 text-slate-400 hover:border-slate-700'"
                    class="p-2 rounded-lg border text-left flex flex-col gap-1 transition-all">
                    <span class="text-[11px] font-bold">🎬 Sinematik</span>
                    <span class="text-[9px] text-slate-400 font-sans">Gölge & Zarif Serif</span>
                  </button>
                  <button 
                    type="button" 
                    (click)="applySubtitlePreset('opaque_banner')"
                    [ngClass]="subtitlePreset() === 'opaque_banner' ? 'border-emerald-400 bg-emerald-500/20 text-emerald-300 ring-1 ring-emerald-400/50' : 'border-slate-800 bg-dark-900/60 text-slate-400 hover:border-slate-700'"
                    class="p-2 rounded-lg border text-left flex flex-col gap-1 transition-all">
                    <span class="text-[11px] font-bold">🏷️ Opaque Kutu</span>
                    <span class="text-[9px] text-slate-400 font-sans">Koyu Banner Rozet</span>
                  </button>
                  <button 
                    type="button" 
                    (click)="applySubtitlePreset('neon_glow')"
                    [ngClass]="subtitlePreset() === 'neon_glow' ? 'border-fuchsia-400 bg-fuchsia-500/20 text-fuchsia-300 ring-1 ring-fuchsia-400/50' : 'border-slate-800 bg-dark-900/60 text-slate-400 hover:border-slate-700'"
                    class="p-2 rounded-lg border text-left flex flex-col gap-1 transition-all">
                    <span class="text-[11px] font-bold">🔮 Neon Glow</span>
                    <span class="text-[9px] text-slate-400 font-sans">Siyan Parıltı & Büyük</span>
                  </button>
                </div>
              </div>

              <!-- Dikey Konum -->
              <div class="space-y-1.5">
                <div class="flex justify-between items-center text-[10px] text-slate-400 uppercase font-semibold">
                  <span>Dikey Konum</span>
                  <span class="text-brand-cyan font-mono font-bold">{{ subtitlePositionY() }}%</span>
                </div>
                <div class="grid grid-cols-3 gap-1">
                  <button 
                    type="button"
                    (click)="subtitlePositionY.set(85); persistSubtitleStyle()" 
                    [ngClass]="subtitlePositionY() >= 75 ? 'bg-brand-cyan text-slate-900 font-bold' : 'bg-dark-900 text-slate-400 hover:text-white'"
                    class="py-1 rounded text-[10px] border border-slate-700 transition-colors">
                    Alt
                  </button>
                  <button 
                    type="button"
                    (click)="subtitlePositionY.set(50); persistSubtitleStyle()" 
                    [ngClass]="subtitlePositionY() > 30 && subtitlePositionY() < 75 ? 'bg-brand-cyan text-slate-900 font-bold' : 'bg-dark-900 text-slate-400 hover:text-white'"
                    class="py-1 rounded text-[10px] border border-slate-700 transition-colors">
                    Orta
                  </button>
                  <button 
                    type="button"
                    (click)="subtitlePositionY.set(15); persistSubtitleStyle()" 
                    [ngClass]="subtitlePositionY() <= 30 ? 'bg-brand-cyan text-slate-900 font-bold' : 'bg-dark-900 text-slate-400 hover:text-white'"
                    class="py-1 rounded text-[10px] border border-slate-700 transition-colors">
                    Üst
                  </button>
                </div>
                <input 
                  type="range" 
                  min="10" 
                  max="90" 
                  step="1" 
                  [ngModel]="subtitlePositionY()" 
                  (ngModelChange)="subtitlePositionY.set($event); persistSubtitleStyle()"
                  class="w-full accent-brand-cyan cursor-pointer mt-1" />
              </div>

              <!-- Tipografi & Boyut -->
              <div class="space-y-1.5">
                <div class="flex justify-between items-center text-[10px] text-slate-400 uppercase font-semibold">
                  <span>Yazı Tipi & Boyutu</span>
                  <span class="text-brand-cyan font-mono font-bold">{{ subtitleFontSize() }}px</span>
                </div>
                <div class="grid grid-cols-2 gap-2">
                  <select 
                    [ngModel]="subtitleFont()" 
                    (ngModelChange)="subtitleFont.set($event); persistSubtitleStyle()" 
                    class="bg-dark-900 border border-slate-700 rounded-lg p-1.5 text-xs text-white focus:border-brand-cyan outline-none">
                    <option value="Montserrat, sans-serif">Montserrat</option>
                    <option value="Poppins, sans-serif">Poppins</option>
                    <option value="Bebas Neue, sans-serif">Bebas Neue</option>
                    <option value="Anton, sans-serif">Anton</option>
                    <option value="Cinzel, serif">Cinzel (Sinematik)</option>
                    <option value="Outfit, sans-serif">Outfit</option>
                    <option value="Inter, sans-serif">Inter</option>
                  </select>
                  <input 
                    type="range" 
                    min="24" 
                    max="72" 
                    step="2" 
                    [ngModel]="subtitleFontSize()" 
                    (ngModelChange)="subtitleFontSize.set($event); persistSubtitleStyle()"
                    class="accent-brand-cyan cursor-pointer w-full self-center" />
                </div>
              </div>

              <!-- Renkler -->
              <div class="grid grid-cols-2 gap-2">
                <div class="space-y-1">
                  <label class="text-[10px] text-slate-400 uppercase font-semibold">Yazı Rengi</label>
                  <div class="flex items-center gap-1.5">
                    <input 
                      type="color" 
                      [ngModel]="subtitleColor()" 
                      (ngModelChange)="subtitleColor.set($event); persistSubtitleStyle()" 
                      class="w-7 h-7 rounded border border-slate-700 bg-transparent p-0 cursor-pointer" />
                    <input 
                      type="text" 
                      [ngModel]="subtitleColor()" 
                      (ngModelChange)="subtitleColor.set($event); persistSubtitleStyle()" 
                      class="flex-1 min-w-0 bg-dark-900 border border-slate-700 rounded-lg p-1.5 text-[11px] text-white font-mono" />
                  </div>
                </div>

                <div class="space-y-1">
                  <label class="text-[10px] text-slate-400 uppercase font-semibold">Karaoke Vurgu</label>
                  <div class="flex items-center gap-1.5">
                    <input 
                      type="color" 
                      [ngModel]="subtitleHighlightColor()" 
                      (ngModelChange)="subtitleHighlightColor.set($event); persistSubtitleStyle()" 
                      class="w-7 h-7 rounded border border-slate-700 bg-transparent p-0 cursor-pointer" />
                    <input 
                      type="text" 
                      [ngModel]="subtitleHighlightColor()" 
                      (ngModelChange)="subtitleHighlightColor.set($event); persistSubtitleStyle()" 
                      class="flex-1 min-w-0 bg-dark-900 border border-slate-700 rounded-lg p-1.5 text-[11px] text-white font-mono" />
                  </div>
                </div>
              </div>

              <!-- Kontur (Stroke) & Harf Seçenekleri -->
              <div class="grid grid-cols-2 gap-2 items-center pt-1 border-t border-slate-800/60">
                <div class="space-y-1">
                  <div class="flex justify-between items-center text-[10px] text-slate-400 uppercase font-semibold">
                    <span>Kontur Kalınlığı</span>
                    <span class="text-brand-cyan font-mono font-bold">{{ subtitleStrokeWidth() }}px</span>
                  </div>
                  <input 
                    type="range" 
                    min="0" 
                    max="6" 
                    step="1" 
                    [ngModel]="subtitleStrokeWidth()" 
                    (ngModelChange)="subtitleStrokeWidth.set($event); persistSubtitleStyle()"
                    class="w-full accent-brand-cyan cursor-pointer" />
                </div>
                <div class="flex items-center gap-2 pt-2">
                  <label class="flex items-center gap-2 cursor-pointer text-[11px] text-slate-300">
                    <input 
                      type="checkbox" 
                      [checked]="subtitleAllCaps()" 
                      (change)="subtitleAllCaps.set($any($event.target).checked); persistSubtitleStyle()" 
                      class="rounded accent-brand-cyan" />
                    <span>Tümü BÜYÜK</span>
                  </label>
                </div>
              </div>

              <!-- Kaydet Butonu -->
              <button 
                type="button"
                (click)="persistSubtitleStyle()" 
                class="w-full py-1.5 bg-brand-cyan/20 hover:bg-brand-cyan/30 text-brand-cyan border border-brand-cyan/40 rounded-lg text-[11px] font-bold transition-all flex items-center justify-center gap-1.5 cursor-pointer">
                <span>📌</span> Bu Stili Tüm Altyazılara Kaydet
              </button>
            </div>

            <!-- Eylemler -->
            <div class="pt-2 border-t border-slate-800 flex flex-col gap-2">
              <button 
                type="button"
                (click)="saveSubtitleInspector()" 
                class="w-full py-2 bg-brand-cyan hover:bg-cyan-400 text-slate-900 font-bold rounded-lg transition-colors shadow-glow-sm cursor-pointer text-xs flex items-center justify-center gap-1.5">
                <span>✓</span> Altyazı Değişikliklerini Kaydet
              </button>

              <button 
                type="button"
                (click)="convertSubtitleToOverlay()" 
                class="w-full py-2 bg-gradient-to-r from-sky-500 to-indigo-600 hover:from-sky-400 hover:to-indigo-500 text-white font-bold rounded-lg transition-all shadow-glow-sm cursor-pointer text-xs flex items-center justify-center gap-1.5"
                title="Bu altyazıyı bağımsız hareket edebilen, boyutlandırılabilen ve animasyonlu bir katmana dönüştürür.">
                <span>✨</span> Serbest Katmana Dönüştür
              </button>

              <button 
                type="button"
                (click)="deleteSubtitleSegment()" 
                class="w-full py-1.5 bg-rose-600/20 hover:bg-rose-600/40 text-rose-300 border border-rose-600/40 rounded-lg text-xs font-semibold cursor-pointer transition-colors flex items-center justify-center gap-1">
                <span>🗑</span> Bu Altyazı Segmentini Sil
              </button>
            </div>
          </div>

          <!-- 2. Durum: Klip Seçili -->
          <div *ngIf="!selectedOverlay() && !selectedSubtitle() && selectedClipIds().length > 0" class="space-y-3.5">
            <div class="flex items-center justify-between border-b border-slate-800 pb-2">
              <h3 class="text-xs font-bold text-slate-200 uppercase tracking-wider">Klip Özellikleri</h3>
              <span class="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                {{ selectedClipIds().length }} Klip Seçili
              </span>
            </div>

            <div class="p-3 bg-dark-950 rounded-xl border border-slate-800 space-y-2 text-xs">
              <div class="flex justify-between text-slate-400">
                <span>Durum:</span>
                <span class="font-bold text-white">{{ selectedHasKeep() ? 'Korunan Sahne' : 'Kesilen Bölge' }}</span>
              </div>
              <div class="flex justify-between text-slate-400">
                <span>İşlem Kısayolları:</span>
                <span class="font-mono text-brand-cyan">Del / B / V / M</span>
              </div>
            </div>

            <!-- Klip Oynatma Hızı & Sahne Geçişi (CapCut Speed & Transitions) -->
            <div class="p-3 bg-dark-950 rounded-xl border border-slate-800 space-y-2.5">
              <div class="flex items-center justify-between text-[10px]">
                <span class="text-slate-300 uppercase font-bold">⚡ Oynatma Hızı (Speed)</span>
                <span class="text-brand-cyan font-mono font-bold">{{ playbackSpeed() }}x</span>
              </div>
              <div class="grid grid-cols-6 gap-1">
                <button *ngFor="let spd of [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]"
                        type="button"
                        (click)="setPlaybackSpeed(spd)"
                        [ngClass]="playbackSpeed() === spd ? 'bg-brand-cyan text-slate-950 font-bold border-brand-cyan' : 'bg-dark-900 text-slate-400 border-slate-700 hover:text-white'"
                        class="py-1 rounded text-[9px] font-mono border transition-colors cursor-pointer">
                  {{ spd }}x
                </button>
              </div>
              <div class="pt-1 border-t border-slate-800/70">
                <button type="button" (click)="openTransitionModalForSelectedClip()" class="w-full py-1.5 rounded-lg bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/40 text-[10px] font-bold flex items-center justify-center gap-1.5 cursor-pointer transition-colors">
                  <span>⚡</span>
                  <span>Sahne Geçiş Efekti Ekle / Düzenle</span>
                </button>
              </div>
            </div>

            <div class="space-y-2 pt-1">
              <button *ngIf="selectedHasKeep()" (click)="deleteSelectedClips()" class="w-full py-2 bg-rose-600/80 hover:bg-rose-500 text-white font-bold rounded-lg text-xs transition-colors flex items-center justify-center gap-1.5 shadow-glow-sm cursor-pointer">
                <span>✕</span> Bu Klipleri Kes / Çıkar (Del)
              </button>
              <button *ngIf="selectedHasCuts()" (click)="restoreSelectedCuts()" class="w-full py-2 bg-sky-600/80 hover:bg-sky-500 text-white font-bold rounded-lg text-xs transition-colors flex items-center justify-center gap-1.5 shadow-glow-sm cursor-pointer">
                <span>↩</span> Kesimi İptal Et ve Geri Al
              </button>
              <button *ngIf="selectedClipIds().length > 1" (click)="mergeSelectedClips()" class="w-full py-2 bg-emerald-600/80 hover:bg-emerald-500 text-white font-bold rounded-lg text-xs transition-colors flex items-center justify-center gap-1.5 shadow-glow-sm cursor-pointer">
                <span>🔗</span> Seçili Klipleri Birleştir (M)
              </button>
              <button (click)="selectedClipIds.set([])" class="w-full py-1.5 bg-dark-800 text-slate-400 hover:text-white rounded-lg text-xs border border-slate-700 cursor-pointer">
                Seçimi Temizle (Esc)
              </button>
            </div>
          </div>

          <!-- 3. Durum: Hiçbir Şey Seçili Değil -->
          <div *ngIf="!selectedOverlay() && !selectedSubtitle() && selectedClipIds().length === 0" class="text-center py-8 space-y-4">
            <div class="w-12 h-12 rounded-2xl bg-dark-800 border border-slate-700/80 flex items-center justify-center mx-auto text-xl shadow-inner">
              ⚙️
            </div>
            <div>
              <p class="font-bold text-slate-200 text-xs">Özellikler Paneli</p>
              <p class="text-[11px] text-slate-400 mt-1 max-w-[220px] mx-auto">
                Düzenlemek için video veya zaman çizelgesindeki bir klip veya katmana tıklayın.
              </p>
            </div>

            <div class="pt-2 flex flex-col gap-2">
              <button (click)="addTextOverlay()" class="w-full py-2 rounded-lg bg-brand-cyan text-slate-900 font-bold text-xs hover:bg-cyan-400 transition-colors shadow-glow-sm flex items-center justify-center gap-1.5">
                <span class="font-black">T</span> + Yeni Yazı Ekle
              </button>
              <button (click)="addImageOverlay()" class="w-full py-2 rounded-lg bg-purple-600 text-white font-bold text-xs hover:bg-purple-500 transition-colors shadow-glow-sm flex items-center justify-center gap-1.5">
                <span>🖼️</span> + Yeni Görsel Ekle
              </button>
            </div>

            <div class="pt-3 border-t border-slate-800/80 text-left space-y-1.5 text-[10px] text-slate-400">
              <span class="font-bold text-slate-300 uppercase tracking-wider block mb-1">Hızlı İpuçları</span>
              <p>• Zaman çizgisinde <kbd class="px-1 bg-dark-800 rounded font-mono text-slate-300">Sağ Tık</kbd> ile gelişmiş bağlam menüsüne erişin.</p>
              <p>• <kbd class="px-1 bg-dark-800 rounded font-mono text-slate-300">Ctrl + Tekerlek</kbd> ile timeline'a yakınlaşın.</p>
              <p>• Çift tıklayarak sahneleri anında kesip geri yükleyebilirsiniz.</p>
            </div>
          </div>
        </aside>
      </div>

      <!-- Alt Alan: Tam Genişlik Çok Kanallı NLE Zaman Çizelgesi (CapCut Tarzı) -->
      <section class="h-[44%] min-h-[220px] shrink-0 flex flex-col bg-dark-950 select-none">
        
        <!-- Timeline Üst Araç Çubuğu (Toolbar) -->
        <div class="h-10 px-4 bg-dark-900/95 border-b border-slate-800 flex items-center justify-between shrink-0 select-none">
          <!-- Sol: Temel Araçlar -->
          <div class="flex items-center gap-1.5">
            <button (click)="addSplitMarker()" class="px-2.5 py-1 rounded bg-dark-800 text-slate-300 hover:text-white hover:bg-slate-700 border border-slate-700 text-xs font-semibold flex items-center gap-1.5 transition-colors cursor-pointer" title="Bulunulan Yerden Böl (B)">
              <span class="text-rose-400 font-bold">✂</span>
              <span>Böl (B)</span>
            </button>
            <button 
              *ngIf="selectedClipIds().length > 0 || selectedOverlayId()"
              (click)="deleteSelectedItems()" 
              class="px-2.5 py-1 rounded bg-rose-600/20 text-rose-300 hover:bg-rose-600/40 border border-rose-500/40 text-xs font-semibold flex items-center gap-1 transition-colors shadow-glow-sm cursor-pointer" 
              title="Seçili Klip veya Katmanı Sil (Del)">
              <span>🗑</span>
              <span>Sil (Del)</span>
            </button>
            <div class="h-4 w-px bg-slate-700 mx-1"></div>
            <button (click)="undo()" class="p-1 px-2.5 rounded bg-dark-800 text-slate-400 hover:text-white border border-slate-700 text-xs transition-colors cursor-pointer" title="Geri Al (Ctrl+Z)">
              ⟲ Geri
            </button>
            <button (click)="redo()" class="p-1 px-2.5 rounded bg-dark-800 text-slate-400 hover:text-white border border-slate-700 text-xs transition-colors cursor-pointer" title="İleri Al (Ctrl+Y)">
              ⟳ İleri
            </button>
            <button 
              *ngIf="selectedClipIds().length > 1" 
              (click)="mergeSelectedClips()" 
              class="px-2.5 py-1 rounded bg-emerald-600/30 text-emerald-300 hover:bg-emerald-600/50 border border-emerald-500/40 text-xs font-semibold flex items-center gap-1 shadow-glow-sm transition-colors cursor-pointer" 
              title="Seçili Klipleri Birleştir (M)">
              <span>🔗</span> Birleştir (M)
            </button>
            <button 
              *ngIf="retakeCount() > 0" 
              (click)="deleteRetakeCuts()" 
              class="px-2.5 py-1 rounded bg-amber-500/20 text-amber-300 hover:bg-amber-500/30 border border-amber-500/40 font-semibold text-xs shadow-glow-sm flex items-center gap-1.5 transition-all cursor-pointer" 
              title="Hatalı Tekrar (Retake) Kesimlerini İptal Et">
              <span>🔄</span>
              <span>{{ retakeCount() }} Retake'i Geri Al</span>
            </button>

            <!-- Toplu Kesim İnce Ayar (Milisaniye Trim) Butonu -->
            <button 
              *ngIf="autoCuts().length > 0"
              (click)="openCutAdjustModal()" 
              class="px-2.5 py-1 rounded bg-indigo-500/20 text-indigo-300 hover:bg-indigo-500/30 border border-indigo-500/40 font-semibold text-xs shadow-glow-sm flex items-center gap-1.5 transition-all cursor-pointer" 
              title="Tüm Otomatik Kesimlerin Başlangıç ve Bitiş Sürelerini Milisaniye Bazında Kaydır / Genişlet">
              <span>⏱️</span>
              <span>Kesim Payı Ayarla</span>
            </button>

            <!-- Kesimleri Geri Al Dropdown Menüsü -->
            <div class="relative inline-block" *ngIf="autoCuts().length > 0">
              <button 
                type="button"
                (click)="showRestoreDropdown.set(!showRestoreDropdown())" 
                class="px-2.5 py-1 rounded bg-rose-500/20 text-rose-300 hover:bg-rose-500/30 border border-rose-500/40 font-semibold text-xs shadow-glow-sm flex items-center gap-1.5 transition-all cursor-pointer" 
                title="Otomatik Kesimleri Kategoriye Göre Geri Al">
                <span>✂️↶</span>
                <span>Kesimleri Geri Al</span>
                <span class="text-[9px] px-1 py-0.2 bg-rose-950/80 rounded-full font-mono text-rose-200 border border-rose-800/50">{{ autoCuts().length }}</span>
                <span class="text-[8px] opacity-70">▼</span>
              </button>
              
              <!-- Dropdown Panel -->
              <div *ngIf="showRestoreDropdown()" (click)="$event.stopPropagation()" class="absolute left-0 top-full mt-1.5 w-64 bg-dark-900/98 backdrop-blur-xl border border-slate-700 rounded-xl shadow-2xl z-50 p-1.5 space-y-1 text-xs animate-in fade-in zoom-in-95 duration-100">
                <div class="px-2.5 py-1 text-[10px] font-bold text-slate-400 uppercase tracking-wider border-b border-slate-800 flex items-center justify-between">
                  <span>Geri Alma Seçenekleri</span>
                  <button type="button" (click)="showRestoreDropdown.set(false)" class="text-slate-500 hover:text-white">✕</button>
                </div>
                <button 
                  type="button"
                  (click)="restoreCutsByScope('short'); showRestoreDropdown.set(false)" 
                  class="w-full text-left px-2.5 py-2 rounded-lg hover:bg-rose-500/20 text-slate-200 hover:text-rose-200 flex items-center justify-between transition-colors cursor-pointer group">
                  <div class="flex flex-col">
                    <span class="font-medium group-hover:text-rose-300">💨 Sadece Kısaları Geri Al</span>
                    <span class="text-[10px] text-slate-400">1 saniyeden kısa nefes kesimleri</span>
                  </div>
                  <span class="px-1.5 py-0.5 rounded bg-dark-800 text-[10px] font-mono text-amber-300 border border-slate-700">{{ shortCuts().length }}</span>
                </button>
                <button 
                  type="button"
                  (click)="restoreCutsByScope('long'); showRestoreDropdown.set(false)" 
                  class="w-full text-left px-2.5 py-2 rounded-lg hover:bg-rose-500/20 text-slate-200 hover:text-rose-200 flex items-center justify-between transition-colors cursor-pointer group">
                  <div class="flex flex-col">
                    <span class="font-medium group-hover:text-rose-300">⏳ Sadece Uzunları Geri Al</span>
                    <span class="text-[10px] text-slate-400">1 saniyeden uzun duraklamalar</span>
                  </div>
                  <span class="px-1.5 py-0.5 rounded bg-dark-800 text-[10px] font-mono text-sky-300 border border-slate-700">{{ longCuts().length }}</span>
                </button>
                <div class="h-px bg-slate-800 my-1"></div>
                <button 
                  type="button"
                  (click)="restoreCutsByScope('all'); showRestoreDropdown.set(false)" 
                  class="w-full text-left px-2.5 py-2 rounded-lg hover:bg-rose-600/30 text-rose-300 hover:text-rose-100 flex items-center justify-between transition-colors cursor-pointer">
                  <span class="font-bold">🚫 Tüm Kesimleri Geri Al</span>
                  <span class="px-1.5 py-0.5 rounded bg-rose-950 text-[10px] font-mono text-rose-300 border border-rose-800">{{ autoCuts().length }}</span>
                </button>
              </div>
            </div>
          </div>

          <!-- Orta: Görünüm Filtreleri -->
          <div class="flex items-center gap-1 text-[11px]">
            <button (click)="rippleAi.set(!rippleAi())" [ngClass]="rippleAi() ? 'bg-sky-500/20 text-sky-300 border-sky-500/40' : 'bg-dark-800 text-slate-400 border-slate-700'" class="px-2 py-0.5 rounded border transition-colors cursor-pointer" title="AI Kesimlerini Sıkıştır/Genişlet">
              🤖 AI {{ rippleAi() ? 'Sıkışık' : 'Açık' }}
            </button>
            <button (click)="rippleRetake.set(!rippleRetake())" [ngClass]="rippleRetake() ? 'bg-amber-500/20 text-amber-300 border-amber-500/40' : 'bg-dark-800 text-slate-400 border-slate-700'" class="px-2 py-0.5 rounded border transition-colors cursor-pointer" title="Retake Kesimlerini Sıkıştır/Genişlet">
              🔄 Retake {{ rippleRetake() ? 'Sıkışık' : 'Açık' }}
            </button>
            <button (click)="rippleManual.set(!rippleManual())" [ngClass]="rippleManual() ? 'bg-purple-500/20 text-purple-300 border-purple-500/40' : 'bg-dark-800 text-slate-400 border-slate-700'" class="px-2 py-0.5 rounded border transition-colors cursor-pointer" title="Manuel Kesimleri Sıkıştır/Genişlet">
              🖐 Manuel {{ rippleManual() ? 'Sıkışık' : 'Açık' }}
            </button>
          </div>

          <!-- Sağ: Zoom Slider ve Hızlı Ekleme -->
          <div class="flex items-center gap-2">
            <div class="flex items-center gap-1.5 bg-dark-800 px-2 py-0.5 rounded-lg border border-slate-700">
              <button (click)="zoomOut()" class="text-slate-400 hover:text-white text-xs px-1 cursor-pointer">🔍-</button>
              <input 
                type="range" 
                min="1" 
                max="50" 
                step="0.5" 
                [ngModel]="timelineZoom()" 
                (ngModelChange)="timelineZoom.set($event)" 
                class="w-20 h-1 accent-brand-cyan cursor-pointer" 
                title="Ctrl + Tekerlek ile de yakınlaşabilirsiniz" />
              <button (click)="zoomIn()" class="text-slate-400 hover:text-white text-xs px-1 cursor-pointer">🔍+</button>
              <span class="text-[10px] font-mono text-slate-400 ml-1">{{ timelineZoom().toFixed(1) }}x</span>
            </div>

            <div class="h-4 w-px bg-slate-700 mx-0.5"></div>

            <button (click)="addTrackLane()" class="px-2 py-1 rounded bg-dark-800 text-slate-300 hover:text-white border border-slate-700 text-xs font-semibold flex items-center gap-1 transition-colors cursor-pointer" title="Yeni Boş Katman Kanalı Ekle">
              <span>+</span>
              <span>Katman</span>
            </button>
            <button (click)="addTextOverlay()" class="px-2.5 py-1 rounded bg-brand-cyan text-slate-900 font-bold hover:bg-cyan-400 border border-cyan-500 shadow-glow-sm text-xs flex items-center gap-1 transition-all cursor-pointer" title="Zaman çizgisine yazı katmanı ekle (T)">
              <span class="font-black">T</span>
              <span>Yazı</span>
            </button>
            <button (click)="addImageOverlay()" class="px-2.5 py-1 rounded bg-purple-500 text-white font-bold hover:bg-purple-400 border border-purple-400 shadow-glow-sm text-xs flex items-center gap-1 transition-all cursor-pointer" title="Zaman çizgisine görsel katmanı ekle">
              <span>🖼️</span>
              <span>Görsel</span>
            </button>
          </div>
        </div>

        <!-- Çok Kanallı Zaman Çizelgesi Gövdesi (Sol Sabit Başlıklar + Sağ Kaydırılabilir Alan) -->
        <div class="flex-1 flex overflow-hidden relative">
          
          <!-- 1. SOL SABİT KATMAN BAŞLIKLARI (Track Headers Panel) -->
          <div class="w-32 md:w-36 shrink-0 bg-dark-900 border-r border-slate-800 flex flex-col z-30 select-none shadow-lg">
            <!-- Cetvel Köşesi -->
            <div class="h-7 border-b border-slate-800/90 px-2.5 flex items-center justify-between bg-dark-950 text-[10px] font-mono text-slate-400">
              <span class="font-bold text-slate-300 flex items-center gap-1">
                <span>🎬</span> KANALLAR
              </span>
              <div class="flex items-center gap-0.5">
                <button (click)="addTrackLane()" class="px-1.5 py-0.5 rounded bg-dark-800 hover:bg-slate-700 text-sky-400 border border-slate-700 hover:text-white transition-colors text-[9px] font-bold cursor-pointer" title="Yeni Katman Kanalı Ekle">
                  + Katman
                </button>
              </div>
            </div>

            <!-- Altyazı Kanalı Başlığı -->
            <div class="h-10 border-b border-slate-800/70 px-2 flex items-center justify-between text-xs bg-dark-900/40 hover:bg-dark-800/60 transition-colors shadow-md z-10">
              <span class="text-[10px] font-bold text-amber-400">💬 Altyazı</span>
              <button 
                type="button"
                (click)="toggleSubtitles()" 
                [title]="showSubtitles() ? 'Altyazıyı Devre Dışı Bırak (Renderda Çıkmaz)' : 'Altyazıyı Etkinleştir (Renderda Çıkar)'"
                class="px-1.5 py-0.5 rounded text-[9px] font-bold transition-all cursor-pointer border"
                [ngClass]="showSubtitles() ? 'text-amber-300 bg-amber-400/20 border-amber-400/40 hover:bg-amber-400/30' : 'text-slate-500 bg-dark-800 border-slate-700 hover:text-slate-300'">
                {{ showSubtitles() ? 'Açık' : 'Kapalı' }}
              </button>
            </div>

            <!-- Overlay Katman Başlıkları (T3, T2, T1) - CapCut Stili Kontroller -->
            <div 
              *ngFor="let trackNum of overlayTrackNumbers()" 
              class="h-10 border-b border-slate-800/70 px-2 flex items-center justify-between text-xs bg-dark-900/90 hover:bg-dark-800/60 transition-colors group">
              <div class="flex items-center gap-1 min-w-0">
                <span class="w-4 h-4 rounded flex items-center justify-center text-[9px] font-black shrink-0 bg-sky-500/20 text-sky-300 border border-sky-500/30">
                  T{{ trackNum }}
                </span>
                <span class="text-[10px] font-semibold text-slate-300 truncate" [title]="'Katman #' + trackNum">
                  Katman {{ trackNum }}
                </span>
              </div>

              <!-- CapCut Stili Kontroller: Göz (Gizle/Göster), Kilit, Hedefli Sil -->
              <div class="flex items-center gap-0.5 shrink-0">
                <!-- Göz / Görünürlük Butonu -->
                <button 
                  type="button"
                  (click)="toggleTrackVisibility(trackNum)"
                  [title]="isTrackHidden(trackNum) ? 'Katmanı Göster' : 'Katmanı Gizle'"
                  class="w-5 h-5 rounded flex items-center justify-center text-[10px] transition-colors cursor-pointer"
                  [ngClass]="isTrackHidden(trackNum) ? 'text-rose-400 bg-rose-950/40 border border-rose-500/30' : 'text-slate-400 hover:text-white hover:bg-slate-700/50'">
                  <span>{{ isTrackHidden(trackNum) ? '🚫' : '👁️' }}</span>
                </button>

                <!-- Kilit Butonu -->
                <button 
                  type="button"
                  (click)="toggleTrackLock(trackNum)"
                  [title]="isTrackLocked(trackNum) ? 'Kilidi Aç' : 'Katmanı Kilitle'"
                  class="w-5 h-5 rounded flex items-center justify-center text-[10px] transition-colors cursor-pointer"
                  [ngClass]="isTrackLocked(trackNum) ? 'text-amber-400 bg-amber-950/40 border border-amber-500/30' : 'text-slate-500 hover:text-slate-300 hover:bg-slate-700/50'">
                  <span>{{ isTrackLocked(trackNum) ? '🔒' : '🔓' }}</span>
                </button>

                <!-- Hedefli Katman Silme Butonu (A6 Çözümü) -->
                <button 
                  type="button"
                  (click)="deleteTrackLane(trackNum)"
                  [title]="'Katman #' + trackNum + ' Kanalını Sil'"
                  class="w-5 h-5 rounded flex items-center justify-center text-[10px] text-slate-500 hover:text-rose-400 hover:bg-rose-950/40 transition-colors cursor-pointer opacity-70 group-hover:opacity-100">
                  <span>✕</span>
                </button>
              </div>
            </div>

            <!-- Video Kanalı Başlığı (V1) -->
            <div class="h-14 px-2.5 flex items-center justify-between text-xs bg-dark-900/95 border-t border-slate-800">
              <div class="flex items-center gap-1.5">
                <span class="w-5 h-5 rounded flex items-center justify-center text-[10px] font-black bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                  V1
                </span>
                <div class="flex flex-col">
                  <span class="text-[11px] font-bold text-emerald-400">Ana Video</span>
                  <span class="text-[9px] text-slate-500 font-mono">{{ clips().length }} Klip</span>
                </div>
              </div>
              <span class="text-xs text-emerald-500/70" title="Ses Dalga Formu Aktif">🔊</span>
            </div>

            <!-- Arka Plan Müziği Kanalı Başlığı (A1) (B5) -->
            <div class="h-12 px-2.5 flex items-center justify-between text-xs bg-dark-900/95 border-t border-slate-800 group">
              <div class="flex items-center gap-1.5">
                <span class="w-5 h-5 rounded flex items-center justify-center text-[10px] font-black bg-violet-500/20 text-violet-300 border border-violet-500/30">
                  A1
                </span>
                <div class="flex flex-col overflow-hidden max-w-[90px]">
                  <span class="text-[11px] font-bold text-violet-400 truncate">BGM Müzik</span>
                  <span class="text-[9px] text-slate-400 font-mono truncate" [title]="bgmTitle()">
                    {{ bgmUrl() ? bgmTitle() : 'Parça Yok' }}
                  </span>
                </div>
              </div>
              <button
                type="button"
                (click)="isBgmSelectorOpen.set(true)"
                class="px-1.5 py-0.5 rounded text-[9px] font-semibold bg-violet-600/30 hover:bg-violet-600/50 text-violet-200 border border-violet-500/40 transition-colors cursor-pointer"
                title="Müzik Seç / Ayarla">
                🎵
              </button>
            </div>

            <!-- Ses Efektleri (SFX) Kanalı Başlığı (A2) -->
            <div class="h-10 px-2.5 flex items-center justify-between text-xs bg-dark-900/95 border-t border-slate-800 group">
              <div class="flex items-center gap-1.5">
                <span class="w-5 h-5 rounded flex items-center justify-center text-[10px] font-black bg-amber-500/20 text-amber-300 border border-amber-500/30">
                  A2
                </span>
                <div class="flex flex-col overflow-hidden max-w-[90px]">
                  <span class="text-[10px] font-bold text-amber-400 truncate">Ses Efektleri</span>
                  <span class="text-[9px] text-slate-400 font-mono truncate">{{ sfxClips().length }} SFX</span>
                </div>
              </div>
              <button
                type="button"
                (click)="activeTab.set('sfx')"
                class="px-1.5 py-0.5 rounded text-[9px] font-semibold bg-amber-500/25 hover:bg-amber-500/40 text-amber-300 border border-amber-500/40 transition-colors cursor-pointer"
                title="SFX Kütüphanesini Aç">
                +🔊
              </button>
            </div>
          </div>

          <!-- 2. SAĞ KAYDIRILABİLİR ZAMAN ÇİZELGESİ (Scrollable Timeline Canvas) -->
          <div 
            #timelineScrollContainer
            (wheel)="onTimelineWheel($event)"
            class="flex-1 overflow-x-auto overflow-y-auto relative pb-2 scrollbar-thin scrollbar-thumb-slate-700 scrollbar-track-dark-900">
            <div 
              #timelineTrack
              id="timelineTrack"
              (mousedown)="onTimelineTrackMouseDown($event)"
              (click)="seekTimeline($event)"
              (contextmenu)="openTimelineContextMenu($event)"
              [style.width.%]="100 * timelineZoom()"
              class="relative min-w-full flex flex-col select-none cursor-pointer bg-dark-950 min-h-full">
              
              <!-- Zaman Cetveli (Timecode Ruler with Ticks) -->
              <div 
                (mousedown)="onRulerMouseDown($event)"
                class="relative h-7 bg-dark-950 border-b border-slate-800 overflow-hidden select-none cursor-pointer">
                <div class="absolute inset-0 bg-[linear-gradient(to_right,#334155_1px,transparent_1px)] bg-[size:10px_100%] opacity-20 pointer-events-none"></div>
                <ng-container *ngFor="let mark of timelineRulerMarks()">
                  <div class="absolute top-0 bottom-0 flex flex-col items-center pointer-events-none -translate-x-1/2" [style.left.%]="mark.percent">
                    <span class="text-[9px] font-mono text-slate-400 font-semibold pt-0.5 tracking-tight">{{ mark.label }}</span>
                    <div class="w-px flex-1 bg-slate-700/80 mt-0.5"></div>
                  </div>
                </ng-container>
              </div>

              
              <!-- Altyazı Kanalı (Subtitle Track - O(1) Pre-Computed Layout) -->
              <div [ngClass]="showSubtitles() ? 'opacity-100' : 'opacity-40'"
                   class="relative h-10 bg-dark-900/40 border-b border-slate-800/60 overflow-hidden flex items-center hover:bg-dark-900/70 transition-all">
                <div class="absolute inset-0 bg-[linear-gradient(to_right,#1e293b_1px,transparent_1px)] bg-[size:50px_100%] opacity-15 pointer-events-none"></div>
                
                <div class="absolute left-0 right-0 top-0 bottom-0 overflow-hidden">
                  <div *ngFor="let seg of visibleSubtitleSegments()"
                       (mousedown)="onSubtitleMouseDown($event, seg)"
                       (click)="$event.stopPropagation(); selectSubtitle(seg)"
                       (dblclick)="$event.stopPropagation(); startEditSubtitle(seg)"
                       class="subtitle-segment group absolute top-1 bottom-1 bg-amber-500/20 border border-amber-500/50 rounded flex items-center px-1 text-[8px] text-amber-100 overflow-hidden hover:bg-amber-500/40 z-20 cursor-pointer select-none"
                       [ngClass]="isSelectedSubtitle(seg) ? 'ring-2 ring-brand-cyan bg-amber-500/50 shadow-glow-sm z-30 font-bold' : (editingSubtitleId() === getSubtitleId(seg) ? 'ring-1 ring-white z-30 bg-amber-500/40' : 'cursor-pointer')"
                       [style.left.%]="seg.leftPercent"
                       [style.width.%]="seg.widthPercent"
                       [title]="editingSubtitleId() === getSubtitleId(seg) ? '' : 'Düzenlemek için tıkla: ' + seg.text">

                       <!-- Sol Yeniden Boyutlandırma Kolu -->
                       <div 
                         *ngIf="isSelectedSubtitle(seg)" 
                         (mousedown)="onSubtitleResizeStart($event, seg, 'left')" 
                         class="absolute left-0 top-0 bottom-0 w-2 cursor-ew-resize bg-brand-cyan/90 hover:bg-cyan-300 z-40 flex items-center justify-center">
                         <div class="w-0.5 h-3 bg-slate-900 rounded"></div>
                       </div>

                       <span *ngIf="editingSubtitleId() !== getSubtitleId(seg)" class="truncate font-semibold px-1">{{ seg.text }}</span>
                       <input *ngIf="editingSubtitleId() === getSubtitleId(seg)" 
                              type="text" 
                              class="w-full bg-dark-950 text-white outline-none border-b border-amber-400 font-semibold h-full shadow-inner"
                              [value]="seg.text"
                              (blur)="saveSubtitleEdit(seg, subtitleInput.value)"
                              (keydown.enter)="$event.preventDefault(); saveSubtitleEdit(seg, subtitleInput.value)"
                              (keydown.escape)="cancelSubtitleEdit()"
                              #subtitleInput 
                              autofocus>

                       <!-- Sağ Yeniden Boyutlandırma Kolu -->
                       <div 
                         *ngIf="isSelectedSubtitle(seg)" 
                         (mousedown)="onSubtitleResizeStart($event, seg, 'right')" 
                         class="absolute right-0 top-0 bottom-0 w-2 cursor-ew-resize bg-brand-cyan/90 hover:bg-cyan-300 z-40 flex items-center justify-center">
                         <div class="w-0.5 h-3 bg-slate-900 rounded"></div>
                       </div>
                  </div>
                </div>
              </div>

              <!-- Katman Şeritleri (T3, T2, T1) -->
              <div 
                *ngFor="let trackNum of overlayTrackNumbers()" 
                [ngClass]="{'opacity-35 grayscale pointer-events-none select-none': isTrackHidden(trackNum)}"
                class="relative h-10 bg-dark-900/40 border-b border-slate-800/60 overflow-hidden flex items-center hover:bg-dark-900/70 transition-colors">
                <div class="absolute inset-0 bg-[linear-gradient(to_right,#1e293b_1px,transparent_1px)] bg-[size:50px_100%] opacity-15 pointer-events-none"></div>

                <div *ngIf="getOverlaysForTrack(trackNum).length === 0" class="absolute inset-0 flex items-center justify-center text-[10px] text-slate-600/40 italic pointer-events-none select-none">
                  Katman #{{ trackNum }} (Boş)
                </div>

                <!-- Katman Öğeleri (Pill'ler) -->
                <div 
                  *ngFor="let ov of getOverlaysForTrack(trackNum)"
                  (mousedown)="!isTrackLocked(trackNum) && onOverlayDragStart($event, ov.id)"
                  (click)="$event.stopPropagation(); !isTrackLocked(trackNum) && selectOverlay(ov.id)"
                  (contextmenu)="openOverlayContextMenu($event, ov)"
                  class="overlay-item absolute top-1 bottom-1 rounded-lg px-2.5 flex items-center justify-between text-[11px] font-bold z-20 group transition-all select-none shadow-lg overflow-hidden min-w-[4px] border"
                  [ngClass]="[
                     isTrackLocked(trackNum) ? 'cursor-not-allowed opacity-85' : 'cursor-grab active:cursor-grabbing',
                     ov.type === 'text' 
                       ? 'bg-gradient-to-r from-[#ba5748] to-[#994033] text-white border-[#e07567]/70 hover:brightness-110 shadow-rose-950/50' 
                       : 'bg-gradient-to-r from-purple-700 to-indigo-700 text-white border-purple-400/70 hover:brightness-110 shadow-purple-950/50',
                     selectedOverlayId() === ov.id 
                       ? 'ring-2 ring-white shadow-[0_0_12px_rgba(255,255,255,0.95)] z-30 brightness-115 scale-[1.01]' 
                       : ''
                  ]"
                  [ngStyle]="getOverlayStyle(ov)"
                  [title]="(ov.type === 'text' ? 'Metin: ' : 'Görsel: ') + (ov.content || ov.source || ov.id) + ' (Katman #' + trackNum + (isTrackLocked(trackNum) ? ' - Kilitli' : '') + ')'">
                  
                  <!-- Sol Boyutlandırma Kolu -->
                  <div *ngIf="!isTrackLocked(trackNum)" (mousedown)="onOverlayResizeStart($event, ov.id, 'left')" class="absolute left-0 top-0 bottom-0 w-3 cursor-ew-resize opacity-0 group-hover:opacity-100 hover:bg-white/50 bg-white/20 rounded-l flex items-center justify-center z-30 transition-opacity">
                    <div class="w-0.5 h-3.5 bg-white/90 rounded"></div>
                  </div>

                  <!-- İçerik -->
                  <div class="truncate px-2 pointer-events-none font-semibold flex items-center gap-1.5 drop-shadow-sm">
                    <span class="w-4 h-4 rounded text-[9px] font-black flex items-center justify-center bg-black/30 border border-white/20">
                      {{ ov.type === 'text' ? 'T' : '🖼️' }}
                    </span>
                    <span *ngIf="isTrackLocked(trackNum)" class="text-[9px]" title="Katman Kilitli">🔒</span>
                    <span class="truncate">{{ ov.content || (ov.type === 'text' ? 'Metin' : 'Görsel') }}</span>
                    <span class="text-[9px] font-mono opacity-80 font-normal ml-1">({{ ov.duration }}s)</span>
                  </div>

                  <!-- Sağ Boyutlandırma Kolu -->
                  <div *ngIf="!isTrackLocked(trackNum)" (mousedown)="onOverlayResizeStart($event, ov.id, 'right')" class="absolute right-0 top-0 bottom-0 w-3 cursor-ew-resize opacity-0 group-hover:opacity-100 hover:bg-white/50 bg-white/20 rounded-r flex items-center justify-center z-30 transition-opacity">
                    <div class="w-0.5 h-3.5 bg-white/90 rounded"></div>
                  </div>
                </div>
              </div>

              <!-- Video Klipleri Şeridi (V1 - Ana Video Kanalı, Gerçek Ses Dalgası & [⚡] Sahne Geçişleri) -->
              <div class="relative bg-dark-950 flex overflow-hidden border-b border-slate-800" [style.height.px]="audioTrackHeight()">
                <!-- Klipler (O(1) Pre-Computed Layout) -->
                <ng-container *ngFor="let clip of clips()">
                  <div 
                    *ngIf="clip.isVisibleClip"
                    (mousedown)="onClipMouseDown($event, clip.id)"
                    (click)="selectClip(clip.id, $event)"
                    (dblclick)="toggleClip(clip, $event)"
                    (contextmenu)="openClipContextMenu($event, clip)"
                    class="timeline-clip absolute top-0 bottom-0 transition-all border-r border-white/20 box-border group flex flex-col justify-between p-1 select-none z-10 cursor-pointer"
                    [ngClass]="{
                       'bg-amber-500/70 hover:bg-amber-500/80 backdrop-blur-xs': isRetakeClip(clip),
                       'bg-rose-500/70 hover:bg-rose-500/80 backdrop-blur-xs': isManualClip(clip),
                       'bg-rose-950/75 hover:bg-rose-900/85 backdrop-blur-xs': clip.isCut && !isRetakeClip(clip) && !isManualClip(clip),
                       'bg-emerald-600/20 hover:bg-emerald-500/35': !clip.isCut,
                       'ring-2 ring-inset ring-brand-yellow shadow-[0_0_12px_rgba(250,204,21,0.6)] z-20': selectedClipIds().includes(clip.id)
                    }"
                    [style.left.%]="clip.leftPercent"
                    [style.width.%]="clip.widthPercent"
                    [title]="getClipTooltip(clip)">
                    
                    <!-- Per-Clip Gerçek Ses Dalgası (CapCut & Premiere Pro Bar & Zoom LOD Style) -->
                    <div class="absolute inset-0 pointer-events-none z-0 overflow-hidden">
                      <canvas
                        appClipWaveform
                        [peaks]="audioPeaks()"
                        [clipStart]="clip.start"
                        [clipEnd]="clip.end"
                        [totalDuration]="totalDuration()"
                        [isCut]="clip.isCut"
                        [zoom]="timelineZoom()"
                        [trackHeight]="audioTrackHeight()"
                        class="w-full h-full block">
                      </canvas>
                    </div>

                    <!-- Üst Klip Başlığı -->
                    <div class="relative flex items-center justify-between text-[9px] text-white/90 font-mono truncate pointer-events-none z-10">
                      <span class="truncate font-semibold flex items-center gap-1">
                        <span *ngIf="clip.isCut" class="w-1.5 h-1.5 rounded-full bg-rose-400"></span>
                        <span>{{ clip.isCut ? (isRetakeClip(clip) ? '🔁 Retake' : '✕ Kesilen') : 'Klip' }}</span>
                      </span>
                      <span class="text-[8px] opacity-80">{{ clip.duration.toFixed(1) }}s</span>
                    </div>

                    <!-- Kesilen Alan Rozeti -->
                    <div *ngIf="clip.isCut" class="my-auto self-center pointer-events-none">
                      <span class="px-1.5 py-0.5 rounded text-[8px] font-bold bg-rose-900/90 text-rose-200 border border-rose-600/50 shadow-sm">
                        {{ isRetakeClip(clip) ? 'TEKRAR' : 'SESSİZLİK' }}
                      </span>
                    </div>

                    <!-- Çift Tıkla İade İpucu -->
                    <div *ngIf="clip.isCut" class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 px-2 py-0.5 rounded opacity-0 group-hover:opacity-100 bg-rose-950/90 transition-opacity z-20 whitespace-nowrap">
                      <span class="text-[10px] text-white font-bold">↩ Geri Yükle</span>
                    </div>
                  </div>
                </ng-container>

                <!-- Sahne Geçiş İkonları ([⚡] Transition Buttons on Clip Boundaries) -->
                <button
                  *ngFor="let b of clipTransitionBoundaries()"
                  type="button"
                  (click)="$event.stopPropagation(); openTransitionModal(b)"
                  [style.left.%]="b.leftPercent"
                  [ngClass]="b.existing ? 'bg-amber-400 text-slate-950 border-white scale-110 shadow-[0_0_10px_rgba(251,191,36,0.9)]' : 'bg-dark-900/90 text-slate-300 hover:bg-brand-cyan hover:text-slate-950 border-slate-600 opacity-75 hover:opacity-100'"
                  class="absolute top-1/2 -translate-x-1/2 -translate-y-1/2 w-5 h-5 rounded-md border flex items-center justify-center text-[10px] font-black z-30 transition-all cursor-pointer"
                  [title]="b.existing ? ('Geçiş: ' + b.existing.type + ' (' + b.existing.duration + 'sn) — Düzenlemek için tıkla') : 'Sahne Geçiş Efekti Ekle (Fade, Whip Pan, Zoom...)'">
                  ⚡
                </button>
              </div>

              <!-- Track Yükseklik Boyutlandırıcı (Resizer) -->
              <div (mousedown)="onTrackResizeStart($event)" class="h-2 w-full bg-slate-900 border-b border-slate-700 cursor-ns-resize hover:bg-slate-700 transition-colors z-20 flex items-center justify-center relative -mt-1 group">
                 <div class="w-12 h-0.5 bg-slate-500 rounded-full group-hover:bg-slate-300"></div>
              </div>

              <!-- Arka Plan Müziği Kanalı (A1 BGM Track) (B5) -->
              <div class="relative h-12 bg-dark-900/60 border-b border-slate-800/80 overflow-hidden flex items-center select-none">
                <div class="absolute inset-0 bg-[linear-gradient(to_right,#312e81_1px,transparent_1px)] bg-[size:60px_100%] opacity-15 pointer-events-none"></div>

                <!-- Müzik Yüklü İse -->
                <ng-container *ngIf="bgmUrl(); else noBgmTemplate">
                  <div class="absolute inset-x-1 top-1 bottom-1 rounded-md bg-gradient-to-r from-violet-950/80 via-purple-900/60 to-indigo-950/80 border border-violet-500/50 shadow-sm flex items-center justify-between px-3 text-white">
                    <!-- Sol: Parça Bilgisi & Ses Dalgası Efekti -->
                    <div class="flex items-center gap-2 overflow-hidden">
                      <span class="text-sm">🎵</span>
                      <div class="flex flex-col truncate">
                        <span class="text-xs font-bold text-violet-200 truncate">{{ bgmTitle() }}</span>
                        <div class="flex items-center gap-2 text-[9px] text-violet-300/80">
                          <span>Döngü (Loop) Aktif</span>
                          <span>•</span>
                          <span class="text-emerald-400 font-semibold" *ngIf="bgmAutoDucking()">🦆 Auto-Ducking Aktif</span>
                        </div>
                      </div>
                    </div>

                    <!-- Sağ: Hızlı Kontroller (Ses Seviyesi & Ducking & Değiştir/Sil) -->
                    <div class="flex items-center gap-3 shrink-0" (click)="$event.stopPropagation()">
                      <!-- Ses Slider -->
                      <div class="flex items-center gap-1.5" title="Müzik Seviyesi">
                        <span class="text-[10px] text-slate-400">🔊</span>
                        <input
                          type="range"
                          min="0"
                          max="1"
                          step="0.05"
                          [value]="bgmVolume()"
                          (input)="bgmVolume.set($any($event.target).value); persistBgmSettings()"
                          class="w-16 h-1.5 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-violet-500" />
                        <span class="text-[9px] font-mono text-slate-300 w-6">{{ (bgmVolume() * 100).toFixed(0) }}%</span>
                      </div>

                      <!-- Auto-Ducking Aç/Kapat Butonu -->
                      <button
                        type="button"
                        (click)="toggleAutoDucking()"
                        [ngClass]="bgmAutoDucking() ? 'bg-emerald-600/30 text-emerald-300 border-emerald-500/50' : 'bg-slate-800 text-slate-400 border-slate-700'"
                        class="px-2 py-0.5 rounded text-[10px] font-bold border transition-colors flex items-center gap-1 cursor-pointer"
                        title="Konuşmacı varken müzik sesini otomatik kısar">
                        <span>🦆 Ducking</span>
                        <span class="text-[9px]">{{ bgmAutoDucking() ? 'AÇIK' : 'KAPALI' }}</span>
                      </button>

                      <!-- Değiştir / Sil Butonları -->
                      <button
                        type="button"
                        (click)="isBgmSelectorOpen.set(true)"
                        class="p-1 rounded text-slate-400 hover:text-white hover:bg-slate-700/50 text-xs transition-colors cursor-pointer"
                        title="Müzik Ayarları">
                        ⚙️
                      </button>
                      <button
                        type="button"
                        (click)="removeBgm()"
                        class="p-1 rounded text-slate-400 hover:text-rose-400 hover:bg-rose-950/40 text-xs transition-colors cursor-pointer"
                        title="Müziği Kaldır">
                        ✕
                      </button>
                    </div>
                  </div>
                </ng-container>

                <!-- Müzik Yüklü Değil İse Boş Slot -->
                <ng-template #noBgmTemplate>
                  <div
                    (click)="isBgmSelectorOpen.set(true)"
                    class="absolute inset-x-2 top-1 bottom-1 rounded-md border border-dashed border-violet-500/30 hover:border-violet-400/70 bg-violet-950/10 hover:bg-violet-950/30 flex items-center justify-center gap-2 text-violet-400/80 hover:text-violet-200 transition-all cursor-pointer">
                    <span class="text-xs">🎵</span>
                    <span class="text-[11px] font-medium">+ Arka Plan Müziği Ekle (Lo-Fi, Vlog, Sinematik...)</span>
                  </div>
                </ng-template>
              </div>

              <!-- Ses Efektleri Kanalı (A2 SFX Track) -->
              <div class="relative h-10 bg-dark-900/50 border-b border-slate-800/80 overflow-hidden flex items-center select-none">
                <div class="absolute inset-0 bg-[linear-gradient(to_right,#78350f_1px,transparent_1px)] bg-[size:50px_100%] opacity-15 pointer-events-none"></div>

                <div *ngIf="sfxClips().length === 0" (click)="activeTab.set('sfx')" class="absolute inset-x-2 top-1 bottom-1 rounded border border-dashed border-amber-500/25 hover:border-amber-400/60 flex items-center justify-center gap-1.5 text-[10px] text-amber-400/70 hover:text-amber-300 cursor-pointer transition-colors">
                  <span>🔊</span>
                  <span>+ Ses Efekti (SFX) Ekle (Whoosh, Pop, Ding, Bass Drop...)</span>
                </div>

                <div
                  *ngFor="let sfx of sfxClips()"
                  (click)="$event.stopPropagation(); previewSfxClip(sfx)"
                  [ngStyle]="getSfxClipStyle(sfx)"
                  class="absolute top-1 bottom-1 rounded-md bg-gradient-to-r from-amber-600/85 to-orange-600/85 border border-amber-300/70 px-2 flex items-center justify-between text-[10px] font-bold text-white shadow z-20 cursor-pointer group overflow-hidden min-w-[24px]"
                  [title]="(sfx.name || sfx.title || 'SFX') + ' (' + sfx.start.toFixed(1) + 'sn) — Dinlemek için tıkla'">
                  <div class="flex items-center gap-1 truncate pointer-events-none">
                    <span>🔊</span>
                    <span class="truncate">{{ sfx.name || sfx.title || 'SFX' }}</span>
                  </div>
                  <button
                    type="button"
                    (click)="$event.stopPropagation(); removeSfxClip(sfx.id)"
                    class="ml-1 text-[9px] text-amber-100 hover:text-rose-200 opacity-80 group-hover:opacity-100 cursor-pointer">
                    ✕
                  </button>
                </div>
              </div>

              <!-- Ortak Zaman İmleci (Playhead) -->
              <div 
                #playhead
                (mousedown)="onPlayheadDragStart($event)"
                (pointerdown)="onPlayheadPointerDown($event)"
                (pointermove)="onPlayheadPointerMove($event)"
                (pointerup)="onPlayheadPointerUp($event)"
                (pointercancel)="onPlayheadPointerUp($event)"
                class="absolute top-0 bottom-0 w-6 -translate-x-1/2 z-50 cursor-ew-resize pointer-events-auto flex flex-col items-center group touch-none select-none"
                [style.left.%]="getPlayheadPosition()">
                <div class="w-3.5 h-3.5 bg-white rotate-45 shadow-lg rounded-sm border border-slate-300 group-hover:scale-125 transition-transform shrink-0 pointer-events-none"></div>
                <div class="w-0.5 flex-1 bg-white shadow-[0_0_8px_white] pointer-events-none"></div>
              </div>
            </div>
          </div>
        </div>

        <!-- Timeline Alt Kaydırma Çubuğu -->
        <div class="h-7 px-4 bg-dark-900/95 border-t border-slate-800 flex items-center justify-between shrink-0 select-none">
          <!-- Sol: Bilgi -->
          <div class="flex items-center gap-2 text-[10px] text-slate-500">
            <span class="font-mono">{{ formatTime(currentTime()) }}</span>
            <span>/</span>
            <span class="font-mono">{{ formatTime(isAnyRippleActive() ? visibleDuration() : totalDuration()) }}</span>
          </div>
          
          <!-- Orta: Kaydırma Butonları -->
          <div class="flex items-center gap-1">
            <button 
              (click)="scrollTimelineLeft()" 
              class="px-2 py-0.5 rounded bg-dark-800 text-slate-400 hover:text-white hover:bg-slate-700 border border-slate-700 text-[10px] font-bold transition-colors cursor-pointer"
              title="Sola Kaydır">
              ◀ Sol
            </button>
            <button 
              (click)="scrollTimelineToPlayhead()" 
              class="px-2 py-0.5 rounded bg-dark-800 text-brand-cyan hover:text-white hover:bg-slate-700 border border-slate-700 text-[10px] font-bold transition-colors cursor-pointer"
              title="İmlece Git">
              ⊙ İmleç
            </button>
            <button 
              (click)="scrollTimelineRight()" 
              class="px-2 py-0.5 rounded bg-dark-800 text-slate-400 hover:text-white hover:bg-slate-700 border border-slate-700 text-[10px] font-bold transition-colors cursor-pointer"
              title="Sağa Kaydır">
              Sağ ▶
            </button>
          </div>
          
          <!-- Sağ: Kısayol İpucu -->
          <div class="text-[9px] text-slate-600">
            Tekerlek: Sola/Sağa kaydır • Ctrl+Tekerlek: Yakınlaş/Uzaklaş
          </div>
        </div>
      </section>

      <!-- CapCut Stili Kayan Sağ Tık Bağlam Menüsü (Floating Context Menu) -->
      <div 
        *ngIf="contextMenu() as menu"
        (click)="$event.stopPropagation()"
        [style.left.px]="menu.x"
        [style.top.px]="menu.y"
        class="fixed z-50 min-w-[210px] bg-dark-900/95 backdrop-blur-xl border border-slate-700 rounded-xl shadow-2xl py-1.5 text-xs text-slate-200 select-none">
        
        <!-- Klip Menüsü -->
        <ng-container *ngIf="menu.type === 'clip'">
          <div class="px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider text-slate-400 border-b border-slate-800 flex items-center justify-between">
            <span>🎬 Klip İşlemleri</span>
            <span class="font-mono text-[9px] text-brand-cyan">{{ menu.targetClip?.duration?.toFixed(1) }}s</span>
          </div>
          <button 
            (click)="splitClipAtPlayhead(menu.targetClip)"
            class="w-full px-3 py-2 text-left hover:bg-brand-cyan/20 hover:text-brand-cyan flex items-center justify-between transition-colors cursor-pointer">
            <span class="flex items-center gap-2"><span>✂</span> Bu Noktadan Böl</span>
            <kbd class="px-1.5 py-0.5 rounded bg-dark-800 text-[10px] font-mono text-slate-400 border border-slate-700">B</kbd>
          </button>
          <button 
            *ngIf="!menu.targetClip?.isCut"
            (click)="rippleDeleteLeft(); closeContextMenu()"
            class="w-full px-3 py-2 text-left hover:bg-amber-500/20 hover:text-amber-400 flex items-center justify-between transition-colors cursor-pointer">
            <span class="flex items-center gap-2"><span>⏪</span> Soldakini Kırp & Birleştir</span>
            <kbd class="px-1.5 py-0.5 rounded bg-dark-800 text-[10px] font-mono text-amber-300 border border-amber-400/50 font-bold">V</kbd>
          </button>
          <button 
            *ngIf="!menu.targetClip?.isCut"
            (click)="deleteClip(menu.targetClip)"
            class="w-full px-3 py-2 text-left hover:bg-rose-500/20 hover:text-rose-400 flex items-center justify-between transition-colors cursor-pointer">
            <span class="flex items-center gap-2"><span>🗑</span> Klibi Kes / Çıkar</span>
            <kbd class="px-1.5 py-0.5 rounded bg-dark-800 text-[10px] font-mono text-slate-400 border border-slate-700">Del</kbd>
          </button>
          <button 
            *ngIf="menu.targetClip?.isCut"
            (click)="restoreClip(menu.targetClip)"
            class="w-full px-3 py-2 text-left hover:bg-emerald-500/20 hover:text-emerald-400 flex items-center justify-between transition-colors cursor-pointer">
            <span class="flex items-center gap-2"><span>↩</span> Kesimi İptal Et (Geri Al)</span>
            <span class="text-[10px] text-slate-500">Restore</span>
          </button>
          <button 
            *ngIf="selectedClipIds().length > 1"
            (click)="mergeSelectedClips(); closeContextMenu()"
            class="w-full px-3 py-2 text-left hover:bg-sky-500/20 hover:text-sky-300 flex items-center justify-between transition-colors cursor-pointer">
            <span class="flex items-center gap-2"><span>🔗</span> Seçili Klipleri Birleştir</span>
            <kbd class="px-1.5 py-0.5 rounded bg-dark-800 text-[10px] font-mono text-slate-400 border border-slate-700">M</kbd>
          </button>
        </ng-container>

        <!-- Katman (Overlay) Menüsü -->
        <ng-container *ngIf="menu.type === 'overlay'">
          <div class="px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider text-slate-400 border-b border-slate-800 flex items-center justify-between">
            <span>🥞 Katman (#{{ menu.targetOverlay?.trackId || 1 }})</span>
            <span class="font-mono text-[9px] text-amber-400">{{ menu.targetOverlay?.type === 'text' ? 'Metin' : 'Görsel' }}</span>
          </div>
          <button 
            (click)="selectOverlay(menu.targetOverlay!.id); closeContextMenu()"
            class="w-full px-3 py-2 text-left hover:bg-amber-500/20 hover:text-amber-300 flex items-center gap-2 transition-colors cursor-pointer">
            <span>📝</span> Özellikleri Düzenle
          </button>
          <button 
            (click)="duplicateOverlay(menu.targetOverlay!.id); closeContextMenu()"
            class="w-full px-3 py-2 text-left hover:bg-brand-cyan/20 hover:text-brand-cyan flex items-center justify-between transition-colors cursor-pointer">
            <span class="flex items-center gap-2"><span>📋</span> Katmanı Çoğalt</span>
            <kbd class="px-1.5 py-0.5 rounded bg-dark-800 text-[10px] font-mono text-slate-400 border border-slate-700">Ctrl+D</kbd>
          </button>
          <button 
            (click)="splitOverlayAtPlayhead(menu.targetOverlay!); closeContextMenu()"
            class="w-full px-3 py-2 text-left hover:bg-sky-500/20 hover:text-sky-300 flex items-center justify-between transition-colors cursor-pointer">
            <span class="flex items-center gap-2"><span>✂</span> İmleçte İkiye Böl</span>
            <kbd class="px-1.5 py-0.5 rounded bg-dark-800 text-[10px] font-mono text-slate-400 border border-slate-700">B</kbd>
          </button>
          <div class="h-px bg-slate-800 my-1"></div>
          <button 
            (click)="bringOverlayForward(menu.targetOverlay!.id); closeContextMenu()"
            class="w-full px-3 py-2 text-left hover:bg-slate-800 hover:text-white flex items-center gap-2 transition-colors cursor-pointer">
            <span>🔼</span> Bir Üst Katmana Çık (+1)
          </button>
          <button 
            (click)="sendOverlayBackward(menu.targetOverlay!.id); closeContextMenu()"
            class="w-full px-3 py-2 text-left hover:bg-slate-800 hover:text-white flex items-center gap-2 transition-colors cursor-pointer">
            <span>🔽</span> Bir Alt Katmana İn (-1)
          </button>
          <div class="h-px bg-slate-800 my-1"></div>
          <button 
            (click)="removeOverlay(menu.targetOverlay!.id); closeContextMenu()"
            class="w-full px-3 py-2 text-left hover:bg-rose-500/20 hover:text-rose-400 flex items-center justify-between transition-colors cursor-pointer">
            <span class="flex items-center gap-2"><span>🗑</span> Katmanı Sil</span>
            <kbd class="px-1.5 py-0.5 rounded bg-dark-800 text-[10px] font-mono text-slate-400 border border-slate-700">Del</kbd>
          </button>
        </ng-container>

        <!-- Boş Zaman Çizelgesi Menüsü -->
        <ng-container *ngIf="menu.type === 'timeline'">
          <div class="px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider text-slate-400 border-b border-slate-800">
            ⏱ Zaman Çizgisi
          </div>
          <button 
            (click)="addSplitMarker(); closeContextMenu()"
            class="w-full px-3 py-2 text-left hover:bg-brand-cyan/20 hover:text-brand-cyan flex items-center justify-between transition-colors cursor-pointer">
            <span class="flex items-center gap-2"><span>✂</span> Buradan Böl</span>
            <kbd class="px-1.5 py-0.5 rounded bg-dark-800 text-[10px] font-mono text-slate-400 border border-slate-700">B</kbd>
          </button>
          <button 
            (click)="addTextOverlay(); closeContextMenu()"
            class="w-full px-3 py-2 text-left hover:bg-brand-cyan/20 hover:text-brand-cyan flex items-center justify-between transition-colors cursor-pointer">
            <span class="flex items-center gap-2"><span class="font-bold">T</span> Metin Ekle</span>
            <kbd class="px-1.5 py-0.5 rounded bg-dark-800 text-[10px] font-mono text-slate-400 border border-slate-700">T</kbd>
          </button>
          <button 
            (click)="addImageOverlay(); closeContextMenu()"
            class="w-full px-3 py-2 text-left hover:bg-purple-500/20 hover:text-purple-300 flex items-center gap-2 transition-colors cursor-pointer">
            <span>🖼️</span> Görsel / B-Roll Ekle
          </button>
          <button 
            (click)="addTrackLane(); closeContextMenu()"
            class="w-full px-3 py-2 text-left hover:bg-sky-500/20 hover:text-sky-300 flex items-center gap-2 transition-colors cursor-pointer">
            <span>➕</span> Yeni Katman Kanalı Ekle
          </button>
          <div class="h-px bg-slate-800 my-1"></div>
          <button 
            (click)="undo(); closeContextMenu()"
            class="w-full px-3 py-2 text-left hover:bg-slate-800 hover:text-white flex items-center justify-between transition-colors cursor-pointer">
            <span class="flex items-center gap-2"><span>⟲</span> Geri Al</span>
            <kbd class="px-1.5 py-0.5 rounded bg-dark-800 text-[10px] font-mono text-slate-400 border border-slate-700">Ctrl+Z</kbd>
          </button>
          <button 
            (click)="redo(); closeContextMenu()"
            class="w-full px-3 py-2 text-left hover:bg-slate-800 hover:text-white flex items-center justify-between transition-colors cursor-pointer">
            <span class="flex items-center gap-2"><span>⟳</span> İleri Al</span>
            <kbd class="px-1.5 py-0.5 rounded bg-dark-800 text-[10px] font-mono text-slate-400 border border-slate-700">Ctrl+Y</kbd>
          </button>
        </ng-container>
      </div>

      <!-- ARKA PLAN MÜZİĞİ (BGM) VE AUTO-DUCKING SEÇİM MODALI (B5) -->
      <div 
        *ngIf="isBgmSelectorOpen()" 
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 animate-in fade-in duration-150"
        (click)="isBgmSelectorOpen.set(false)">
        <div 
          class="bg-dark-900 border border-slate-700/80 rounded-2xl w-full max-w-xl shadow-2xl overflow-hidden flex flex-col"
          (click)="$event.stopPropagation()">
          
          <!-- Modal Başlığı -->
          <div class="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-dark-950/60">
            <div class="flex items-center gap-2.5">
              <span class="w-8 h-8 rounded-lg bg-violet-600/20 text-violet-400 flex items-center justify-center text-lg border border-violet-500/30">
                🎵
              </span>
              <div>
                <h3 class="text-base font-bold text-white tracking-wide">Arka Plan Müziği & Auto-Ducking</h3>
                <p class="text-xs text-slate-400">Telif ücretsiz müzik kütüphanesinden seçin veya kendi parçanızı ekleyin</p>
              </div>
            </div>
            <button 
              type="button"
              (click)="isBgmSelectorOpen.set(false)"
              class="w-7 h-7 rounded-lg flex items-center justify-center text-slate-400 hover:text-white hover:bg-slate-800 transition-colors text-sm cursor-pointer">
              ✕
            </button>
          </div>

          <!-- Modal İçeriği: Hazır Telif Ücretsiz Parçalar & Özel URL -->
          <div class="p-6 space-y-5 max-h-[70vh] overflow-y-auto scrollbar-thin">
            <!-- Hazır Preset Kartları -->
            <div>
              <span class="text-xs font-semibold text-slate-300 block mb-2.5 uppercase tracking-wider">Öne Çıkan Parçalar (Royalty-Free)</span>
              <div class="grid grid-cols-2 gap-3">
                <!-- Lo-Fi Chill -->
                <button
                  type="button"
                  (click)="setBgmPreset('https://cdn.pixabay.com/download/audio/2022/05/27/audio_1808fbf07a.mp3?filename=lofi-study-112191.mp3', '☕ Lo-Fi Chill Beat')"
                  [ngClass]="bgmTitle() === '☕ Lo-Fi Chill Beat' ? 'border-violet-500 bg-violet-950/30 ring-1 ring-violet-500' : 'border-slate-800 bg-dark-800/60 hover:border-slate-700 hover:bg-dark-800'"
                  class="p-3 rounded-xl border text-left flex flex-col gap-1 transition-all cursor-pointer group">
                  <div class="flex items-center justify-between">
                    <span class="text-sm font-bold text-violet-300 group-hover:text-violet-200">☕ Lo-Fi Chill</span>
                    <span class="text-[10px] px-1.5 py-0.5 rounded bg-violet-500/20 text-violet-300 font-semibold">Sakin & Vlog</span>
                  </div>
                  <p class="text-[11px] text-slate-400 line-clamp-1">Odaklanma, sakin anlatımlar ve vloglar için yumuşak ritim</p>
                </button>

                <!-- Upbeat Vlog -->
                <button
                  type="button"
                  (click)="setBgmPreset('https://cdn.pixabay.com/download/audio/2022/01/18/audio_d0a13f69d2.mp3?filename=electronic-future-beats-117997.mp3', '⚡ Upbeat Tech Vlog')"
                  [ngClass]="bgmTitle() === '⚡ Upbeat Tech Vlog' ? 'border-violet-500 bg-violet-950/30 ring-1 ring-violet-500' : 'border-slate-800 bg-dark-800/60 hover:border-slate-700 hover:bg-dark-800'"
                  class="p-3 rounded-xl border text-left flex flex-col gap-1 transition-all cursor-pointer group">
                  <div class="flex items-center justify-between">
                    <span class="text-sm font-bold text-violet-300 group-hover:text-violet-200">⚡ Upbeat Tech</span>
                    <span class="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-semibold">Dinamik</span>
                  </div>
                  <p class="text-[11px] text-slate-400 line-clamp-1">YouTube inceleme ve Reels için enerjik elektronik ritim</p>
                </button>

                <!-- Cinematic Ambient -->
                <button
                  type="button"
                  (click)="setBgmPreset('https://cdn.pixabay.com/download/audio/2022/03/15/audio_c8c8a73467.mp3?filename=cinematic-atmosphere-score-11004.mp3', '🎬 Cinematic Ambient')"
                  [ngClass]="bgmTitle() === '🎬 Cinematic Ambient' ? 'border-violet-500 bg-violet-950/30 ring-1 ring-violet-500' : 'border-slate-800 bg-dark-800/60 hover:border-slate-700 hover:bg-dark-800'"
                  class="p-3 rounded-xl border text-left flex flex-col gap-1 transition-all cursor-pointer group">
                  <div class="flex items-center justify-between">
                    <span class="text-sm font-bold text-violet-300 group-hover:text-violet-200">🎬 Cinematic Drama</span>
                    <span class="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 font-semibold">Duygusal</span>
                  </div>
                  <p class="text-[11px] text-slate-400 line-clamp-1">Derin yaylılar ve piyano ile etkileyici hikaye anlatımı</p>
                </button>

                <!-- Modern Synthwave -->
                <button
                  type="button"
                  (click)="setBgmPreset('https://cdn.pixabay.com/download/audio/2022/10/14/audio_9939f77cd0.mp3?filename=synthwave-80s-110045.mp3', '🚀 Modern Synthwave')"
                  [ngClass]="bgmTitle() === '🚀 Modern Synthwave' ? 'border-violet-500 bg-violet-950/30 ring-1 ring-violet-500' : 'border-slate-800 bg-dark-800/60 hover:border-slate-700 hover:bg-dark-800'"
                  class="p-3 rounded-xl border text-left flex flex-col gap-1 transition-all cursor-pointer group">
                  <div class="flex items-center justify-between">
                    <span class="text-sm font-bold text-violet-300 group-hover:text-violet-200">🚀 Modern Synth</span>
                    <span class="text-[10px] px-1.5 py-0.5 rounded bg-cyan-500/20 text-cyan-300 font-semibold">Retro Hızlı</span>
                  </div>
                  <p class="text-[11px] text-slate-400 line-clamp-1">80'ler retro-fütüristik dinamik video akışı</p>
                </button>
              </div>
            </div>

            <!-- Özel Ses Dosyası / URL -->
            <div class="pt-2 border-t border-slate-800">
              <label class="text-xs font-semibold text-slate-300 block mb-1.5">Özel Ses URL'si (MP3/WAV)</label>
              <div class="flex gap-2">
                <input 
                  type="text" 
                  #customBgmInput
                  [value]="bgmUrl()"
                  placeholder="https://example.com/audio/track.mp3"
                  class="flex-1 bg-dark-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-violet-500 font-mono" />
                <button
                  type="button"
                  (click)="setBgmPreset(customBgmInput.value, 'Özel Ses Parçası')"
                  class="px-4 py-2 bg-violet-600 hover:bg-violet-500 text-white rounded-lg text-xs font-bold transition-colors cursor-pointer shrink-0">
                  Uygula
                </button>
              </div>
            </div>

            <!-- Auto-Ducking ve Ses Seviyesi Detay Ayarları -->
            <div class="pt-3 border-t border-slate-800 space-y-3">
              <span class="text-xs font-semibold text-slate-300 block">Akıllı Ses Mikseri & Auto-Ducking</span>
              
              <!-- Ducking Toggle -->
              <div class="flex items-center justify-between p-3 rounded-xl bg-dark-950/60 border border-slate-800">
                <div class="flex items-center gap-2.5">
                  <span class="text-lg">🦆</span>
                  <div>
                    <span class="text-xs font-bold text-white block">Sidechain Auto-Ducking</span>
                    <p class="text-[11px] text-slate-400">Konuşmacı başladığında müziği yumuşakça kısar, susunca eski seviyesine yükseltir.</p>
                  </div>
                </div>
                <button
                  type="button"
                  (click)="toggleAutoDucking()"
                  [ngClass]="bgmAutoDucking() ? 'bg-violet-600 text-white' : 'bg-slate-800 text-slate-400'"
                  class="px-3 py-1.5 rounded-lg text-xs font-bold transition-colors cursor-pointer">
                  {{ bgmAutoDucking() ? 'Aktif' : 'Pasif' }}
                </button>
              </div>

              <!-- Ses Seviyeleri -->
              <div class="grid grid-cols-2 gap-4">
                <div>
                  <div class="flex justify-between text-xs text-slate-300 mb-1">
                    <span>Müzik Ses Gücü</span>
                    <span class="font-mono text-violet-400 font-bold">{{ (bgmVolume() * 100).toFixed(0) }}%</span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.05"
                    [value]="bgmVolume()"
                    (input)="bgmVolume.set($any($event.target).value); persistBgmSettings()"
                    class="w-full h-1.5 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-violet-500" />
                </div>
                <div>
                  <div class="flex justify-between text-xs text-slate-300 mb-1">
                    <span>Ducking Seviyesi (Konuşma Anında)</span>
                    <span class="font-mono text-emerald-400 font-bold">{{ (bgmDuckingAmount() * 100).toFixed(0) }}%</span>
                  </div>
                  <input
                    type="range"
                    min="0.05"
                    max="0.40"
                    step="0.02"
                    [value]="bgmDuckingAmount()"
                    (input)="bgmDuckingAmount.set($any($event.target).value); persistBgmSettings()"
                    class="w-full h-1.5 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-emerald-500" />
                </div>
              </div>
            </div>
          </div>

          <!-- Modal Altı -->
          <div class="px-6 py-3 border-t border-slate-800 bg-dark-950/80 flex items-center justify-between">
            <button
              *ngIf="bgmUrl()"
              type="button"
              (click)="removeBgm()"
              class="px-3 py-1.5 rounded-lg text-xs font-semibold text-rose-400 hover:text-rose-300 hover:bg-rose-950/30 transition-colors cursor-pointer">
              Müziği Kaldır
            </button>
            <div *ngIf="!bgmUrl()"></div>
            <button
              type="button"
              (click)="isBgmSelectorOpen.set(false)"
              class="px-5 py-2 rounded-lg bg-violet-600 hover:bg-violet-500 text-white text-xs font-bold transition-colors cursor-pointer">
              Tamamla
            </button>
          </div>

        </div>
      </div>

      <!-- TOPLU KESİM İNCE AYAR (MİLİSANİYE TRİM) MODALI -->
      <div 
        *ngIf="showCutAdjustModal()" 
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 animate-in fade-in duration-150"
        (click)="showCutAdjustModal.set(false)">
        <div 
          class="bg-dark-900 border border-indigo-500/40 rounded-2xl w-full max-w-xl shadow-2xl overflow-hidden flex flex-col"
          (click)="$event.stopPropagation()">
          
          <!-- Modal Başlığı -->
          <div class="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-dark-950/80">
            <div class="flex items-center gap-2.5">
              <span class="w-8 h-8 rounded-lg bg-indigo-600/20 text-indigo-400 flex items-center justify-center text-lg border border-indigo-500/30">
                ⏱️
              </span>
              <div>
                <h3 class="text-base font-bold text-white tracking-wide">Toplu Kesim İnce Ayar (Milisaniye Trim)</h3>
                <p class="text-xs text-slate-400">Kelimelerin erken kesilmesini önlemek ve nefes aralıklarını kusursuz hizalamak için sınırları kaydırın</p>
              </div>
            </div>
            <button 
              type="button"
              (click)="showCutAdjustModal.set(false)"
              class="w-7 h-7 rounded-lg flex items-center justify-center text-slate-400 hover:text-white hover:bg-slate-800 transition-colors text-sm cursor-pointer">
              ✕
            </button>
          </div>

          <!-- Modal İçeriği -->
          <div class="p-6 space-y-5">
            <!-- 1. Kapsam Seçimi -->
            <div>
              <label class="text-xs font-semibold text-slate-300 block mb-2">1. Hangi Kesimler Güncellensin?</label>
              <div class="grid grid-cols-3 gap-2">
                <button 
                  type="button"
                  (click)="cutAdjustScope.set('short')"
                  [ngClass]="cutAdjustScope() === 'short' ? 'bg-indigo-600 text-white border-indigo-400 shadow-glow-sm' : 'bg-dark-800 text-slate-400 border-slate-700 hover:text-slate-200'"
                  class="p-2.5 rounded-xl border text-center transition-all cursor-pointer flex flex-col items-center gap-1">
                  <span class="text-xs font-bold">💨 Kısa Kesimler</span>
                  <span class="text-[10px] opacity-80">&lt; 1.0s ({{ shortCuts().length }} adet)</span>
                </button>
                <button 
                  type="button"
                  (click)="cutAdjustScope.set('long')"
                  [ngClass]="cutAdjustScope() === 'long' ? 'bg-indigo-600 text-white border-indigo-400 shadow-glow-sm' : 'bg-dark-800 text-slate-400 border-slate-700 hover:text-slate-200'"
                  class="p-2.5 rounded-xl border text-center transition-all cursor-pointer flex flex-col items-center gap-1">
                  <span class="text-xs font-bold">⏳ Uzun Kesimler</span>
                  <span class="text-[10px] opacity-80">&gt;= 1.0s ({{ longCuts().length }} adet)</span>
                </button>
                <button 
                  type="button"
                  (click)="cutAdjustScope.set('all')"
                  [ngClass]="cutAdjustScope() === 'all' ? 'bg-indigo-600 text-white border-indigo-400 shadow-glow-sm' : 'bg-dark-800 text-slate-400 border-slate-700 hover:text-slate-200'"
                  class="p-2.5 rounded-xl border text-center transition-all cursor-pointer flex flex-col items-center gap-1">
                  <span class="text-xs font-bold">⚡ Tüm Kesimler</span>
                  <span class="text-[10px] opacity-80">Hepsi ({{ autoCuts().length }} adet)</span>
                </button>
              </div>
            </div>

            <!-- 2. Kesim Başlangıç Kaydırma (Start Offset) -->
            <div class="p-3.5 rounded-xl bg-dark-950/60 border border-slate-800 space-y-2.5">
              <div class="flex items-center justify-between gap-3">
                <div class="flex-1">
                  <span class="text-xs font-bold text-white block">Kesim Başlangıç Noktası (Önceki Kelime Payı)</span>
                  <span class="text-[11px] text-slate-400 block">Pozitif (+) değer kesimi ileri iter; önceki kelimeye daha fazla nefes/sönümlenme payı bırakır.</span>
                </div>
                <div class="flex items-center gap-1.5 shrink-0">
                  <div class="flex items-center bg-dark-900 border border-indigo-500/40 rounded-lg px-2 py-0.5 focus-within:border-indigo-400">
                    <input 
                      type="number" 
                      step="10" 
                      [value]="cutStartOffsetMs()" 
                      (input)="onCutStartInput($event)" 
                      class="w-16 bg-transparent text-right font-mono text-xs font-bold text-indigo-300 focus:outline-none" />
                    <span class="text-[10px] font-mono font-bold text-indigo-400 ml-1">ms</span>
                  </div>
                  <button 
                    type="button" 
                    (click)="cutStartOffsetMs.set(0)" 
                    class="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white text-[10px] font-bold border border-slate-700 transition-colors cursor-pointer"
                    title="Başlangıç Payını Sıfırla">
                    0 ms
                  </button>
                </div>
              </div>
              <div class="flex items-center gap-1.5 flex-wrap">
                <button type="button" *ngFor="let val of [-500, -250, -100, -50, 0, 50, 80, 100, 150, 250, 500, 1000]" 
                  (click)="cutStartOffsetMs.set(val)" 
                  [ngClass]="cutStartOffsetMs() === val ? 'bg-indigo-600 text-white border-indigo-400' : 'bg-dark-800 text-slate-300 border-slate-700 hover:bg-slate-700'"
                  class="px-2 py-0.8 rounded text-[11px] font-mono font-semibold border transition-colors cursor-pointer">
                  {{ val > 0 ? '+' : '' }}{{ val }}ms
                </button>
              </div>
              <div class="flex items-center gap-2">
                <span class="text-[10px] font-mono text-slate-500 shrink-0">-5000</span>
                <input 
                  type="range" 
                  min="-5000" 
                  max="5000" 
                  step="10" 
                  [value]="cutStartOffsetMs()" 
                  (input)="cutStartOffsetMs.set($any($event.target).valueAsNumber)"
                  class="w-full h-1.5 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-indigo-500" />
                <span class="text-[10px] font-mono text-slate-500 shrink-0">+5000</span>
              </div>
            </div>

            <!-- 3. Kesim Bitiş Kaydırma (End Offset) -->
            <div class="p-3.5 rounded-xl bg-dark-950/60 border border-slate-800 space-y-2.5">
              <div class="flex items-center justify-between gap-3">
                <div class="flex-1">
                  <span class="text-xs font-bold text-white block">Kesim Bitiş Noktası (Sonraki Kelime Payı)</span>
                  <span class="text-[11px] text-slate-400 block">Negatif (-) değer kesimi erken bitirir; sonraki kelimenin başlangıç harfini/atağını korur.</span>
                </div>
                <div class="flex items-center gap-1.5 shrink-0">
                  <div class="flex items-center bg-dark-900 border border-emerald-500/40 rounded-lg px-2 py-0.5 focus-within:border-emerald-400">
                    <input 
                      type="number" 
                      step="10" 
                      [value]="cutEndOffsetMs()" 
                      (input)="onCutEndInput($event)" 
                      class="w-16 bg-transparent text-right font-mono text-xs font-bold text-emerald-300 focus:outline-none" />
                    <span class="text-[10px] font-mono font-bold text-emerald-400 ml-1">ms</span>
                  </div>
                  <button 
                    type="button" 
                    (click)="cutEndOffsetMs.set(0)" 
                    class="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white text-[10px] font-bold border border-slate-700 transition-colors cursor-pointer"
                    title="Bitiş Payını Sıfırla">
                    0 ms
                  </button>
                </div>
              </div>
              <div class="flex items-center gap-1.5 flex-wrap">
                <button type="button" *ngFor="let val of [-1000, -500, -250, -150, -100, -80, -50, 0, 50, 100, 250, 500]" 
                  (click)="cutEndOffsetMs.set(val)" 
                  [ngClass]="cutEndOffsetMs() === val ? 'bg-emerald-600 text-white border-emerald-400' : 'bg-dark-800 text-slate-300 border-slate-700 hover:bg-slate-700'"
                  class="px-2 py-0.8 rounded text-[11px] font-mono font-semibold border transition-colors cursor-pointer">
                  {{ val > 0 ? '+' : '' }}{{ val }}ms
                </button>
              </div>
              <div class="flex items-center gap-2">
                <span class="text-[10px] font-mono text-slate-500 shrink-0">-5000</span>
                <input 
                  type="range" 
                  min="-5000" 
                  max="5000" 
                  step="10" 
                  [value]="cutEndOffsetMs()" 
                  (input)="cutEndOffsetMs.set($any($event.target).valueAsNumber)"
                  class="w-full h-1.5 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-emerald-500" />
                <span class="text-[10px] font-mono text-slate-500 shrink-0">+5000</span>
              </div>
            </div>

            <!-- Hızlı Tavsiye Butonları (Presets) & Sıfırla -->
            <div class="flex items-center justify-between p-2.5 rounded-lg bg-indigo-950/30 border border-indigo-900/50 text-[11px] flex-wrap gap-2">
              <div class="flex items-center gap-2">
                <span class="text-indigo-300 font-medium">💡 Hızlı Öneri: Kelime sonu erken kesiliyorsa</span>
                <button 
                  type="button"
                  (click)="cutStartOffsetMs.set(100); cutEndOffsetMs.set(-60)"
                  class="px-2.5 py-1 rounded bg-indigo-600/40 hover:bg-indigo-600 text-indigo-100 font-bold transition-colors cursor-pointer border border-indigo-400/40">
                  +100ms Baş / -60ms Son Ayarla
                </button>
              </div>
              <button 
                type="button"
                (click)="resetCutAdjustOffsets()"
                class="px-3 py-1 rounded bg-rose-500/20 text-rose-300 hover:bg-rose-500/30 border border-rose-500/40 font-bold transition-colors cursor-pointer flex items-center gap-1.5">
                <span>🔄</span>
                <span>Tümünü Sıfırla (0 ms)</span>
              </button>
            </div>
          </div>

          <!-- Modal Altı Butonlar -->
          <div class="px-6 py-3.5 border-t border-slate-800 bg-dark-950/80 flex items-center justify-between">
            <span class="text-xs text-slate-400 font-medium">
              Uygulanacak: <strong class="text-white">{{ getTargetCutsCount() }}</strong> kesim
            </span>
            <div class="flex items-center gap-2">
              <button 
                type="button"
                (click)="showCutAdjustModal.set(false)"
                class="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold transition-colors cursor-pointer">
                Vazgeç
              </button>
              <button 
                type="button"
                [disabled]="cutAdjustLoading()"
                (click)="applyBatchCutAdjustment()"
                class="px-5 py-2 rounded-lg bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white text-xs font-bold transition-all shadow-glow-sm cursor-pointer disabled:opacity-50">
                {{ cutAdjustLoading() ? 'Uygulanıyor...' : 'Değişiklikleri Uygula' }}
              </button>
            </div>
          </div>

        </div>
      </div>

      <!-- VİDEO RENK AYARLARI (COLOR GRADING) MODALI -->
      <div 
        *ngIf="showColorModal()" 
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 animate-in fade-in duration-150"
        (click)="showColorModal.set(false)">
        <div 
          class="bg-dark-900 border border-amber-500/40 rounded-2xl w-full max-w-lg shadow-2xl overflow-hidden flex flex-col"
          (click)="$event.stopPropagation()">
          
          <!-- Modal Başlığı -->
          <div class="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-dark-950/80">
            <div class="flex items-center gap-2.5">
              <span class="w-8 h-8 rounded-lg bg-amber-500/20 text-amber-400 flex items-center justify-center text-lg border border-amber-500/30">
                🎨
              </span>
              <div>
                <h3 class="text-sm font-bold text-white">Video Renk Ayarları (Color Grading)</h3>
                <p class="text-[11px] text-slate-400">Canlı parlaklık, kontrast, doygunluk ve renk sıcaklığı filtreleri</p>
              </div>
            </div>
            <button 
              type="button" 
              (click)="showColorModal.set(false)"
              class="w-7 h-7 rounded-lg bg-dark-800 hover:bg-slate-700 text-slate-400 hover:text-white flex items-center justify-center text-sm transition-colors cursor-pointer">
              ✕
            </button>
          </div>

          <!-- Modal İçeriği (Kaydırıcılar ve Ön Tanımlar) -->
          <div class="p-6 space-y-4 max-h-[75vh] overflow-y-auto">
            
            <!-- Hazır Filtre Presets -->
            <div class="space-y-1.5">
              <label class="text-[10px] text-slate-400 uppercase font-semibold block">Hazır Renk Stilleri (Presets)</label>
              <div class="grid grid-cols-5 gap-1.5 text-[11px]">
                <button 
                  type="button" 
                  (click)="applyColorPreset('default')"
                  [ngClass]="!isColorGraded() ? 'bg-amber-500 text-slate-950 font-bold' : 'bg-dark-800 text-slate-300 hover:bg-slate-700'"
                  class="p-2 rounded-lg border border-slate-700 text-center transition-colors cursor-pointer">
                  Doğal
                </button>
                <button 
                  type="button" 
                  (click)="applyColorPreset('vibrant')"
                  class="p-2 rounded-lg bg-dark-800 hover:bg-slate-700 border border-slate-700 text-center text-slate-300 transition-colors cursor-pointer">
                  ✨ Canlı
                </button>
                <button 
                  type="button" 
                  (click)="applyColorPreset('cinematic')"
                  class="p-2 rounded-lg bg-dark-800 hover:bg-slate-700 border border-slate-700 text-center text-slate-300 transition-colors cursor-pointer">
                  🎬 Sinematik
                </button>
                <button 
                  type="button" 
                  (click)="applyColorPreset('cool')"
                  class="p-2 rounded-lg bg-dark-800 hover:bg-slate-700 border border-slate-700 text-center text-slate-300 transition-colors cursor-pointer">
                  ❄️ Soğuk
                </button>
                <button 
                  type="button" 
                  (click)="applyColorPreset('bw')"
                  class="p-2 rounded-lg bg-dark-800 hover:bg-slate-700 border border-slate-700 text-center text-slate-300 transition-colors cursor-pointer">
                  🎞️ S&B
                </button>
              </div>
            </div>

            <!-- 1. Parlaklık (Brightness) -->
            <div class="p-3.5 rounded-xl bg-dark-950/60 border border-slate-800 space-y-2">
              <div class="flex items-center justify-between text-xs">
                <span class="font-bold text-white">☀️ Parlaklık (Brightness)</span>
                <span class="font-mono text-amber-400 font-bold">%{{ videoBrightness() }}</span>
              </div>
              <input 
                type="range" 
                min="50" 
                max="150" 
                step="1" 
                [value]="videoBrightness()" 
                (input)="videoBrightness.set($any($event.target).valueAsNumber)"
                class="w-full h-1.5 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-amber-500" />
              <div class="flex justify-between text-[9px] text-slate-500 font-mono">
                <span>Koyu (%50)</span>
                <span>Varsayılan (%100)</span>
                <span>Açık (%150)</span>
              </div>
            </div>

            <!-- 2. Kontrast (Contrast) -->
            <div class="p-3.5 rounded-xl bg-dark-950/60 border border-slate-800 space-y-2">
              <div class="flex items-center justify-between text-xs">
                <span class="font-bold text-white">🌓 Kontrast (Contrast)</span>
                <span class="font-mono text-amber-400 font-bold">%{{ videoContrast() }}</span>
              </div>
              <input 
                type="range" 
                min="50" 
                max="160" 
                step="1" 
                [value]="videoContrast()" 
                (input)="videoContrast.set($any($event.target).valueAsNumber)"
                class="w-full h-1.5 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-amber-500" />
              <div class="flex justify-between text-[9px] text-slate-500 font-mono">
                <span>Yumuşak (%50)</span>
                <span>Varsayılan (%100)</span>
                <span>Keskin (%160)</span>
              </div>
            </div>

            <!-- 3. Doygunluk (Saturation) -->
            <div class="p-3.5 rounded-xl bg-dark-950/60 border border-slate-800 space-y-2">
              <div class="flex items-center justify-between text-xs">
                <span class="font-bold text-white">🌈 Doygunluk (Saturation)</span>
                <span class="font-mono text-amber-400 font-bold">%{{ videoSaturation() }}</span>
              </div>
              <input 
                type="range" 
                min="0" 
                max="200" 
                step="2" 
                [value]="videoSaturation()" 
                (input)="videoSaturation.set($any($event.target).valueAsNumber)"
                class="w-full h-1.5 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-amber-500" />
              <div class="flex justify-between text-[9px] text-slate-500 font-mono">
                <span>Gri/Soluk (%0)</span>
                <span>Varsayılan (%100)</span>
                <span>Çok Renkli (%200)</span>
              </div>
            </div>

            <!-- 4. Renk Sıcaklığı (Temperature / Hue) -->
            <div class="p-3.5 rounded-xl bg-dark-950/60 border border-slate-800 space-y-2">
              <div class="flex items-center justify-between text-xs">
                <span class="font-bold text-white">🌡️ Renk Sıcaklığı / Ton (Hue)</span>
                <span class="font-mono text-amber-400 font-bold">{{ videoTemperature() > 0 ? '+' : '' }}{{ videoTemperature() }}°</span>
              </div>
              <input 
                type="range" 
                min="-30" 
                max="30" 
                step="1" 
                [value]="videoTemperature()" 
                (input)="videoTemperature.set($any($event.target).valueAsNumber)"
                class="w-full h-1.5 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-amber-500" />
              <div class="flex justify-between text-[9px] text-slate-500 font-mono">
                <span>Soğuk (-30°)</span>
                <span>Nötr (0°)</span>
                <span>Sıcak (+30°)</span>
              </div>
            </div>

          </div>

          <!-- Modal Altı Butonlar -->
          <div class="px-6 py-3.5 border-t border-slate-800 bg-dark-950/80 flex items-center justify-between">
            <button 
              type="button"
              (click)="resetColorGrading()"
              class="px-3 py-1.5 rounded-lg bg-dark-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold transition-colors cursor-pointer flex items-center gap-1.5 border border-slate-700">
              <span>🔄</span>
              <span>Sıfırla</span>
            </button>
            <div class="flex items-center gap-2">
              <button 
                type="button"
                (click)="showColorModal.set(false)"
                class="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold transition-colors cursor-pointer">
                Kapat
              </button>
              <button 
                type="button"
                (click)="saveColorGrading()"
                class="px-5 py-2 rounded-lg bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 text-slate-950 text-xs font-bold transition-all shadow-glow-sm cursor-pointer">
                Kaydet
              </button>
            </div>
          </div>

        </div>
      </div>

      <!-- SAHNE GEÇİŞ EFEKTLERİ (FFMPEG XFADE TRANSITIONS) MODALI -->
      <div 
        *ngIf="showTransitionModal()" 
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 animate-in fade-in duration-150"
        (click)="showTransitionModal.set(false)">
        <div 
          class="bg-dark-900 border border-brand-cyan/40 rounded-2xl w-full max-w-xl shadow-2xl overflow-hidden flex flex-col"
          (click)="$event.stopPropagation()">
          
          <div class="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-dark-950/80">
            <div class="flex items-center gap-2.5">
              <span class="w-8 h-8 rounded-lg bg-brand-cyan/20 text-brand-cyan flex items-center justify-center text-lg border border-brand-cyan/30">
                ⚡
              </span>
              <div>
                <h3 class="text-sm font-bold text-white">Sahne Geçiş Efektleri (CapCut & Premiere Transitions)</h3>
                <p class="text-[11px] text-slate-400">
                  Kesim Noktası: <strong class="text-brand-cyan font-mono">{{ activeTransitionBoundary()?.boundaryTime?.toFixed(2) }}sn</strong> • FFmpeg xfade + acrossfade
                </p>
              </div>
            </div>
            <button type="button" (click)="showTransitionModal.set(false)" class="w-7 h-7 rounded-lg bg-dark-800 hover:bg-slate-700 text-slate-400 hover:text-white flex items-center justify-center text-sm cursor-pointer">✕</button>
          </div>

          <div class="p-5 space-y-4 max-h-[70vh] overflow-y-auto">
            <!-- 14 Geçiş Efekti Kartları -->
            <div class="grid grid-cols-2 sm:grid-cols-3 gap-2">
              <button
                *ngFor="let tr of studio.transitionLibrary"
                type="button"
                (click)="selectedTransitionType.set(tr.type)"
                [ngClass]="selectedTransitionType() === tr.type ? 'border-brand-cyan bg-brand-cyan/15 ring-1 ring-brand-cyan text-white' : 'border-slate-800 bg-dark-950/70 hover:border-slate-700 text-slate-300'"
                class="p-2.5 rounded-xl border text-left flex items-start gap-2 transition-all cursor-pointer">
                <span class="text-lg shrink-0">{{ tr.icon }}</span>
                <div class="min-w-0">
                  <div class="text-xs font-bold truncate">{{ tr.name }}</div>
                  <div class="text-[9px] text-slate-400 line-clamp-1">{{ tr.description }}</div>
                </div>
              </button>
            </div>

            <!-- Geçiş Süresi -->
            <div class="p-3 rounded-xl bg-dark-950/70 border border-slate-800 space-y-1.5">
              <div class="flex items-center justify-between text-xs">
                <span class="font-bold text-slate-200">⏱ Geçiş Süresi (Duration)</span>
                <span class="font-mono text-brand-cyan font-bold">{{ selectedTransitionDuration().toFixed(2) }} sn</span>
              </div>
              <input
                type="range"
                min="0.2"
                max="1.5"
                step="0.05"
                [value]="selectedTransitionDuration()"
                (input)="selectedTransitionDuration.set($any($event.target).valueAsNumber)"
                class="w-full accent-brand-cyan cursor-pointer" />
            </div>
          </div>

          <div class="px-6 py-3.5 border-t border-slate-800 bg-dark-950/80 flex items-center justify-between gap-2 flex-wrap">
            <div class="flex items-center gap-2">
              <button
                *ngIf="activeTransitionBoundary()?.existing"
                type="button"
                (click)="removeCurrentTransition()"
                class="px-3 py-1.5 rounded-lg bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 border border-rose-500/40 text-xs font-semibold cursor-pointer">
                🗑 Geçişi Kaldır
              </button>
              <button
                type="button"
                (click)="applyTransitionToAllCuts()"
                class="px-3 py-1.5 rounded-lg bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/40 text-xs font-bold cursor-pointer">
                ⚡ Tüm Kesimlere Uygula
              </button>
            </div>
            <div class="flex items-center gap-2">
              <button type="button" (click)="showTransitionModal.set(false)" class="px-4 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold cursor-pointer">
                Kapat
              </button>
              <button type="button" (click)="saveCurrentTransition()" class="px-5 py-1.5 rounded-lg bg-brand-cyan hover:bg-cyan-400 text-slate-950 text-xs font-bold shadow-glow-sm cursor-pointer">
                ✓ Bu Kesime Uygula
              </button>
            </div>
          </div>
        </div>
      </div>
    </main>
  `,
  styles: [`
    @keyframes loopPulse {
      0%, 100% { transform: scale(1); }
      50% { transform: scale(1.08); }
    }
    @keyframes loopFloat {
      0%, 100% { transform: translateY(0px); }
      50% { transform: translateY(-8px); }
    }
    @keyframes loopWiggle {
      0%, 100% { transform: rotate(-3deg); }
      50% { transform: rotate(3deg); }
    }
    @keyframes loopShake {
      0%, 100% { transform: translate(0, 0); }
      25% { transform: translate(-3px, 2px); }
      50% { transform: translate(3px, -2px); }
      75% { transform: translate(-2px, -2px); }
    }
    @keyframes loopNeonFlicker {
      0%, 19%, 21%, 23%, 25%, 54%, 56%, 100% { opacity: 1; }
      20%, 24%, 55% { opacity: 0.45; }
    }
    @keyframes loopPendulum {
      0%, 100% { transform: rotate(-6deg); transform-origin: top center; }
      50% { transform: rotate(6deg); transform-origin: top center; }
    }
    .anim-loop-pulse { animation: loopPulse 1.2s ease-in-out infinite; }
    .anim-loop-float { animation: loopFloat 2.0s ease-in-out infinite; }
    .anim-loop-wiggle { animation: loopWiggle 0.8s ease-in-out infinite; }
    .anim-loop-shake { animation: loopShake 0.35s linear infinite; }
    .anim-loop-neon { animation: loopNeonFlicker 2.2s infinite; }
    .anim-loop-pendulum { animation: loopPendulum 1.6s ease-in-out infinite; }
  `]
})
export class EditorComponent implements OnInit, OnDestroy {
  isScrubbing = false;
  private wasDragging = false;
  private scrubSeekPending = false;
  private scrubTargetTime: number | null = null;
  private wasPlayingBeforeScrub = false;
  private scrubMoveLogCounter = 0;

  handleScrubMouseMove(clientX: number): void {
    if (!this.isScrubbing) return;
    this.wasDragging = true;
    
    const targetTime = this.getTimeAtClientX(clientX);
    this.currentTime.set(targetTime);

    if (this.scrubMoveLogCounter++ % 5 === 0) {
      console.log(`%c[SCRUB:MOVE] clientX=${clientX} -> targetTime=${targetTime.toFixed(2)}s | playheadPos=${this.getPlayheadPosition().toFixed(1)}% | videoSeeking=${this.videoRef?.nativeElement?.seeking}`, 'color: #38bdf8;');
    }

    // Throttled video preview: requestAnimationFrame & fastSeek ile donma yapmayan akıcı önizleme
    this.scrubTargetTime = targetTime;
    if (!this.scrubSeekPending) {
      this.scrubSeekPending = true;
      requestAnimationFrame(() => {
        this.scrubSeekPending = false;
        const v = this.videoRef?.nativeElement;
        if (v && this.scrubTargetTime !== null && !v.seeking) {
          try {
            const videoEl = v as any;
            if (typeof videoEl.fastSeek === 'function') {
              videoEl.fastSeek(this.scrubTargetTime);
            } else {
              videoEl.currentTime = this.scrubTargetTime;
            }
          } catch (err) {
            console.error('[SCRUB:PREVIEW_ERROR]', err);
          }
        }
      });
    }
  }

  handleScrubMouseUp(): void {
    if (this.isScrubbing) {
      console.log(`%c[SCRUB:MOUSE_UP] Bırakıldı! wasDragging=${this.wasDragging}, currentTime=${this.currentTime().toFixed(2)}s`, 'color: #10b981; font-weight: bold;');
      this.isScrubbing = false;
      this.scrubTargetTime = null;
      const v = this.videoRef?.nativeElement;
      if (v) {
        try {
          v.currentTime = this.currentTime();
          if (this.wasPlayingBeforeScrub) {
            v.play().catch(e => console.warn('[SCRUB:RESUME_ERROR]', e));
            this.wasPlayingBeforeScrub = false;
          }
        } catch (err) {
          console.error('[SCRUB:MOUSE_UP_ERROR]', err);
        }
      }
    }
  }

  onPlayheadPointerDown(event: PointerEvent): void {
    if (event.button !== 0) return;
    event.preventDefault();
    event.stopPropagation();
    const target = event.currentTarget as HTMLElement;
    if (target && typeof target.setPointerCapture === 'function') {
      try {
        target.setPointerCapture(event.pointerId);
      } catch (e) {
        console.warn('[SCRUB:POINTER_CAPTURE_FAIL]', e);
      }
    }
    console.log(`%c[SCRUB:PLAYHEAD_POINTER_DOWN] Beyaz iğne tutuldu (PointerCapture)! clientX=${event.clientX}, currentTime=${this.currentTime().toFixed(2)}s`, 'color: #f59e0b; font-weight: bold;');
    this.startScrubbing(event.clientX);
  }

  onPlayheadPointerMove(event: PointerEvent): void {
    if (!this.isScrubbing) return;
    event.preventDefault();
    this.handleScrubMouseMove(event.clientX);
  }

  onPlayheadPointerUp(event: PointerEvent): void {
    const target = event.currentTarget as HTMLElement;
    if (target && typeof target.releasePointerCapture === 'function') {
      try {
        if (target.hasPointerCapture(event.pointerId)) {
          target.releasePointerCapture(event.pointerId);
        }
      } catch (e) {
        // ignore
      }
    }
    this.handleScrubMouseUp();
  }

  onPlayheadDragStart(event: MouseEvent): void {
    if (event.button !== 0) return;
    event.preventDefault();
    event.stopPropagation();
    console.log(`%c[SCRUB:PLAYHEAD_DOWN] Beyaz iğne tutuldu! clientX=${event.clientX}, currentTime=${this.currentTime().toFixed(2)}s`, 'color: #f59e0b; font-weight: bold;');
    this.startScrubbing(event.clientX);
  }

  onRulerMouseDown(event: MouseEvent): void {
    if (event.button !== 0) return;
    event.preventDefault();
    console.log(`%c[SCRUB:RULER_DOWN] Zaman Cetveli tıklandı! clientX=${event.clientX}`, 'color: #f59e0b; font-weight: bold;');
    this.startScrubbing(event.clientX);
  }

  onTimelineTrackMouseDown(event: MouseEvent): void {
    if (event.button !== 0) return;
    const target = event.target as HTMLElement;
    // Eğer tıklanan element bir buton, klip, katman, altyazı, input veya playhead ise timeline zemin sürüklemesi BAŞLATMA
    if (target && (
      target.closest('button') ||
      target.closest('input') ||
      target.closest('.timeline-clip') ||
      target.closest('.overlay-item') ||
      target.closest('.subtitle-segment') ||
      target.closest('#playhead')
    )) {
      return;
    }
    console.log(`%c[SCRUB:TRACK_DOWN] Timeline zemini tıklandı! clientX=${event.clientX}`, 'color: #f59e0b; font-weight: bold;');
    this.startScrubbing(event.clientX);
  }

  onClipMouseDown(event: MouseEvent, clipId: string): void {
    if (event.button !== 0) return;
    event.stopPropagation();
    this.selectClip(clipId, event);
  }

  onSubtitleMouseDown(event: MouseEvent, seg: TranscriptSegment): void {
    if (event.button !== 0) return;
    this.onSubtitleDragStart(event, seg);
  }

  startScrubbing(clientX: number): void {
    this.isScrubbing = true;
    this.wasDragging = false;
    this.scrubMoveLogCounter = 0;
    const v = this.videoRef?.nativeElement;
    if (v && !v.paused) {
      this.wasPlayingBeforeScrub = true;
      v.pause();
    } else {
      this.wasPlayingBeforeScrub = false;
    }
    const targetTime = this.getTimeAtClientX(clientX);
    console.log(`%c[SCRUB:START] targetTime=${targetTime.toFixed(2)}s, totalDur=${this.totalDuration().toFixed(1)}s, visDur=${this.visibleDuration().toFixed(1)}s, ripple=${this.isAnyRippleActive()}`, 'color: #818cf8; font-weight: bold;');
    this.currentTime.set(targetTime);
    if (v && !v.seeking) {
      try {
        v.currentTime = targetTime;
      } catch (err) {
        console.error('[SCRUB:START_SEEK_ERROR]', err);
      }
    }
  }

  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private projectService = inject(ProjectService);
  private videoService = inject(VideoService);
  private edlService = inject(EdlService);
  private chatService = inject(ChatService);
  private renderService = inject(RenderService);
  private assetService = inject(AssetService);
  private signalr = inject(SignalrService);
  private diagnostics = inject(DiagnosticsService);
  readonly studio = inject(StudioEngineService);
  readonly studioEngine = this.studio;

  @ViewChild('videoPlayer') videoRef!: ElementRef<HTMLVideoElement>;
  @ViewChild('bgmAudioPlayer') bgmAudioRef?: ElementRef<HTMLAudioElement>;
  @ViewChild('chatMessagesContainer') chatContainer!: ElementRef<HTMLDivElement>;
  @ViewChild('timelineTrack') timelineTrackRef!: ElementRef<HTMLDivElement>;
  @ViewChild('timelineScrollContainer') timelineScrollContainerRef?: ElementRef<HTMLDivElement>;
  @ViewChild('assetFileInput') assetFileInput?: ElementRef<HTMLInputElement>;

  readonly assets = signal<ProjectAssetDto[]>([]);
  readonly isUploadingAsset = signal<boolean>(false);
  readonly isDragOver = signal<boolean>(false);

  projectId = '';
  readonly project = signal<ProjectDetailDto | null>(null);
  readonly edl = signal<EdlContent | null>(null);
  readonly videoUrl = signal<string>('');
  readonly videoAspectRatio = signal<string>('16 / 9');
  readonly currentTime = signal<number>(0);
  readonly totalDuration = signal<number>(100);

  // Ses Dalga Formu (Web Audio API Waveform)
  readonly audioPeaks = signal<number[] | null>(null);
  readonly isWaveformLoading = signal<boolean>(false);

  // Oynatma Durumu
  readonly isPlaying = signal<boolean>(false);

  // Altyazı & Karaoke Stüdyosu (CapCut Stili B4)
  readonly showSubtitles = signal<boolean>(true);
  readonly subtitlePreset = signal<'tiktok_yellow' | 'cinematic_shadow' | 'opaque_banner' | 'neon_glow' | 'custom'>('tiktok_yellow');
  readonly subtitleFont = signal<string>('Montserrat, Inter, sans-serif');
  readonly subtitleFontSize = signal<number>(44);
  readonly subtitleColor = signal<string>('#FFFFFF');
  readonly subtitleHighlightColor = signal<string>('#FFD700');
  readonly subtitleStrokeColor = signal<string>('#000000');
  readonly subtitleStrokeWidth = signal<number>(3);
  readonly subtitleShadowColor = signal<string>('rgba(0, 0, 0, 0.8)');
  readonly subtitleShadowBlur = signal<number>(2);
  readonly subtitleBgColor = signal<string>('rgba(0, 0, 0, 0.7)');
  readonly subtitleBgPadding = signal<number>(10);
  readonly subtitleBorderRadius = signal<number>(8);
  readonly subtitleAllCaps = signal<boolean>(false);
  readonly subtitleLetterSpacing = signal<number>(0);
  readonly subtitlePositionY = signal<number>(85);

  // Arka Plan Müziği (BGM) & Auto-Ducking State (B5)
  readonly bgmUrl = signal<string>('');
  readonly bgmTitle = signal<string>('Arka Plan Müziği Yok');
  readonly bgmVolume = signal<number>(0.25);
  readonly bgmAutoDucking = signal<boolean>(true);
  readonly bgmDuckingAmount = signal<number>(0.15);
  readonly isBgmSelectorOpen = signal<boolean>(false);

  // Profesyonel Stüdyo Sekme & Filtre Durumları (Faz 1-6)
  readonly textInspectorTab = signal<'style' | 'presets' | 'effects' | 'anim' | 'transform'>('style');
  readonly imageInspectorTab = signal<'ai' | 'adjust' | 'transform' | 'anim'>('ai');
  readonly selectedSfxCategory = signal<string>('all');
  readonly selectedStickerCategory = signal<string>('all');
  customGifUrl = '';
  readonly isRemovingBgNow = signal<boolean>(false);
  readonly bgRemovalProcessing = this.isRemovingBgNow;
  readonly normalizeAudio = signal<boolean>(false);
  readonly smartPunchIn = signal<boolean>(false);
  readonly clipSpeedMap = signal<Record<string, number>>({});
  private triggeredSfxSet = new Set<string>();

  // Sahne Geçişleri (Transitions) Durumu (Faz 4)
  readonly showTransitionModal = signal<boolean>(false);
  readonly transitionModalOpen = this.showTransitionModal;
  readonly activeTransitionBoundary = signal<any | null>(null);
  readonly editingTransitionBoundaryTime = signal<number>(0);
  readonly selectedTransitionType = signal<string>('fade');
  readonly editingTransitionType = this.selectedTransitionType;
  readonly selectedTransitionDuration = signal<number>(0.45);
  readonly editingTransitionDuration = this.selectedTransitionDuration;

  readonly filteredSfxLibrary = computed<SfxLibraryItem[]>(() => {
    const cat = this.selectedSfxCategory();
    if (cat === 'all') return this.studio.sfxLibrary;
    return this.studio.sfxLibrary.filter(item => item.category === cat);
  });

  readonly filteredStickers = computed<StickerLibraryItem[]>(() => {
    const cat = this.selectedStickerCategory();
    if (cat === 'all') return this.studio.stickerLibrary;
    return this.studio.stickerLibrary.filter(item => item.category === cat);
  });

  readonly sfxClips = computed<EdlSfxClip[]>(() => {
    return this.activeEdl()?.sfxClips || [];
  });

  readonly transitions = computed<EdlTransition[]>(() => {
    return this.activeEdl()?.transitions || [];
  });

  readonly pendingSuggestions = computed<SuggestionItem[]>(() => {
    return (this.activeEdl()?.suggestions || []).filter(s => s.status === 'pending' || !s.status);
  });

  readonly currentSubtitleSegment = computed<TranscriptSegment | null>(() => {
    const edl = this.activeEdl();
    const segments = edl?.transcript?.segments;
    if (!segments || segments.length === 0) return null;
    const t = this.currentTime();

    // Adım 4.1: Oynatma kafası aktif bir kesim bölgesindeyse (retake/sessizlik) altyazı gösterme
    const cuts = edl?.cuts;
    if (cuts && cuts.some(c => t >= c.start && t <= c.end)) {
      return null;
    }

    return segments.find(s => t >= s.start && t <= s.end) || null;
  });

  readonly vttTrackUrl = computed<string | null>(() => {
    const edl = this.activeEdl();
    const segments = edl?.transcript?.segments;
    if (!segments || segments.length === 0) return null;

    const cuts = edl?.cuts || [];

    let vttContent = 'WEBVTT\n\n';
    let trackIdx = 1;
    segments.forEach((seg) => {
      // Eğer segment tamamen bir kesimin içindeyse VTT parçasına ekleme
      const isCutOut = cuts.some(c => c.start <= seg.start && seg.end <= c.end);
      if (!isCutOut) {
        const start = this.formatVttTimestamp(seg.start);
        const end = this.formatVttTimestamp(seg.end);
        vttContent += `${trackIdx++}\n${start} --> ${end}\n${seg.text.trim()}\n\n`;
      }
    });

    const blob = new Blob([vttContent], { type: 'text/vtt' });
    return URL.createObjectURL(blob);
  });

  // Katman Kontrolleri (B7: Hide, Lock, Delete)
  readonly hiddenTracks = signal<Set<number>>(new Set());
  readonly lockedTracks = signal<Set<number>>(new Set());

  readonly activeOverlays = computed(() => {
    const t = this.currentTime();
    const overlays = this.activeEdl()?.overlays || [];
    const hidden = this.hiddenTracks();
    return overlays.filter(ov => {
      const trackId = Number(ov.trackId) || 1;
      if (hidden.has(trackId)) return false;
      return t >= ov.timestamp && t <= (ov.timestamp + ov.duration);
    });
  });

  // Sol Panel Aktif Sekmesi
  readonly activeTab = signal<'chat' | 'overlays' | 'inspector' | 'media' | 'sfx' | 'transcript'>('chat');
  readonly rendering = signal<boolean>(false);
  readonly rippleAi = signal<boolean>(true);
  readonly rippleManual = signal<boolean>(true);
  readonly rippleRetake = signal<boolean>(true);

  readonly retakeCount = computed(() => {
    const edl = this.activeEdl();
    if (!edl || !edl.cuts) return 0;
    return edl.cuts.filter(c => {
      const r = (c.reason || '').toLowerCase();
      return r.includes('retake') || r.includes('tekrar');
    }).length;
  });

  // Oynatma Hızı (0.5x, 0.75x, 1x, 1.25x, 1.5x, 2x)
  readonly playbackSpeed = signal<number>(1.0);

  // Video Renk Ayarları (Color Grading)
  readonly showColorModal = signal<boolean>(false);
  readonly videoBrightness = signal<number>(100);
  readonly videoContrast = signal<number>(100);
  readonly videoSaturation = signal<number>(100);
  readonly videoTemperature = signal<number>(0);
  readonly isColorGraded = computed<boolean>(() => {
    return this.videoBrightness() !== 100 || 
           this.videoContrast() !== 100 || 
           this.videoSaturation() !== 100 || 
           this.videoTemperature() !== 0;
  });
  readonly videoFilterStyle = computed<string>(() => {
    const b = this.videoBrightness() / 100;
    const c = this.videoContrast() / 100;
    const s = this.videoSaturation() / 100;
    const h = this.videoTemperature();
    return `brightness(${b}) contrast(${c}) saturate(${s}) hue-rotate(${h}deg)`;
  });

  // B-Roll Stok Kütüphanesi
  readonly stockCategories = [
    { id: 'legal', name: '⚖️ Hukuk & Adalet' },
    { id: 'tech', name: '💻 Teknoloji' },
    { id: 'nature', name: '🌿 Doğa' },
    { id: 'history', name: '📚 Tarih & Kitap' },
    { id: 'business', name: '📈 İş & Ekonomi' }
  ];
  readonly selectedStockCategory = signal<string>('legal');
  readonly stockImagesLibrary: Record<string, { title: string; thumb: string; url: string }[]> = {
    legal: [
      { title: 'Adalet Terazisi', thumb: 'https://images.unsplash.com/photo-1589829545856-d10d557cf95f?w=300&q=80', url: 'https://images.unsplash.com/photo-1589829545856-d10d557cf95f?w=1080&q=80' },
      { title: 'Mahkeme Tokmağı', thumb: 'https://images.unsplash.com/photo-1589994965851-a8f479c573a9?w=300&q=80', url: 'https://images.unsplash.com/photo-1589994965851-a8f479c573a9?w=1080&q=80' },
      { title: 'Hukuk Kütüphanesi', thumb: 'https://images.unsplash.com/photo-1505664194779-8beaceb93744?w=300&q=80', url: 'https://images.unsplash.com/photo-1505664194779-8beaceb93744?w=1080&q=80' },
      { title: 'Anayasa & Kanun', thumb: 'https://images.unsplash.com/photo-1453733197783-64a0888e5243?w=300&q=80', url: 'https://images.unsplash.com/photo-1453733197783-64a0888e5243?w=1080&q=80' }
    ],
    tech: [
      { title: 'Yapay Zeka & Kod', thumb: 'https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?w=300&q=80', url: 'https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?w=1080&q=80' },
      { title: 'Siber Güvenlik', thumb: 'https://images.unsplash.com/photo-1550751827-4bd374c3f58b?w=300&q=80', url: 'https://images.unsplash.com/photo-1550751827-4bd374c3f58b?w=1080&q=80' },
      { title: 'Dijital Ağlar', thumb: 'https://images.unsplash.com/photo-1518770660439-4636190af475?w=300&q=80', url: 'https://images.unsplash.com/photo-1518770660439-4636190af475?w=1080&q=80' }
    ],
    nature: [
      { title: 'Dağ & Gökyüzü', thumb: 'https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=300&q=80', url: 'https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=1080&q=80' },
      { title: 'Deniz Dalgası', thumb: 'https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=300&q=80', url: 'https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=1080&q=80' },
      { title: 'Orman Yolu', thumb: 'https://images.unsplash.com/photo-1448375240586-882707db888b?w=300&q=80', url: 'https://images.unsplash.com/photo-1448375240586-882707db888b?w=1080&q=80' }
    ],
    history: [
      { title: 'Antik Kitap & El Yazması', thumb: 'https://images.unsplash.com/photo-1461360370896-922624d12aa1?w=300&q=80', url: 'https://images.unsplash.com/photo-1461360370896-922624d12aa1?w=1080&q=80' },
      { title: 'Klasik Saat & Zaman', thumb: 'https://images.unsplash.com/photo-1509042239860-f550ce710b93?w=300&q=80', url: 'https://images.unsplash.com/photo-1509042239860-f550ce710b93?w=1080&q=80' },
      { title: 'Tarihi Arşiv', thumb: 'https://images.unsplash.com/photo-1481627834876-b7833e8f5570?w=300&q=80', url: 'https://images.unsplash.com/photo-1481627834876-b7833e8f5570?w=1080&q=80' }
    ],
    business: [
      { title: 'Finansal Grafik & Analiz', thumb: 'https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=300&q=80', url: 'https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=1080&q=80' },
      { title: 'Modern Ofis', thumb: 'https://images.unsplash.com/photo-1497366216548-37526070297c?w=300&q=80', url: 'https://images.unsplash.com/photo-1497366216548-37526070297c?w=1080&q=80' }
    ]
  };
  readonly currentCategoryImages = computed(() => this.stockImagesLibrary[this.selectedStockCategory()] || []);

  // Toplu Kesim & Trim Aracı Durumu
  readonly showCutAdjustModal = signal<boolean>(false);
  readonly showRestoreDropdown = signal<boolean>(false);
  readonly cutAdjustScope = signal<'all' | 'short' | 'long'>('short');
  readonly cutStartOffsetMs = signal<number>(80);
  readonly cutEndOffsetMs = signal<number>(-50);
  readonly cutAdjustLoading = signal<boolean>(false);

  readonly autoCuts = computed(() => {
    const edl = this.activeEdl();
    if (!edl || !edl.cuts) return [];
    return edl.cuts.filter(c => {
      const src = (c.source || 'auto').toLowerCase();
      const r = (c.reason || '').toLowerCase();
      return src === 'auto' || r.includes('silence') || r.includes('retake') || r.includes('jump');
    });
  });

  readonly shortCuts = computed(() => {
    return this.autoCuts().filter(c => (c.end - c.start) < 1.0);
  });

  readonly longCuts = computed(() => {
    return this.autoCuts().filter(c => (c.end - c.start) >= 1.0);
  });

  readonly timelineZoom = signal<number>(1);
  readonly audioTrackHeight = signal<number>(56);
  isResizingTrack = false;
  resizeStartY = 0;
  resizeStartHeight = 0;
  
  readonly splitMarkers = signal<number[]>([]);
  readonly selectedClipIds = signal<string[]>([]);
  readonly selectedHasCuts = computed(() => {
    const selIds = this.selectedClipIds();
    return this.clips().some(c => selIds.includes(c.id) && c.isCut);
  });
  readonly selectedHasKeep = computed(() => {
    const selIds = this.selectedClipIds();
    return this.clips().some(c => selIds.includes(c.id) && !c.isCut);
  });
  readonly selectedOverlayId = signal<string | null>(null);
  readonly selectedSubtitleId = signal<string | null>(null);
  readonly selectedSubtitleIndex = signal<number | null>(null);
  readonly selectedSubtitle = computed(() => {
    const idx = this.selectedSubtitleIndex();
    const segs = this.activeEdl()?.transcript?.segments;
    if (idx !== null && segs && idx >= 0 && idx < segs.length) {
      return segs[idx];
    }
    const id = this.selectedSubtitleId();
    if (!id) return null;
    return segs?.find((s: any) => this.getSubtitleId(s) === id) || null;
  });
  readonly editingSubtitleId = signal<string | null>(null);

  // Subtitle Inspector Data
  subtitleInspectorData: {
    index: number;
    text: string;
    start: number;
    end: number;
    duration: number;
  } = { index: -1, text: '', start: 0, end: 0, duration: 0 };

  // Subtitle Drag & Drop State
  isDraggingSubtitle = false;
  isResizingSubtitle = false;
  subtitleResizeEdge: 'left' | 'right' | null = null;
  dragSubtitleOriginalStart = 0;
  dragSubtitleOriginalEnd = 0;

  // Çok Kanallı (Multi-Track) Katman Mimarisi
  readonly customTrackCount = signal<number>(3);
  readonly overlayTrackNumbers = computed<number[]>(() => {
    const overlays = this.activeEdl()?.overlays || [];
    const maxTrackInOverlays = overlays.reduce((max, o) => Math.max(max, Number(o.trackId) || 1), 1);
    const totalTracks = Math.max(this.customTrackCount(), maxTrackInOverlays);
    
    const tracks: number[] = [];
    for (let i = totalTracks; i >= 1; i--) {
      tracks.push(i);
    }
    return tracks;
  });

  // Dinamik Zaman Cetveli İşaretleri
  readonly timelineRulerMarks = computed<{ time: number; label: string; percent: number; isMajor: boolean }[]>(() => {
    const dur = Math.max(1, (this.isAnyRippleActive() ? this.visibleDuration() : this.totalDuration()) || 60);
    const zoom = Math.max(1, this.timelineZoom() || 1);
    
    let step = 10;
    if (dur <= 30) step = 2;
    else if (dur <= 60) step = 5;
    else if (dur <= 180) step = 10;
    else if (dur <= 600) step = 20;
    else if (dur <= 1800) step = 30;
    else step = 60;
    
    if (zoom >= 4) step = Math.max(1, Math.round(step / 4));
    else if (zoom >= 2) step = Math.max(2, Math.round(step / 2));
    
    const marks: { time: number; label: string; percent: number; isMajor: boolean }[] = [];
    for (let t = 0; t <= dur; t += step) {
      const mins = Math.floor(t / 60);
      const secs = Math.floor(t % 60);
      const label = `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
      const percent = (t / dur) * 100;
      marks.push({ time: t, label, percent, isMajor: true });
    }
    return marks;
  });

  // Transkript Arama
  readonly transcriptSearchQuery = signal<string>('');
  readonly filteredTranscriptSegments = computed(() => {
    const segs = this.activeEdl()?.transcript?.segments || [];
    const q = this.transcriptSearchQuery().trim().toLowerCase();
    if (!q) return segs;
    return segs.filter(s => s.text.toLowerCase().includes(q));
  });

  // Context Menu State
  readonly contextMenu = signal<ContextMenuState | null>(null);

  // Inspector Data State
  inspectorData: any = {};
  
  // Drag & Drop State
  isDraggingOverlay = false;
  isResizingOverlay = false;
  resizeEdge: 'left' | 'right' | null = null;
  dragStartX = 0;
  dragStartY = 0;
  dragOverlayOriginalStart = 0;
  dragOverlayOriginalDuration = 0;
  dragOverlayOriginalTrack = 1;
  
  // Canvas Drag & Drop State
  isCanvasDragging = false;
  canvasDragOverlayId: string | null = null;
  canvasDragStartX = 0;
  canvasDragStartY = 0;
  canvasDragOriginalX = 0;
  canvasDragOriginalY = 0;

  // Canvas Resize State
  isCanvasResizing = false;
  canvasResizeOverlayId: string | null = null;
  canvasResizeStartX = 0;
  canvasResizeStartY = 0;
  canvasResizeOriginalScale = 1;
  canvasResizeOriginalFontSize = 48;
  
  readonly selectedOverlay = computed(() => {
    const id = this.selectedOverlayId();
    if (!id) return null;
    return this.activeEdl()?.overlays?.find(o => o.id === id) || null;
  });

  // Preview Logic
  readonly previewEdl = signal<EdlContent | null>(null);
  readonly previewMessageId = signal<string | null>(null);
  readonly activeEdl = computed(() => this.previewEdl() || this.edl());

  // Canlı Taslak (Ghost Layer)
  readonly ghostPreview = computed(() => {
    const msgs = this.chatMessages();
    const clarMsg = [...msgs].reverse().find(m => m.patchDurumu === 'clarification' && m.formFields);
    if (!clarMsg) return null;

    const data = clarMsg.formData || {};
    const text = data['content'] || clarMsg.formFields?.find(f => f.id === 'content')?.defaultValue || 'Önizleme Başlığı';
    const color = data['color'] || clarMsg.formFields?.find(f => f.id === 'color')?.defaultValue || '#FACC15';
    const font = data['font'] || clarMsg.formFields?.find(f => f.id === 'font')?.defaultValue || 'Montserrat';

    let posX = 50;
    let posY = 85;

    if (data['positionX'] !== undefined && data['positionY'] !== undefined) {
      posX = Number(data['positionX']);
      posY = Number(data['positionY']);
    } else {
      const pos = data['position'] || clarMsg.formFields?.find(f => f.id === 'position')?.defaultValue || 'bottom-center';
      const coords = this.getPresetCoords(String(pos));
      posX = coords.x;
      posY = coords.y;
    }

    return { text: String(text), color: String(color), font: String(font), posX, posY };
  });

  // O(1) Pre-Computed Clips hesaplaması (Zero-Lag Optimization)
  readonly clips = computed(() => {
    const total = Math.max(0.1, this.totalDuration());
    const edl = this.activeEdl();
    const cuts = edl?.cuts || [];
    const splits = [...this.splitMarkers(), total].sort((a,b) => a-b);
    const rAi = this.rippleAi();
    const rMan = this.rippleManual();
    const rRet = this.rippleRetake();
    const rippleActive = rAi || rMan || rRet;
    
    let allPoints = new Set<number>();
    allPoints.add(0);
    allPoints.add(total);
    for (const s of splits) allPoints.add(s);
    for (const c of cuts) {
      allPoints.add(c.start);
      allPoints.add(c.end);
    }
    
    const sortedPoints = Array.from(allPoints).sort((a,b) => a-b);
    const rawClips: any[] = [];
    let totalVisDur = 0;
    
    for (let i = 0; i < sortedPoints.length - 1; i++) {
      const start = sortedPoints[i];
      const end = sortedPoints[i+1];
      if (end - start < 0.05) continue;
      
      const mid = (start + end) / 2;
      const cut = cuts.find(c => mid >= c.start && mid <= c.end);
      const isCut = !!cut;
      const reason = (cut?.reason || '').toLowerCase();
      const isRetake = isCut && (reason.includes('retake') || reason.includes('tekrar'));
      const isManual = isCut && reason.includes('manuel');

      let isVisibleClip = true;
      if (isCut) {
        if (isManual) isVisibleClip = !rMan;
        else if (isRetake) isVisibleClip = !rRet;
        else isVisibleClip = !rAi;
      }

      const duration = end - start;
      if (isVisibleClip) {
        totalVisDur += duration;
      }

      rawClips.push({
        id: `clip_${i}_${start}`,
        start,
        end,
        duration,
        isCut,
        cutObj: cut,
        isVisibleClip,
        leftPercent: 0,
        widthPercent: 0
      });
    }

    const visDur = Math.max(0.1, totalVisDur);
    let accVis = 0;
    let keepIndex = 0;
    for (const c of rawClips) {
      if (!c.isCut) {
        c.keepIndex = keepIndex++;
      }
      if (!rippleActive) {
        c.leftPercent = (c.start / total) * 100;
        c.widthPercent = (c.duration / total) * 100;
      } else {
        c.leftPercent = (accVis / visDur) * 100;
        c.widthPercent = c.isVisibleClip ? (c.duration / visDur) * 100 : 0;
        if (c.isVisibleClip) {
          accVis += c.duration;
        }
      }
    }
    return rawClips;
  });

  // O(1) Pre-Computed Altyazı Segmentleri (Zero-Lag Optimization)
  readonly visibleSubtitleSegments = computed(() => {
    const segments = this.activeEdl()?.transcript?.segments || [];
    const total = Math.max(0.1, this.totalDuration());
    const rippleActive = this.isAnyRippleActive();
    const visDur = Math.max(0.1, this.visibleDuration());
    const visibleClips = this.clips().filter(c => c.isVisibleClip);

    const filtered = !rippleActive
      ? segments
      : segments.filter(seg => visibleClips.some(c => (Math.min(seg.end, c.end) - Math.max(seg.start, c.start)) > 0.03));

    return filtered.map(seg => {
      if (!rippleActive) {
        return {
          ...seg,
          leftPercent: (seg.start / total) * 100,
          widthPercent: Math.max(0.1, ((seg.end - seg.start) / total) * 100)
        };
      }
      const startVis = this.getVisTimeFromRawTime(seg.start);
      const endVis = this.getVisTimeFromRawTime(seg.end);
      return {
        ...seg,
        leftPercent: (startVis / visDur) * 100,
        widthPercent: Math.max(0.1, ((endVis - startVis) / visDur) * 100)
      };
    });
  });

  // V1 Klipleri Arasındaki Sahne Geçiş Noktaları ([⚡] Transition Boundaries)
  readonly clipTransitionBoundaries = computed(() => {
    const visibleKeepClips = this.clips().filter(c => c.isVisibleClip && !c.isCut);
    const transitions = this.transitions();
    const boundaries: Array<{
      id: string;
      boundaryTime: number;
      leftPercent: number;
      fromClipId: string;
      toClipId: string;
      existing?: EdlTransition;
    }> = [];

    for (let i = 0; i < visibleKeepClips.length - 1; i++) {
      const prev = visibleKeepClips[i];
      const next = visibleKeepClips[i + 1];
      const boundaryTime = next.start;
      const leftPercent = prev.leftPercent + prev.widthPercent;
      const existing = transitions.find(tr => Math.abs((tr.boundaryTime || 0) - boundaryTime) < 0.35);
      boundaries.push({
        id: `tr_bound_${i}_${boundaryTime.toFixed(2)}`,
        boundaryTime,
        leftPercent,
        fromClipId: prev.id,
        toClipId: next.id,
        existing
      });
    }
    return boundaries;
  });

  // Canlı Önizleme Monitörü için Aktif Geçiş Efekti & Smart Punch-In
  readonly activeTransitionEffect = computed<{ badge: string; overlayStyle: any; videoScale?: number; videoTranslateX?: number; videoOpacity?: number } | null>(() => {
    const t = this.currentTime();
    const transitions = this.transitions();
    if (!transitions || transitions.length === 0) return null;

    for (const tr of transitions) {
      const half = (tr.duration || 0.45) / 2;
      const bTime = tr.boundaryTime || 0;
      if (t >= bTime - half && t <= bTime + half) {
        const progress = (t - (bTime - half)) / Math.max(0.1, tr.duration || 0.45); // 0..1
        const intensity = 1 - Math.abs(progress - 0.5) * 2; // 0 -> 1 -> 0 peak at boundary
        const trMeta = this.studio.transitionLibrary.find(x => x.type === tr.type);
        const badge = trMeta?.name || tr.type;

        if (tr.type === 'fadeblack') {
          return { badge, overlayStyle: { backgroundColor: `rgba(0,0,0,${(intensity * 0.92).toFixed(2)})` } };
        }
        if (tr.type === 'fadewhite') {
          return { badge, overlayStyle: { backgroundColor: `rgba(255,255,255,${(intensity * 0.92).toFixed(2)})` } };
        }
        if (tr.type === 'slideleft' || tr.type === 'wipeleft') {
          return { badge, overlayStyle: { backgroundColor: `rgba(6,182,212,${(intensity * 0.15).toFixed(2)})` }, videoTranslateX: (0.5 - progress) * 14 };
        }
        if (tr.type === 'slideright' || tr.type === 'wiperight') {
          return { badge, overlayStyle: { backgroundColor: `rgba(6,182,212,${(intensity * 0.15).toFixed(2)})` }, videoTranslateX: (progress - 0.5) * 14 };
        }
        if (tr.type === 'zoomin' || tr.type === 'circleopen') {
          return { badge, overlayStyle: { boxShadow: `inset 0 0 ${Math.round(intensity * 60)}px rgba(6,182,212,0.45)` }, videoScale: 1 + intensity * 0.18 };
        }
        return { badge, overlayStyle: { backgroundColor: `rgba(15,23,42,${(intensity * 0.5).toFixed(2)})` }, videoOpacity: 1 - intensity * 0.45 };
      }
    }
    return null;
  });

  readonly videoPreviewTransform = computed<string>(() => {
    const tr = this.activeTransitionEffect();
    let scale = 1.0;
    let tx = 0;

    // Smart Punch-In (1.10x alternatif sahne yakınlaştırması)
    if (this.smartPunchIn()) {
      const t = this.currentTime();
      const curClip = this.clips().find(c => !c.isCut && t >= c.start && t < c.end);
      if (curClip && curClip.keepIndex % 2 === 1) {
        scale = 1.10;
      }
    }

    if (tr?.videoScale) scale *= tr.videoScale;
    if (tr?.videoTranslateX) tx = tr.videoTranslateX;

    if (scale === 1.0 && tx === 0) return 'none';
    return `scale(${scale.toFixed(3)}) translateX(${tx.toFixed(1)}%)`;
  });

  readonly videoPreviewOpacity = computed<number>(() => {
    const tr = this.activeTransitionEffect();
    return tr?.videoOpacity ?? 1.0;
  });

  isAnyRippleActive(): boolean {
    return this.rippleAi() || this.rippleManual() || this.rippleRetake();
  }

  getClipLeft(clip: any): number {
    return clip.leftPercent ?? 0;
  }

  getClipWidth(clip: any): number {
    return clip.widthPercent ?? 0;
  }

  getSubtitleLeft(seg: any): number {
    return seg.leftPercent ?? 0;
  }

  getSubtitleWidth(seg: any): number {
    return seg.widthPercent ?? 0;
  }

  getSubtitleId(seg: any): string {
    return `sub_${seg.start}_${seg.end}`;
  }

  startEditSubtitle(seg: any): void {
    this.editingSubtitleId.set(this.getSubtitleId(seg));
  }

  cancelSubtitleEdit(): void {
    this.editingSubtitleId.set(null);
  }

  saveSubtitleEdit(seg: any, newText: string): void {
    if (!newText || newText.trim() === '') {
       this.cancelSubtitleEdit();
       return;
    }
    const edl = this.activeEdl();
    if (!edl || !edl.transcript || !edl.transcript.segments) {
       this.cancelSubtitleEdit();
       return;
    }
    const segmentIndex = edl.transcript.segments.findIndex((s: any) => this.getSubtitleId(s) === this.getSubtitleId(seg));
    if (segmentIndex !== -1) {
       console.log(`[SUBTITLE:EDIT] Altyazı güncellendi: "${seg.text}" -> "${newText}"`);
       edl.transcript.segments[segmentIndex].text = newText;
       this.edlService.patchEdl(this.projectId, { transcript: edl.transcript } as any).subscribe(() => {
          this.loadEdl();
          this.cancelSubtitleEdit();
       });
    } else {
       this.cancelSubtitleEdit();
    }
  }

  selectSubtitle(seg: any, index?: number): void {
    const segs = this.activeEdl()?.transcript?.segments || [];
    let idx = index;
    if (idx === undefined || idx < 0) {
      idx = segs.findIndex((s: any) => Math.abs(s.start - seg.start) < 0.05 && Math.abs(s.end - seg.end) < 0.05);
    }
    if (idx === -1) {
      idx = segs.indexOf(seg);
    }
    if (idx !== -1) {
      this.selectedSubtitleIndex.set(idx);
      this.selectedSubtitleId.set(this.getSubtitleId(segs[idx]));
      this.selectedOverlayId.set(null);
      this.selectedClipIds.set([]);
      
      const s = segs[idx];
      this.subtitleInspectorData = {
        index: idx,
        text: s.text,
        start: Number(s.start.toFixed(2)),
        end: Number(s.end.toFixed(2)),
        duration: Number((s.end - s.start).toFixed(2))
      };
      
      const v = this.videoRef?.nativeElement;
      if (v && !v.seeking) {
        v.currentTime = s.start;
      }
      this.currentTime.set(s.start);
      console.log(`%c[SUBTITLE:SELECTED] Segment #${idx}: "${s.text}" [${s.start}s - ${s.end}s]`, 'color: #f59e0b; font-weight: bold;');
    }
  }

  clearSubtitleSelection(): void {
    this.selectedSubtitleIndex.set(null);
    this.selectedSubtitleId.set(null);
    this.subtitleInspectorData = { index: -1, text: '', start: 0, end: 0, duration: 0 };
  }

  isSelectedSubtitle(seg: any): boolean {
    const id = this.selectedSubtitleId();
    if (!id) return false;
    return this.getSubtitleId(seg) === id;
  }

  onSubtitleTextChange(): void {
    const idx = this.subtitleInspectorData.index;
    const segs = this.activeEdl()?.transcript?.segments;
    if (idx >= 0 && segs && segs[idx]) {
      segs[idx].text = this.subtitleInspectorData.text;
    }
  }

  onSubtitleStartChange(): void {
    const s = Number(this.subtitleInspectorData.start);
    const d = Number(this.subtitleInspectorData.duration);
    if (!isNaN(s) && !isNaN(d)) {
      this.subtitleInspectorData.end = Number((s + d).toFixed(2));
      const idx = this.subtitleInspectorData.index;
      const segs = this.activeEdl()?.transcript?.segments;
      if (idx >= 0 && segs && segs[idx]) {
        segs[idx].start = s;
        segs[idx].end = this.subtitleInspectorData.end;
      }
    }
  }

  onSubtitleEndChange(): void {
    const s = Number(this.subtitleInspectorData.start);
    const e = Number(this.subtitleInspectorData.end);
    if (!isNaN(s) && !isNaN(e) && e > s) {
      this.subtitleInspectorData.duration = Number((e - s).toFixed(2));
      const idx = this.subtitleInspectorData.index;
      const segs = this.activeEdl()?.transcript?.segments;
      if (idx >= 0 && segs && segs[idx]) {
        segs[idx].end = e;
      }
    }
  }

  onSubtitleDurationChange(): void {
    const s = Number(this.subtitleInspectorData.start);
    const d = Number(this.subtitleInspectorData.duration);
    if (!isNaN(s) && !isNaN(d) && d > 0) {
      this.subtitleInspectorData.end = Number((s + d).toFixed(2));
      const idx = this.subtitleInspectorData.index;
      const segs = this.activeEdl()?.transcript?.segments;
      if (idx >= 0 && segs && segs[idx]) {
        segs[idx].end = this.subtitleInspectorData.end;
      }
    }
  }

  applySubtitlePreset(preset: 'tiktok_yellow' | 'cinematic_shadow' | 'opaque_banner' | 'neon_glow'): void {
    this.subtitlePreset.set(preset);
    if (preset === 'tiktok_yellow') {
      this.subtitleFont.set('Montserrat, Inter, sans-serif');
      this.subtitleFontSize.set(48);
      this.subtitleColor.set('#FFFFFF');
      this.subtitleHighlightColor.set('#FFD700');
      this.subtitleStrokeColor.set('#000000');
      this.subtitleStrokeWidth.set(3);
      this.subtitleShadowColor.set('rgba(0,0,0,0.8)');
      this.subtitleShadowBlur.set(2);
      this.subtitleBgColor.set('rgba(0,0,0,0.65)');
      this.subtitleBgPadding.set(8);
      this.subtitleBorderRadius.set(8);
      this.subtitleAllCaps.set(false);
      this.subtitleLetterSpacing.set(0);
      this.subtitlePositionY.set(85);
    } else if (preset === 'cinematic_shadow') {
      this.subtitleFont.set('Cinzel, serif');
      this.subtitleFontSize.set(38);
      this.subtitleColor.set('#F0F0F0');
      this.subtitleHighlightColor.set('#FFCC00');
      this.subtitleStrokeColor.set('#000000');
      this.subtitleStrokeWidth.set(1);
      this.subtitleShadowColor.set('rgba(0,0,0,0.95)');
      this.subtitleShadowBlur.set(5);
      this.subtitleBgColor.set('transparent');
      this.subtitleBgPadding.set(4);
      this.subtitleBorderRadius.set(4);
      this.subtitleAllCaps.set(false);
      this.subtitleLetterSpacing.set(2);
      this.subtitlePositionY.set(88);
    } else if (preset === 'opaque_banner') {
      this.subtitleFont.set('Inter, sans-serif');
      this.subtitleFontSize.set(40);
      this.subtitleColor.set('#FFFFFF');
      this.subtitleHighlightColor.set('#38BDF8');
      this.subtitleStrokeColor.set('#000000');
      this.subtitleStrokeWidth.set(0);
      this.subtitleShadowColor.set('rgba(0,0,0,0.5)');
      this.subtitleShadowBlur.set(1);
      this.subtitleBgColor.set('rgba(0,0,0,0.85)');
      this.subtitleBgPadding.set(12);
      this.subtitleBorderRadius.set(12);
      this.subtitleAllCaps.set(false);
      this.subtitleLetterSpacing.set(0);
      this.subtitlePositionY.set(82);
    } else if (preset === 'neon_glow') {
      this.subtitleFont.set('Bebas Neue, sans-serif');
      this.subtitleFontSize.set(52);
      this.subtitleColor.set('#FFFFFF');
      this.subtitleHighlightColor.set('#00FFFF');
      this.subtitleStrokeColor.set('#FF00FF');
      this.subtitleStrokeWidth.set(2);
      this.subtitleShadowColor.set('rgba(255,0,255,0.7)');
      this.subtitleShadowBlur.set(8);
      this.subtitleBgColor.set('rgba(10,10,25,0.6)');
      this.subtitleBgPadding.set(8);
      this.subtitleBorderRadius.set(6);
      this.subtitleAllCaps.set(true);
      this.subtitleLetterSpacing.set(1);
      this.subtitlePositionY.set(85);
    }
    this.persistSubtitleStyle();
  }

  persistSubtitleStyle(): void {
    const styleCfg: SubtitleStyleConfig = {
      preset: this.subtitlePreset(),
      fontFamily: this.subtitleFont(),
      fontSize: this.subtitleFontSize(),
      textColor: this.subtitleColor(),
      highlightColor: this.subtitleHighlightColor(),
      strokeColor: this.subtitleStrokeColor(),
      strokeWidth: this.subtitleStrokeWidth(),
      shadowColor: this.subtitleShadowColor(),
      shadowDistance: 3.0,
      shadowBlur: this.subtitleShadowBlur(),
      backgroundColor: this.subtitleBgColor(),
      backgroundPadding: this.subtitleBgPadding(),
      borderRadius: this.subtitleBorderRadius(),
      allCaps: this.subtitleAllCaps(),
      letterSpacing: this.subtitleLetterSpacing(),
      verticalPosition: this.subtitlePositionY()
    };

    const edl = this.edl();
    if (edl) {
      if (!edl.settings) edl.settings = {};
      edl.settings.subtitleStyle = styleCfg;
      this.edl.set({ ...edl });
    }

    this.edlService.patchEdl(this.projectId, {
      settings: {
        subtitleStyle: styleCfg,
        subtitlesEnabled: this.showSubtitles()
      }
    }).subscribe({
      next: () => console.log('[SUBTITLE:STYLE] Altyazı stili kaydedildi:', styleCfg),
      error: (err) => console.error('[SUBTITLE:STYLE] Altyazı stili kaydedilemedi:', err)
    });
  }

  initSubtitleStyleFromSettings(cfg?: SubtitleStyleConfig): void {
    if (!cfg) return;
    if (cfg.preset) this.subtitlePreset.set(cfg.preset);
    if (cfg.fontFamily) this.subtitleFont.set(cfg.fontFamily);
    if (cfg.fontSize) this.subtitleFontSize.set(cfg.fontSize);
    if (cfg.textColor) this.subtitleColor.set(cfg.textColor);
    if (cfg.highlightColor) this.subtitleHighlightColor.set(cfg.highlightColor);
    if (cfg.strokeColor) this.subtitleStrokeColor.set(cfg.strokeColor);
    if (cfg.strokeWidth !== undefined) this.subtitleStrokeWidth.set(cfg.strokeWidth);
    if (cfg.shadowColor) this.subtitleShadowColor.set(cfg.shadowColor);
    if (cfg.shadowBlur !== undefined) this.subtitleShadowBlur.set(cfg.shadowBlur);
    if (cfg.backgroundColor) this.subtitleBgColor.set(cfg.backgroundColor);
    if (cfg.backgroundPadding !== undefined) this.subtitleBgPadding.set(cfg.backgroundPadding);
    if (cfg.borderRadius !== undefined) this.subtitleBorderRadius.set(cfg.borderRadius);
    if (cfg.allCaps !== undefined) this.subtitleAllCaps.set(cfg.allCaps);
    if (cfg.letterSpacing !== undefined) this.subtitleLetterSpacing.set(cfg.letterSpacing);
    if (cfg.verticalPosition !== undefined) this.subtitlePositionY.set(cfg.verticalPosition);
  }

  // --- ARKA PLAN MÜZİĞİ & AUTO-DUCKING (B5) ---
  setBgmPreset(url: string, title: string): void {
    this.bgmUrl.set(url);
    this.bgmTitle.set(title);
    this.isBgmSelectorOpen.set(false);
    this.persistBgmSettings();
  }

  removeBgm(): void {
    this.bgmUrl.set('');
    this.bgmTitle.set('Arka Plan Müziği Yok');
    this.persistBgmSettings();
  }

  toggleAutoDucking(): void {
    this.bgmAutoDucking.update(v => !v);
    this.persistBgmSettings();
  }

  persistBgmSettings(): void {
    const bgmCfg: BackgroundMusicConfig = {
      url: this.bgmUrl(),
      title: this.bgmTitle(),
      volume: this.bgmVolume(),
      autoDucking: this.bgmAutoDucking(),
      duckingAmount: this.bgmDuckingAmount(),
      fadeIn: 1.0,
      fadeOut: 2.0,
      loop: true
    };
    const edl = this.edl();
    if (edl) {
      if (!edl.settings) edl.settings = {};
      edl.settings.backgroundMusic = bgmCfg;
      this.edl.set({ ...edl });
    }
    this.edlService.patchEdl(this.projectId, {
      settings: { backgroundMusic: bgmCfg }
    }).subscribe({
      next: () => console.log('[BGM:PERSIST] BGM ayarları kaydedildi:', bgmCfg),
      error: (err) => console.error('[BGM:PERSIST] BGM kaydedilemedi:', err)
    });
  }

  initBgmFromSettings(cfg?: BackgroundMusicConfig): void {
    if (!cfg) return;
    if (cfg.url) this.bgmUrl.set(cfg.url);
    if (cfg.title) this.bgmTitle.set(cfg.title);
    if (cfg.volume !== undefined) this.bgmVolume.set(cfg.volume);
    if (cfg.autoDucking !== undefined) this.bgmAutoDucking.set(cfg.autoDucking);
    if (cfg.duckingAmount !== undefined) this.bgmDuckingAmount.set(cfg.duckingAmount);
  }

  saveSubtitleInspector(): void {
    const idx = this.subtitleInspectorData.index;
    const edl = this.activeEdl();
    if (idx < 0 || !edl?.transcript?.segments || idx >= edl.transcript.segments.length) return;

    const seg = edl.transcript.segments[idx];
    seg.text = this.subtitleInspectorData.text.trim();
    seg.start = Number(this.subtitleInspectorData.start);
    seg.end = Number(this.subtitleInspectorData.end);

    this.edlService.patchEdl(this.projectId, { transcript: edl.transcript } as any).subscribe({
      next: () => {
        console.log('[SUBTITLE] Altyazı kaydedildi:', seg);
        this.loadEdl();
      },
      error: (err) => console.error('[SUBTITLE] Altyazı kaydetme hatası:', err)
    });
  }

  convertSubtitleToOverlay(): void {
    const idx = this.subtitleInspectorData.index;
    const edl = this.activeEdl();
    if (idx < 0 || !edl?.transcript?.segments || idx >= edl.transcript.segments.length) return;

    const seg = edl.transcript.segments[idx];
    const newOverlayId = `ov_sub_${Date.now()}`;
    const start = Number(this.subtitleInspectorData.start);
    const end = Number(this.subtitleInspectorData.end);
    const duration = Math.max(0.5, end - start);

    const newOverlay: OverlayItem = {
      id: newOverlayId,
      type: 'text',
      content: this.subtitleInspectorData.text || seg.text,
      timestamp: start,
      duration: duration,
      color: this.subtitleColor() || '#FFFFFF',
      fontSize: 42,
      font: this.subtitleFont() || 'Montserrat',
      positionX: 50,
      positionY: this.subtitlePositionY() || 85,
      animation: 'pop-up',
      exitAnimation: 'fade',
      trackId: 1
    };

    edl.transcript.segments.splice(idx, 1);
    const overlays = [...(edl.overlays || []), newOverlay];

    this.edlService.patchEdl(this.projectId, {
      transcript: edl.transcript,
      overlays: overlays as any
    } as any).subscribe({
      next: () => {
        this.clearSubtitleSelection();
        this.loadEdl();
        setTimeout(() => {
          this.selectOverlay(newOverlayId);
        }, 300);
      },
      error: (err) => console.error('[SUBTITLE] Katmana dönüştürme hatası:', err)
    });
  }

  deleteSubtitleSegment(): void {
    const idx = this.subtitleInspectorData.index;
    const edl = this.activeEdl();
    if (idx < 0 || !edl?.transcript?.segments || idx >= edl.transcript.segments.length) return;

    if (confirm('Bu altyazı parçasını silmek istediğinize emin misiniz?')) {
      edl.transcript.segments.splice(idx, 1);
      this.edlService.patchEdl(this.projectId, { transcript: edl.transcript } as any).subscribe({
        next: () => {
          this.clearSubtitleSelection();
          this.loadEdl();
        },
        error: (err) => console.error('[SUBTITLE] Altyazı silme hatası:', err)
      });
    }
  }

  onSubtitleDragStart(event: MouseEvent, seg: any): void {
     if (event.button !== 0) return;
     event.stopPropagation();
     this.selectSubtitle(seg);
     this.isDraggingSubtitle = true;
     this.dragStartX = event.clientX;
     this.dragStartY = event.clientY;
     this.dragSubtitleOriginalStart = seg.start;
     this.dragSubtitleOriginalEnd = seg.end;
  }

  onSubtitleResizeStart(event: MouseEvent, seg: any, edge: 'left' | 'right'): void {
     if (event.button !== 0) return;
     event.stopPropagation();
     this.selectSubtitle(seg);
     this.isResizingSubtitle = true;
     this.subtitleResizeEdge = edge;
     this.dragStartX = event.clientX;
     this.dragSubtitleOriginalStart = seg.start;
     this.dragSubtitleOriginalEnd = seg.end;
  }

  getVisibleSubtitleSegments(): any[] {
    const segments = this.activeEdl()?.transcript?.segments || [];
    if (!this.isAnyRippleActive()) return segments;
    
    const visibleClips = this.clips().filter(c => this.isVisible(c));
    const result = segments.filter(seg => {
      // Bir altyazının gösterilmesi için, görünür (kesilmemiş) kliplerden en az biriyle anlamlı bir süre (>30ms) kesişmesi gerekir
      return visibleClips.some(c => (Math.min(seg.end, c.end) - Math.max(seg.start, c.start)) > 0.03);
    });
    // Sadece dizi değiştiyse konsola basmak için ufak bir hack olabilir ama şimdilik sadece timeline render'ı logla
    if (result.length > 0 && Math.random() < 0.05) { // Log spami önlemek için %5 ihtimalle bas
       console.log(`[SUBTITLE:TRACK_RENDER] ${result.length} adet altyazı segmenti render ediliyor.`);
    }
    return result;
  }

  isRetakeClip(clip: any): boolean {
    if (!clip || !clip.isCut || !clip.cutObj) return false;
    const r = (clip.cutObj.reason || '').toLowerCase();
    return r.includes('retake') || r.includes('tekrar');
  }

  isManualClip(clip: any): boolean {
    if (!clip || !clip.isCut || !clip.cutObj) return false;
    const r = (clip.cutObj.reason || '').toLowerCase();
    return r.includes('manuel');
  }

  getClipTooltip(clip: any): string {
    const startStr = clip.start.toFixed(1);
    const endStr = clip.end.toFixed(1);
    if (!clip.isCut) {
      return `Klip (${startStr}s - ${endStr}s) - Kesmek için çift tıkla / Sağ tık`;
    }
    if (this.isRetakeClip(clip)) {
      const desc = clip.cutObj?.command || clip.cutObj?.reason || 'Hatalı Tekrar';
      return `🔁 Hatalı Tekrar (Retake) [${startStr}s - ${endStr}s]: ${desc} - İptal için çift tıkla`;
    }
    if (this.isManualClip(clip)) {
      return `🖐 Manuel Kesim [${startStr}s - ${endStr}s] - İptal için çift tıkla`;
    }
    return `🤖 AI Jump-Cut [${startStr}s - ${endStr}s]: ${clip.cutObj?.reason || 'Sessizlik'} - İptal için çift tıkla`;
  }

  isVisible(clip: any): boolean {
    if (!clip.isCut) return true;
    if (this.isManualClip(clip)) {
       return !this.rippleManual();
    }
    if (this.isRetakeClip(clip)) {
       return !this.rippleRetake();
    }
    return !this.rippleAi();
  }

  deleteRetakeCuts(): void {
    const edl = this.activeEdl();
    if (!edl || !edl.cuts) return;

    const retakeCuts = edl.cuts.filter(c => {
      const r = (c.reason || '').toLowerCase();
      return r.includes('retake') || r.includes('tekrar');
    });

    if (retakeCuts.length === 0) return;

    if (confirm(`Tespit edilen ${retakeCuts.length} adet hatalı tekrar (Retake) kesimi iptal edilecek ve bu sahneler geri yüklenecektir. Onaylıyor musunuz?`)) {
      const patchPayload = retakeCuts.map(c => ({ id: c.id, start: 0, end: 0, action: 'remove' }));
      this.edlService.patchEdl(this.projectId, { cuts: patchPayload as any }).subscribe({
        next: () => this.loadEdl(),
        error: (err) => console.error('Retake kesimleri kaldırılamadı:', err)
      });
    }
  }

  openCutAdjustModal(): void {
    this.showCutAdjustModal.set(true);
    this.showRestoreDropdown.set(false);
  }

  resetCutAdjustOffsets(): void {
    this.cutStartOffsetMs.set(0);
    this.cutEndOffsetMs.set(0);
  }

  onCutStartInput(event: Event): void {
    const val = (event.target as HTMLInputElement).valueAsNumber;
    this.cutStartOffsetMs.set(isNaN(val) ? 0 : Math.round(val));
  }

  onCutEndInput(event: Event): void {
    const val = (event.target as HTMLInputElement).valueAsNumber;
    this.cutEndOffsetMs.set(isNaN(val) ? 0 : Math.round(val));
  }

  getTargetCutsCount(): number {
    const scope = this.cutAdjustScope();
    if (scope === 'short') return this.shortCuts().length;
    if (scope === 'long') return this.longCuts().length;
    return this.autoCuts().length;
  }

  applyBatchCutAdjustment(): void {
    const edl = this.activeEdl();
    if (!edl || !edl.cuts) return;

    const scope = this.cutAdjustScope();
    let targetCuts = this.autoCuts();
    if (scope === 'short') {
      targetCuts = this.shortCuts();
    } else if (scope === 'long') {
      targetCuts = this.longCuts();
    }

    if (targetCuts.length === 0) {
      alert('Seçilen kapsamda kesim bulunamadı.');
      return;
    }

    const startShiftSec = this.cutStartOffsetMs() / 1000.0;
    const endShiftSec = this.cutEndOffsetMs() / 1000.0;
    const videoDuration = this.totalDuration() || 999999;

    this.cutAdjustLoading.set(true);

    const patchPayload: Array<{ id: string; start: number; end: number; action?: string }> = [];

    for (const c of targetCuts) {
      const newStart = Math.max(0, Math.round((c.start + startShiftSec) * 1000) / 1000);
      const newEnd = Math.min(videoDuration, Math.round((c.end + endShiftSec) * 1000) / 1000);

      // Eğer yeni kesim süresi 60ms'nin altına düşerse veya başlangıç bitişi geçerse kesimi kaldır
      if (newEnd - newStart < 0.06) {
        patchPayload.push({ id: c.id, start: 0, end: 0, action: 'remove' });
      } else {
        patchPayload.push({ id: c.id, start: newStart, end: newEnd });
      }
    }

    this.edlService.patchEdl(this.projectId, { cuts: patchPayload as any }).subscribe({
      next: () => {
        this.cutAdjustLoading.set(false);
        this.showCutAdjustModal.set(false);
        this.loadEdl();
      },
      error: (err) => {
        console.error('Toplu kesim ayarlama hatası:', err);
        this.cutAdjustLoading.set(false);
        alert('Kesimler güncellenirken bir hata oluştu.');
      }
    });
  }

  cyclePlaybackSpeed(): void {
    const speeds = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0];
    const current = this.playbackSpeed();
    const idx = speeds.indexOf(current);
    const next = idx === -1 || idx === speeds.length - 1 ? speeds[0] : speeds[idx + 1];
    this.setPlaybackSpeed(next);
  }

  setPlaybackSpeed(speed: number): void {
    this.playbackSpeed.set(speed);
    const v = this.videoRef?.nativeElement;
    if (v) {
      v.playbackRate = speed;
    }
  }

  resetColorGrading(): void {
    this.videoBrightness.set(100);
    this.videoContrast.set(100);
    this.videoSaturation.set(100);
    this.videoTemperature.set(0);
  }

  applyColorPreset(preset: 'default' | 'vibrant' | 'cinematic' | 'cool' | 'bw'): void {
    switch (preset) {
      case 'default':
        this.resetColorGrading();
        break;
      case 'vibrant':
        this.videoBrightness.set(105);
        this.videoContrast.set(115);
        this.videoSaturation.set(130);
        this.videoTemperature.set(0);
        break;
      case 'cinematic':
        this.videoBrightness.set(95);
        this.videoContrast.set(115);
        this.videoSaturation.set(90);
        this.videoTemperature.set(8);
        break;
      case 'cool':
        this.videoBrightness.set(100);
        this.videoContrast.set(105);
        this.videoSaturation.set(90);
        this.videoTemperature.set(-12);
        break;
      case 'bw':
        this.videoBrightness.set(100);
        this.videoContrast.set(120);
        this.videoSaturation.set(0);
        this.videoTemperature.set(0);
        break;
    }
  }

  saveColorGrading(): void {
    const cg: ColorGradingConfig = {
      brightness: this.videoBrightness(),
      contrast: this.videoContrast(),
      saturation: this.videoSaturation(),
      temperature: this.videoTemperature()
    };
    this.edlService.patchEdl(this.projectId, {
      settings: {
        colorGrading: cg
      }
    }).subscribe({
      next: () => {
        this.showColorModal.set(false);
      },
      error: (err) => {
        console.error('Renk ayarları kaydedilemedi:', err);
        this.showColorModal.set(false);
      }
    });
  }

  restoreCutsByScope(scope: 'short' | 'long' | 'all'): void {
    const edl = this.activeEdl();
    if (!edl || !edl.cuts) return;

    let targetCuts = this.autoCuts();
    let scopeDesc = 'tüm otomatik';
    if (scope === 'short') {
      targetCuts = this.shortCuts();
      scopeDesc = '1 saniyeden kısa';
    } else if (scope === 'long') {
      targetCuts = this.longCuts();
      scopeDesc = '1 saniyeden uzun';
    }

    if (targetCuts.length === 0) {
      alert(`Seçilen kategoride (${scopeDesc}) kesim bulunamadı.`);
      return;
    }

    if (confirm(`Tespit edilen ${targetCuts.length} adet ${scopeDesc} kesim iptal edilecek ve bu sahneler videoya geri eklenecektir. Onaylıyor musunuz?`)) {
      const patchPayload = targetCuts.map(c => ({ id: c.id, start: 0, end: 0, action: 'remove' }));
      this.edlService.patchEdl(this.projectId, { cuts: patchPayload as any }).subscribe({
        next: () => this.loadEdl(),
        error: (err) => console.error('Kesimler geri alınamadı:', err)
      });
    }
  }

  readonly visibleDuration = computed(() => {
     const allClips = this.clips(); 
     let totalVisible = 0;
     for (const c of allClips) {
         if (this.isVisible(c)) {
             totalVisible += c.duration;
         }
     }
     return Math.max(0.1, totalVisible);
  });

  // Chat
  readonly chatMessages = signal<ChatMessageDto[]>([]);
  readonly chatLoading = signal<boolean>(false);
  userPrompt = '';

  private sub = new Subscription();

  ngOnInit(): void {
    this.projectId = this.route.snapshot.paramMap.get('id') || '';
    if (this.projectId) {
      this.loadProject();
      this.loadVideo();
      this.loadEdl();
      this.loadChatHistory();
      this.loadAssets();
      this.signalr.joinProjectGroup(this.projectId);
    }
  }

  ngOnDestroy(): void {
    if (this.projectId) {
      this.signalr.leaveProjectGroup(this.projectId);
    }
    this.sub.unsubscribe();
  }

  loadProject(): void {
    this.projectService.getById(this.projectId).subscribe({
      next: (p) => this.project.set(p),
      error: (err) => console.error('Proje yüklenemedi:', err)
    });
  }

  loadVideo(): void {
    this.videoService.getVideo(this.projectId).subscribe({
      next: (v) => {
        let streamUrl = '';
        if (v.streamUrl) {
          streamUrl = v.streamUrl;
        } else if (v.id) {
          const apiKey = environment.apiKey || 'SUPER_SECRET_OTOEDIT_KEY_123!';
          streamUrl = `${environment.apiUrl}/videos/${v.id}/stream?apiKey=${apiKey}`;
        }
        
        if (streamUrl) {
          this.videoUrl.set(streamUrl);
        }
        
        if (v.sure) {
          const parts = v.sure.split(':');
          if (parts.length >= 3) {
            const h = parseInt(parts[0], 10);
            const m = parseInt(parts[1], 10);
            const s = parseFloat(parts[2]);
            this.totalDuration.set((h * 3600) + (m * 60) + s);
          }
        }
      },
      error: () => {
        console.error('Video yüklenemedi.');
      }
    });
  }

  loadEdl(): void {
    this.edlService.getEdl(this.projectId).subscribe({
      next: (res) => {
        if (res.edl.overlays && res.edl.overlays.length > 0) {
          const { overlays, changed } = this.autoAssignOverlayTracks(res.edl.overlays);
          res.edl.overlays = overlays;
          if (changed) {
            this.edlService.patchEdl(this.projectId, {
              overlays: overlays.map(o => ({ id: o.id, trackId: o.trackId, action: 'update' } as any))
            }).subscribe({
              error: (err) => console.warn('Katman ayrıştırma kaydedilemedi:', err)
            });
          }
        }
        // Otonom Video Yönetmeni (Faz 6): Eğer henüz proaktif AI önerisi yoksa ilk yüklemede akıllı öneriler üret
        if (!res.edl.suggestions || res.edl.suggestions.length === 0) {
          res.edl.suggestions = this.studio.generateProactiveSuggestions(res.edl);
        }
        this.edl.set(res.edl);
        if (res.edl.settings?.subtitlesEnabled !== undefined) {
          this.showSubtitles.set(res.edl.settings.subtitlesEnabled);
        }
        if (res.edl.settings?.normalizeAudio !== undefined) {
          this.normalizeAudio.set(Boolean(res.edl.settings.normalizeAudio));
        }
        if (res.edl.settings?.smartPunchIn !== undefined) {
          this.smartPunchIn.set(Boolean(res.edl.settings.smartPunchIn));
        }
        if (res.edl.settings?.subtitleStyle) {
          this.initSubtitleStyleFromSettings(res.edl.settings.subtitleStyle);
        }
        if (res.edl.settings?.backgroundMusic) {
          this.initBgmFromSettings(res.edl.settings.backgroundMusic);
        }
        if (res.edl.settings?.colorGrading) {
          const cg = res.edl.settings.colorGrading;
          if (cg.brightness !== undefined) this.videoBrightness.set(cg.brightness);
          if (cg.contrast !== undefined) this.videoContrast.set(cg.contrast);
          if (cg.saturation !== undefined) this.videoSaturation.set(cg.saturation);
          if (cg.temperature !== undefined) this.videoTemperature.set(cg.temperature);
        }
        if (res.edl.duration && res.edl.duration > 5) {
          this.totalDuration.set(res.edl.duration);
        }
        const selId = this.selectedOverlayId();
        if (selId) {
          const ov = res.edl.overlays?.find(o => o.id === selId);
          if (ov) {
            this.inspectorData = { ...this.inspectorData, ...ov };
          }
        }
        // EDL içerisinden gelen gerçek peaks varsa öncelikli olarak yükle
        if (res.edl.audioPeaks && res.edl.audioPeaks.length > 0) {
          this.audioPeaks.set(res.edl.audioPeaks);
        }
        // Eğer eski düşük çözünürlüklü (örn. 1000 noktalı) bir projeyse arka planda otomatik olarak yüksek çözünürlüğe yükselt
        const dur = Math.max(10, res.edl.duration || this.totalDuration() || 60);
        const minHighResPoints = Math.max(2000, Math.round(dur * 20));
        if (!res.edl.audioPeaks || res.edl.audioPeaks.length < minHighResPoints) {
          this.ensureHighResWaveform();
        }
      },
      error: (err) => console.error('EDL yüklenemedi:', err)
    });
  }

  // --- YÜKSEK ÇÖZÜNÜRLÜKLÜ (ZERO-DRIFT dBFS) GERÇEK SES DALGASI YÜKSELTİCİ ---
  private isUpgradingWaveform = false;

  ensureHighResWaveform(): void {
    if (!this.projectId || this.isUpgradingWaveform) return;
    this.isUpgradingWaveform = true;
    this.isWaveformLoading.set(true);
    console.log('[WAVEFORM:UPGRADE] Eski/Düşük çözünürlüklü dalga formu tespit edildi, yüksek çözünürlüklü (Zero-Drift dBFS) ses verisi talep ediliyor...');

    this.edlService.getHighResWaveform(this.projectId).subscribe({
      next: (peaks) => {
        if (peaks && peaks.length > (this.audioPeaks()?.length || 0)) {
          console.log(`[WAVEFORM:UPGRADE_SUCCESS] Yüksek çözünürlüklü dalga formu yüklendi: ${peaks.length} nokta.`);
          this.audioPeaks.set(peaks);
        }
        this.isWaveformLoading.set(false);
        this.isUpgradingWaveform = false;
      },
      error: (err) => {
        console.warn('[WAVEFORM:UPGRADE_WARN] Yüksek çözünürlüklü dalga formu alınamadı:', err);
        this.isWaveformLoading.set(false);
        this.isUpgradingWaveform = false;
      }
    });
  }

  // --- OYNATMA & TRANSPORT İŞLEMLERİ ---
  togglePlayPause(): void {
    const video = this.videoRef?.nativeElement;
    if (!video) return;
    if (video.paused) {
      video.play().then(() => this.isPlaying.set(true)).catch(e => console.warn(e));
    } else {
      video.pause();
      this.isPlaying.set(false);
    }
  }

  skipSeconds(seconds: number): void {
    const video = this.videoRef?.nativeElement;
    if (!video) return;
    const newTime = Math.max(0, Math.min(this.totalDuration(), video.currentTime + seconds));
    video.currentTime = newTime;
    this.currentTime.set(newTime);
  }

  toggleFullscreen(): void {
    const video = this.videoRef?.nativeElement;
    if (!video) return;
    if (document.fullscreenElement) {
      document.exitFullscreen();
    } else {
      video.requestFullscreen().catch(e => console.warn(e));
    }
  }

  seekToTranscript(time: number): void {
    console.log(`[TRANSCRIPT:SEEK] Transkript üzerinden süreye atlandı: ${time.toFixed(2)}s`);
    if (this.videoRef?.nativeElement) {
      this.videoRef.nativeElement.currentTime = time;
    }
    this.currentTime.set(time);
  }

  // --- GERİ AL & İLERİ AL (UNDO / REDO) ---
  undo(): void {
    this.edlService.undoEdl(this.projectId).subscribe({
      next: () => this.loadEdl(),
      error: (err) => console.warn('Undo:', err)
    });
  }

  redo(): void {
    this.edlService.redoEdl(this.projectId).subscribe({
      next: () => this.loadEdl(),
      error: (err) => console.warn('Redo:', err)
    });
  }

  // --- SAĞ TIK BAĞLAM MENÜSÜ (CONTEXT MENU) ---
  openClipContextMenu(event: MouseEvent, clip: any): void {
    event.preventDefault();
    event.stopPropagation();
    this.contextMenu.set({
      visible: true,
      x: Math.min(window.innerWidth - 220, event.clientX),
      y: Math.min(window.innerHeight - 250, event.clientY),
      type: 'clip',
      targetClip: clip
    });
  }

  openOverlayContextMenu(event: MouseEvent, ov: OverlayItem): void {
    event.preventDefault();
    event.stopPropagation();
    this.selectedOverlayId.set(ov.id);
    this.contextMenu.set({
      visible: true,
      x: Math.min(window.innerWidth - 220, event.clientX),
      y: Math.min(window.innerHeight - 280, event.clientY),
      type: 'overlay',
      targetOverlay: ov
    });
  }

  openTimelineContextMenu(event: MouseEvent): void {
    event.preventDefault();
    event.stopPropagation();
    const time = this.getTimeAtClientX(event.clientX);
    this.contextMenu.set({
      visible: true,
      x: Math.min(window.innerWidth - 220, event.clientX),
      y: Math.min(window.innerHeight - 260, event.clientY),
      type: 'timeline',
      seekTime: time
    });
  }

  closeContextMenu(): void {
    this.contextMenu.set(null);
  }

  splitClipAtPlayhead(clip: any): void {
    const t = this.currentTime();
    this.splitMarkers.update(m => [...m, t]);
    this.closeContextMenu();
  }

  deleteClip(clip: any): void {
    const newCut = { 
      id: `manual_cut_${Date.now()}`, 
      start: clip.start, 
      end: clip.end, 
      reason: 'Manuel kesim',
      action: 'add'
    };
    this.edlService.patchEdl(this.projectId, {
      cuts: [newCut as any]
    }).subscribe(() => {
      this.loadEdl();
      this.closeContextMenu();
    });
  }

  restoreClip(clip: any): void {
    if (clip.cutObj?.id) {
      this.edlService.patchEdl(this.projectId, {
        cuts: [{ id: clip.cutObj.id, start: 0, end: 0, action: 'remove' } as any]
      }).subscribe(() => {
        this.loadEdl();
        this.closeContextMenu();
      });
    }
  }

  duplicateOverlay(overlayId: string): void {
    const currentOverlays = this.activeEdl()?.overlays || [];
    const ov = currentOverlays.find(o => o.id === overlayId);
    if (!ov) return;
    
    const newId = `ov_${ov.type}_${Date.now()}`;
    const newStart = parseFloat(Math.min(this.totalDuration() - 1, ov.timestamp + 1.0).toFixed(2));
    
    const duplicated: any = {
      ...ov,
      id: newId,
      timestamp: newStart,
      content: ov.type === 'text' ? `${ov.content || 'Metin'} (Kopya)` : ov.content,
      action: 'add'
    };
    
    this.edlService.patchEdl(this.projectId, {
      overlays: [duplicated]
    }).subscribe({
      next: () => {
        this.loadEdl();
        this.selectOverlay(newId);
      },
      error: (err) => console.error('Katman kopyalanamadı:', err)
    });
  }

  splitOverlayAtPlayhead(ov: OverlayItem): void {
    const t = this.currentTime();
    if (t <= ov.timestamp || t >= (ov.timestamp + ov.duration)) {
      alert('Zaman imleci katmanın sınırları içinde olmalıdır.');
      return;
    }
    const part1Duration = parseFloat((t - ov.timestamp).toFixed(2));
    const part2Duration = parseFloat(((ov.timestamp + ov.duration) - t).toFixed(2));
    
    const updatedPart1 = {
      ...ov,
      duration: part1Duration,
      action: 'update'
    };
    const newPart2 = {
      ...ov,
      id: `ov_${ov.type}_${Date.now()}`,
      timestamp: parseFloat(t.toFixed(2)),
      duration: part2Duration,
      action: 'add'
    };
    
    this.edlService.patchEdl(this.projectId, {
      overlays: [updatedPart1 as any, newPart2 as any]
    }).subscribe(() => {
      this.loadEdl();
    });
  }

  deleteSelectedItems(): void {
    if (this.selectedOverlayId()) {
      this.removeOverlay(this.selectedOverlayId()!);
      this.selectedOverlayId.set(null);
      return;
    }
    if (this.selectedClipIds().length > 0) {
      this.deleteSelectedClips();
    }
  }

  // --- MOUSE TEKERLEĞİ İLE ZOOM & SCROLL ---
  onTimelineWheel(event: WheelEvent): void {
    if (event.ctrlKey || event.metaKey) {
      event.preventDefault();
      if (event.deltaY < 0) {
        this.zoomIn();
      } else {
        this.zoomOut();
      }
    } else {
      event.preventDefault();
      const container = this.timelineScrollContainerRef?.nativeElement;
      if (container) {
        const scrollAmount = event.shiftKey ? event.deltaY : event.deltaY * 1.5;
        container.scrollLeft += scrollAmount;
      }
    }
  }

  scrollTimelineLeft(): void {
    const container = this.timelineScrollContainerRef?.nativeElement;
    if (container) {
      container.scrollBy({ left: -200, behavior: 'smooth' });
    }
  }

  scrollTimelineRight(): void {
    const container = this.timelineScrollContainerRef?.nativeElement;
    if (container) {
      container.scrollBy({ left: 200, behavior: 'smooth' });
    }
  }

  scrollTimelineToPlayhead(): void {
    const container = this.timelineScrollContainerRef?.nativeElement;
    if (!container) return;
    
    const playheadPercent = this.getPlayheadPosition() / 100;
    const targetScrollLeft = (playheadPercent * container.scrollWidth) - (container.clientWidth / 2);
    
    container.scrollTo({
      left: Math.max(0, targetScrollLeft),
      behavior: 'smooth'
    });
  }

  formatTime(seconds: number): string {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }

  // --- KLAVYE KISAYOLLARI (HOSTLISTENER) ---
  @HostListener('window:keydown', ['$event'])
  onGlobalKeyDown(event: KeyboardEvent): void {
    const target = event.target as HTMLElement;
    if (target) {
      const tag = target.tagName?.toLowerCase();
      if (tag === 'input' || tag === 'textarea' || tag === 'select' || target.isContentEditable) {
        return;
      }
    }

    if (event.code === 'Escape') {
      if (this.contextMenu()) {
        this.closeContextMenu();
        return;
      }
      if (this.selectedOverlayId()) {
        this.selectedOverlayId.set(null);
        return;
      }
      if (this.selectedClipIds().length > 0) {
        this.selectedClipIds.set([]);
        return;
      }
    }

    if (event.code === 'Space') {
      event.preventDefault();
      this.togglePlayPause();
      return;
    }

    if ((event.ctrlKey || event.metaKey) && !event.shiftKey && event.code === 'KeyZ') {
      event.preventDefault();
      this.undo();
      return;
    }

    if ((event.ctrlKey || event.metaKey) && (event.code === 'KeyY' || (event.shiftKey && event.code === 'KeyZ'))) {
      event.preventDefault();
      this.redo();
      return;
    }

    if (event.code === 'KeyB') {
      event.preventDefault();
      this.addSplitMarker();
      return;
    }

    if (event.code === 'KeyV' || event.key.toLowerCase() === 'v') {
      event.preventDefault();
      this.rippleDeleteLeft();
      return;
    }

    if ((event.ctrlKey || event.metaKey) && event.code === 'KeyD') {
      event.preventDefault();
      const ovId = this.selectedOverlayId();
      if (ovId) {
        this.duplicateOverlay(ovId);
      }
      return;
    }

    if (event.code === 'Delete' || event.code === 'Backspace') {
      this.deleteSelectedItems();
      return;
    }

    if (event.code === 'KeyM') {
      if (this.selectedClipIds().length > 1) {
        event.preventDefault();
        this.mergeSelectedClips();
        return;
      }
    }

    if (event.code === 'KeyC') {
      event.preventDefault();
      this.toggleSubtitles();
      return;
    }

    if (event.code === 'KeyT' && !event.ctrlKey && !event.metaKey) {
      event.preventDefault();
      this.addTextOverlay();
      return;
    }
  }

  // --- MEDYA YÖNETİMİ ---
  loadChatHistory(): void {
    this.chatService.getHistory(this.projectId).subscribe({
      next: (msgs) => this.chatMessages.set(msgs),
      error: (err) => console.error('Chat geçmişi alınamadı:', err)
    });
  }

  loadAssets(): void {
    if (!this.projectId) return;
    this.assetService.getAssets(this.projectId).subscribe({
      next: (assets) => this.assets.set(assets),
      error: (err) => console.error('Medya varlıkları yüklenemedi:', err)
    });
  }

  triggerAssetUpload(): void {
    this.assetFileInput?.nativeElement.click();
  }

  onAssetFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      this.uploadFile(input.files[0]);
      input.value = '';
    }
  }

  onAssetDragOver(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragOver.set(true);
  }

  onAssetDragLeave(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragOver.set(false);
  }

  onAssetDrop(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragOver.set(false);
    if (event.dataTransfer?.files && event.dataTransfer.files.length > 0) {
      this.uploadFile(event.dataTransfer.files[0]);
    }
  }

  uploadFile(file: File): void {
    if (!this.projectId) return;
    this.isUploadingAsset.set(true);
    this.assetService.uploadAsset(this.projectId, file).subscribe({
      next: (newAsset) => {
        this.isUploadingAsset.set(false);
        this.assets.update(list => [newAsset, ...list]);
      },
      error: (err) => {
        this.isUploadingAsset.set(false);
        alert('Medya yüklenemedi: ' + (err.error?.detail || err.message));
      }
    });
  }

  deleteAsset(assetId: string): void {
    if (!confirm('Bu medya dosyasını silmek istediğinize emin misiniz?')) return;
    this.assetService.deleteAsset(this.projectId, assetId).subscribe({
      next: () => {
        this.assets.update(list => list.filter(a => a.id !== assetId));
      },
      error: (err) => alert('Medya silinemedi: ' + err.message)
    });
  }

  addAssetOverlay(asset: ProjectAssetDto): void {
    const isImage = asset.mimeTuru.startsWith('image/');
    const isVideo = asset.mimeTuru.startsWith('video/');
    const t = Math.max(0, this.currentTime());
    const currentOverlays = this.activeEdl()?.overlays || [];
    const overlapping = currentOverlays.filter(ov => {
       const ovEnd = ov.timestamp + ov.duration;
       return (t < ovEnd && (t + 5.0) > ov.timestamp);
    });
    let nextTrack = 1;
    if (overlapping.length > 0) {
       const usedTracks = overlapping.map(o => Number(o.trackId) || 1);
       nextTrack = Math.max(...usedTracks) + 1;
    }

    const newOverlay: any = {
      id: `asset_${Date.now()}`,
      type: isImage ? 'image' : (isVideo ? 'video' : 'text'),
      content: asset.dosyaAdi,
      source: asset.url,
      timestamp: parseFloat(t.toFixed(2)),
      duration: 5.0,
      positionX: 50,
      positionY: 50,
      scale: 1.0,
      trackId: nextTrack,
      animation: 'fade',
      exitAnimation: 'fade',
      action: 'add'
    };

    this.edlService.patchEdl(this.projectId, {
      overlays: [newOverlay]
    }).subscribe(() => {
      this.loadEdl();
      this.activeTab.set('overlays');
    });
  }

  isSkippingCut = false;
  private playedSfxIdsInPass = new Set<string>();

  onVideoSeeked(): void {
    this.isSkippingCut = false;
    this.playedSfxIdsInPass.clear();
    const bgm = this.bgmAudioRef?.nativeElement;
    const video = this.videoRef?.nativeElement;
    if (bgm && video && this.bgmUrl()) {
      bgm.currentTime = video.currentTime % Math.max(1, bgm.duration || 60);
    }
  }

  onVideoPlay(): void {
    const bgm = this.bgmAudioRef?.nativeElement;
    const video = this.videoRef?.nativeElement;
    if (bgm && this.bgmUrl()) {
      bgm.currentTime = (video?.currentTime || 0) % Math.max(1, bgm.duration || 60);
      bgm.volume = (this.edl()?.settings?.bgmVolume ?? 15) / 100;
      bgm.play().catch(() => {});
    }
  }

  onVideoPause(): void {
    const bgm = this.bgmAudioRef?.nativeElement;
    if (bgm) {
      bgm.pause();
    }
  }

  // --- CANLI EDL SİMÜLASYONU (Cut Skip + BGM Auto-Ducking + Canlı SFX + Klip Hızı) ---
  onTimeUpdate(): void {
    if (this.isScrubbing) return;
    
    const video = this.videoRef?.nativeElement;
    if (!video) return;

    const t = video.currentTime;
    this.currentTime.set(t);

    if (video.seeking || this.isSkippingCut) return;

    // 1. Canlı BGM Auto-Ducking ([E2])
    const bgm = this.bgmAudioRef?.nativeElement;
    if (bgm && this.bgmUrl() && !video.paused) {
      const baseVol = Math.max(0, Math.min(1, (this.edl()?.settings?.bgmVolume ?? 15) / 100));
      const autoDuck = this.edl()?.settings?.bgmAutoDuck ?? true;
      const isSpeaking = autoDuck && this.visibleSubtitleSegments().some((seg: any) => t >= seg.start && t <= seg.end);
      const targetVol = isSpeaking ? Math.max(0.02, baseVol * 0.25) : baseVol;
      bgm.volume = bgm.volume + (targetVol - bgm.volume) * 0.35;
    }

    // 2. Canlı SFX Tetikleme (A2 SFX Kanalı)
    if (!video.paused) {
      const sfxList = this.sfxClips();
      for (const sfx of sfxList) {
        if (t >= sfx.start && t <= sfx.start + 0.18) {
          if (!this.playedSfxIdsInPass.has(sfx.id)) {
            this.playedSfxIdsInPass.add(sfx.id);
            this.studioEngine.playSynthesizedSfx(sfx.presetId || 'whoosh-fast', sfx.volume ?? 0.8);
          }
        } else if (t < sfx.start - 0.1 || t > sfx.start + (sfx.duration || 1.0)) {
          this.playedSfxIdsInPass.delete(sfx.id);
        }
      }
    }

    // 3. Klip Hızı (0.5x - 2.0x) ve Kesilmiş Klipleri Atlama
    const allClips = this.clips();
    const currentClip = allClips.find(c => t >= c.start && t < c.end);
    if (currentClip) {
      const targetSpeed = this.clipSpeedMap()[currentClip.id] || 1.0;
      if (Math.abs(video.playbackRate - targetSpeed) > 0.05) {
        video.playbackRate = targetSpeed;
      }
    }
    if (currentClip && !this.isVisible(currentClip)) {
      // Kesilmiş bir klipteyiz. Bu klibi ve ardışık gelen tüm kesilmiş klipleri birleştirip tek seferde atla!
      let targetJumpTime = currentClip.end;
      const sortedClips = allClips.slice().sort((a, b) => a.start - b.start);
      const currIdx = sortedClips.findIndex(c => c.id === currentClip.id);
      if (currIdx !== -1) {
        for (let i = currIdx + 1; i < sortedClips.length; i++) {
          const nextClip = sortedClips[i];
          if (!this.isVisible(nextClip) && Math.abs(nextClip.start - targetJumpTime) < 0.05) {
            targetJumpTime = nextClip.end;
          } else {
            break;
          }
        }
      }

      this.isSkippingCut = true;
      // 0.04s (1 video frame) tampon ekleyerek geriye düşme (infinite seek-loop) riskini sıfırla
      const finalJumpTime = Math.min(this.totalDuration(), targetJumpTime + 0.04);
      video.currentTime = finalJumpTime;
      this.currentTime.set(finalJumpTime);
    }
  }

  onMetadataLoaded(): void {
    const video = this.videoRef?.nativeElement;
    if (video && video.duration && !isNaN(video.duration)) {
      this.totalDuration.set(video.duration);
    }
    if (video && video.videoWidth && video.videoHeight) {
      const ratio = `${video.videoWidth} / ${video.videoHeight}`;
      this.videoAspectRatio.set(ratio);
      this.diagnostics.logTrace('GEOMETRY', 'Video Metadatası Yüklendi', {
        videoWidth: video.videoWidth,
        videoHeight: video.videoHeight,
        aspectRatio: ratio,
        duration: video.duration
      });
    }
    if (!this.audioPeaks() || this.audioPeaks()!.length === 0) {
      this.ensureHighResWaveform();
    }
  }

  getRawTimeFromVisTime(visTime: number): number {
    if (!this.isAnyRippleActive()) {
       return Math.max(0, Math.min(this.totalDuration(), visTime));
    }
    let accumulated = 0;
    for (const c of this.clips()) {
       if (this.isVisible(c)) {
          if (accumulated + c.duration >= visTime) {
             return c.start + (visTime - accumulated);
          }
          accumulated += c.duration;
       }
    }
    return this.totalDuration();
  }

  getVisTimeFromRawTime(rawTime: number): number {
    if (!this.isAnyRippleActive()) {
       return Math.max(0, Math.min(this.totalDuration(), rawTime));
    }
    let passed = 0;
    for (const c of this.clips()) {
       if (rawTime >= c.start && rawTime < c.end) {
          if (this.isVisible(c)) {
             passed += (rawTime - c.start);
          }
          break;
       }
       if (rawTime === c.end && c === this.clips()[this.clips().length - 1]) {
          if (this.isVisible(c)) {
             passed += (rawTime - c.start);
          }
          break;
       }
       if (this.isVisible(c)) {
          passed += c.duration;
       }
    }
    return passed;
  }

  getTimeAtClientX(clientX: number): number {
    const track = this.timelineTrackRef?.nativeElement;
    if (!track) {
      console.warn('[SCRUB:WARN] timelineTrackRef referansı DOM üzerinde bulunamadı!');
      return 0;
    }
    const rect = track.getBoundingClientRect();
    const clickX = clientX - rect.left;
    const percentage = Math.max(0, Math.min(1, clickX / Math.max(1, rect.width)));
    
    let resultTime: number;
    if (!this.isAnyRippleActive()) {
       resultTime = percentage * this.totalDuration();
    } else {
       const targetVisDuration = percentage * this.visibleDuration();
       resultTime = this.getRawTimeFromVisTime(targetVisDuration);
    }

    if (isNaN(resultTime) || resultTime < 0) {
      console.error('[SCRUB:TIME_NAN_ERROR]', { clientX, rectLeft: rect.left, rectWidth: rect.width, clickX, percentage, resultTime });
      return 0;
    }
    return resultTime;
  }

  getPlayheadPosition(): number {
    const t = this.currentTime();
    let pos: number;
    if (!this.isAnyRippleActive()) {
       pos = (t / Math.max(0.001, this.totalDuration())) * 100;
    } else {
       const visDur = this.visibleDuration();
       if (visDur <= 0) return 0;
       pos = (this.getVisTimeFromRawTime(t) / visDur) * 100;
    }
    if (isNaN(pos)) {
      console.error('[PLAYHEAD:POS_NAN]', { t, totalDur: this.totalDuration(), visDur: this.visibleDuration() });
      return 0;
    }
    return Math.max(0, Math.min(100, pos));
  }

  getTimelineTime(event: MouseEvent): number {
    return this.getTimeAtClientX(event.clientX);
  }

  seekTimeline(event: MouseEvent): void {
    if (this.wasDragging) {
      console.log('[SEEK:SKIP_BECAUSE_DRAGGED]');
      this.wasDragging = false;
      return;
    }
    const target = event.target as HTMLElement;
    if (target && (
      target.closest('button') || 
      target.closest('input') || 
      target.closest('.timeline-clip') || 
      target.closest('.overlay-item') || 
      target.closest('.subtitle-segment') ||
      target.closest('#playhead')
    )) {
      return;
    }

    // Boş timeline alanına tıklandığında seçili klip ve katmanları temizle
    this.selectedClipIds.set([]);
    this.selectedOverlayId.set(null);

    const targetTime = this.getTimeAtClientX(event.clientX);
    console.log(`%c[SEEK:CLICK] clientX=${event.clientX} -> targetTime=${targetTime.toFixed(2)}s`, 'color: #ec4899; font-weight: bold;');
    const v = this.videoRef?.nativeElement;
    if (v && !v.seeking) {
      v.currentTime = targetTime;
    }
    this.currentTime.set(targetTime);
  }

  selectClip(clipId: string, event: MouseEvent): void {
    event.stopPropagation();
    this.clearSubtitleSelection();
    this.selectedOverlayId.set(null);
    const current = this.selectedClipIds();
    
    if (event.ctrlKey || event.metaKey) {
       if (current.includes(clipId)) {
          this.selectedClipIds.set(current.filter(id => id !== clipId));
       } else {
          this.selectedClipIds.set([...current, clipId]);
       }
    } else if (event.shiftKey && current.length > 0) {
       const allClips = this.clips();
       const lastSelectedId = current[current.length - 1];
       const lastIdx = allClips.findIndex(c => c.id === lastSelectedId);
       const curIdx = allClips.findIndex(c => c.id === clipId);
       
       if (lastIdx !== -1 && curIdx !== -1) {
          const start = Math.min(lastIdx, curIdx);
          const end = Math.max(lastIdx, curIdx);
          const rangeIds = allClips.slice(start, end + 1).map(c => c.id);
          this.selectedClipIds.set(Array.from(new Set([...current, ...rangeIds])));
       } else {
          this.selectedClipIds.set([clipId]);
       }
    } else {
       this.selectedClipIds.set([clipId]);
    }
    console.log(`%c[CLIP:SELECTED] clipId=${clipId}, totalSelected=${this.selectedClipIds().length}`, 'color: #10b981; font-weight: bold;');
  }

  toggleClip(clip: any, event: MouseEvent): void {
     event.stopPropagation();
     if (clip.isCut) {
        if (confirm('Bu kesimi iptal edip sahneyi geri getirmek istiyor musunuz?')) {
           this.edlService.patchEdl(this.projectId, {
             cuts: [{ id: clip.cutObj.id, start: 0, end: 0, action: 'remove' } as any]
           }).subscribe(() => this.loadEdl());
        }
     } else {
        const newCut = { 
          id: `manual_cut_${Date.now()}`, 
          start: clip.start, 
          end: clip.end, 
          reason: 'Manuel kesim' 
        };
        this.edlService.patchEdl(this.projectId, {
          cuts: [{ ...newCut, action: 'add' } as any]
        }).subscribe(() => {
          this.selectedClipIds.set(this.selectedClipIds().filter(id => id !== clip.id));
          this.loadEdl();
        });
     }
  }

  deleteSelectedClips(): void {
    const selIds = this.selectedClipIds();
    if (!selIds.length) return;
    
    const selectedClips = this.clips().filter(c => selIds.includes(c.id) && !c.isCut);
    if (!selectedClips.length) return;

    const newCuts = selectedClips.map((clip, idx) => ({
      id: `manual_cut_${Date.now()}_${idx}`,
      start: clip.start,
      end: clip.end,
      reason: 'Manuel kesim',
      action: 'add'
    }));

    this.edlService.patchEdl(this.projectId, {
      cuts: newCuts as any
    }).subscribe(() => {
      this.selectedClipIds.set([]);
      this.loadEdl();
    });
  }

  restoreSelectedCuts(): void {
    const selIds = this.selectedClipIds();
    if (!selIds.length) return;

    const selectedCutClips = this.clips().filter(c => selIds.includes(c.id) && c.isCut && c.cutObj);
    if (!selectedCutClips.length) return;

    const patchCuts = selectedCutClips.map(clip => ({
      id: clip.cutObj.id,
      start: 0,
      end: 0,
      action: 'remove'
    }));

    this.edlService.patchEdl(this.projectId, {
      cuts: patchCuts as any
    }).subscribe(() => {
      this.selectedClipIds.set([]);
      this.loadEdl();
    });
  }

  mergeSelectedClips(): void {
    const selIds = this.selectedClipIds();
    if (selIds.length < 2) return;
    
    const allClips = this.clips();
    const selectedClips = allClips.filter(c => selIds.includes(c.id)).sort((a,b) => a.start - b.start);
    
    const startRange = selectedClips[0].start;
    const endRange = selectedClips[selectedClips.length - 1].end;
    
    const edl = this.activeEdl();
    if (!edl || !edl.cuts) return;
    
    const cutsToRemove = edl.cuts.filter(c => c.start >= (startRange - 0.05) && c.end <= (endRange + 0.05));
    if (cutsToRemove.length === 0) {
       alert('Seçilen klipler arasında birleştirilecek bir kesim bulunamadı.');
       return;
    }
    
    if (confirm(`Seçili aralıktaki ${cutsToRemove.length} kesim iptal edilerek klipler birleştirilecek. Onaylıyor musunuz?`)) {
       const patchCuts = cutsToRemove.map(c => ({ id: c.id, start: 0, end: 0, action: 'remove' }));
       this.edlService.patchEdl(this.projectId, {
          cuts: patchCuts as any
       }).subscribe(() => {
          this.selectedClipIds.set([]);
          this.loadEdl();
       });
    }
  }

  zoomIn(): void {
    this.timelineZoom.update(z => Math.min(50, parseFloat((z + 0.5).toFixed(2))));
  }

  zoomOut(): void {
    this.timelineZoom.update(z => Math.max(1, parseFloat((z - 0.5).toFixed(2))));
  }

  addSplitMarker(): void {
    const t = this.currentTime();
    this.splitMarkers.update(m => [...m, t]);
  }

  rippleDeleteLeft(): void {
    const t = this.currentTime();
    const allClips = this.clips();
    
    // İmlecin (Playhead) bulunduğu o anki "sağlam" klibi bul
    const targetClip = allClips.find(c => t >= c.start && t < c.end);
    if (!targetClip || targetClip.isCut) return; 

    // O klibin başlangıcından (bir önceki kesiğin bittiği yer) imlece kadar olan kısmı kes
    const cutStart = targetClip.start;
    const cutEnd = t;

    if (cutEnd - cutStart < 0.05) return; 

    const edl = this.activeEdl();
    if (!edl) return;

    const newCut = {
      id: `manual_cut_${Date.now()}`,
      start: cutStart,
      end: cutEnd,
      reason: 'manual',
      source: 'user',
      command: 'Ripple Delete Left'
    };

    const newCuts = [...(edl.cuts || []), newCut];
    this.edlService.patchEdl(this.projectId, { cuts: newCuts } as any).subscribe(() => {
      this.loadEdl();
    });
  }

  getOverlayTop(ov: OverlayItem): string {
    if (ov.keyframes && ov.keyframes.length >= 2) {
      const relT = Math.max(0, this.currentTime() - ov.timestamp);
      const sorted = [...ov.keyframes].sort((a, b) => a.timeOffset - b.timeOffset);
      if (relT <= sorted[0].timeOffset) return `${sorted[0].y}%`;
      if (relT >= sorted[sorted.length - 1].timeOffset) return `${sorted[sorted.length - 1].y}%`;
      for (let i = 0; i < sorted.length - 1; i++) {
        if (relT >= sorted[i].timeOffset && relT <= sorted[i + 1].timeOffset) {
          const span = Math.max(0.01, sorted[i + 1].timeOffset - sorted[i].timeOffset);
          const ratio = (relT - sorted[i].timeOffset) / span;
          const y = sorted[i].y + (sorted[i + 1].y - sorted[i].y) * ratio;
          return `${y.toFixed(2)}%`;
        }
      }
    }
    if (ov.positionY !== undefined && ov.positionY !== null) return `${ov.positionY}%`;
    const vPos = ov.position?.[1] || 'bottom';
    if (vPos === 'top') return '10%';
    if (vPos === 'center') return '45%';
    return '80%';
  }

  getOverlayLeft(ov: OverlayItem): string {
    if (ov.keyframes && ov.keyframes.length >= 2) {
      const relT = Math.max(0, this.currentTime() - ov.timestamp);
      const sorted = [...ov.keyframes].sort((a, b) => a.timeOffset - b.timeOffset);
      if (relT <= sorted[0].timeOffset) return `${sorted[0].x}%`;
      if (relT >= sorted[sorted.length - 1].timeOffset) return `${sorted[sorted.length - 1].x}%`;
      for (let i = 0; i < sorted.length - 1; i++) {
        if (relT >= sorted[i].timeOffset && relT <= sorted[i + 1].timeOffset) {
          const span = Math.max(0.01, sorted[i + 1].timeOffset - sorted[i].timeOffset);
          const ratio = (relT - sorted[i].timeOffset) / span;
          const x = sorted[i].x + (sorted[i + 1].x - sorted[i].x) * ratio;
          return `${x.toFixed(2)}%`;
        }
      }
    }
    if (ov.positionX !== undefined && ov.positionX !== null) return `${ov.positionX}%`;
    const hPos = ov.position?.[0] || 'center';
    if (hPos === 'left') return '10%';
    if (hPos === 'right') return '90%';
    return '50%';
  }

  getOverlayZIndex(ov: OverlayItem): number {
    return 20 + (Number(ov.trackId) || 1);
  }

  getOverlayAnimationClass(ov: OverlayItem): string {
    const t = this.currentTime();
    const anim = ov.animation || 'fade';
    const exitAnim = ov.exitAnimation || 'fade';
    const loopAnim = ov.loopAnimation || 'none';
    const classes: string[] = [];

    if (t < ov.timestamp + 0.5) {
      if (anim === 'fade') classes.push('animate-fade-in');
      else if (anim === 'pop-up') classes.push('animate-scale-in');
      else if (anim === 'bounce') classes.push('animate-bounce-in');
      else if (anim === 'zoom-crash') classes.push('animate-zoom-crash');
      else if (anim === 'slide-up') classes.push('animate-slide-up-forwards');
      else if (anim === 'slide-down') classes.push('animate-slide-down-in');
      else if (anim === 'slide-left') classes.push('animate-slide-left-in');
      else if (anim === 'slide-right') classes.push('animate-slide-right-in');
      else if (anim === 'glitch') classes.push('animate-glitch-in');
      else if (anim === 'blur-in') classes.push('animate-blur-in');
    } else if (t > (ov.timestamp + ov.duration - 0.5)) {
      if (exitAnim === 'fade') classes.push('animate-fade-out');
      else if (exitAnim === 'scale-out') classes.push('animate-scale-out');
      else if (exitAnim === 'slide-down') classes.push('animate-slide-down-out');
      else if (exitAnim === 'blur-out') classes.push('animate-blur-out');
    } else if (loopAnim !== 'none') {
      if (loopAnim === 'pulse') classes.push('animate-loop-pulse');
      else if (loopAnim === 'float') classes.push('animate-loop-float');
      else if (loopAnim === 'wiggle') classes.push('animate-loop-wiggle');
      else if (loopAnim === 'shake') classes.push('animate-loop-shake');
      else if (loopAnim === 'neon-flicker') classes.push('animate-loop-neon');
      else if (loopAnim === 'pendulum') classes.push('animate-loop-pendulum');
    }

    return classes.join(' ');
  }

  autoAssignOverlayTracks(overlays: OverlayItem[]): { overlays: OverlayItem[]; changed: boolean } {
    if (!overlays || overlays.length === 0) return { overlays: [], changed: false };
    
    let changed = false;
    const sorted = [...overlays].sort((a, b) => a.timestamp - b.timestamp);
    const trackIntervals = new Map<number, { start: number; end: number }[]>();
    
    for (const ov of sorted) {
      const ovStart = ov.timestamp;
      const ovEnd = ov.timestamp + Math.max(0.5, ov.duration || 3);
      
      const hasCollision = (tId: number) => {
        const intervals = trackIntervals.get(tId) || [];
        return intervals.some(inv => ovStart < inv.end && ovEnd > inv.start);
      };
      
      let targetTrack = Number(ov.trackId);
      if (!targetTrack || targetTrack < 1) {
        targetTrack = 1;
      }
      
      if (hasCollision(targetTrack)) {
        let candidate = 1;
        while (hasCollision(candidate)) {
          candidate++;
        }
        targetTrack = candidate;
      }
      
      if (ov.trackId !== targetTrack) {
        ov.trackId = targetTrack;
        changed = true;
      }
      
      if (!trackIntervals.has(targetTrack)) {
        trackIntervals.set(targetTrack, []);
      }
      trackIntervals.get(targetTrack)!.push({ start: ovStart, end: ovEnd });
    }
    
    return { overlays: sorted, changed };
  }

  addTrackLane(): void {
    const currentMax = this.overlayTrackNumbers()[0] || 1;
    this.customTrackCount.set(currentMax + 1);
  }

  removeTrackLane(): void {
    const currentMax = this.overlayTrackNumbers()[0] || 1;
    if (currentMax > 1) {
      this.deleteTrackLane(currentMax);
    }
  }

  deleteTrackLane(trackNum: number): void {
    const edl = this.activeEdl();
    if (!edl) return;

    const overlays = edl.overlays || [];
    const removedOverlays = overlays.filter(o => (Number(o.trackId) || 1) === trackNum);
    // 1. O katmandaki overlay'leri temizle ve üst katmanları 1 numara kaydır
    const remainingOverlays = overlays
      .filter(o => (Number(o.trackId) || 1) !== trackNum)
      .map(o => {
        const tId = Number(o.trackId) || 1;
        if (tId > trackNum) {
          return { ...o, trackId: tId - 1 };
        }
        return o;
      });

    // Eğer seçili overlay silinen katmandaysa seçimi kaldır
    const selId = this.selectedOverlayId();
    if (selId && !remainingOverlays.some(o => o.id === selId)) {
      this.selectedOverlayId.set(null);
    }

    this.edl.update((curr: any) => curr ? { ...curr, overlays: remainingOverlays } : null);

    // 2. Gizli ve kilitli katman indekslerini kaydır
    const nextHidden = new Set<number>();
    for (const h of this.hiddenTracks()) {
      if (h < trackNum) nextHidden.add(h);
      else if (h > trackNum) nextHidden.add(h - 1);
    }
    this.hiddenTracks.set(nextHidden);

    const nextLocked = new Set<number>();
    for (const l of this.lockedTracks()) {
      if (l < trackNum) nextLocked.add(l);
      else if (l > trackNum) nextLocked.add(l - 1);
    }
    this.lockedTracks.set(nextLocked);

    // 3. customTrackCount'u güncelle
    const curCount = this.customTrackCount();
    if (curCount > 1) {
      this.customTrackCount.set(curCount - 1);
    }

    // 4. Backend'e senkronize et
    const patchPayload: any[] = [
      ...removedOverlays.map(o => ({ id: o.id, action: 'remove' })),
      ...remainingOverlays.map(o => ({ id: o.id, trackId: o.trackId, action: 'update' }))
    ];
    if (patchPayload.length > 0) {
      this.edlService.patchEdl(this.projectId, { overlays: patchPayload }).subscribe({
        error: (err: any) => console.warn('Patch error on delete track:', err)
      });
    }
  }


  isTrackHidden(trackNum: number): boolean {
    return this.hiddenTracks().has(trackNum);
  }

  isTrackLocked(trackNum: number): boolean {
    return this.lockedTracks().has(trackNum);
  }

  toggleTrackVisibility(trackNum: number): void {
    const current = new Set(this.hiddenTracks());
    if (current.has(trackNum)) {
      current.delete(trackNum);
    } else {
      current.add(trackNum);
    }
    this.hiddenTracks.set(current);
  }

  toggleTrackLock(trackNum: number): void {
    const current = new Set(this.lockedTracks());
    if (current.has(trackNum)) {
      current.delete(trackNum);
    } else {
      current.add(trackNum);
    }
    this.lockedTracks.set(current);
  }

  assignAssetToSelectedOverlay(asset: ProjectAssetDto): void {
    const selId = this.selectedOverlayId();
    if (!selId) return;
    const ov = this.activeEdl()?.overlays?.find(o => o.id === selId);
    if (ov) {
      ov.source = asset.url;
      ov.content = asset.dosyaAdi;
      if (this.inspectorData && this.inspectorData.id === selId) {
        this.inspectorData.source = asset.url;
        this.inspectorData.content = asset.dosyaAdi;
      }
      this.edl.update(e => e ? { ...e } : null);
      this.edlService.patchEdl(this.projectId, {
        overlays: [{ id: selId, source: asset.url, content: asset.dosyaAdi, action: 'update' } as any]
      }).subscribe(() => {
        this.loadEdl();
      });
    }
  }

  assignUrlToSelectedOverlay(url: string, name: string): void {
    const selId = this.selectedOverlayId();
    if (!selId) return;
    const ov = this.activeEdl()?.overlays?.find(o => o.id === selId);
    if (ov) {
      ov.source = url;
      ov.content = name;
      if (this.inspectorData && this.inspectorData.id === selId) {
        this.inspectorData.source = url;
        this.inspectorData.content = name;
      }
      this.edl.update(e => e ? { ...e } : null);
      this.edlService.patchEdl(this.projectId, {
        overlays: [{ id: selId, source: url, content: name, action: 'update' } as any]
      }).subscribe(() => {
        this.loadEdl();
      });
    }
  }
  
  onCanvasDragStart(event: MouseEvent, overlayId: string): void {
     event.preventDefault();
     event.stopPropagation();
     const ov = this.activeEdl()?.overlays?.find(o => o.id === overlayId);
     if (ov && this.isTrackLocked(Number(ov.trackId) || 1)) {
        return;
     }
     if (this.selectedOverlayId() !== overlayId) {
        this.selectOverlay(overlayId);
     }
     this.isCanvasDragging = true;
     this.canvasDragOverlayId = overlayId;
     this.canvasDragStartX = event.clientX;
     this.canvasDragStartY = event.clientY;
     
     if (ov) {
        if (ov.positionX !== undefined && ov.positionX !== null) {
           this.canvasDragOriginalX = ov.positionX;
        } else {
           this.canvasDragOriginalX = parseFloat(this.getOverlayLeft(ov));
        }
        
        if (ov.positionY !== undefined && ov.positionY !== null) {
           this.canvasDragOriginalY = ov.positionY;
        } else {
           this.canvasDragOriginalY = parseFloat(this.getOverlayTop(ov));
        }
     }
  }

  getOverlayStyle(ov: any): any {
     const totalDur = Math.max(1, this.totalDuration());
     if (!this.isAnyRippleActive()) {
        return {
           left: `${(ov.timestamp / totalDur) * 100}%`,
           width: `${Math.max(0.1, (ov.duration / totalDur) * 100)}%`
        };
     }

     const startVis = this.getVisTimeFromRawTime(ov.timestamp);
     const endVis = this.getVisTimeFromRawTime(ov.timestamp + ov.duration);
     const visDur = this.visibleDuration();
     
     if (visDur <= 0 || endVis <= startVis) return { display: 'none' };
     
     return {
        left: `${(startVis / visDur) * 100}%`,
        width: `${Math.max(0.1, ((endVis - startVis) / visDur) * 100)}%`
     };
  }

  addTextOverlay(): void {
    let start = this.currentTime();
    let duration = 3.0;
    
    const selIds = this.selectedClipIds();
    if (selIds.length > 0) {
      const selectedClips = this.clips().filter(c => selIds.includes(c.id)).sort((a,b) => a.start - b.start);
      if (selectedClips.length > 0) {
        start = selectedClips[0].start;
        const end = selectedClips[selectedClips.length - 1].end;
        duration = Math.max(1.0, end - start);
      }
    }
    
    const newOvId = `ov_txt_${Date.now()}`;
    const currentOverlays = this.activeEdl()?.overlays || [];
    const overlapping = currentOverlays.filter(ov => {
       const ovEnd = ov.timestamp + ov.duration;
       return (start < ovEnd && (start + duration) > ov.timestamp);
    });
    let nextTrack = 1;
    if (overlapping.length > 0) {
       const usedTracks = overlapping.map(o => Number(o.trackId) || 1);
       nextTrack = Math.max(...usedTracks) + 1;
    }

    const newOverlay: any = {
      id: newOvId,
      type: 'text',
      content: 'Yeni Metin',
      timestamp: parseFloat(start.toFixed(2)),
      duration: parseFloat(duration.toFixed(2)),
      color: '#FFFFFF',
      fontSize: 54,
      font: 'Inter',
      positionX: 50,
      positionY: 80,
      trackId: nextTrack,
      animation: 'fade',
      exitAnimation: 'fade',
      action: 'add'
    };

    // Anında (0ms) yerel EDL'e ekle ve sağdaki Stüdyo Denetçisini aç
    this.edl.update(curr => curr ? { ...curr, overlays: [...(curr.overlays || []), newOverlay] } : null);
    this.selectOverlay(newOvId);

    this.edlService.patchEdl(this.projectId, {
      overlays: [newOverlay]
    }).subscribe({
      next: () => {
        this.loadEdl();
        if (this.videoRef?.nativeElement) {
          this.videoRef.nativeElement.currentTime = start;
          this.currentTime.set(start);
        }
        this.selectOverlay(newOvId);
      },
      error: (err) => console.error('Metin eklenemedi:', err)
    });
  }

  addImageOverlay(): void {
    const imgAssets = this.assets().filter(a => a.mimeTuru?.startsWith('image/'));
    if (imgAssets.length > 0) {
      const latestAsset = imgAssets[imgAssets.length - 1];
      this.addAssetOverlay(latestAsset);
      return;
    }
    this.activeTab.set('media');
  }

  addImageOverlayFromUrl(url: string, contentName = 'Stok Görsel'): void {
    let start = this.currentTime();
    let duration = 4.0;
    
    const selIds = this.selectedClipIds();
    if (selIds.length > 0) {
      const selectedClips = this.clips().filter(c => selIds.includes(c.id)).sort((a,b) => a.start - b.start);
      if (selectedClips.length > 0) {
        start = selectedClips[0].start;
        const end = selectedClips[selectedClips.length - 1].end;
        duration = Math.max(1.0, end - start);
      }
    }
    
    const newOvId = `ov_img_${Date.now()}`;
    const currentOverlays = this.activeEdl()?.overlays || [];
    const overlapping = currentOverlays.filter(ov => {
       const ovEnd = ov.timestamp + ov.duration;
       return (start < ovEnd && (start + duration) > ov.timestamp);
    });
    let nextTrack = 1;
    if (overlapping.length > 0) {
       const usedTracks = overlapping.map(o => Number(o.trackId) || 1);
       nextTrack = Math.max(...usedTracks) + 1;
    }

    const newOverlay: any = {
      id: newOvId,
      type: 'image',
      content: contentName,
      source: url,
      timestamp: parseFloat(start.toFixed(2)),
      duration: parseFloat(duration.toFixed(2)),
      positionX: 50,
      positionY: 45,
      scale: 1.0,
      trackId: nextTrack,
      animation: 'fade',
      exitAnimation: 'fade',
      action: 'add'
    };

    // Anında (0ms) yerel EDL'e ekle ve sağdaki Görsel/Photoshop Denetçisini aç
    this.edl.update(curr => curr ? { ...curr, overlays: [...(curr.overlays || []), newOverlay] } : null);
    this.selectOverlay(newOvId);

    this.edlService.patchEdl(this.projectId, {
      overlays: [newOverlay]
    }).subscribe({
      next: () => {
        this.loadEdl();
        if (this.videoRef?.nativeElement) {
          this.videoRef.nativeElement.currentTime = start;
          this.currentTime.set(start);
        }
        this.selectOverlay(newOvId);
      },
      error: (err) => console.error('Görsel eklenemedi:', err)
    });
  }

  addOverlayToSelected(): void {
    this.addTextOverlay();
  }

  addImageOverlayToSelected(): void {
    this.addImageOverlay();
  }

  selectOverlay(id: string): void {
     this.clearSubtitleSelection();
     this.selectedOverlayId.set(id);
     const ov = this.activeEdl()?.overlays?.find(o => o.id === id);
     if (ov) {
        this.inspectorData = {
          id: ov.id,
          type: ov.type || 'text',
          content: ov.content || '',
          source: ov.source || '',
          originalSource: ov.originalSource || ov.source || '',
          timestamp: ov.timestamp ?? 0,
          duration: ov.duration ?? 3,
          fontSize: ov.fontSize ?? 48,
          font: ov.font || 'Inter',
          fontWeight: ov.fontWeight || '900',
          lineHeight: ov.lineHeight ?? 1.2,
          textAlign: ov.textAlign || 'center',
          color: ov.color || '#FFFFFF',
          fillType: ov.fillType || 'solid',
          gradientStart: ov.gradientStart || '#FACC15',
          gradientEnd: ov.gradientEnd || '#EF4444',
          gradientAngle: ov.gradientAngle ?? 90,
          positionX: ov.positionX ?? 50,
          positionY: ov.positionY ?? 50,
          animation: ov.animation || 'none',
          exitAnimation: ov.exitAnimation || 'fade',
          loopAnimation: ov.loopAnimation || 'none',
          keyframes: ov.keyframes ? [...ov.keyframes] : [],
          scale: ov.scale ?? 1.0,
          trackId: ov.trackId ?? 1,
          // Tipografi & Efektler
          strokeColor: ov.strokeColor || '#000000',
          strokeWidth: ov.strokeWidth ?? 0,
          outerStrokeColor: ov.outerStrokeColor || '#EF4444',
          outerStrokeWidth: ov.outerStrokeWidth ?? 0,
          glowEnabled: ov.glowEnabled ?? false,
          glowColor: ov.glowColor || '#22D3EE',
          glowRadius: ov.glowRadius ?? 18,
          shadowColor: ov.shadowColor || 'rgba(0,0,0,0.8)',
          shadowBlur: ov.shadowBlur ?? 2,
          shadowDistance: ov.shadowDistance ?? 4,
          shadowAngle: ov.shadowAngle ?? 45,
          boxStyle: ov.boxStyle || 'none',
          boxBgColor: ov.boxBgColor || '#1E293B',
          boxPadding: ov.boxPadding ?? 14,
          borderRadius: ov.borderRadius ?? 20,
          allCaps: ov.allCaps ?? false,
          letterSpacing: ov.letterSpacing ?? 0,
          curveBend: ov.curveBend ?? 0,
          rotateX: ov.rotateX ?? 0,
          rotateY: ov.rotateY ?? 0,
          skewX: ov.skewX ?? 0,
          skewY: ov.skewY ?? 0,
          // Görsel, Photoshop & AI Sticker
          removeBg: ov.removeBg ?? false,
          stickerBorder: ov.stickerBorder ?? false,
          stickerBorderWidth: ov.stickerBorderWidth ?? 6,
          stickerBorderColor: ov.stickerBorderColor || '#FFFFFF',
          rotation: ov.rotation ?? 0,
          maskShape: ov.maskShape || 'rect',
          feather: ov.feather ?? 0,
          chromaKeyColor: ov.chromaKeyColor || '',
          brightness: ov.brightness ?? 0,
          contrast: ov.contrast ?? 0,
          saturation: ov.saturation ?? 0,
          warmth: ov.warmth ?? 0,
          hue: ov.hue ?? 0,
          blur: ov.blur ?? 0,
          sharpen: ov.sharpen ?? 0,
          opacity: ov.opacity ?? 100,
          flipH: ov.flipH ?? false,
          flipV: ov.flipV ?? false,
          blendMode: ov.blendMode || 'normal',
          dropShadow: ov.dropShadow ?? false
        };
        
        const t = this.currentTime();
        if (t < ov.timestamp || t > (ov.timestamp + ov.duration)) {
           if (this.videoRef?.nativeElement) {
              this.videoRef.nativeElement.currentTime = ov.timestamp + 0.05;
              this.currentTime.set(ov.timestamp + 0.05);
           }
        }
     }
  }

  onInspectorChange(): void {
    const selId = this.selectedOverlayId();
    if (!selId) return;
    const ov = this.activeEdl()?.overlays?.find(o => o.id === selId);
    if (ov) {
      ov.content = this.inspectorData.content;
      ov.source = this.inspectorData.source;
      ov.originalSource = this.inspectorData.originalSource || ov.originalSource;
      ov.color = this.inspectorData.color;
      ov.fontSize = Number(this.inspectorData.fontSize) || 48;
      ov.font = this.inspectorData.font;
      ov.fontWeight = this.inspectorData.fontWeight || '900';
      ov.lineHeight = Number(this.inspectorData.lineHeight) || 1.2;
      ov.textAlign = this.inspectorData.textAlign || 'center';
      ov.fillType = this.inspectorData.fillType || 'solid';
      ov.gradientStart = this.inspectorData.gradientStart || '#FACC15';
      ov.gradientEnd = this.inspectorData.gradientEnd || '#EF4444';
      ov.gradientAngle = Number(this.inspectorData.gradientAngle) ?? 90;
      ov.scale = Number(this.inspectorData.scale) || 1.0;
      ov.animation = this.inspectorData.animation;
      ov.exitAnimation = this.inspectorData.exitAnimation || 'fade';
      ov.loopAnimation = this.inspectorData.loopAnimation || 'none';
      ov.keyframes = this.inspectorData.keyframes || [];
      ov.positionX = Number(this.inspectorData.positionX);
      ov.positionY = Number(this.inspectorData.positionY);
      ov.timestamp = Number(this.inspectorData.timestamp);
      ov.duration = Number(this.inspectorData.duration);
      ov.trackId = Number(this.inspectorData.trackId) || 1;

      // Tipografi & Rozet & 3D
      ov.strokeColor = this.inspectorData.strokeColor;
      ov.strokeWidth = Number(this.inspectorData.strokeWidth) || 0;
      ov.outerStrokeColor = this.inspectorData.outerStrokeColor || '#EF4444';
      ov.outerStrokeWidth = Number(this.inspectorData.outerStrokeWidth) || 0;
      ov.glowEnabled = Boolean(this.inspectorData.glowEnabled);
      ov.glowColor = this.inspectorData.glowColor || '#22D3EE';
      ov.glowRadius = Number(this.inspectorData.glowRadius) || 18;
      ov.shadowColor = this.inspectorData.shadowColor;
      ov.shadowBlur = Number(this.inspectorData.shadowBlur) || 0;
      ov.shadowDistance = Number(this.inspectorData.shadowDistance) || 0;
      ov.shadowAngle = Number(this.inspectorData.shadowAngle) || 45;
      ov.boxStyle = this.inspectorData.boxStyle || 'none';
      ov.boxBgColor = this.inspectorData.boxBgColor;
      ov.boxPadding = Number(this.inspectorData.boxPadding) || 14;
      ov.borderRadius = Number(this.inspectorData.borderRadius) || 20;
      ov.allCaps = Boolean(this.inspectorData.allCaps);
      ov.letterSpacing = Number(this.inspectorData.letterSpacing) || 0;
      ov.curveBend = Number(this.inspectorData.curveBend) || 0;
      ov.rotateX = Number(this.inspectorData.rotateX) || 0;
      ov.rotateY = Number(this.inspectorData.rotateY) || 0;
      ov.skewX = Number(this.inspectorData.skewX) || 0;
      ov.skewY = Number(this.inspectorData.skewY) || 0;

      // Görsel, Photoshop & AI
      ov.removeBg = Boolean(this.inspectorData.removeBg);
      ov.stickerBorder = Boolean(this.inspectorData.stickerBorder);
      ov.stickerBorderWidth = Number(this.inspectorData.stickerBorderWidth) || 6;
      ov.stickerBorderColor = this.inspectorData.stickerBorderColor || '#FFFFFF';
      ov.rotation = Number(this.inspectorData.rotation) || 0;
      ov.maskShape = this.inspectorData.maskShape || 'rect';
      ov.feather = Number(this.inspectorData.feather) || 0;
      ov.chromaKeyColor = this.inspectorData.chromaKeyColor || '';
      ov.brightness = Number(this.inspectorData.brightness) || 0;
      ov.contrast = Number(this.inspectorData.contrast) || 0;
      ov.saturation = Number(this.inspectorData.saturation) || 0;
      ov.warmth = Number(this.inspectorData.warmth) || 0;
      ov.hue = Number(this.inspectorData.hue) || 0;
      ov.blur = Number(this.inspectorData.blur) || 0;
      ov.sharpen = Number(this.inspectorData.sharpen) || 0;
      ov.opacity = Number(this.inspectorData.opacity ?? 100);
      ov.flipH = Boolean(this.inspectorData.flipH);
      ov.flipV = Boolean(this.inspectorData.flipV);
      ov.blendMode = this.inspectorData.blendMode || 'normal';
      ov.dropShadow = Boolean(this.inspectorData.dropShadow);
      
      this.edl.update(e => e ? { ...e, overlays: [...(e.overlays || [])] } : null);
      this.diagnostics.logTrace('INSPECTOR', 'Overlay Değiştirildi', {
        id: selId,
        type: ov.type,
        font: ov.font,
        scale: ov.scale,
        posX: ov.positionX,
        posY: ov.positionY
      });
    }
  }

  saveInspector(): void {
     const selId = this.selectedOverlayId();
     if (!selId || !this.inspectorData) return;
     
     this.edlService.patchEdl(this.projectId, {
        overlays: [{
          ...this.inspectorData,
          id: selId,
          type: this.inspectorData.type || 'text',
          timestamp: Number(this.inspectorData.timestamp),
          duration: Number(this.inspectorData.duration),
          positionX: Number(this.inspectorData.positionX),
          positionY: Number(this.inspectorData.positionY),
          fontSize: Number(this.inspectorData.fontSize),
          scale: Number(this.inspectorData.scale),
          trackId: Number(this.inspectorData.trackId) || 1,
          action: 'update'
        } as any]
     }).subscribe({
        next: () => {
           this.loadEdl();
        },
        error: (err) => console.error('Katman kaydedilemedi:', err)
     });
  }

  cancelInspector(): void {
     this.selectedOverlayId.set(null);
     this.loadEdl();
  }

  setPrompt(p: string): void {
    this.userPrompt = p;
  }

  sendChatMessage(): void {
    if (!this.userPrompt.trim() || this.chatLoading()) return;

    let msgText = this.userPrompt.trim();
    
    const selIds = this.selectedClipIds();
    if (selIds.length > 0) {
       const selectedClips = this.clips().filter(c => selIds.includes(c.id)).sort((a,b) => a.start - b.start);
       if (selectedClips.length > 0) {
          const startRange = selectedClips[0].start;
          const endRange = selectedClips[selectedClips.length - 1].end;
          msgText = `[Seçili Aralık: ${startRange.toFixed(1)}s - ${endRange.toFixed(1)}s] ` + msgText;
       }
    }

    this.userPrompt = '';

    this.chatMessages.update(msgs => [
      ...msgs,
      {
        projectId: this.projectId,
        rol: 'user',
        mesaj: msgText,
        olusturulmaZamani: new Date().toISOString()
      }
    ]);

    this.chatLoading.set(true);

    this.chatService.sendMessage(this.projectId, msgText).subscribe({
      next: (res) => {
        this.chatLoading.set(false);
        this.chatMessages.update(msgs => [
          ...msgs,
          {
            projectId: this.projectId,
            rol: 'assistant',
            mesaj: res.mesaj,
            olusturulmaZamani: new Date().toISOString(),
            edlPatch: res.edlPatch,
            pendingEdlPatch: res.pendingEdlPatch,
            patchDurumu: res.patchDurumu,
            intent: res.intent,
            formFields: res.formFields,
            id: res.id
          }
        ]);
        this.loadEdl();
      },
      error: (err) => {
        this.chatLoading.set(false);
        alert('AI yanıt verirken hata oluştu: ' + (err.error?.detail || err.message));
      }
    });
  }

  // --- FAZ 1: METİN STÜDYOSU & PHOTOSHOP TİPOGRAFİ METOTLARI ---
  getFontsByCategory(category: string): FontOption[] {
    return this.studioEngine.fonts.filter(f => f.category === category);
  }

  applyTextPreset(preset: TextTemplatePreset): void {
    if (!this.inspectorData) return;
    const p = preset.props;
    Object.assign(this.inspectorData, {
      font: p.font ?? this.inspectorData.font,
      fontSize: p.fontSize ?? this.inspectorData.fontSize,
      fontWeight: p.fontWeight ?? '900',
      color: p.color ?? '#FFFFFF',
      fillType: p.fillType ?? 'solid',
      gradientStart: p.gradientStart ?? '#FACC15',
      gradientEnd: p.gradientEnd ?? '#EF4444',
      gradientAngle: p.gradientAngle ?? 90,
      strokeColor: p.strokeColor ?? '#000000',
      strokeWidth: p.strokeWidth ?? 0,
      outerStrokeColor: p.outerStrokeColor ?? '#EF4444',
      outerStrokeWidth: p.outerStrokeWidth ?? 0,
      glowEnabled: p.glowEnabled ?? false,
      glowColor: p.glowColor ?? '#22D3EE',
      glowRadius: p.glowRadius ?? 18,
      shadowColor: p.shadowColor ?? 'rgba(0,0,0,0.85)',
      shadowBlur: p.shadowBlur ?? 4,
      shadowDistance: p.shadowDistance ?? 4,
      shadowAngle: p.shadowAngle ?? 45,
      boxStyle: p.boxStyle ?? 'none',
      boxBgColor: p.boxBgColor ?? '#1E293B',
      boxPadding: p.boxPadding ?? 14,
      borderRadius: p.borderRadius ?? 20,
      allCaps: p.allCaps ?? false,
      letterSpacing: p.letterSpacing ?? 0,
      curveBend: p.curveBend ?? 0,
      rotateX: p.rotateX ?? 0,
      rotateY: p.rotateY ?? 0,
      skewX: p.skewX ?? 0,
      animation: p.animation ?? this.inspectorData.animation,
      loopAnimation: p.loopAnimation ?? 'none'
    });
    this.onInspectorChange();
  }

  getCurvedTextPath(bend: number): string {
    const clamped = Math.max(-100, Math.min(100, bend || 0));
    const ctrlY = 90 - (clamped * 0.75);
    return `M 20,90 Q 250,${ctrlY.toFixed(1)} 480,90`;
  }

  getTextOverlayStyle(ov: OverlayItem): any {
    const scale = ov.scale || 1;
    const fSize = Math.max(12, ((ov.fontSize || 48) * 0.45) * scale);
    const angleRad = ((ov.shadowAngle ?? 45) * Math.PI) / 180;
    const dist = ov.shadowDistance ?? 4;
    const dx = Math.round(Math.cos(angleRad) * dist);
    const dy = Math.round(Math.sin(angleRad) * dist);
    const blur = ov.shadowBlur ?? 2;
    const sColor = ov.shadowColor || 'rgba(0,0,0,0.85)';

    const shadows: string[] = [];
    if (blur > 0 || dist > 0) {
      shadows.push(`${dx}px ${dy}px ${blur}px ${sColor}`);
    }
    if (ov.glowEnabled) {
      const gCol = ov.glowColor || '#22D3EE';
      const gRad = ov.glowRadius || 18;
      shadows.push(`0 0 ${Math.round(gRad * 0.5)}px ${gCol}`, `0 0 ${gRad}px ${gCol}`);
    }

    const isBox = ov.boxStyle && ov.boxStyle !== 'none';
    const isGrad = ov.fillType === 'gradient' || ov.fillType === 'radial';
    const gradBg = ov.fillType === 'radial'
      ? `radial-gradient(circle, ${ov.gradientStart || '#FACC15'}, ${ov.gradientEnd || '#EF4444'})`
      : `linear-gradient(${ov.gradientAngle ?? 90}deg, ${ov.gradientStart || '#FACC15'}, ${ov.gradientEnd || '#EF4444'})`;

    const style: any = {
      'font-size.px': fSize,
      'font-family': ov.font || 'Inter',
      'font-weight': ov.fontWeight || '900',
      'line-height': ov.lineHeight || 1.2,
      'text-align': ov.textAlign || 'center',
      'text-transform': ov.allCaps ? 'uppercase' : 'none',
      'letter-spacing.px': ov.letterSpacing || 0,
      'paint-order': 'stroke fill',
      '-webkit-text-stroke': ov.strokeWidth ? `${(ov.strokeWidth * 0.45).toFixed(1)}px ${ov.strokeColor || '#000'}` : 'none',
      'text-shadow': shadows.length > 0 ? shadows.join(', ') : 'none'
    };

    if (isGrad && !isBox) {
      style['background-image'] = gradBg;
      style['-webkit-background-clip'] = 'text';
      style['background-clip'] = 'text';
      style['color'] = 'transparent';
    } else {
      style['color'] = ov.color || '#FFFFFF';
    }

    if (isBox) {
      style['background-color'] = ov.boxBgColor || '#1E293B';
      style['padding'] = ov.boxStyle === 'highlight-marker'
        ? '4px 14px'
        : `${(ov.boxPadding || 14) * 0.45}px ${(ov.boxPadding || 14) * 0.9}px`;
      style['border-radius'] = ov.boxStyle === 'pill'
        ? '9999px'
        : (ov.boxStyle === 'rounded' ? `${ov.borderRadius || 16}px` : '4px');
      if (ov.boxStyle === 'highlight-marker') {
        style['transform'] = 'skewX(-8deg)';
      }
    }

    return style;
  }

  getTextOverlayFilter(ov: OverlayItem): string {
    const filters: string[] = [];
    if (ov.outerStrokeWidth && ov.outerStrokeWidth > 0) {
      const w = Math.max(1, Math.round(ov.outerStrokeWidth * 0.45));
      const c = ov.outerStrokeColor || '#EF4444';
      filters.push(
        `drop-shadow(${w}px 0 0 ${c})`,
        `drop-shadow(-${w}px 0 0 ${c})`,
        `drop-shadow(0 ${w}px 0 ${c})`,
        `drop-shadow(0 -${w}px 0 ${c})`
      );
    }
    return filters.length > 0 ? filters.join(' ') : 'none';
  }

  getOverlay3DTransform(ov: OverlayItem): string {
    const parts: string[] = [];
    if (ov.rotateX || ov.rotateY) {
      parts.push('perspective(600px)');
    }
    if (ov.rotation) parts.push(`rotate(${ov.rotation}deg)`);
    if (ov.rotateX) parts.push(`rotateX(${ov.rotateX}deg)`);
    if (ov.rotateY) parts.push(`rotateY(${ov.rotateY}deg)`);
    if (ov.skewX || ov.skewY) parts.push(`skew(${ov.skewX || 0}deg, ${ov.skewY || 0}deg)`);
    if (ov.flipH) parts.push('scaleX(-1)');
    if (ov.flipV) parts.push('scaleY(-1)');
    return parts.length > 0 ? parts.join(' ') : 'none';
  }

  // --- FAZ 2: PHOTOSHOP GÖRSEL DÜZENLEME & CANLI REMBG AI STICKER METOTLARI ---
  getImageOverlayFilter(ov: OverlayItem): string {
    const filters: string[] = [];
    // Gerçek Silüet Sticker Konturu (SVG feMorphology dilate filtresi)
    if (ov.stickerBorder) {
      filters.push(`url(#sticker-outline-${ov.id})`);
    }
    if (ov.brightness) {
      filters.push(`brightness(${Math.max(0.1, 1 + ov.brightness / 100).toFixed(2)})`);
    }
    if (ov.contrast) {
      filters.push(`contrast(${Math.max(0.1, 1 + ov.contrast / 100).toFixed(2)})`);
    }
    if (ov.saturation) {
      filters.push(`saturate(${Math.max(0, 1 + ov.saturation / 100).toFixed(2)})`);
    }
    if (ov.warmth && ov.warmth > 0) {
      filters.push(`sepia(${(ov.warmth / 160).toFixed(2)})`);
    }
    if (ov.hue) {
      filters.push(`hue-rotate(${ov.hue}deg)`);
    }
    if (ov.blur && ov.blur > 0) {
      filters.push(`blur(${ov.blur}px)`);
    }
    if (ov.dropShadow) {
      filters.push(`drop-shadow(0 8px 16px rgba(0,0,0,0.65))`);
    }
    return filters.length > 0 ? filters.join(' ') : 'none';
  }

  getImageClipPath(ov: OverlayItem): string {
    const shape = ov.maskShape || 'rect';
    if (shape === 'circle') return 'circle(50% at 50% 50%)';
    if (shape === 'diamond') return 'polygon(50% 0%, 100% 50%, 50% 100%, 0% 50%)';
    if (shape === 'hexagon') return 'polygon(25% 5%, 75% 5%, 100% 50%, 75% 95%, 25% 95%, 0% 50%)';
    if (shape === 'star') return 'polygon(50% 0%, 61% 35%, 98% 35%, 68% 57%, 79% 91%, 50% 70%, 21% 91%, 32% 57%, 2% 35%, 39% 35%)';
    if (shape === 'heart') return 'polygon(50% 20%, 65% 5%, 85% 5%, 100% 25%, 100% 50%, 50% 95%, 0% 50%, 0% 25%, 15% 5%, 35% 5%)';
    return 'none';
  }

  async removeBackgroundNow(): Promise<void> {
    if (!this.inspectorData || !this.inspectorData.source) return;
    this.bgRemovalProcessing.set(true);
    try {
      const origUrl = this.inspectorData.originalSource || this.inspectorData.source;
      this.inspectorData.originalSource = origUrl;
      const transparentDataUrl = await this.studioEngine.removeImageBackgroundInstant(
        origUrl,
        this.inspectorData.chromaKeyColor || undefined
      );
      this.inspectorData.source = transparentDataUrl;
      this.inspectorData.removeBg = true;
      this.inspectorData.stickerBorder = true;
      this.onInspectorChange();
      this.saveInspector();
    } catch (err) {
      console.error('Canlı arka plan kaldırma hatası:', err);
    } finally {
      this.bgRemovalProcessing.set(false);
    }
  }

  restoreOriginalBackground(): void {
    if (!this.inspectorData || !this.inspectorData.originalSource) return;
    this.inspectorData.source = this.inspectorData.originalSource;
    this.inspectorData.removeBg = false;
    this.onInspectorChange();
    this.saveInspector();
  }

  resetImageAdjustments(): void {
    if (!this.inspectorData) return;
    Object.assign(this.inspectorData, {
      brightness: 0,
      contrast: 0,
      saturation: 0,
      warmth: 0,
      hue: 0,
      blur: 0,
      sharpen: 0,
      opacity: 100,
      flipH: false,
      flipV: false,
      blendMode: 'normal',
      dropShadow: false,
      feather: 0
    });
    this.onInspectorChange();
  }

  // --- FAZ 3: SES EFEKTLERİ (SFX), CANLI BGM & -14 LUFS METOTLARI ---
  previewSfxItem(sfx: SfxLibraryItem, event?: MouseEvent): void {
    event?.stopPropagation();
    this.studioEngine.playSynthesizedSfx(sfx.id, 0.85);
  }

  previewSfxClip(sfx: EdlSfxClip): void {
    this.studioEngine.playSynthesizedSfx(sfx.presetId || sfx.synthPreset || 'whoosh-fast', sfx.volume ?? 0.85);
    if (this.videoRef?.nativeElement) {
      this.videoRef.nativeElement.currentTime = sfx.start;
      this.currentTime.set(sfx.start);
    }
  }

  addSfxToTimeline(sfx: SfxLibraryItem): void {
    const start = parseFloat(this.currentTime().toFixed(2));
    const wavDataUri = this.studioEngine.generateSfxWavDataUri(sfx.id, sfx.duration);
    const newClip: EdlSfxClip = {
      id: `sfx_${Date.now()}`,
      name: sfx.name,
      title: sfx.name,
      category: sfx.category,
      presetId: sfx.id,
      synthPreset: sfx.synthPreset || sfx.id,
      sourceUrl: wavDataUri,
      start,
      duration: sfx.duration,
      volume: 0.85,
      action: 'add'
    };

    // Anında sesli geri bildirim ver
    this.studioEngine.playSynthesizedSfx(sfx.id, 0.85);

    this.edlService.patchEdl(this.projectId, {
      sfxClips: [newClip]
    }).subscribe(() => this.loadEdl());
  }

  removeSfxClip(sfxId: string, event?: MouseEvent): void {
    event?.stopPropagation();
    this.edlService.patchEdl(this.projectId, {
      sfxClips: [{ id: sfxId, name: '', start: 0, duration: 0, action: 'remove' }]
    }).subscribe(() => this.loadEdl());
  }

  getSfxClipStyle(sfx: EdlSfxClip): any {
    const totalDur = Math.max(1, this.totalDuration());
    const start = sfx.start || 0;
    const dur = Math.max(0.3, sfx.duration || 1.0);
    if (!this.isAnyRippleActive()) {
      return {
        left: `${(start / totalDur) * 100}%`,
        width: `${Math.max(0.8, (dur / totalDur) * 100)}%`
      };
    }
    const startVis = this.getVisTimeFromRawTime(start);
    const endVis = this.getVisTimeFromRawTime(start + dur);
    const visDur = Math.max(0.1, this.visibleDuration());
    return {
      left: `${(startVis / visDur) * 100}%`,
      width: `${Math.max(0.8, ((endVis - startVis) / visDur) * 100)}%`
    };
  }

  toggleNormalizeAudio(enabled: boolean): void {
    this.edlService.patchEdl(this.projectId, {
      settings: { normalizeAudio: enabled }
    }).subscribe(() => this.loadEdl());
  }

  toggleSmartPunchIn(enabled: boolean): void {
    this.edlService.patchEdl(this.projectId, {
      settings: { smartPunchIn: enabled }
    }).subscribe(() => this.loadEdl());
  }

  // --- FAZ 4: SAHNE GEÇİŞ EFEKTLERİ (XFADE TRANSITIONS) METOTLARI ---
  getTransitionAtBoundary(boundaryTime: number): EdlTransition | undefined {
    return this.transitions().find(tr => Math.abs(((tr.boundaryTime ?? tr.boundarySourceTime) || 0) - boundaryTime) < 0.25);
  }

  openTransitionModal(clipOrBound: any, event?: MouseEvent): void {
    event?.stopPropagation();
    const bTime = clipOrBound.boundaryTime ?? clipOrBound.end ?? 0;
    const existing = this.getTransitionAtBoundary(bTime);
    this.activeTransitionBoundary.set(clipOrBound);
    this.editingTransitionBoundaryTime.set(parseFloat(Number(bTime).toFixed(2)));
    this.editingTransitionType.set(existing?.type || 'fade');
    this.editingTransitionDuration.set(existing?.duration || 0.5);
    this.transitionModalOpen.set(true);
  }

  openTransitionModalForSelectedClip(): void {
    const selIds = this.selectedClipIds();
    if (!selIds.length) return;
    const clip = this.clips().find(c => c.id === selIds[0]);
    if (!clip) return;
    const existing = this.getTransitionAtBoundary(clip.end);
    this.editingTransitionBoundaryTime.set(parseFloat(clip.end.toFixed(2)));
    this.editingTransitionType.set(existing?.type || 'fade');
    this.editingTransitionDuration.set(existing?.duration || 0.5);
    this.transitionModalOpen.set(true);
  }

  saveCurrentTransition(): void {
    const bTime = this.editingTransitionBoundaryTime();
    const existing = this.getTransitionAtBoundary(bTime);
    const trObj: EdlTransition = {
      id: existing?.id || `tr_${Date.now()}`,
      boundaryTime: bTime,
      boundarySourceTime: bTime,
      type: this.editingTransitionType(),
      duration: this.editingTransitionDuration(),
      action: existing ? 'update' : 'add'
    };
    this.edlService.patchEdl(this.projectId, {
      transitions: [trObj]
    }).subscribe(() => {
      this.transitionModalOpen.set(false);
      this.loadEdl();
    });
  }

  applyTransitionToAllCuts(): void {
    const allClips = this.clips();
    const patches: EdlTransition[] = [];
    for (let i = 0; i < allClips.length - 1; i++) {
      const bTime = parseFloat(allClips[i].end.toFixed(2));
      const existing = this.getTransitionAtBoundary(bTime);
      patches.push({
        id: existing?.id || `tr_all_${Date.now()}_${i}`,
        boundaryTime: bTime,
        boundarySourceTime: bTime,
        type: this.editingTransitionType(),
        duration: this.editingTransitionDuration(),
        action: existing ? 'update' : 'add'
      });
    }
    if (patches.length > 0) {
      this.edlService.patchEdl(this.projectId, { transitions: patches }).subscribe(() => {
        this.transitionModalOpen.set(false);
        this.loadEdl();
      });
    }
  }

  removeCurrentTransition(): void {
    const existing = this.getTransitionAtBoundary(this.editingTransitionBoundaryTime());
    if (!existing) {
      this.transitionModalOpen.set(false);
      return;
    }
    this.edlService.patchEdl(this.projectId, {
      transitions: [{ ...existing, action: 'remove' }]
    }).subscribe(() => {
      this.transitionModalOpen.set(false);
      this.loadEdl();
    });
  }

  setSelectedClipSpeed(speed: number): void {
    const selIds = this.selectedClipIds();
    if (!selIds.length) return;
    const map = { ...this.clipSpeedMap() };
    for (const id of selIds) {
      map[id] = speed;
    }
    this.clipSpeedMap.set(map);
    if (this.videoRef?.nativeElement) {
      this.videoRef.nativeElement.playbackRate = speed;
    }
  }

  // --- FAZ 5: STICKER, GIF & KEYFRAME METOTLARI ---
  addStickerOverlay(sticker: StickerLibraryItem): void {
    this.addImageOverlayFromUrl(sticker.dataUrl || sticker.dataUri || '', sticker.name);
  }

  addCustomGifFromInput(): void {
    const url = this.customGifUrl.trim();
    if (!url) return;
    this.addImageOverlayFromUrl(url, 'Hareketli GIF');
    this.customGifUrl = '';
  }

  addKeyFrameToSelectedOverlay(): void {
    if (!this.inspectorData) return;
    const relTime = Math.max(0, parseFloat((this.currentTime() - (this.inspectorData.timestamp || 0)).toFixed(2)));
    const kfList: OverlayKeyframe[] = [...(this.inspectorData.keyframes || [])];
    kfList.push({
      id: `kf_${Date.now()}`,
      timeOffset: relTime,
      x: Number(this.inspectorData.positionX ?? 50),
      y: Number(this.inspectorData.positionY ?? 50),
      scale: Number(this.inspectorData.scale ?? 1),
      rotation: Number(this.inspectorData.rotation ?? 0),
      opacity: Number(this.inspectorData.opacity ?? 100)
    });
    kfList.sort((a, b) => a.timeOffset - b.timeOffset);
    this.inspectorData.keyframes = kfList;
    this.onInspectorChange();
  }

  removeKeyframeFromSelectedOverlay(index: number): void {
    if (!this.inspectorData || !this.inspectorData.keyframes) return;
    this.inspectorData.keyframes.splice(index, 1);
    this.onInspectorChange();
  }

  // --- FAZ 6: OTONOM VİDEO YÖNETMENİ (PROAKTİF AI ÖNERİLERİ [E1]) ---
  generateAiDirectorSuggestions(): void {
    const edl = this.activeEdl();
    if (!edl) return;
    const generated = this.studioEngine.generateProactiveSuggestions(edl, this.totalDuration());
    if (generated.length === 0) return;

    this.edlService.patchEdl(this.projectId, {
      suggestions: generated.map((s: SuggestionItem) => ({ ...s, action: 'add' as const }))
    }).subscribe(() => this.loadEdl());
  }

  previewSuggestion(sug: SuggestionItem): void {
    if (this.videoRef?.nativeElement) {
      this.videoRef.nativeElement.currentTime = Math.max(0, sug.timestamp);
      this.currentTime.set(Math.max(0, sug.timestamp));
    }
    const sfxId = sug.sfxPreset || sug.sfxPayload?.presetId;
    if (sfxId) {
      this.studioEngine.playSynthesizedSfx(sfxId, sug.sfxPayload?.volume ?? 0.85);
    }
  }

  acceptSuggestion(sug: SuggestionItem): void {
    const patch: EdlPatchDto = {
      suggestions: [{ ...sug, status: 'accepted', action: 'update' }]
    };

    const sType = String(sug.type || '');
    const presetKey = sug.templatePreset || sug.presetId;

    // 1. Eğer öneri bir metin şablonu veya sticker/görsel içeriyorsa:
    if (
      sType === 'viral_hook' ||
      sType === 'text_highlight' ||
      sType === 'text_template' ||
      sType === 'text_overlay' ||
      sType === 'sticker_callout' ||
      sType === 'sticker' ||
      sType === 'image_broll'
    ) {
      const preset = this.studioEngine.textPresets.find((p: TextTemplatePreset) => p.id === presetKey);
      const isImg = sType === 'image_broll' || sType === 'sticker' || sType === 'sticker_callout';
      const ov: OverlayItem = {
        id: `ov_${sug.id}`,
        type: isImg ? 'image' : 'text',
        content: sug.content,
        source: sug.sourceUrl,
        timestamp: sug.timestamp,
        duration: sug.duration || 3.5,
        positionX: 50,
        positionY: isImg ? 82 : 78,
        scale: 1.0,
        stickerBorder: sType === 'sticker_callout',
        stickerBorderWidth: 6,
        stickerBorderColor: '#FFFFFF',
        ...(preset?.props || {}),
        ...(sug.overlayPayload || {}),
        action: 'add'
      };
      patch.overlays = [ov];
    }

    // 2. Eğer öneri bir sahne geçişi (Transition) içeriyorsa:
    if (sug.transitionPayload || sug.transitionType) {
      const bTime = sug.transitionPayload?.boundaryTime ?? sug.transitionPayload?.boundarySourceTime ?? sug.timestamp;
      patch.transitions = [{
        id: sug.transitionPayload?.id || `tr_${sug.id}`,
        boundaryTime: bTime,
        boundarySourceTime: bTime,
        type: sug.transitionPayload?.type || sug.transitionType || 'slideleft',
        duration: sug.transitionPayload?.duration || sug.duration || 0.45,
        action: 'add'
      }];
    }

    // 3. Eğer öneri bir ses efekti (SFX) içeriyorsa:
    const sfxPreset = sug.sfxPreset || sug.sfxPayload?.presetId;
    if (sfxPreset || sug.sfxPayload) {
      const pId = sfxPreset || 'whoosh-fast';
      const sfxLibItem = this.studioEngine.sfxLibrary.find(x => x.id === pId);
      const wavUri = this.studioEngine.generateSfxWavDataUri(pId, sfxLibItem?.duration || 0.8);
      patch.sfxClips = [{
        id: sug.sfxPayload?.id || `sfx_${sug.id}`,
        name: sug.sfxPayload?.name || sfxLibItem?.name || 'Stüdyo SFX',
        title: sug.sfxPayload?.name || sfxLibItem?.name || 'Stüdyo SFX',
        category: sug.sfxPayload?.category || sfxLibItem?.category || 'whoosh',
        presetId: pId,
        synthPreset: pId,
        sourceUrl: wavUri,
        start: sug.sfxPayload?.start ?? sug.timestamp,
        duration: sug.sfxPayload?.duration ?? sfxLibItem?.duration ?? 0.8,
        volume: 0.85,
        action: 'add'
      }];
      this.studioEngine.playSynthesizedSfx(pId, 0.85);
    }

    // 4. Eğer öneri ses dengeleme + Smart Punch-In içeriyorsa:
    if (sType === 'audio_master' || sType === 'audio_enhance' || sType === 'smart_zoom') {
      this.normalizeAudio.set(true);
      this.smartPunchIn.set(true);
      patch.settings = {
        normalizeAudio: true,
        smartPunchIn: true
      };
    }

    this.edlService.patchEdl(this.projectId, patch).subscribe(() => this.loadEdl());
  }

  rejectSuggestion(sug: SuggestionItem): void {
    this.edlService.patchEdl(this.projectId, {
      suggestions: [{ ...sug, status: 'rejected', action: 'update' }]
    }).subscribe(() => this.loadEdl());
  }

  removeOverlay(overlayId: string): void {
    this.edlService.patchEdl(this.projectId, {
      overlays: [{ id: overlayId, timestamp: 0, duration: 0, type: 'text', action: 'remove' }]
    }).subscribe(() => this.loadEdl());
  }

  requestExport(): void {
    this.rendering.set(true);
    const isSubActive = this.showSubtitles();
    // Render öncesi güncel altyazı tercihini EDL'e garantile
    this.edlService.patchEdl(this.projectId, {
      settings: { subtitlesEnabled: isSubActive }
    }).subscribe({
      next: () => {
        this.renderService.requestRender(this.projectId).subscribe({
          next: (res) => {
            this.rendering.set(false);
            this.router.navigate(['/project', this.projectId, 'render', res.renderJobId]);
          },
          error: (err) => {
            this.rendering.set(false);
            alert('Render talebi başlatılamadı: ' + (err.error?.detail || err.message));
          }
        });
      },
      error: () => {
        this.renderService.requestRender(this.projectId).subscribe({
          next: (res) => {
            this.rendering.set(false);
            this.router.navigate(['/project', this.projectId, 'render', res.renderJobId]);
          },
          error: (err) => {
            this.rendering.set(false);
            alert('Render talebi başlatılamadı: ' + (err.error?.detail || err.message));
          }
        });
      }
    });
  }

  previewPatch(msg: ChatMessageDto): void {
    if (!msg.pendingEdlPatch) return;
    if (this.previewMessageId() === msg.id) {
       this.previewEdl.set(null);
       this.previewMessageId.set(null);
       return;
    }

    const currentEdlStr = JSON.stringify(this.edl());
    if (!currentEdlStr) return;
    const simulated = JSON.parse(currentEdlStr) as EdlContent;
    
    const patch = msg.pendingEdlPatch;
    
    if (patch.cuts) {
       simulated.cuts = simulated.cuts || [];
       for (const c of patch.cuts) {
          if (c.action === 'add') simulated.cuts.push(c as any);
          if (c.action === 'remove') simulated.cuts = simulated.cuts.filter(x => x.id !== c.id);
       }
    }
    if (patch.overlays) {
       simulated.overlays = simulated.overlays || [];
       for (const o of patch.overlays) {
          if (o.action === 'add') simulated.overlays.push(o as any);
          if (o.action === 'remove') simulated.overlays = simulated.overlays.filter(x => x.id !== o.id);
       }
    }

    this.previewEdl.set(simulated);
    this.previewMessageId.set(msg.id || null);
    
    if (this.videoRef?.nativeElement) {
      let seekTo = 0;
      if (patch.cuts && patch.cuts.length > 0) {
        seekTo = Math.max(0, patch.cuts[0].start - 2);
      } else if (patch.overlays && patch.overlays.length > 0) {
        seekTo = Math.max(0, patch.overlays[0].timestamp - 2);
      }
      if (seekTo > 0) this.videoRef.nativeElement.currentTime = seekTo;
      this.videoRef.nativeElement.play();
    }
  }

  applyPatch(msg: ChatMessageDto): void {
    if (!msg.id) return;
    this.previewEdl.set(null);
    this.previewMessageId.set(null);
    this.chatService.applyPendingPatch(this.projectId, msg.id).subscribe({
      next: () => {
        msg.patchDurumu = 'applied';
        this.loadEdl();
      },
      error: (err) => alert('Patch uygulanamadı: ' + err.message)
    });
  }

  cancelPatch(msg: ChatMessageDto): void {
    msg.patchDurumu = 'rejected';
    if (this.previewMessageId() === msg.id) {
       this.previewEdl.set(null);
       this.previewMessageId.set(null);
    }
  }

  // --- Dynamic Clarification Form & 16:9 Stage Methods ---
  readonly colorPalette = [
    '#FFFFFF',
    '#FACC15',
    '#06B6D4',
    '#EF4444',
    '#10B981',
    '#8B5CF6',
    '#F97316',
    '#EC4899',
    '#000000'
  ];

  getMarkerPosition(msg: ChatMessageDto, field: FormFieldDto): { x: number; y: number } {
     const data = msg.formData || {};
     if (data['positionX'] !== undefined && data['positionY'] !== undefined) {
        return { x: Number(data['positionX']), y: Number(data['positionY']) };
     }
     const posVal = data[field.id] || field.defaultValue || 'bottom-center';
     return this.getPresetCoords(String(posVal));
  }

  onMiniStageClick(event: MouseEvent, msg: ChatMessageDto, fieldId: string): void {
     const rect = (event.currentTarget as HTMLElement).getBoundingClientRect();
     const x = Math.round(((event.clientX - rect.left) / rect.width) * 100);
     const y = Math.round(((event.clientY - rect.top) / rect.height) * 100);
     
     msg.formData = msg.formData || {};
     msg.formData['positionX'] = x;
     msg.formData['positionY'] = y;
     msg.formData[fieldId] = 'custom';
  }

  setPresetPosition(msg: ChatMessageDto, fieldId: string, preset: string): void {
     msg.formData = msg.formData || {};
     const coords = this.getPresetCoords(preset);
     msg.formData['positionX'] = coords.x;
     msg.formData['positionY'] = coords.y;
     msg.formData[fieldId] = preset;
  }

  getPresetCoords(preset: string): { x: number; y: number } {
     switch (preset) {
        case 'top-left': return { x: 15, y: 15 };
        case 'top-center': return { x: 50, y: 15 };
        case 'top-right': return { x: 85, y: 15 };
        case 'center-left': return { x: 15, y: 50 };
        case 'center': return { x: 50, y: 50 };
        case 'center-right': return { x: 85, y: 50 };
        case 'bottom-left': return { x: 15, y: 85 };
        case 'bottom-center': return { x: 50, y: 85 };
        case 'bottom-right': return { x: 85, y: 85 };
        default: return { x: 50, y: 85 };
     }
  }

  updateFormData(msg: ChatMessageDto, fieldId: string, val: any): void {
     msg.formData = msg.formData || {};
     msg.formData[fieldId] = val;
  }

  getOptValue(opt: any): string {
     return typeof opt === 'string' ? opt : (opt.value || opt.label || '');
  }

  getOptLabel(opt: any): string {
     return typeof opt === 'string' ? opt : (opt.label || opt.value || '');
  }

  submitForm(msg: ChatMessageDto): void {
    if (!msg.formFields) return;
    
    const requiredEmpty = msg.formFields.some(f => f.required && !msg.formData?.[f.id]);
    if (requiredEmpty) {
       alert('Lütfen tüm zorunlu alanları doldurunuz.');
       return;
    }
    
    const params: { [key: string]: string } = {};
    for (const key of Object.keys(msg.formData || {})) {
       params[key] = String(msg.formData![key]);
    }
    
    this.chatLoading.set(true);
    this.chatService.submitForm(this.projectId, msg.id!, params).subscribe({
       next: (res: any) => {
          this.chatLoading.set(false);
          msg.patchDurumu = res.patchDurumu || 'applied';
          this.loadEdl();
       },
       error: (err: any) => {
          this.chatLoading.set(false);
          alert('Form gönderilemedi: ' + (err.error?.detail || err.message));
       }
    });
  }

  // --- TIMELINE & CANVAS DRAG & RESIZE ---
  onOverlayDragStart(event: MouseEvent, overlayId: string): void {
     event.stopPropagation();
     const ov = this.activeEdl()?.overlays?.find(o => o.id === overlayId);
     if (ov && this.isTrackLocked(Number(ov.trackId) || 1)) {
        return;
     }
     this.selectOverlay(overlayId);
     this.isDraggingOverlay = true;
     this.dragStartX = event.clientX;
     this.dragStartY = event.clientY;
     
     if (ov) {
        this.dragOverlayOriginalStart = ov.timestamp;
        this.dragOverlayOriginalDuration = ov.duration;
        this.dragOverlayOriginalTrack = Number(ov.trackId) || 1;
     }
  }

  onOverlayResizeStart(event: MouseEvent, overlayId: string, edge: 'left' | 'right'): void {
     event.stopPropagation();
     const ov = this.activeEdl()?.overlays?.find(o => o.id === overlayId);
     if (ov && this.isTrackLocked(Number(ov.trackId) || 1)) {
        return;
     }
     this.selectOverlay(overlayId);
     this.isResizingOverlay = true;
     this.resizeEdge = edge;
     this.dragStartX = event.clientX;
     
     if (ov) {
        this.dragOverlayOriginalStart = ov.timestamp;
        this.dragOverlayOriginalDuration = ov.duration;
     }
  }

  onCanvasResizeStart(event: MouseEvent, overlayId: string): void {
     event.preventDefault();
     event.stopPropagation();
     const ov = this.activeEdl()?.overlays?.find(o => o.id === overlayId);
     if (ov && this.isTrackLocked(Number(ov.trackId) || 1)) {
        return;
     }
     this.isCanvasResizing = true;
     this.canvasResizeOverlayId = overlayId;
     this.canvasResizeStartX = event.clientX;
     this.canvasResizeStartY = event.clientY;
     if (ov) {
        this.canvasResizeOriginalScale = ov.scale || 1.0;
        this.canvasResizeOriginalFontSize = ov.fontSize || 48;
     }


  }

  bringOverlayForward(overlayId: string): void {
    const overlays = this.activeEdl()?.overlays || [];
    const ov = overlays.find(o => o.id === overlayId);
    if (!ov) return;
    
    const newTrack = (Number(ov.trackId) || 1) + 1;
    ov.trackId = newTrack;
    if (this.inspectorData && this.inspectorData.id === overlayId) {
       this.inspectorData.trackId = newTrack;
    }
    
    this.edlService.patchEdl(this.projectId, {
       overlays: [{ id: ov.id, trackId: newTrack, action: 'update' } as any]
    }).subscribe(() => this.loadEdl());
  }

  sendOverlayBackward(overlayId: string): void {
    const overlays = this.activeEdl()?.overlays || [];
    const ov = overlays.find(o => o.id === overlayId);
    if (!ov) return;
    
    const newTrack = Math.max(1, (Number(ov.trackId) || 1) - 1);
    ov.trackId = newTrack;
    if (this.inspectorData && this.inspectorData.id === overlayId) {
       this.inspectorData.trackId = newTrack;
    }
    
    this.edlService.patchEdl(this.projectId, {
       overlays: [{ id: ov.id, trackId: newTrack, action: 'update' } as any]
    }).subscribe(() => this.loadEdl());
  }

  setOverlayTrack(overlayId: string, trackId: number): void {
    const overlays = this.activeEdl()?.overlays || [];
    const ov = overlays.find(o => o.id === overlayId);
    if (!ov) return;
    
    ov.trackId = trackId;
    if (this.inspectorData && this.inspectorData.id === overlayId) {
       this.inspectorData.trackId = trackId;
    }
    
    this.edlService.patchEdl(this.projectId, {
       overlays: [{ id: ov.id, trackId: trackId, action: 'update' } as any]
    }).subscribe(() => this.loadEdl());
  }

  getOverlaysForTrack(trackNum: number): OverlayItem[] {
    const overlays = this.activeEdl()?.overlays || [];
    return overlays.filter(o => (Number(o.trackId) || 1) === trackNum);
  }

  @HostListener('window:mousemove', ['$event'])
  onGlobalMouseMove(event: MouseEvent): void {
     if (this.isScrubbing) {
        this.handleScrubMouseMove(event.clientX);
        return;
     }

     if (this.isResizingTrack) {
        event.preventDefault();
        const delta = event.clientY - this.resizeStartY;
        const newHeight = Math.max(40, Math.min(400, this.resizeStartHeight + delta));
        this.audioTrackHeight.set(newHeight);
        return;
     }

     if (this.isCanvasDragging) {
         const video = this.videoRef?.nativeElement;
         if (!video) return;
         
         const rect = video.getBoundingClientRect();
         const deltaX = event.clientX - this.canvasDragStartX;
         const deltaY = event.clientY - this.canvasDragStartY;
         
         const deltaXPercent = (deltaX / rect.width) * 100;
         const deltaYPercent = (deltaY / rect.height) * 100;
         
         const ov = this.activeEdl()?.overlays?.find(o => o.id === this.canvasDragOverlayId);
         if (ov) {
             let newX = this.canvasDragOriginalX + deltaXPercent;
             let newY = this.canvasDragOriginalY + deltaYPercent;
             
             if (newX < 0) newX = 0; if (newX > 100) newX = 100;
             if (newY < 0) newY = 0; if (newY > 100) newY = 100;
             
             ov.positionX = newX;
             ov.positionY = newY;
             
             if (this.inspectorData && this.inspectorData.id === ov.id) {
                 this.inspectorData.positionX = parseFloat(newX.toFixed(2));
                 this.inspectorData.positionY = parseFloat(newY.toFixed(2));
             }
             this.edl.update(e => e ? { ...e, overlays: [...(e.overlays || [])] } : null);
         }
         return;
     }

     if (this.isCanvasResizing) {
         const deltaX = event.clientX - this.canvasResizeStartX;
         const deltaY = event.clientY - this.canvasResizeStartY;
         const delta = (deltaX + deltaY) / 2;

         const ov = this.activeEdl()?.overlays?.find(o => o.id === this.canvasResizeOverlayId);
         if (ov) {
             if (ov.type === 'image') {
                 let newScale = this.canvasResizeOriginalScale + (delta / 120);
                 if (newScale < 0.2) newScale = 0.2;
                 if (newScale > 5.0) newScale = 5.0;
                 ov.scale = parseFloat(newScale.toFixed(2));
                 if (this.inspectorData && this.inspectorData.id === ov.id) {
                     this.inspectorData.scale = ov.scale;
                 }
             } else if (ov.type === 'text') {
                 let newSize = this.canvasResizeOriginalFontSize + delta;
                 if (newSize < 10) newSize = 10;
                 if (newSize > 400) newSize = 400;
                 ov.fontSize = Math.round(newSize);
                 if (this.inspectorData && this.inspectorData.id === ov.id) {
                     this.inspectorData.fontSize = ov.fontSize;
                 }
             }
             this.edl.update(e => e ? { ...e, overlays: [...(e.overlays || [])] } : null);
         }
         return;
     }
     
     if (this.isDraggingSubtitle || this.isResizingSubtitle) {
        const seg = this.selectedSubtitle();
        if (!seg) return;

        const track = this.timelineTrackRef?.nativeElement;
        if (!track) return;
        const rect = track.getBoundingClientRect();
        const pixelsPerSec = rect.width / this.totalDuration();
        const deltaSec = (event.clientX - this.dragStartX) / pixelsPerSec;

        if (this.isDraggingSubtitle) {
           const dur = this.dragSubtitleOriginalEnd - this.dragSubtitleOriginalStart;
           let newStart = Math.max(0, this.dragSubtitleOriginalStart + deltaSec);
           let newEnd = newStart + dur;
           seg.start = parseFloat(newStart.toFixed(2));
           seg.end = parseFloat(newEnd.toFixed(2));
           this.subtitleInspectorData.start = seg.start;
           this.subtitleInspectorData.end = seg.end;
        } else if (this.isResizingSubtitle) {
           if (this.subtitleResizeEdge === 'left') {
              let newStart = Math.max(0, Math.min(this.dragSubtitleOriginalEnd - 0.2, this.dragSubtitleOriginalStart + deltaSec));
              seg.start = parseFloat(newStart.toFixed(2));
              this.subtitleInspectorData.start = seg.start;
              this.subtitleInspectorData.duration = parseFloat((seg.end - seg.start).toFixed(2));
           } else {
              let newEnd = Math.max(this.dragSubtitleOriginalStart + 0.2, this.dragSubtitleOriginalEnd + deltaSec);
              seg.end = parseFloat(newEnd.toFixed(2));
              this.subtitleInspectorData.end = seg.end;
              this.subtitleInspectorData.duration = parseFloat((seg.end - seg.start).toFixed(2));
           }
        }
        return;
     }

     if (!this.isDraggingOverlay && !this.isResizingOverlay) return;
     
     const ovId = this.selectedOverlayId();
     if (!ovId) return;
     
     const overlays = this.activeEdl()?.overlays || [];
     const ov = overlays.find(o => o.id === ovId);
     if (!ov) return;
     
     if (this.isDraggingOverlay) {
        if (!this.isAnyRippleActive()) {
           const track = this.timelineTrackRef?.nativeElement;
           if (!track) return;
           const rect = track.getBoundingClientRect();
           const pixelsPerSec = rect.width / this.totalDuration();
           const deltaSec = (event.clientX - this.dragStartX) / pixelsPerSec;
           let newStart = Math.max(0, this.dragOverlayOriginalStart + deltaSec);
           ov.timestamp = parseFloat(newStart.toFixed(2));
        } else {
           const startVis = this.getVisTimeFromRawTime(this.dragOverlayOriginalStart);
           const currentMouseRaw = this.getTimeAtClientX(event.clientX);
           const startMouseRaw = this.getTimeAtClientX(this.dragStartX);
           const deltaVis = this.getVisTimeFromRawTime(currentMouseRaw) - this.getVisTimeFromRawTime(startMouseRaw);
           const newVis = Math.max(0, startVis + deltaVis);
           const newStart = this.getRawTimeFromVisTime(newVis);
           ov.timestamp = parseFloat(newStart.toFixed(2));
        }
        
        const deltaTrack = Math.round((this.dragStartY - event.clientY) / 40);
        const newTrack = Math.max(1, this.dragOverlayOriginalTrack + deltaTrack);
        if (ov.trackId !== newTrack) {
           ov.trackId = newTrack;
        }

        if (this.inspectorData && this.inspectorData.id === ovId) {
            this.inspectorData.timestamp = ov.timestamp;
            this.inspectorData.trackId = ov.trackId;
        }
     } else if (this.isResizingOverlay) {
        const mouseRawTime = this.getTimeAtClientX(event.clientX);
        
        if (this.resizeEdge === 'left') {
           const originalEnd = this.dragOverlayOriginalStart + this.dragOverlayOriginalDuration;
           let newStart = Math.max(0, mouseRawTime);
           if (newStart >= originalEnd - 0.3) {
              newStart = originalEnd - 0.3;
           }
           const newDuration = originalEnd - newStart;
           ov.timestamp = parseFloat(newStart.toFixed(2));
           ov.duration = parseFloat(newDuration.toFixed(2));
           
           if (this.inspectorData && this.inspectorData.id === ovId) {
              this.inspectorData.timestamp = ov.timestamp;
              this.inspectorData.duration = ov.duration;
           }
        } else if (this.resizeEdge === 'right') {
           const newEnd = mouseRawTime;
           const newDuration = Math.max(0.3, newEnd - ov.timestamp);
           ov.duration = parseFloat(newDuration.toFixed(2));
           
           if (this.inspectorData && this.inspectorData.id === ovId) {
              this.inspectorData.duration = ov.duration;
           }
        }
     }
  }

  @HostListener('window:mouseup', ['$event'])
  onGlobalMouseUp(event: MouseEvent): void {
     if (this.isScrubbing) {
        this.handleScrubMouseUp();
     }

     if (this.isResizingTrack) {
        this.isResizingTrack = false;
     }

     if (this.isCanvasDragging) {
         this.isCanvasDragging = false;
         const ovId = this.canvasDragOverlayId;
         this.canvasDragOverlayId = null;
         
         const moved = Math.abs(event.clientX - this.canvasDragStartX) > 2 || 
                       Math.abs(event.clientY - this.canvasDragStartY) > 2;
                       
         if (ovId && moved) {
             const ov = this.activeEdl()?.overlays?.find(o => o.id === ovId);
             if (ov) {
                 this.edlService.patchEdl(this.projectId, {
                     overlays: [{ ...ov, action: 'update' } as any]
                 }).subscribe(() => this.loadEdl());
             }
         }
         return;
     }
     
     if (this.isCanvasResizing) {
         this.isCanvasResizing = false;
         const ovId = this.canvasResizeOverlayId;
         this.canvasResizeOverlayId = null;
         if (ovId) {
            const ov = this.activeEdl()?.overlays?.find(o => o.id === ovId);
            if (ov) {
                this.edlService.patchEdl(this.projectId, {
                    overlays: [{ ...ov, action: 'update' } as any]
                }).subscribe(() => this.loadEdl());
            }
         }
         return;
     }
     
     if (this.isDraggingSubtitle || this.isResizingSubtitle) {
         this.isDraggingSubtitle = false;
         this.isResizingSubtitle = false;
         this.subtitleResizeEdge = null;

         const edl = this.activeEdl();
         if (edl?.transcript) {
            this.edlService.patchEdl(this.projectId, {
               transcript: edl.transcript
            } as any).subscribe(() => {
               this.loadEdl();
            });
         }
         return;
     }

     if (this.isDraggingOverlay || this.isResizingOverlay) {
         this.isDraggingOverlay = false;
         this.isResizingOverlay = false;
         this.resizeEdge = null;
         
         const ovId = this.selectedOverlayId();
         if (ovId) {
            const ov = this.activeEdl()?.overlays?.find(o => o.id === ovId);
            if (ov) {
               this.edlService.patchEdl(this.projectId, {
                  overlays: [{ ...ov, action: 'update' } as any]
               }).subscribe(() => {
                  this.loadEdl();
               });
            }
         }
     }
  }

  onTrackResizeStart(event: MouseEvent): void {
     event.preventDefault();
     this.isResizingTrack = true;
     this.resizeStartY = event.clientY;
     this.resizeStartHeight = this.audioTrackHeight();
  }

  isWordActive(word: TranscriptWord): boolean {
    const t = this.currentTime();
    // 50ms akustik ve kare geçiş toleransı ile kelime tam telaffuz edilirken sarı parlar
    return t >= (word.start - 0.05) && t <= (word.end + 0.05);
  }

  toggleSubtitles(): void {
    const nextVal = !this.showSubtitles();
    this.showSubtitles.set(nextVal);

    // EDL yerel nesnesini güncelle
    const edl = this.edl();
    if (edl) {
      if (!edl.settings) edl.settings = {};
      edl.settings.subtitlesEnabled = nextVal;
      this.edl.set({ ...edl });
    }

    // Backend'e kaydet (böylece render motoru subtitlesEnabled ayarını okur)
    this.edlService.patchEdl(this.projectId, {
      settings: { subtitlesEnabled: nextVal }
    }).subscribe({
      next: () => console.log(`[SUBTITLE:TOGGLE] Altyazı ayarı kaydedildi: subtitlesEnabled=${nextVal}`),
      error: (err) => console.error('[SUBTITLE:TOGGLE] Altyazı ayarı kaydedilemedi:', err)
    });
  }

  private formatVttTimestamp(seconds: number): string {
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    const ms = Math.floor((seconds % 1) * 1000);
    return `${hrs.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}.${ms.toString().padStart(3, '0')}`;
  }
}
