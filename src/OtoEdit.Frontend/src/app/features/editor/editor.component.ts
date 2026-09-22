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
import { VideoDetailDto } from '../../core/models/video.model';
import { CutItem, EdlContent, EdlDto, OverlayItem, SuggestionItem, TranscriptSegment, TranscriptWord } from '../../core/models/edl.model';
import { ChatMessageDto, FormFieldDto } from '../../core/models/chat.model';
import { ProjectAssetDto } from '../../core/models/asset.model';
import { NavbarComponent } from '../../shared/components/navbar/navbar.component';
import { DurationPipe } from '../../shared/pipes/duration.pipe';
import { environment } from '../../../environments/environment';

@Component({
  selector: 'app-editor',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule, NavbarComponent, DurationPipe],
  template: `
    <app-navbar [projectTitle]="project()?.ad"></app-navbar>

    <main class="h-[calc(100vh-65px)] flex flex-col bg-dark-900 text-slate-100 overflow-hidden">
      <!-- Üst Bar: Zaman, Dışa Aktar ve Simülasyon Durumu -->
      <div class="px-6 py-2.5 bg-dark-800/90 border-b border-slate-800 flex items-center justify-between z-10">
        <div class="flex items-center gap-4">
          <a [routerLink]="['/project', projectId]" class="text-xs text-slate-400 hover:text-white flex items-center gap-1 transition-colors">
            ← Detaya Dön
          </a>
          <div class="h-4 w-px bg-slate-700"></div>
          <div class="flex items-center gap-2">
            <span class="w-2 h-2 rounded-full bg-brand-cyan"></span>
            <span class="text-xs font-semibold text-white">Canlı EDL Simülasyonu</span>
            <span class="text-[10px] px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">Render Bekletmez</span>
          </div>
        </div>

        <div class="flex items-center gap-3">
          <!-- Render / Dışa Aktar Butonu -->
          <button 
            (click)="requestExport()"
            [disabled]="rendering()"
            class="px-5 py-2 rounded-xl bg-gradient-to-r from-brand-blue via-brand-indigo to-brand-purple hover:from-blue-600 hover:to-purple-600 text-white font-bold text-xs shadow-glow-sm hover:shadow-glow-purple transition-all active:scale-95 flex items-center gap-2">
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
            </svg>
            {{ rendering() ? 'Kuyruğa Alınıyor...' : 'Nihai Videoyu Render Et' }}
          </button>
        </div>
      </div>

      <!-- Orta Alan: Video Player & Timeline (Üst) ve Alt Paneller (Inspector + AI Chat) -->
      <div class="flex-1 grid grid-cols-1 lg:grid-cols-12 overflow-hidden">
        
        <!-- Sol Bölüm (8 Kolon): Video Önizleme + Timeline -->
        <div class="lg:col-span-8 flex flex-col border-r border-slate-800/80 bg-dark-950 p-4 gap-4 overflow-y-auto">
          
          <!-- Video Player Alanı -->
          <div class="relative bg-black rounded-2xl overflow-hidden shadow-2xl border border-slate-800 flex items-center justify-center min-h-[320px] max-h-[460px]">
            <video 
              #videoPlayer
              [src]="videoUrl()"
              (timeupdate)="onTimeUpdate()"
              (loadedmetadata)="onMetadataLoaded()"
              class="w-full h-full object-contain max-h-[440px]"
              controls>
              <track *ngIf="vttTrackUrl()" kind="subtitles" [src]="vttTrackUrl()" srclang="tr" label="Türkçe" [default]="showSubtitles()">
            </video>

              <!-- Dinamik Aktif Metin & Görsel Overlay Önizlemesi -->
              <div 
                *ngFor="let ov of activeOverlays()" 
                (mousedown)="onCanvasDragStart($event, ov.id)"
                (click)="$event.stopPropagation(); selectOverlay(ov.id)"
                [style.top]="getOverlayTop(ov)"
                [style.left]="getOverlayLeft(ov)"
                [style.zIndex]="getOverlayZIndex(ov)"
                class="absolute transition-none cursor-move hover:ring-2 hover:ring-brand-cyan rounded p-1 -translate-x-1/2 -translate-y-1/2 select-none"
                [ngClass]="[
                   selectedOverlayId() === ov.id ? 'ring-2 ring-brand-cyan shadow-glow-sm' : '',
                   getOverlayAnimationClass(ov)
                ]"
                [style.color]="ov.color || '#FFFFFF'"
                [style.backgroundColor]="ov.backgroundColor || 'transparent'"
                [style.fontFamily]="ov.font || 'Inter, sans-serif'">
                
                <!-- Metin Kaplaması -->
                <span *ngIf="ov.type === 'text'" class="px-3 py-1 rounded font-bold whitespace-nowrap block drop-shadow-[0_2px_4px_rgba(0,0,0,0.85)]" [style.fontSize.px]="(ov.fontSize || 48) / 2">
                  {{ ov.content }}
                </span>

                <!-- Görsel / B-Roll Kaplaması -->
                <div *ngIf="ov.type === 'image'" class="relative group">
                  <img 
                    *ngIf="ov.source" 
                    [src]="ov.source" 
                    [alt]="ov.content || 'Görsel'" 
                    class="rounded-lg shadow-xl border border-brand-cyan/50 pointer-events-none object-cover"
                    [style.width.px]="(160 * (ov.scale || 1.0))"
                    [style.maxHeight.px]="(120 * (ov.scale || 1.0))" />
                  
                  <!-- Kaynak yoksa placeholder -->
                  <div *ngIf="!ov.source" class="px-4 py-3 rounded-lg bg-dark-800/90 border border-brand-cyan/40 text-brand-cyan text-xs font-bold flex items-center gap-2">
                    <span>🖼️</span>
                    <span>{{ ov.content || 'B-Roll Görseli' }}</span>
                  </div>

                  <span class="absolute -top-2 -right-2 text-[9px] bg-brand-cyan text-slate-900 font-extrabold px-1 rounded shadow">
                    GÖRSEL
                  </span>
                </div>

                <!-- Canvas Resize Handle -->
                <div *ngIf="selectedOverlayId() === ov.id"
                     (mousedown)="onCanvasResizeStart($event, ov.id)"
                     class="absolute -bottom-2 -right-2 w-5 h-5 bg-white border-2 border-brand-cyan rounded-full cursor-nwse-resize z-30 shadow-md hover:scale-125 transition-transform flex items-center justify-center">
                     <span class="text-[8px] text-brand-cyan">⤡</span>
                </div>
              </div>

              <!-- Canlı Taslak (Ghost Layer) Önizlemesi (Yönetmen AI Formu İçin) -->
              <div 
                *ngIf="ghostPreview() as ghost" 
                class="absolute pointer-events-none z-30 -translate-x-1/2 -translate-y-1/2 select-none border-2 border-dashed border-brand-cyan bg-black/70 backdrop-blur-xs px-3 py-1.5 rounded-lg shadow-glow-sm transition-all duration-100"
                [style.left.%]="ghost.posX"
                [style.top.%]="ghost.posY"
                [style.color]="ghost.color"
                [style.fontFamily]="ghost.font">
                <span class="font-bold whitespace-nowrap block drop-shadow-[0_2px_4px_rgba(0,0,0,0.85)] text-lg">
                  {{ ghost.text }}
                </span>
                <span class="absolute -top-3 -right-3 text-[9px] bg-brand-cyan text-slate-900 font-extrabold px-1.5 py-0.5 rounded shadow">
                  📍 Taslak Konum
                </span>
              </div>

              <!-- Canlı TikTok / Reels Tarzı Karaoke Altyazı Katmanı -->
              <div 
                *ngIf="showSubtitles() && currentSubtitleSegment() as seg" 
                class="absolute bottom-6 left-1/2 -translate-x-1/2 z-25 max-w-[85%] text-center pointer-events-none select-none px-4 py-2 rounded-xl bg-black/75 backdrop-blur-md border border-white/10 shadow-2xl transition-all duration-150">
                <div class="flex flex-wrap items-center justify-center gap-x-1.5 gap-y-0.5" [style.fontFamily]="subtitleFont()" [style.color]="subtitleColor()">
                  <ng-container *ngIf="seg.words && seg.words.length > 0; else plainText">
                    <span 
                      *ngFor="let w of seg.words"
                      class="transition-all duration-100 inline-block px-0.5 rounded"
                      [ngClass]="isWordActive(w) ? 'text-amber-300 font-black scale-110 bg-amber-400/20 shadow-glow-sm' : 'text-slate-100 font-semibold opacity-90'">
                      {{ w.word }}
                    </span>
                  </ng-container>
                  <ng-template #plainText>
                    <span class="font-bold text-slate-100 text-sm md:text-base drop-shadow-[0_2px_4px_rgba(0,0,0,0.9)]">
                      {{ seg.text }}
                    </span>
                  </ng-template>
                </div>
              </div>
          </div>

          <!-- Video Zaman Kontrolleri -->
          <div class="flex items-center justify-between text-xs font-mono text-slate-400 px-2">
            <div class="flex items-center gap-4">
              <span>İzlenen: {{ currentTime() | duration }} / {{ totalDuration() | duration }}</span>
              <span class="text-brand-cyan font-bold">Net Süre: {{ visibleDuration() | duration }}</span>
              <button 
                (click)="toggleSubtitles()" 
                [ngClass]="showSubtitles() ? 'text-amber-300 bg-amber-400/20 border-amber-400/40' : 'border-slate-700'"
                class="px-2.5 py-1 rounded border hover:border-slate-500 bg-dark-800 transition-colors flex items-center gap-1.5 text-[11px]"
                title="Altyazıyı Aç/Kapat (Kısayol: C)">
                <span>💬</span>
                <span>{{ showSubtitles() ? 'Altyazı: Açık' : 'Altyazı: Kapalı' }}</span>
              </button>
            </div>
            <div class="flex items-center gap-4">
              <span class="flex items-center gap-1.5"><span class="w-2.5 h-2.5 rounded-sm bg-emerald-500"></span> Korunan</span>
              <span class="flex items-center gap-1.5"><span class="w-2.5 h-2.5 rounded-sm bg-amber-500"></span> Retake</span>
              <span class="flex items-center gap-1.5"><span class="w-2.5 h-2.5 rounded-sm bg-rose-500"></span> Jump-Cut</span>
              <span class="flex items-center gap-1.5"><span class="w-2.5 h-2.5 rounded-sm bg-sky-400"></span> Yazı</span>
              <span class="flex items-center gap-1.5"><span class="w-2.5 h-2.5 rounded-sm bg-purple-400"></span> Görsel</span>
            </div>
          </div>

          <!-- Timeline Viewer (Yatay Şerit) -->
          <div class="glass-panel rounded-2xl p-4 border border-slate-800 space-y-3">
            <div class="flex items-center justify-between text-xs mb-1">
              <h3 class="font-bold text-white uppercase tracking-wider text-[11px]">Etkileşimli Kurgu Timeline'ı</h3>
              <div class="flex items-center gap-2">
                <button (click)="undo()" class="p-1 px-2 rounded bg-dark-800 text-slate-400 hover:text-white border border-slate-700" title="Geri Al (Ctrl+Z)">⟲ Geri Al</button>
                <button (click)="redo()" class="p-1 px-2 rounded bg-dark-800 text-slate-400 hover:text-white border border-slate-700" title="İleri Al (Ctrl+Y)">⟳ İleri</button>
                <button (click)="zoomIn()" class="p-1 px-2 rounded bg-dark-800 text-slate-400 hover:text-white border border-slate-700" title="Yakınlaş (Zoom In)">🔍 +</button>
                <button (click)="zoomOut()" class="p-1 px-2 rounded bg-dark-800 text-slate-400 hover:text-white border border-slate-700" title="Uzaklaş (Zoom Out)">🔍 -</button>
                <button (click)="addSplitMarker()" class="p-1 px-2 rounded bg-dark-800 text-slate-400 hover:text-rose-400 border border-slate-700" title="Bulunulan Yerden Böl (B)">✂ Böl (B)</button>
                <button (click)="rippleAi.set(!rippleAi())" class="p-1 px-2 rounded bg-dark-800 text-slate-400 hover:text-sky-400 border border-slate-700" title="AI Kesimlerini Sıkıştır/Genişlet">
                  {{ rippleAi() ? '🤖 AI Sıkıştırılmış' : '🤖 AI Geniş' }}
                </button>
                <button (click)="rippleRetake.set(!rippleRetake())" class="p-1 px-2 rounded bg-dark-800 text-slate-400 hover:text-amber-400 border border-slate-700" title="Retake (Hatalı Tekrar) Kısımlarını Sıkıştır/Genişlet">
                  {{ rippleRetake() ? '🔄 Retake Sıkıştırılmış' : '🔄 Retake Geniş' }}
                </button>
                <button 
                  *ngIf="retakeCount() > 0" 
                  (click)="deleteRetakeCuts()" 
                  class="p-1 px-2.5 rounded bg-amber-500/20 text-amber-300 hover:bg-amber-500/30 border border-amber-500/40 font-semibold text-[11px] shadow-glow-sm flex items-center gap-1.5 transition-all" 
                  title="Tüm Hatalı Tekrar (Retake) Kesimlerini İptal Et ve Sahneyi Geri Yükle">
                  <span>🔄</span>
                  <span>{{ retakeCount() }} Retake'i Geri Al</span>
                </button>
                <button (click)="rippleManual.set(!rippleManual())" class="p-1 px-2 rounded bg-dark-800 text-slate-400 hover:text-sky-400 border border-slate-700" title="Manuel Kesimleri Sıkıştır/Genişlet">
                  {{ rippleManual() ? '🖐 Manuel Sıkıştırılmış' : '🖐 Manuel Geniş' }}
                </button>
                <div *ngIf="selectedClipIds().length > 0" class="flex items-center gap-2 border-l border-slate-700 pl-2 ml-1">
                  <span class="text-[10px] font-bold text-slate-300">{{ selectedClipIds().length }} Seçili</span>
                  <button (click)="deleteSelectedClips()" class="p-1 px-2.5 rounded bg-rose-600/80 text-white font-bold hover:bg-rose-500 border border-rose-500 shadow-glow-sm" title="Seçili Klipleri Sil (Del)">✕ Sil (Del)</button>
                  <button *ngIf="selectedClipIds().length > 1" (click)="mergeSelectedClips()" class="p-1 px-2.5 rounded bg-emerald-600/80 text-white font-bold hover:bg-emerald-500 border border-emerald-500 shadow-glow-sm" title="Seçili Klipleri Birleştir">🔗 Birleştir</button>
                </div>
                <button (click)="addTextOverlay()" class="p-1 px-2.5 rounded bg-brand-cyan text-slate-900 font-bold hover:bg-cyan-400 border border-cyan-500 shadow-glow-sm flex items-center gap-1 ml-auto" title="Zaman çizgisine yazı katmanı ekle">
                  <span class="font-black">T</span>
                  <span>Yazı Ekle</span>
                </button>
                <button (click)="addImageOverlay()" class="p-1 px-2.5 rounded bg-purple-500 text-white font-bold hover:bg-purple-400 border border-purple-400 shadow-glow-sm flex items-center gap-1" title="Zaman çizgisine görsel katmanı ekle">
                  <span>🖼️</span>
                  <span>Görsel Ekle</span>
                </button>
              </div>
            </div>

            <!-- Interaktif Timeline Track (Çok Kanallı / Katmanlı Mimari) -->
            <div class="overflow-x-auto pb-3 w-full scrollbar-thin scrollbar-thumb-slate-700 scrollbar-track-dark-900">
              <div 
                #timelineTrack
                (click)="seekTimeline($event)"
                [style.width.%]="100 * timelineZoom()"
                class="relative bg-dark-950 rounded-xl overflow-hidden cursor-pointer border border-slate-700/60 select-none min-w-full flex flex-col gap-1 p-2">
                
                <!-- Kanal 1: Katmanlar (Yazı / Görsel Track) -->
                <div class="relative h-8 bg-dark-900/90 rounded-lg border border-slate-800/80 overflow-hidden flex items-center">
                  <!-- Katman Etiketi -->
                  <div class="absolute left-2 top-0 bottom-0 flex items-center gap-1 text-[9px] font-bold text-sky-400/70 uppercase tracking-wider pointer-events-none z-10">
                    <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16m-7 6h7" />
                    </svg>
                    Katmanlar
                  </div>

                  <!-- Katman Yoksa Bilgi -->
                  <div *ngIf="!activeEdl()?.overlays?.length" class="absolute inset-0 flex items-center justify-center text-[10px] text-slate-500 italic pointer-events-none">
                    Yazı veya görsel eklemek için yukarıdaki 'T Yazı Ekle' veya '🖼️ Görsel Ekle' butonuna basın
                  </div>

                  <!-- Katman Öğeleri (Pill'ler) -->
                  <div 
                    *ngFor="let ov of activeEdl()?.overlays"
                    (mousedown)="onOverlayDragStart($event, ov.id)"
                    (click)="$event.stopPropagation(); selectOverlay(ov.id)"
                    class="absolute top-1 bottom-1 rounded-md px-2 flex items-center justify-between text-[10px] font-bold cursor-grab active:cursor-grabbing z-20 group transition-all select-none shadow-md overflow-hidden"
                    [ngClass]="[
                       ov.type === 'text' ? 'bg-gradient-to-r from-sky-600 to-cyan-500 text-white border border-sky-300/80' : 'bg-gradient-to-r from-purple-600 to-fuchsia-500 text-white border border-purple-300/80',
                       selectedOverlayId() === ov.id ? 'ring-2 ring-white shadow-[0_0_10px_rgba(255,255,255,0.9)] z-30 brightness-110' : 'hover:brightness-105'
                    ]"
                    [ngStyle]="getOverlayStyle(ov)"
                    [title]="(ov.type === 'text' ? 'Metin: ' : 'Görsel: ') + (ov.content || ov.source || ov.id)">
                    
                    <!-- Sol Boyutlandırma Kolu (Resize Left) -->
                    <div 
                      (mousedown)="onOverlayResizeStart($event, ov.id, 'left')"
                      class="absolute left-0 top-0 bottom-0 w-3 cursor-ew-resize opacity-0 group-hover:opacity-100 hover:bg-white/60 bg-white/30 rounded-l flex items-center justify-center z-30"
                      title="Başlangıcı Sürükle">
                      <div class="w-0.5 h-3 bg-black/60 rounded"></div>
                    </div>

                    <!-- Katman Başlığı ve İkonu -->
                    <span class="truncate px-2 pointer-events-none font-medium flex items-center gap-1">
                      <span>{{ ov.type === 'text' ? 'T' : '🖼️' }}</span>
                      <span class="truncate">{{ ov.content || (ov.type === 'text' ? 'Metin' : 'Görsel') }}</span>
                    </span>

                    <!-- Sağ Boyutlandırma Kolu (Resize Right) -->
                    <div 
                      (mousedown)="onOverlayResizeStart($event, ov.id, 'right')"
                      class="absolute right-0 top-0 bottom-0 w-3 cursor-ew-resize opacity-0 group-hover:opacity-100 hover:bg-white/60 bg-white/30 rounded-r flex items-center justify-center z-30"
                      title="Bitişi Sürükle">
                      <div class="w-0.5 h-3 bg-black/60 rounded"></div>
                    </div>
                  </div>
                </div>

                <!-- Kanal 2: Video Klipleri Track -->
                <div class="relative h-12 bg-dark-900 rounded-lg overflow-hidden border border-slate-800/80 flex">
                  <!-- Video Etiketi -->
                  <div class="absolute left-2 top-0 bottom-0 flex items-center gap-1 text-[9px] font-bold text-emerald-400/60 uppercase tracking-wider pointer-events-none z-10">
                    <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                    </svg>
                    Video
                  </div>

                  <!-- Klipler (Flexbox ile sıralanır) -->
                  <ng-container *ngFor="let clip of clips()">
                    <div 
                      *ngIf="isVisible(clip)"
                      (click)="selectClip(clip.id, $event)"
                      (dblclick)="toggleClip(clip, $event)"
                      class="relative h-full transition-colors border-r border-white/20 box-border group"
                      [ngClass]="{
                         'bg-amber-500/80 hover:bg-amber-400': isRetakeClip(clip),
                         'bg-rose-500/80 hover:bg-rose-400': isManualClip(clip),
                         'bg-rose-900/80 hover:bg-rose-800': clip.isCut && !isRetakeClip(clip) && !isManualClip(clip),
                         'bg-emerald-600/40 hover:bg-emerald-500/60': !clip.isCut,
                         'ring-2 ring-inset ring-brand-yellow shadow-[0_0_10px_rgba(250,204,21,0.5)] z-10': selectedClipIds().includes(clip.id)
                      }"
                      [style.width.%]="(clip.duration / ( (rippleAi() || rippleManual() || rippleRetake()) ? visibleDuration() : totalDuration() )) * 100"
                      [title]="getClipTooltip(clip)">
                      
                      <!-- Kırmızı kısımları silme (Gizle modu kapalıyken) -->
                      <div *ngIf="clip.isCut" class="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100">
                        <span class="text-[10px] text-white font-bold">✕ İptal</span>
                      </div>
                    </div>
                  </ng-container>
                </div>

                <!-- Ortak Zaman İmleci (Playhead) - Her iki kanalı da dikine keser -->
                <div 
                  class="absolute top-0 bottom-0 w-0.5 bg-white shadow-[0_0_8px_white] z-40 pointer-events-none"
                  [style.left.%]="getPlayheadPosition()">
                  <div class="w-3.5 h-3.5 bg-white rotate-45 -translate-x-[6px] -translate-y-[4px] shadow-lg rounded-sm border border-slate-300"></div>
                </div>
              </div>
            </div>

            <!-- Akıllı Öneri Çipleri (AI Suggestions) -->
            <div *ngIf="activeEdl()?.suggestions?.length" class="pt-2">
              <span class="text-[11px] font-bold text-slate-400 uppercase tracking-wider block mb-2">AI B-Roll ve Vurgu Önerileri</span>
              <div class="flex items-center gap-2 overflow-x-auto pb-1">
                <div 
                  *ngFor="let sug of activeEdl()?.suggestions"
                  [ngClass]="sug.status === 'accepted' ? 'border-emerald-500/50 bg-emerald-500/10 text-emerald-300' : (sug.status === 'rejected' ? 'border-rose-500/50 bg-rose-500/10 text-rose-400 line-through' : 'border-slate-700 bg-dark-800 text-slate-200')"
                  class="shrink-0 text-xs px-3 py-1.5 rounded-lg border flex items-center gap-2">
                  <span class="font-medium">{{ sug.title }}</span>
                  <div *ngIf="sug.status === 'pending'" class="flex items-center gap-1">
                    <button (click)="acceptSuggestion(sug)" title="Onayla" class="p-1 hover:text-emerald-400 text-slate-400">✓</button>
                    <button (click)="rejectSuggestion(sug)" title="Reddet" class="p-1 hover:text-rose-400 text-slate-400">✕</button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Sağ Bölüm (4 Kolon): AI Chat Paneli & Overlay Inspector -->
        <div class="lg:col-span-4 flex flex-col h-full bg-dark-900 border-l border-slate-800/80">
          
          <!-- Sekme Başlığı -->
          <div class="flex border-b border-slate-800 bg-dark-800/50">
            <button 
              (click)="activeTab.set('chat')"
              [ngClass]="activeTab() === 'chat' ? 'text-brand-cyan border-brand-cyan bg-dark-900/60' : 'text-slate-400 hover:text-slate-200 border-transparent'"
              class="flex-1 py-3 text-xs font-bold uppercase tracking-wider border-b-2 transition-all flex items-center justify-center gap-2">
              <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
              </svg>
              AI Kurgu Sohbeti
            </button>
            <button 
              (click)="activeTab.set('overlays')"
              [ngClass]="activeTab() === 'overlays' ? 'text-brand-cyan border-brand-cyan bg-dark-900/60' : 'text-slate-400 hover:text-slate-200 border-transparent'"
              class="flex-1 py-3 text-xs font-bold uppercase tracking-wider border-b-2 transition-all flex items-center justify-center gap-2">
              <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16m-7 6h7" />
              </svg>
              Katmanlar ({{ activeEdl()?.overlays?.length || 0 }})
            </button>
            <button 
              (click)="activeTab.set('inspector')"
              [ngClass]="activeTab() === 'inspector' ? 'text-brand-yellow border-brand-yellow bg-dark-900/60' : 'text-slate-400 hover:text-slate-200 border-transparent'"
              class="flex-1 py-3 text-xs font-bold uppercase tracking-wider border-b-2 transition-all flex items-center justify-center gap-2">
              <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
              </svg>
              Özellikler
            </button>
            <button 
              (click)="activeTab.set('media')"
              [ngClass]="activeTab() === 'media' ? 'text-brand-cyan border-brand-cyan bg-dark-900/60' : 'text-slate-400 hover:text-slate-200 border-transparent'"
              class="flex-1 py-3 text-xs font-bold uppercase tracking-wider border-b-2 transition-all flex items-center justify-center gap-2">
              <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
              Medya
            </button>
          </div>

          <!-- Sekme 1: AI Chat Paneli -->
          <div *ngIf="activeTab() === 'chat'" class="flex-1 flex flex-col h-full overflow-hidden">
            <!-- Mesaj Listesi -->
            <div #chatMessagesContainer class="flex-1 p-4 overflow-y-auto space-y-4">
              <div *ngIf="chatMessages().length === 0" class="text-center py-10 text-slate-500 text-xs">
                <p class="mb-2">💡 AI ile videonuza doğal dilde müdahale edin:</p>
                <div class="space-y-1.5 text-slate-400">
                  <p class="p-2 rounded-lg bg-dark-800 cursor-pointer hover:bg-slate-700" (click)="setPrompt('Girişteki sessizlikleri kes')">"Girişteki sessizlikleri kes"</p>
                  <p class="p-2 rounded-lg bg-dark-800 cursor-pointer hover:bg-slate-700" (click)="setPrompt('10. saniyeye Kanala Abone Ol yazısı koy')">"10. saniyeye Kanala Abone Ol yazısı koy"</p>
                  <p class="p-2 rounded-lg bg-dark-800 cursor-pointer hover:bg-slate-700" (click)="setPrompt('20. saniyeye kedi görseli ekle')">"20. saniyeye kedi görseli ekle"</p>
                </div>
              </div>

              <div 
                *ngFor="let msg of chatMessages()" 
                [ngClass]="msg.rol === 'user' ? 'flex justify-end' : 'flex justify-start'">
                <div 
                  [ngClass]="msg.rol === 'user' ? 'bg-gradient-to-r from-brand-blue to-brand-indigo text-white rounded-2xl rounded-tr-none' : 'bg-dark-800 border border-slate-700/60 text-slate-200 rounded-2xl rounded-tl-none'"
                  class="max-w-[85%] p-3.5 text-xs shadow-md space-y-1.5 animate-fade-in">
                  <p class="leading-relaxed">{{ msg.mesaj }}</p>
                  
                  <div *ngIf="msg.patchDurumu === 'pending'" class="mt-2 flex gap-2">
                    <button (click)="previewPatch(msg)" [ngClass]="previewMessageId() === msg.id ? 'bg-sky-500/40 text-sky-300' : 'bg-sky-500/20 text-sky-400'" class="flex-1 py-1.5 hover:bg-sky-500/40 border border-sky-500/50 rounded font-bold transition-colors shadow-glow-sm">
                      {{ previewMessageId() === msg.id ? '👀 İzleniyor' : '🔍 Önizle' }}
                    </button>
                    <button (click)="applyPatch(msg)" class="flex-1 py-1.5 bg-emerald-500/20 hover:bg-emerald-500/40 text-emerald-400 border border-emerald-500/50 rounded font-bold transition-colors">Onayla</button>
                    <button (click)="cancelPatch(msg)" class="flex-1 py-1.5 bg-rose-500/20 hover:bg-rose-500/40 text-rose-400 border border-rose-500/50 rounded font-bold transition-colors">İptal Et</button>
                  </div>
                  
                  <!-- Dinamik Form (Clarification - Zengin Renk ve 16:9 Konum Seçici) -->
                  <div *ngIf="msg.patchDurumu === 'clarification' && msg.formFields" class="mt-3 p-3.5 bg-dark-900 border border-brand-cyan/40 rounded-xl space-y-3.5 shadow-lg">
                     <div class="flex items-center justify-between border-b border-slate-800 pb-2">
                       <span class="text-[11px] text-brand-cyan font-bold uppercase tracking-wider flex items-center gap-1.5">
                         <span>⚙️</span> Katman Özelliklerini Belirleyin
                       </span>
                       <span class="text-[9px] text-slate-500 font-mono">Yönetmen AI</span>
                     </div>
                     
                     <div *ngFor="let field of msg.formFields" class="space-y-1.5">
                        <label class="text-[10px] text-slate-300 font-medium flex items-center justify-between">
                          <span>{{ field.label }}</span>
                          <span *ngIf="field.required" class="text-rose-400 text-[9px]">*Zorunlu</span>
                        </label>
                        
                        <!-- Metin Girişi (Text) -->
                        <input *ngIf="field.type === 'text'" type="text"
                               [ngModel]="msg.formData?.[field.id] || field.defaultValue"
                               (ngModelChange)="updateFormData(msg, field.id, $event)"
                               placeholder="Metin giriniz..."
                               class="w-full bg-dark-800 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-100 placeholder-slate-500 focus:border-brand-cyan outline-none transition-colors" />
                               
                        <!-- Sayısal Giriş (Number) -->
                        <input *ngIf="field.type === 'number'" type="number"
                               [ngModel]="msg.formData?.[field.id] || field.defaultValue"
                               (ngModelChange)="updateFormData(msg, field.id, $event)"
                               class="w-full bg-dark-800 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-100 focus:border-brand-cyan outline-none transition-colors" />
                               
                        <!-- Özel Zengin Renk Aracı (Color Palette + Hex + Picker) -->
                        <div *ngIf="field.type === 'color'" class="space-y-2">
                          <!-- Hazır Renk Palet Butonları -->
                          <div class="flex flex-wrap gap-1.5 items-center">
                            <button 
                              *ngFor="let c of colorPalette"
                              type="button"
                              (click)="updateFormData(msg, field.id, c)"
                              [style.backgroundColor]="c"
                              [ngClass]="(msg.formData?.[field.id] || field.defaultValue) === c ? 'ring-2 ring-brand-cyan ring-offset-2 ring-offset-dark-900 scale-110 shadow-glow-sm' : 'opacity-85 hover:opacity-100 hover:scale-105'"
                              class="w-6 h-6 rounded-full border border-white/20 transition-all shadow-sm"
                              [title]="c">
                            </button>
                          </div>
                          <!-- Özel Renk ve Hex Kutusu -->
                          <div class="flex items-center gap-2 bg-dark-800 p-1.5 rounded-lg border border-slate-700/80">
                            <input 
                              type="color" 
                              [ngModel]="msg.formData?.[field.id] || field.defaultValue || '#FACC15'"
                              (ngModelChange)="updateFormData(msg, field.id, $event)"
                              class="w-7 h-7 rounded cursor-pointer border-0 bg-transparent p-0" />
                            <input 
                              type="text" 
                              [ngModel]="msg.formData?.[field.id] || field.defaultValue || '#FACC15'"
                              (ngModelChange)="updateFormData(msg, field.id, $event)"
                              class="bg-transparent text-xs font-mono text-slate-200 outline-none w-20 uppercase font-semibold" 
                              maxlength="7" />
                            <span class="text-[10px] text-slate-400 font-mono ml-auto">Özel Hex</span>
                          </div>
                        </div>

                        <!-- 16:9 İnteraktif Konum Seçici (Mini-Sahne + Snap Çapalar) -->
                        <div *ngIf="field.type === 'position'" class="space-y-1.5">
                          <div class="flex justify-between items-center text-[10px] text-slate-400 font-mono">
                            <span>16:9 Video Sahne Alanı</span>
                            <span class="text-brand-cyan font-bold bg-dark-800 px-1.5 py-0.5 rounded border border-slate-700">
                              X: %{{ getMarkerPosition(msg, field).x }} | Y: %{{ getMarkerPosition(msg, field).y }}
                            </span>
                          </div>
                          <div 
                            (click)="onMiniStageClick($event, msg, field.id)"
                            class="w-full aspect-video bg-dark-950 border border-slate-700/90 rounded-lg relative overflow-hidden cursor-crosshair select-none group shadow-inner">
                            <!-- Kılavuz Çizgileri (Üçte Bir Kuralı) -->
                            <div class="absolute inset-0 grid grid-cols-3 grid-rows-3 pointer-events-none opacity-20">
                              <div class="border-r border-b border-slate-400"></div>
                              <div class="border-r border-b border-slate-400"></div>
                              <div class="border-b border-slate-400"></div>
                              <div class="border-r border-b border-slate-400"></div>
                              <div class="border-r border-b border-slate-400"></div>
                              <div class="border-b border-slate-400"></div>
                              <div class="border-r border-b border-slate-400"></div>
                              <div class="border-r border-b border-slate-400"></div>
                              <div></div>
                            </div>
                            
                            <!-- 9 Hızlı Çapa Butonu -->
                            <button type="button" (click)="$event.stopPropagation(); setPresetPosition(msg, field.id, 'top-left')" title="Sol Üst" class="absolute top-2 left-2 w-3.5 h-3.5 rounded bg-slate-700/60 hover:bg-brand-cyan/80 transition-colors"></button>
                            <button type="button" (click)="$event.stopPropagation(); setPresetPosition(msg, field.id, 'top-center')" title="Üst Orta" class="absolute top-2 left-1/2 -translate-x-1/2 w-3.5 h-3.5 rounded bg-slate-700/60 hover:bg-brand-cyan/80 transition-colors"></button>
                            <button type="button" (click)="$event.stopPropagation(); setPresetPosition(msg, field.id, 'top-right')" title="Sağ Üst" class="absolute top-2 right-2 w-3.5 h-3.5 rounded bg-slate-700/60 hover:bg-brand-cyan/80 transition-colors"></button>
                            <button type="button" (click)="$event.stopPropagation(); setPresetPosition(msg, field.id, 'center-left')" title="Sol Orta" class="absolute top-1/2 -translate-y-1/2 left-2 w-3.5 h-3.5 rounded bg-slate-700/60 hover:bg-brand-cyan/80 transition-colors"></button>
                            <button type="button" (click)="$event.stopPropagation(); setPresetPosition(msg, field.id, 'center')" title="Tam Merkez" class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-3.5 h-3.5 rounded bg-slate-700/60 hover:bg-brand-cyan/80 transition-colors"></button>
                            <button type="button" (click)="$event.stopPropagation(); setPresetPosition(msg, field.id, 'center-right')" title="Sağ Orta" class="absolute top-1/2 -translate-y-1/2 right-2 w-3.5 h-3.5 rounded bg-slate-700/60 hover:bg-brand-cyan/80 transition-colors"></button>
                            <button type="button" (click)="$event.stopPropagation(); setPresetPosition(msg, field.id, 'bottom-left')" title="Sol Alt" class="absolute bottom-2 left-2 w-3.5 h-3.5 rounded bg-slate-700/60 hover:bg-brand-cyan/80 transition-colors"></button>
                            <button type="button" (click)="$event.stopPropagation(); setPresetPosition(msg, field.id, 'bottom-center')" title="Alt Orta (Altyazı/Başlık)" class="absolute bottom-2 left-1/2 -translate-x-1/2 w-3.5 h-3.5 rounded bg-slate-700/60 hover:bg-brand-cyan/80 transition-colors"></button>
                            <button type="button" (click)="$event.stopPropagation(); setPresetPosition(msg, field.id, 'bottom-right')" title="Sağ Alt" class="absolute bottom-2 right-2 w-3.5 h-3.5 rounded bg-slate-700/60 hover:bg-brand-cyan/80 transition-colors"></button>

                            <!-- Konum Göstergesi (Pin Marker) -->
                            <div 
                              class="absolute -translate-x-1/2 -translate-y-1/2 pointer-events-none transition-all duration-75 flex flex-col items-center"
                              [style.left.%]="getMarkerPosition(msg, field).x"
                              [style.top.%]="getMarkerPosition(msg, field).y">
                              <div class="w-3.5 h-3.5 rounded-full bg-brand-cyan border-2 border-white shadow-glow-sm animate-pulse"></div>
                              <span class="text-[9px] font-bold text-brand-cyan -mt-0.5 select-none drop-shadow">📍</span>
                            </div>
                          </div>
                          <p class="text-[9px] text-slate-400 italic">Kutuya tıklayarak konumu belirleyin. Video oynatıcı üzerinde canlı taslak önizlenir.</p>
                        </div>
                        
                        <!-- Font / Animasyon Seçim Dropdown'ları -->
                        <select *ngIf="field.type === 'select'"
                                [ngModel]="msg.formData?.[field.id] || field.defaultValue"
                                (ngModelChange)="updateFormData(msg, field.id, $event)"
                                class="w-full bg-dark-800 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-100 focus:border-brand-cyan outline-none transition-colors">
                            <option *ngFor="let opt of field.options" [value]="getOptValue(opt)">
                              {{ getOptLabel(opt) }}
                            </option>
                        </select>
                     </div>
                     
                     <button (click)="submitForm(msg)" class="w-full py-2 bg-gradient-to-r from-brand-cyan to-cyan-500 hover:from-cyan-400 hover:to-cyan-600 text-slate-950 font-bold rounded-lg transition-all shadow-md active:scale-98 flex items-center justify-center gap-1.5 mt-2">
                        <span>✨</span>
                        <span>Seçimleri Onayla ve Ekle</span>
                     </button>
                  </div>
                  <div *ngIf="msg.patchDurumu === 'applied'" class="mt-1 text-[10px] text-emerald-400 font-semibold flex items-center gap-1">
                    <span>✓ Uygulandı</span>
                  </div>
                  <div *ngIf="msg.patchDurumu === 'rejected'" class="mt-1 text-[10px] text-rose-400 font-semibold flex items-center gap-1">
                    <span>✕ Reddedildi</span>
                  </div>

                  <span class="text-[10px] opacity-60 block text-right mt-1">
                    {{ msg.olusturulmaZamani | date:'HH:mm' }}
                  </span>
                </div>
              </div>

              <!-- AI Typing -->
              <div *ngIf="chatLoading()" class="flex items-center gap-2 text-slate-400 text-xs p-3">
                <span class="w-2 h-2 rounded-full bg-brand-cyan animate-ping"></span>
                <span>AI komutunuzu çözüyor ve EDL kararlarını güncelliyor...</span>
              </div>
            </div>

            <!-- Mesaj Gönderme Kutusu -->
            <div class="p-3 bg-dark-800 border-t border-slate-800">
              <form (ngSubmit)="sendChatMessage()" class="flex items-center gap-2">
                <input 
                  type="text" 
                  [(ngModel)]="userPrompt" 
                  name="prompt"
                  placeholder="Komut yazın (Enter)..."
                  [disabled]="chatLoading()"
                  class="flex-1 px-4 py-2.5 rounded-xl bg-dark-900 border border-slate-700 text-white placeholder-slate-500 focus:outline-none focus:border-brand-blue text-xs transition-all" />
                <button 
                  type="submit"
                  [disabled]="!userPrompt.trim() || chatLoading()"
                  class="px-4 py-2.5 rounded-xl bg-brand-blue hover:bg-blue-600 text-white text-xs font-bold disabled:opacity-40 transition-all shadow-glow-sm">
                  Gönder
                </button>
              </form>
            </div>
          </div>

          <!-- Sekme 2: Overlay Inspector (Katmanlar) -->
          <div *ngIf="activeTab() === 'overlays'" class="flex-1 p-4 overflow-y-auto space-y-3">
            <div *ngIf="!activeEdl()?.overlays?.length" class="text-center py-12 text-slate-500 text-xs">
              Henüz eklenmiş bir yazı veya görsel katmanı bulunmuyor.
            </div>

            <div 
              *ngFor="let ov of activeEdl()?.overlays"
              (click)="selectOverlay(ov.id)"
              class="p-3.5 rounded-xl border flex items-start justify-between gap-3 cursor-pointer transition-colors"
              [ngClass]="selectedOverlayId() === ov.id ? 'bg-dark-700 border-brand-cyan shadow-[0_0_10px_rgba(6,182,212,0.3)]' : 'bg-dark-800 border-slate-700 hover:bg-dark-750'">
              <div class="flex-1">
                <div class="flex items-center gap-2 mb-1">
                  <span 
                    [ngClass]="ov.type === 'text' ? 'bg-sky-500/20 text-sky-400' : 'bg-purple-500/20 text-purple-400'"
                    class="px-2 py-0.5 rounded text-[10px] font-bold uppercase">
                    {{ ov.type }}
                  </span>
                  <span class="px-1.5 py-0.5 rounded text-[9px] font-mono font-bold bg-slate-800 text-brand-cyan border border-slate-700">
                    Katman #{{ ov.trackId || 1 }}
                  </span>
                  <span class="text-xs font-mono text-slate-400">{{ ov.timestamp | number:'1.1-1' }}s - {{ (ov.timestamp + ov.duration) | number:'1.1-1' }}s</span>
                </div>
                <p class="text-xs font-medium text-white line-clamp-2">
                  {{ ov.content || ov.source || ov.id }}
                </p>
                <div class="text-[10px] text-slate-400 mt-1">
                  <span>Animasyon: {{ ov.animation || 'fade' }}</span> • 
                  <span>Konum: {{ ov.position?.join(', ') || 'merkez' }}</span>
                </div>
              </div>

              <div class="flex flex-col items-end gap-1">
                <div class="flex items-center gap-0.5 bg-dark-900 rounded p-0.5 border border-slate-700/60">
                  <button 
                    (click)="$event.stopPropagation(); bringOverlayForward(ov.id)" 
                    title="Öne Getir (Z-Index +1)"
                    class="text-slate-400 hover:text-brand-cyan hover:bg-slate-700 p-1 rounded text-xs transition-colors cursor-pointer">
                    🔼
                  </button>
                  <button 
                    (click)="$event.stopPropagation(); sendOverlayBackward(ov.id)" 
                    title="Arkaya Gönder (Z-Index -1)"
                    class="text-slate-400 hover:text-brand-cyan hover:bg-slate-700 p-1 rounded text-xs transition-colors cursor-pointer">
                    🔽
                  </button>
                </div>
                <button 
                  (click)="$event.stopPropagation(); removeOverlay(ov.id)" 
                  title="Katmanı Sil"
                  class="text-slate-500 hover:text-rose-400 p-1 rounded-lg hover:bg-rose-500/10 transition-colors text-xs cursor-pointer">
                  ✕
                </button>
              </div>
            </div>
          </div>

          <!-- Sekme 3: Özellikler (Inspector) -->
          <div *ngIf="activeTab() === 'inspector'" class="flex-1 p-5 overflow-y-auto space-y-4">
             <!-- Hiçbir katman seçili değilse -->
             <div *ngIf="!selectedOverlay()" class="text-center py-16 text-slate-500 text-xs space-y-3">
                <div class="text-3xl">📝</div>
                <p class="font-bold text-slate-300">Hiçbir Katman Seçili Değil</p>
                <p class="text-[11px] text-slate-400 max-w-xs mx-auto">
                  Düzenlemek istediğiniz yazı veya görsele video ekranından veya timeline katman kanalından tıklayın.
                </p>
                <div class="pt-2 flex justify-center gap-2">
                  <button (click)="addTextOverlay()" class="px-3 py-1.5 rounded-lg bg-brand-cyan text-slate-900 font-bold text-xs hover:bg-cyan-400 transition-colors shadow-glow-sm">
                    + Yeni Yazı Ekle
                  </button>
                </div>
             </div>

             <!-- Seçili katman varsa düzenleme paneli -->
             <div *ngIf="selectedOverlay()" class="space-y-4">
                <div class="flex items-center justify-between border-b border-slate-800 pb-2">
                  <h3 class="text-xs font-bold text-slate-200 uppercase tracking-wider">Katman Özellikleri</h3>
                  <span 
                    [ngClass]="inspectorData.type === 'text' ? 'bg-sky-500/20 text-sky-400 border-sky-500/30' : 'bg-purple-500/20 text-purple-400 border-purple-500/30'"
                    class="px-2 py-0.5 rounded text-[10px] font-bold uppercase border">
                    {{ inspectorData.type === 'text' ? 'Metin Katmanı' : 'Görsel Katmanı' }}
                  </span>
                </div>
                
                <!-- Content Edit -->
                <div class="space-y-1">
                   <label class="text-[10px] text-slate-400 uppercase font-semibold">
                     {{ inspectorData.type === 'image' ? 'Görsel Başlığı / Açıklaması' : 'Metin İçeriği' }}
                   </label>
                   <textarea 
                      [(ngModel)]="inspectorData.content" 
                      (ngModelChange)="onInspectorChange()"
                      class="w-full bg-dark-900 border border-slate-700 rounded-lg p-2.5 text-xs text-white focus:border-brand-cyan focus:outline-none transition-all"
                      rows="2"
                      placeholder="Ekranda görünecek metni yazın..."></textarea>
                </div>

                <!-- Görsel URL / Kaynak (Image ise) -->
                <div class="space-y-1.5" *ngIf="inspectorData.type === 'image'">
                   <div class="flex items-center justify-between">
                     <label class="text-[10px] text-slate-400 uppercase font-semibold">Görsel Kaynağı (URL veya Stok Yolu)</label>
                     <button 
                       type="button" 
                       (click)="activeTab.set('media')" 
                       class="text-[10px] font-bold text-brand-cyan hover:underline flex items-center gap-1 cursor-pointer">
                       <span>🖼️</span> Medyadan Seç
                     </button>
                   </div>
                   <input 
                      type="text" 
                      [(ngModel)]="inspectorData.source" 
                      (ngModelChange)="onInspectorChange()"
                      class="w-full bg-dark-900 border border-slate-700 rounded-lg p-2 text-xs text-white focus:border-brand-cyan focus:outline-none"
                      placeholder="https://images.pexels.com/..." />
                </div>

                <!-- Görsel Ölçek / Boyut (Image ise) -->
                <div class="space-y-1" *ngIf="inspectorData.type === 'image'">
                   <div class="flex justify-between items-center text-[10px] text-slate-400 uppercase font-semibold">
                     <span>Ölçek / Boyut</span>
                     <span class="text-brand-cyan font-bold">{{ inspectorData.scale || 1.0 }}x</span>
                   </div>
                   <input 
                      type="range" 
                      min="0.2" 
                      max="2.0" 
                      step="0.05" 
                      [(ngModel)]="inspectorData.scale" 
                      (ngModelChange)="onInspectorChange()"
                      class="w-full accent-brand-cyan cursor-pointer" />
                </div>

                <!-- Times -->
                <div class="grid grid-cols-2 gap-3">
                   <div class="space-y-1">
                      <label class="text-[10px] text-slate-400 uppercase font-semibold">Başlangıç (sn)</label>
                      <input type="number" step="0.1" [(ngModel)]="inspectorData.timestamp" (ngModelChange)="onInspectorChange()" class="w-full bg-dark-900 border border-slate-700 rounded-lg p-2 text-xs text-white focus:border-brand-cyan focus:outline-none" />
                   </div>
                   <div class="space-y-1">
                      <label class="text-[10px] text-slate-400 uppercase font-semibold">Süre (sn)</label>
                      <input type="number" step="0.1" [(ngModel)]="inspectorData.duration" (ngModelChange)="onInspectorChange()" class="w-full bg-dark-900 border border-slate-700 rounded-lg p-2 text-xs text-white focus:border-brand-cyan focus:outline-none" />
                   </div>
                </div>

                <!-- Appearance -->
                <div class="grid grid-cols-2 gap-3" *ngIf="inspectorData.type === 'text'">
                   <div class="space-y-1">
                      <label class="text-[10px] text-slate-400 uppercase font-semibold">Yazı Rengi</label>
                      <div class="flex items-center gap-2">
                        <input type="color" [(ngModel)]="inspectorData.color" (ngModelChange)="onInspectorChange()" class="w-8 h-8 rounded border border-slate-700 bg-transparent p-0 cursor-pointer" />
                        <input type="text" [(ngModel)]="inspectorData.color" (ngModelChange)="onInspectorChange()" class="flex-1 bg-dark-900 border border-slate-700 rounded-lg p-2 text-xs text-white focus:border-brand-cyan focus:outline-none font-mono" placeholder="#FFFFFF" />
                      </div>
                   </div>
                   <div class="space-y-1">
                      <label class="text-[10px] text-slate-400 uppercase font-semibold">Boyut (px)</label>
                      <input type="number" [(ngModel)]="inspectorData.fontSize" (ngModelChange)="onInspectorChange()" class="w-full bg-dark-900 border border-slate-700 rounded-lg p-2 text-xs text-white focus:border-brand-cyan focus:outline-none" />
                   </div>
                </div>

                <div class="space-y-1" *ngIf="inspectorData.type === 'text'">
                   <label class="text-[10px] text-slate-400 uppercase font-semibold">Yazı Tipi (Font & Tipografi)</label>
                   <select [(ngModel)]="inspectorData.font" (ngModelChange)="onInspectorChange()" class="w-full bg-dark-900 border border-slate-700 rounded-lg p-2 text-xs text-white focus:border-brand-cyan focus:outline-none">
                     <optgroup label="🔥 YouTube & Sosyal Medya Başlık">
                       <option value="Bebas Neue">Bebas Neue (Büyük & Vurucu)</option>
                       <option value="Montserrat">Montserrat (Modern & Kalın)</option>
                       <option value="Anton">Anton (Ağır & Dikkat Çekici)</option>
                       <option value="Oswald">Oswald (Dar & Yüksek Başlık)</option>
                       <option value="Impact">Impact (Klasik Meme/YouTube)</option>
                     </optgroup>
                     <optgroup label="✨ Modern & Geometrik Sans">
                       <option value="Poppins">Poppins (Temiz & Yuvarlak)</option>
                       <option value="Outfit">Outfit (Fütüristik Sans)</option>
                       <option value="Inter">Inter (Ultra Okunabilir UI)</option>
                       <option value="Roboto">Roboto (Google Standart)</option>
                       <option value="Arial">Arial (Sade & Klasik)</option>
                     </optgroup>
                     <optgroup label="🎨 Yaratıcı & Tematik">
                       <option value="Syne">Syne (Özgün Sanatsal Başlık)</option>
                       <option value="Bangers">Bangers (Çizgi Roman / Enerjik)</option>
                       <option value="Cinzel">Cinzel (Sinematik Serif / Tarih)</option>
                       <option value="Playfair Display">Playfair Display (Zarif Serif)</option>
                       <option value="Fira Code">Fira Code (Kod / Teknoloji)</option>
                       <option value="Comic Sans MS">Comic Sans (Eğlenceli)</option>
                     </optgroup>
                   </select>
                </div>

                <!-- Animation & Position -->
                <div class="grid grid-cols-2 gap-3">
                   <div class="space-y-1">
                      <label class="text-[10px] text-slate-400 uppercase font-semibold">X Konumu (%)</label>
                      <input type="number" step="0.5" [(ngModel)]="inspectorData.positionX" (ngModelChange)="onInspectorChange()" class="w-full bg-dark-900 border border-slate-700 rounded-lg p-2 text-xs text-white focus:border-brand-cyan focus:outline-none" />
                   </div>
                   <div class="space-y-1">
                      <label class="text-[10px] text-slate-400 uppercase font-semibold">Y Konumu (%)</label>
                      <input type="number" step="0.5" [(ngModel)]="inspectorData.positionY" (ngModelChange)="onInspectorChange()" class="w-full bg-dark-900 border border-slate-700 rounded-lg p-2 text-xs text-white focus:border-brand-cyan focus:outline-none" />
                   </div>
                </div>

                <!-- Katman Sırası / Hiyerarşi (Z-Index) -->
                <div class="p-3 bg-dark-950/70 rounded-xl border border-slate-800 space-y-2">
                   <div class="flex items-center justify-between">
                     <span class="text-[10px] text-slate-400 uppercase font-semibold flex items-center gap-1.5">
                       <span>🥞</span> Katman Hiyerarşisi (Z-Index)
                     </span>
                     <span class="text-[11px] font-mono font-bold px-2 py-0.5 rounded bg-brand-cyan/20 text-brand-cyan border border-brand-cyan/30">
                       Katman #{{ inspectorData.trackId || 1 }}
                     </span>
                   </div>
                   <div class="grid grid-cols-2 gap-2">
                     <button 
                       type="button"
                       (click)="bringOverlayForward(selectedOverlayId()!)"
                       class="px-2.5 py-1.5 rounded-lg bg-dark-800 hover:bg-slate-700 text-xs text-white font-semibold border border-slate-700 flex items-center justify-center gap-1.5 transition-all cursor-pointer">
                       <span>🔼</span> Öne Getir (+1)
                     </button>
                     <button 
                       type="button"
                       (click)="sendOverlayBackward(selectedOverlayId()!)"
                       class="px-2.5 py-1.5 rounded-lg bg-dark-800 hover:bg-slate-700 text-xs text-white font-semibold border border-slate-700 flex items-center justify-center gap-1.5 transition-all cursor-pointer">
                       <span>🔽</span> Arkaya Gönder (-1)
                     </button>
                   </div>
                   <div class="flex items-center gap-2 pt-1 text-[10px] text-slate-400">
                     <span>Özel Katman No:</span>
                     <input 
                       type="number" 
                       min="1" 
                       max="99" 
                       [(ngModel)]="inspectorData.trackId" 
                       (ngModelChange)="onInspectorChange()" 
                       class="w-16 bg-dark-900 border border-slate-700 rounded p-1 text-xs text-center text-white focus:border-brand-cyan focus:outline-none font-mono" />
                     <span class="text-[9px] text-slate-500 italic">(Daha büyük = Daha üstte)</span>
                   </div>
                </div>
                
                <!-- Animasyon Kontrolleri (Giriş ve Çıkış) -->
                <div class="grid grid-cols-2 gap-3">
                   <div class="space-y-1">
                      <label class="text-[10px] text-slate-400 uppercase font-semibold">Giriş Animasyonu</label>
                      <select [(ngModel)]="inspectorData.animation" (ngModelChange)="onInspectorChange()" class="w-full bg-dark-900 border border-slate-700 rounded-lg p-2 text-xs text-white focus:border-brand-cyan focus:outline-none">
                        <option value="none">Yok (Doğrudan Göster)</option>
                        <option value="fade">Fade In (Yumuşak Geçiş)</option>
                        <option value="pop-up">Pop Up (Büyüyerek Çık)</option>
                        <option value="slide-up">Slide Up (Aşağıdan Yukarı)</option>
                      </select>
                   </div>
                   <div class="space-y-1">
                      <label class="text-[10px] text-slate-400 uppercase font-semibold">Çıkış Animasyonu</label>
                      <select [(ngModel)]="inspectorData.exitAnimation" (ngModelChange)="onInspectorChange()" class="w-full bg-dark-900 border border-slate-700 rounded-lg p-2 text-xs text-white focus:border-brand-cyan focus:outline-none">
                        <option value="none">Yok (Aniden Kaybol)</option>
                        <option value="fade">Fade Out (Sönerek Çık)</option>
                        <option value="scale-out">Scale Out (Küçülerek Çık)</option>
                        <option value="slide-down">Slide Down (Aşağıya İterek)</option>
                        <option value="slide-up">Slide Up (Yukarıya Uçarak)</option>
                      </select>
                   </div>
                </div>

                <!-- Actions -->
                <div class="pt-4 border-t border-slate-800 flex gap-2">
                   <button (click)="saveInspector()" class="flex-1 py-2 bg-brand-cyan hover:bg-cyan-400 text-slate-900 font-bold rounded-lg transition-colors shadow-glow-sm">
                     Kaydet
                   </button>
                   <button (click)="removeOverlay(selectedOverlayId()!)" class="px-3 py-2 bg-rose-600/20 hover:bg-rose-600/40 text-rose-400 border border-rose-600/40 font-bold rounded-lg transition-colors" title="Katmanı Sil">
                     Sil
                   </button>
                   <button (click)="cancelInspector()" class="px-3 py-2 bg-dark-800 hover:bg-dark-700 text-slate-300 border border-slate-700 font-bold rounded-lg transition-colors">
                     Kapat
                   </button>
                </div>
             </div>
          </div>

          <!-- Sekme 4: Medya (Assets & Sürükle-Bırak) -->
          <div *ngIf="activeTab() === 'media'" class="flex-1 p-5 overflow-y-auto space-y-4">
             <div class="flex items-center justify-between mb-1">
               <h3 class="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                 <span>📁</span> Medya Kütüphanesi
               </h3>
               <span class="text-[10px] text-slate-400 font-mono">{{ assets().length }} Dosya</span>
             </div>

             <!-- Gizli File Input -->
             <input 
               #assetFileInput 
               type="file" 
               (change)="onAssetFileSelected($event)" 
               accept="image/*,video/*,audio/*" 
               class="hidden" />
             
             <!-- İnteraktif Yükleme & Sürükle-Bırak Alanı -->
             <div 
               (click)="triggerAssetUpload()"
               (dragover)="onAssetDragOver($event)"
               (dragleave)="onAssetDragLeave($event)"
               (drop)="onAssetDrop($event)"
               [ngClass]="isDragOver() ? 'border-brand-cyan bg-brand-cyan/10 scale-[1.02] shadow-glow-sm' : 'border-slate-700 hover:border-slate-500 bg-dark-800/80'"
               class="p-5 rounded-xl border-2 border-dashed text-center space-y-2.5 cursor-pointer transition-all duration-150 relative select-none">
               
               <div *ngIf="isUploadingAsset()" class="py-3 flex flex-col items-center gap-2">
                 <div class="w-6 h-6 border-2 border-brand-cyan border-t-transparent rounded-full animate-spin"></div>
                 <span class="text-xs text-brand-cyan font-bold">MinIO'ya Yükleniyor...</span>
               </div>

               <div *ngIf="!isUploadingAsset()">
                 <svg class="w-8 h-8 mx-auto text-slate-400 mb-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                   <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                 </svg>
                 <p class="text-xs text-slate-300 font-medium">
                   <span class="text-brand-cyan font-bold">Dosya Seçin</span> veya buraya sürükleyip bırakın
                 </p>
                 <p class="text-[10px] text-slate-500">PNG, JPG, WEBP, MP4, MP3 (Maks 50MB)</p>
               </div>
             </div>

              <!-- Seçili Katman Bilgisi / Hızlı Değiştirme Bildirimi -->
              <div *ngIf="selectedOverlay()?.type === 'image'" class="p-2.5 rounded-xl bg-purple-950/60 border border-purple-500/40 flex items-center justify-between text-xs mt-3">
                <div class="flex items-center gap-2 truncate">
                  <span class="text-sm">🎯</span>
                  <div class="truncate">
                    <span class="text-purple-300 font-bold block">Seçili Görsel Katmanı</span>
                    <span class="text-[10px] text-slate-400 truncate">{{ selectedOverlay()?.content || selectedOverlay()?.id }}</span>
                  </div>
                </div>
                <span class="px-2 py-0.5 rounded text-[9px] font-mono font-bold bg-purple-900/80 text-purple-300 border border-purple-600/50">
                  Katman #{{ selectedOverlay()?.trackId || 1 }}
                </span>
              </div>

             <!-- Kullanıcının Yüklediği Medyalar -->
             <div *ngIf="assets().length > 0" class="space-y-2 mt-2">
               <h4 class="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Yüklenen Dosyalar</h4>
               <div class="grid grid-cols-2 gap-2">
                 <div 
                   *ngFor="let asset of assets()"
                   class="aspect-video bg-dark-900 border border-slate-700/80 rounded-lg overflow-hidden relative group hover:border-brand-cyan transition-all shadow-sm">
                   
                   <!-- Görsel İse Thumbnail -->
                   <img 
                     *ngIf="asset.mimeTuru.startsWith('image/')" 
                     [src]="asset.url" 
                     [alt]="asset.dosyaAdi" 
                     class="w-full h-full object-cover" />

                   <!-- Video / Ses İse İkon -->
                   <div *ngIf="!asset.mimeTuru.startsWith('image/')" class="w-full h-full flex flex-col items-center justify-center bg-dark-800 p-2 text-center">
                     <span class="text-xl">{{ asset.mimeTuru.startsWith('audio/') ? '🎵' : '🎬' }}</span>
                     <span class="text-[9px] text-slate-300 truncate w-full mt-1">{{ asset.dosyaAdi }}</span>
                   </div>

                   <!-- Hover Kontrolleri -->
                   <div class="absolute inset-0 bg-dark-950/85 opacity-0 group-hover:opacity-100 transition-opacity flex flex-col items-center justify-center gap-1.5 p-2">
                     <button 
                       *ngIf="selectedOverlay()?.type === 'image'"
                       (click)="$event.stopPropagation(); assignAssetToSelectedOverlay(asset)"
                       class="px-2 py-1 bg-purple-600 hover:bg-purple-500 text-white font-bold text-[9px] rounded shadow transition-colors w-full flex items-center justify-center gap-1 cursor-pointer">
                       <span>🎯</span>
                       <span>Seçili Katmana Ata</span>
                     </button>
                     <button 
                       (click)="$event.stopPropagation(); addAssetOverlay(asset)"
                       class="px-2.5 py-1 bg-brand-cyan hover:bg-cyan-400 text-slate-950 font-bold text-[10px] rounded shadow-md transition-colors w-full flex items-center justify-center gap-1">
                       <span>+</span>
                       <span>Katmana Ekle</span>
                     </button>
                     <button 
                       (click)="$event.stopPropagation(); deleteAsset(asset.id)"
                       class="px-2 py-0.5 bg-rose-600/20 hover:bg-rose-600/40 text-rose-300 text-[9px] rounded border border-rose-500/30 transition-colors w-full">
                       Sil
                     </button>
                   </div>

                   <!-- Başlık Çubuğu -->
                   <div class="absolute bottom-0 inset-x-0 bg-black/60 backdrop-blur-xs px-1.5 py-0.5 truncate text-[9px] text-slate-200">
                     {{ asset.dosyaAdi }}
                   </div>
                 </div>
               </div>
             </div>
             
             <!-- Örnek Stok Görseller -->
             <div class="mt-4 pt-4 border-t border-slate-800">
               <h4 class="text-[10px] font-bold text-slate-400 uppercase mb-2">Pexels Stok Görseller (Örnek)</h4>
               <div class="grid grid-cols-2 gap-2">
                 <div class="aspect-video bg-dark-800 border border-slate-700 rounded overflow-hidden relative group cursor-pointer hover:border-brand-cyan transition-colors">
                  <img src="https://images.pexels.com/photos/1181675/pexels-photo-1181675.jpeg?auto=compress&cs=tinysrgb&w=150" class="w-full h-full object-cover" />
                  <div class="absolute inset-0 bg-dark-950/85 opacity-0 group-hover:opacity-100 transition-opacity flex flex-col items-center justify-center gap-1 p-1.5">
                    <button 
                      *ngIf="selectedOverlay()?.type === 'image'"
                      (click)="$event.stopPropagation(); assignUrlToSelectedOverlay('https://images.pexels.com/photos/1181675/pexels-photo-1181675.jpeg', 'Yazılım & Teknoloji')"
                      class="px-1.5 py-0.5 bg-purple-600 hover:bg-purple-500 text-white text-[9px] rounded font-bold w-full cursor-pointer">
                      🎯 Seçiliye Ata
                    </button>
                    <button 
                      (click)="$event.stopPropagation(); addImageOverlayFromUrl('https://images.pexels.com/photos/1181675/pexels-photo-1181675.jpeg', 'Yazılım & Teknoloji')"
                      class="px-1.5 py-0.5 bg-brand-cyan hover:bg-cyan-400 text-slate-950 text-[9px] rounded font-bold w-full cursor-pointer">
                      + Katman Ekle
                    </button>
                  </div>
                </div>
                <div class="aspect-video bg-dark-800 border border-slate-700 rounded overflow-hidden relative group cursor-pointer hover:border-brand-cyan transition-colors">
                  <img src="https://images.pexels.com/photos/3183150/pexels-photo-3183150.jpeg?auto=compress&cs=tinysrgb&w=150" class="w-full h-full object-cover" />
                  <div class="absolute inset-0 bg-dark-950/85 opacity-0 group-hover:opacity-100 transition-opacity flex flex-col items-center justify-center gap-1 p-1.5">
                    <button 
                      *ngIf="selectedOverlay()?.type === 'image'"
                      (click)="$event.stopPropagation(); assignUrlToSelectedOverlay('https://images.pexels.com/photos/3183150/pexels-photo-3183150.jpeg', 'Toplantı & Ekip')"
                      class="px-1.5 py-0.5 bg-purple-600 hover:bg-purple-500 text-white text-[9px] rounded font-bold w-full cursor-pointer">
                      🎯 Seçiliye Ata
                    </button>
                    <button 
                      (click)="$event.stopPropagation(); addImageOverlayFromUrl('https://images.pexels.com/photos/3183150/pexels-photo-3183150.jpeg', 'Toplantı & Ekip')"
                      class="px-1.5 py-0.5 bg-brand-cyan hover:bg-cyan-400 text-slate-950 text-[9px] rounded font-bold w-full cursor-pointer">
                      + Katman Ekle
                    </button>
                  </div>
                </div>
               </div>
             </div>
          </div>
        </div>
      </div>
    </main>
  `
})
export class EditorComponent implements OnInit, OnDestroy {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private projectService = inject(ProjectService);
  private videoService = inject(VideoService);
  private edlService = inject(EdlService);
  private chatService = inject(ChatService);
  private renderService = inject(RenderService);
  private assetService = inject(AssetService);
  private signalr = inject(SignalrService);

  @ViewChild('videoPlayer') videoRef!: ElementRef<HTMLVideoElement>;
  @ViewChild('chatMessagesContainer') chatContainer!: ElementRef<HTMLDivElement>;
  @ViewChild('timelineTrack') timelineTrackRef!: ElementRef<HTMLDivElement>;
  @ViewChild('assetFileInput') assetFileInput?: ElementRef<HTMLInputElement>;

  readonly assets = signal<ProjectAssetDto[]>([]);
  readonly isUploadingAsset = signal<boolean>(false);
  readonly isDragOver = signal<boolean>(false);

  projectId = '';
  readonly project = signal<ProjectDetailDto | null>(null);
  readonly edl = signal<EdlContent | null>(null);
  readonly videoUrl = signal<string>('');
  readonly currentTime = signal<number>(0);
  readonly totalDuration = signal<number>(100);

  // Altyazı & Karaoke State
  readonly showSubtitles = signal<boolean>(true);
  readonly subtitleFont = signal<string>('Montserrat, Inter, sans-serif');
  readonly subtitleColor = signal<string>('#FFFFFF');

  readonly currentSubtitleSegment = computed<TranscriptSegment | null>(() => {
    const edl = this.activeEdl();
    const segments = edl?.transcript?.segments;
    if (!segments || segments.length === 0) return null;
    const t = this.currentTime();
    return segments.find(s => t >= s.start && t <= s.end) || null;
  });

  readonly vttTrackUrl = computed<string | null>(() => {
    const edl = this.activeEdl();
    const segments = edl?.transcript?.segments;
    if (!segments || segments.length === 0) return null;

    let vttContent = 'WEBVTT\n\n';
    segments.forEach((seg, index) => {
      const start = this.formatVttTimestamp(seg.start);
      const end = this.formatVttTimestamp(seg.end);
      vttContent += `${index + 1}\n${start} --> ${end}\n${seg.text.trim()}\n\n`;
    });

    const blob = new Blob([vttContent], { type: 'text/vtt' });
    return URL.createObjectURL(blob);
  });
  readonly activeOverlays = computed(() => {
    const t = this.currentTime();
    const overlays = this.activeEdl()?.overlays || [];
    return overlays.filter(ov => t >= ov.timestamp && t <= (ov.timestamp + ov.duration));
  });
  readonly activeTab = signal<'chat' | 'overlays' | 'inspector' | 'media'>('chat');
  readonly rendering = signal<boolean>(false);
  readonly rippleAi = signal<boolean>(true); // Varsayılan: AI kısımları Sıkıştırılmış
  readonly rippleManual = signal<boolean>(true); // Varsayılan: Manuel kısımlar Sıkıştırılmış
  readonly rippleRetake = signal<boolean>(true); // Varsayılan: Retake kısımları Sıkıştırılmış
  readonly retakeCount = computed(() => {
    const edl = this.activeEdl();
    if (!edl || !edl.cuts) return 0;
    return edl.cuts.filter(c => {
      const r = (c.reason || '').toLowerCase();
      return r.includes('retake') || r.includes('tekrar');
    }).length;
  });
  readonly timelineZoom = signal<number>(1);
  readonly splitMarkers = signal<number[]>([]);
  readonly selectedClipIds = signal<string[]>([]);
  readonly selectedOverlayId = signal<string | null>(null);
  
  // Inspector Data State
  inspectorData: any = {};
  
  // Drag & Drop State
  isDraggingOverlay = false;
  isResizingOverlay = false;
  resizeEdge: 'left' | 'right' | null = null;
  dragStartX = 0;
  dragOverlayOriginalStart = 0;
  dragOverlayOriginalDuration = 0;
  
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

  // Canlı Taslak (Ghost Layer) - Yönetmen AI soru formunu doldururken ekranda canlı gösterilir
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

  // Clips (Parçalar) hesaplaması
  readonly clips = computed(() => {
    const total = this.totalDuration();
    const edl = this.activeEdl();
    const cuts = edl?.cuts || [];
    const splits = [...this.splitMarkers(), total].sort((a,b) => a-b);
    
    // Bütün sınır noktalarını (cut başı/sonu, split noktaları) topla
    let allPoints = new Set<number>();
    allPoints.add(0);
    allPoints.add(total);
    for (const s of splits) allPoints.add(s);
    for (const c of cuts) {
      allPoints.add(c.start);
      allPoints.add(c.end);
    }
    
    const sortedPoints = Array.from(allPoints).sort((a,b) => a-b);
    const result: any[] = [];
    
    for (let i = 0; i < sortedPoints.length - 1; i++) {
      const start = sortedPoints[i];
      const end = sortedPoints[i+1];
      if (end - start < 0.05) continue; // çok küçük fragmanları (artifact) atla
      
      const mid = (start + end) / 2;
      const cut = cuts.find(c => mid >= c.start && mid <= c.end);
      result.push({
        id: `clip_${i}_${start}`,
        start,
        end,
        duration: end - start,
        isCut: !!cut,
        cutObj: cut
      });
    }
    return result;
  });

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
      return `Klip (${startStr}s - ${endStr}s) - Kesmek için çift tıkla`;
    }
    if (this.isRetakeClip(clip)) {
      const desc = clip.cutObj?.command || clip.cutObj?.reason || 'Hatalı Tekrar';
      return `🔁 Hatalı Tekrar (Retake) [${startStr}s - ${endStr}s]: ${desc} - İptal edip geri almak için çift tıkla`;
    }
    if (this.isManualClip(clip)) {
      return `🖐 Manuel Kesim [${startStr}s - ${endStr}s] - İptal edip geri almak için çift tıkla`;
    }
    return `🤖 AI Jump-Cut [${startStr}s - ${endStr}s]: ${clip.cutObj?.reason || 'Sessizlik'} - İptal edip geri almak için çift tıkla`;
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

  readonly visibleDuration = computed(() => {
     return this.clips().filter(c => this.isVisible(c)).reduce((sum, c) => sum + c.duration, 0);
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
        if (v.streamUrl) {
          this.videoUrl.set(v.streamUrl);
        } else if (v.id) {
          const apiKey = environment.apiKey || 'SUPER_SECRET_OTOEDIT_KEY_123!';
          this.videoUrl.set(`${environment.apiUrl}/videos/${v.id}/stream?apiKey=${apiKey}`);
        }
        
        // v.sure is a string "hh:mm:ss.fff" from C# TimeSpan
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
        this.edl.set(res.edl);
        // EDL'den gelen duration 0 veya çok küçükse video metasını ezmesini engelle
        if (res.edl.duration && res.edl.duration > 5) {
          this.totalDuration.set(res.edl.duration);
        }
        // Seçili katman varsa verilerini yenilenen EDL ile senkronize et
        const selId = this.selectedOverlayId();
        if (selId) {
          const ov = res.edl.overlays?.find(o => o.id === selId);
          if (ov) {
            this.inspectorData = { ...this.inspectorData, ...ov };
          }
        }
      },
      error: (err) => console.error('EDL yüklenemedi:', err)
    });
  }

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
    const maxTrack = currentOverlays.reduce((max, o) => Math.max(max, o.trackId || 1), 0);
    const nextTrack = maxTrack + 1;

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

  /**
   * CANLI EDL SİMÜLASYONU:
   * Video oynarken kesilen (cut) bir bölgeye girerse beklemeden cut.end konumuna atlar.
   */
  onTimeUpdate(): void {
    const video = this.videoRef?.nativeElement;
    if (!video) return;

    const t = video.currentTime;
    this.currentTime.set(t);

    // 1. Cut atlama kontrolü (Skip logic)
    const cuts = this.activeEdl()?.cuts || [];
    for (const cut of cuts) {
      if (t >= cut.start && t < cut.end) {
        console.log(`[EDL Simülasyonu] Kesilen bölge atlanıyor: ${cut.start}s -> ${cut.end}s`);
        video.currentTime = cut.end;
        return;
      }
    }
  }

  onMetadataLoaded(): void {
    const video = this.videoRef?.nativeElement;
    if (video && video.duration && !isNaN(video.duration)) {
      this.totalDuration.set(video.duration);
    }
  }

  getRawTimeFromVisTime(visTime: number): number {
    if (!this.rippleAi() && !this.rippleManual()) {
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
    if (!this.rippleAi() && !this.rippleManual()) {
       return Math.max(0, Math.min(this.totalDuration(), rawTime));
    }
    let passed = 0;
    for (const c of this.clips()) {
       if (rawTime >= c.start && rawTime <= c.end) {
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
    if (!track) return 0;
    const rect = track.getBoundingClientRect();
    const clickX = clientX - rect.left;
    const percentage = Math.max(0, Math.min(1, clickX / rect.width));
    
    if (!this.rippleAi() && !this.rippleManual()) {
       return percentage * this.totalDuration();
    }

    const targetVisDuration = percentage * this.visibleDuration();
    return this.getRawTimeFromVisTime(targetVisDuration);
  }

  getPlayheadPosition(): number {
    const t = this.currentTime();
    if (!this.rippleAi() && !this.rippleManual()) {
       return (t / this.totalDuration()) * 100;
    }
    const visDur = this.visibleDuration();
    if (visDur <= 0) return 0;
    return (this.getVisTimeFromRawTime(t) / visDur) * 100;
  }

  getTimelineTime(event: MouseEvent): number {
    return this.getTimeAtClientX(event.clientX);
  }

  seekTimeline(event: MouseEvent): void {
    const targetTime = this.getTimeAtClientX(event.clientX);
    if (this.videoRef?.nativeElement) {
      this.videoRef.nativeElement.currentTime = targetTime;
    }
    this.currentTime.set(targetTime);
  }

  selectClip(clipId: string, event: MouseEvent): void {
    event.stopPropagation();
    
    const current = this.selectedClipIds();
    
    // Ctrl (Windows) veya Cmd (Mac) basılıysa çoklu seçim yap
    if (event.ctrlKey || event.metaKey) {
       if (current.includes(clipId)) {
          this.selectedClipIds.set(current.filter(id => id !== clipId));
       } else {
          this.selectedClipIds.set([...current, clipId]);
       }
    } else {
       // Tekli seçim
       if (current.length === 1 && current[0] === clipId) {
          this.selectedClipIds.set([]); // Zaten seçiliyse kaldır
       } else {
          this.selectedClipIds.set([clipId]);
       }
    }
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
    if (!selectedClips.length) return; // Kalanların hepsi zaten kesikse işlem yapma

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

  mergeSelectedClips(): void {
    const selIds = this.selectedClipIds();
    if (selIds.length < 2) return;
    
    const allClips = this.clips();
    const selectedClips = allClips.filter(c => selIds.includes(c.id)).sort((a,b) => a.start - b.start);
    
    // Seçili kliplerin arasındaki tüm kesimleri (cuts) bul ve sil
    const startRange = selectedClips[0].start;
    const endRange = selectedClips[selectedClips.length - 1].end;
    
    const edl = this.activeEdl();
    if (!edl || !edl.cuts) return;
    
    // Bu aralığa denk gelen tüm cut'ları bul
    const cutsToRemove = edl.cuts.filter(c => c.start >= startRange && c.end <= endRange);
    if (cutsToRemove.length === 0) {
       alert('Seçilen klipler arasında birleştirilecek (silinecek) bir kesim bulunamadı.');
       return;
    }
    
    if (confirm(`Seçili aralıktaki ${cutsToRemove.length} kesim iptal edilerek klipler birleştirilecek. Onaylıyor musunuz?`)) {
       const patchCuts = cutsToRemove.map(c => ({ id: c.id, start: 0, end: 0, action: 'remove' }));
       this.edlService.patchEdl(this.projectId, {
          cuts: patchCuts as any
       }).subscribe(() => {
          this.selectedClipIds.set([]); // seçimi temizle
          this.loadEdl();
       });
    }
  }

  zoomIn(): void {
    this.timelineZoom.update(z => z + 0.5);
  }

  zoomOut(): void {
    this.timelineZoom.update(z => Math.max(1, z - 0.5));
  }

  addSplitMarker(): void {
    const t = this.currentTime();
    this.splitMarkers.update(m => [...m, t]);
  }

  getOverlayTop(ov: OverlayItem): string {
    if (ov.positionY !== undefined && ov.positionY !== null) return `${ov.positionY}%`;
    const vPos = ov.position?.[1] || 'bottom';
    if (vPos === 'top') return '10%';
    if (vPos === 'center') return '45%';
    return '80%';
  }

  getOverlayLeft(ov: OverlayItem): string {
    if (ov.positionX !== undefined && ov.positionX !== null) return `${ov.positionX}%`;
    const hPos = ov.position?.[0] || 'center';
    if (hPos === 'left') return '10%';
    if (hPos === 'right') return '70%';
    return '35%';
  }

  getOverlayZIndex(ov: OverlayItem): number {
    if (this.selectedOverlayId() === ov.id) {
      return 50; // Seçili eleman her zaman en üstte yer alır (kulp ve sürükleme engellenemez)
    }
    return 20 + (ov.trackId ?? 1);
  }

  isOverlayExiting(ov: OverlayItem): boolean {
    const remaining = (ov.timestamp + ov.duration) - this.currentTime();
    return remaining > 0 && remaining <= 0.45;
  }

  getOverlayAnimationClass(ov: OverlayItem): string {
    if (this.isOverlayExiting(ov)) {
      const exitAnim = ov.exitAnimation || 'fade';
      switch (exitAnim) {
        case 'fade': return 'animate-fade-out';
        case 'pop-up':
        case 'scale-out': return 'animate-scale-out';
        case 'slide-down': return 'animate-slide-down-out';
        case 'slide-up': return 'animate-slide-up-out';
        case 'none': return '';
        default: return 'animate-fade-out';
      }
    }

    const enterAnim = ov.animation || 'none';
    switch (enterAnim) {
      case 'fade': return 'animate-fade-in';
      case 'pop-up': return 'scale-in';
      case 'slide-up': return 'translate-y-4 opacity-0 animate-slide-up-forwards';
      case 'none': return '';
      default: return '';
    }
  }

  bringOverlayForward(ovId: string): void {
    const ov = this.activeEdl()?.overlays?.find(o => o.id === ovId);
    if (!ov) return;
    const currentTrack = ov.trackId ?? 1;
    const newTrack = currentTrack + 1;
    ov.trackId = newTrack;
    if (this.selectedOverlayId() === ovId && this.inspectorData) {
      this.inspectorData.trackId = newTrack;
    }
    this.edl.update(e => e ? { ...e } : null);
    this.edlService.patchEdl(this.projectId, {
      overlays: [{ id: ovId, trackId: newTrack, action: 'update' } as any]
    }).subscribe({
      next: () => this.loadEdl(),
      error: (err) => console.error('Katman sırası öne alınamadı:', err)
    });
  }

  sendOverlayBackward(ovId: string): void {
    const ov = this.activeEdl()?.overlays?.find(o => o.id === ovId);
    if (!ov) return;
    const currentTrack = ov.trackId ?? 1;
    const newTrack = Math.max(1, currentTrack - 1);
    ov.trackId = newTrack;
    if (this.selectedOverlayId() === ovId && this.inspectorData) {
      this.inspectorData.trackId = newTrack;
    }
    this.edl.update(e => e ? { ...e } : null);
    this.edlService.patchEdl(this.projectId, {
      overlays: [{ id: ovId, trackId: newTrack, action: 'update' } as any]
    }).subscribe({
      next: () => this.loadEdl(),
      error: (err) => console.error('Katman sırası arkaya alınamadı:', err)
    });
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
        this.activeTab.set('inspector');
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
        this.activeTab.set('inspector');
      });
    }
  }
  
  onCanvasDragStart(event: MouseEvent, overlayId: string): void {
     event.preventDefault(); // Prevent text selection
     event.stopPropagation();
     if (this.selectedOverlayId() !== overlayId) {
        this.selectOverlay(overlayId);
     }
     this.isCanvasDragging = true;
     this.canvasDragOverlayId = overlayId;
     this.canvasDragStartX = event.clientX;
     this.canvasDragStartY = event.clientY;
     
     const ov = this.activeEdl()?.overlays?.find(o => o.id === overlayId);
     if (ov) {
        if (ov.positionX !== undefined && ov.positionX !== null) {
           this.canvasDragOriginalX = ov.positionX;
        } else {
           // Parse current string pos to approximate percentage
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
     if (!this.rippleAi() && !this.rippleManual()) {
        return {
           left: `${(ov.timestamp / this.totalDuration()) * 100}%`,
           width: `${(ov.duration / this.totalDuration()) * 100}%`
        };
     }

     const startVis = this.getVisTimeFromRawTime(ov.timestamp);
     const endVis = this.getVisTimeFromRawTime(ov.timestamp + ov.duration);
     const visDur = this.visibleDuration();
     
     if (visDur <= 0 || endVis <= startVis) return { display: 'none' };
     
     return {
        left: `${(startVis / visDur) * 100}%`,
        width: `${Math.max(0.6, ((endVis - startVis) / visDur) * 100)}%`
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
    const maxTrack = currentOverlays.reduce((max, o) => Math.max(max, o.trackId || 1), 0);
    const nextTrack = maxTrack + 1;

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
        this.activeTab.set('inspector');
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
    // Yüklenmiş görsel yoksa kullanıcıyı dosya yüklemesi / seçmesi için Medya sekmesine yönlendir
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
    const maxTrack = currentOverlays.reduce((max, o) => Math.max(max, o.trackId || 1), 0);
    const nextTrack = maxTrack + 1;

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
        this.activeTab.set('inspector');
      },
      error: (err) => console.error('Görsel eklenemedi:', err)
    });
  }

  // Geriye dönük uyumluluk için alias'lar
  addOverlayToSelected(): void {
    this.addTextOverlay();
  }

  addImageOverlayToSelected(): void {
    this.addImageOverlay();
  }

  selectOverlay(id: string): void {
     this.selectedOverlayId.set(id);
     const ov = this.activeEdl()?.overlays?.find(o => o.id === id);
     if (ov) {
        this.inspectorData = {
          id: ov.id,
          type: ov.type || 'text',
          content: ov.content || '',
          source: ov.source || '',
          timestamp: ov.timestamp ?? 0,
          duration: ov.duration ?? 3,
          fontSize: ov.fontSize ?? 48,
          font: ov.font || 'Inter',
          color: ov.color || '#FFFFFF',
          positionX: ov.positionX ?? 50,
          positionY: ov.positionY ?? 50,
          animation: ov.animation || 'none',
          exitAnimation: ov.exitAnimation || 'fade',
          scale: ov.scale ?? 1.0,
          trackId: ov.trackId ?? 1
        };
        this.activeTab.set('inspector');
        
        // Zaman imleci katmanın dışındaysa, ekranda görünmesi için oraya git
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
      ov.color = this.inspectorData.color;
      ov.fontSize = Number(this.inspectorData.fontSize) || 48;
      ov.font = this.inspectorData.font;
      ov.scale = Number(this.inspectorData.scale) || 1.0;
      ov.animation = this.inspectorData.animation;
      ov.exitAnimation = this.inspectorData.exitAnimation || 'fade';
      ov.positionX = Number(this.inspectorData.positionX);
      ov.positionY = Number(this.inspectorData.positionY);
      ov.timestamp = Number(this.inspectorData.timestamp);
      ov.duration = Number(this.inspectorData.duration);
      ov.trackId = Number(this.inspectorData.trackId) || 1;
      
      this.edl.update(e => e ? { ...e } : null);
    }
  }

  saveInspector(): void {
     const selId = this.selectedOverlayId();
     if (!selId || !this.inspectorData) return;
     
     this.edlService.patchEdl(this.projectId, {
        overlays: [{
          id: selId,
          type: this.inspectorData.type || 'text',
          content: this.inspectorData.content,
          source: this.inspectorData.source,
          timestamp: Number(this.inspectorData.timestamp),
          duration: Number(this.inspectorData.duration),
          positionX: Number(this.inspectorData.positionX),
          positionY: Number(this.inspectorData.positionY),
          color: this.inspectorData.color,
          fontSize: Number(this.inspectorData.fontSize),
          font: this.inspectorData.font,
          scale: Number(this.inspectorData.scale),
          animation: this.inspectorData.animation,
          exitAnimation: this.inspectorData.exitAnimation || 'fade',
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
     this.activeTab.set('overlays');
     this.loadEdl();
  }

  setPrompt(p: string): void {
    this.userPrompt = p;
  }

  sendChatMessage(): void {
    if (!this.userPrompt.trim() || this.chatLoading()) return;

    let msgText = this.userPrompt.trim();
    
    // Seçili klip(ler) varsa prompt'a context ekle
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

    // Kullanıcı mesajını anında UI'a ekle
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
        // Asistan yanıtını ekle
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

        // EDL'i yenile
        this.loadEdl();
      },
      error: (err) => {
        this.chatLoading.set(false);
        alert('AI yanıt verirken hata oluştu: ' + (err.error?.detail || err.message));
      }
    });
  }

  acceptSuggestion(sug: SuggestionItem): void {
    this.edlService.patchEdl(this.projectId, {
      suggestions: [{ ...sug, status: 'accepted', action: 'update' }],
      overlays: [{
        id: `ov_${sug.id}`,
        type: sug.type === 'image_broll' ? 'image' : 'text',
        content: sug.content,
        source: sug.sourceUrl,
        timestamp: sug.timestamp,
        duration: sug.duration,
        action: 'add'
      }]
    }).subscribe(() => this.loadEdl());
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

  // B.1 HitL Patch Uygulama
  previewPatch(msg: ChatMessageDto): void {
    if (!msg.pendingEdlPatch) return;
    if (this.previewMessageId() === msg.id) {
       // Kapat
       this.previewEdl.set(null);
       this.previewMessageId.set(null);
       return;
    }

    // Önizleme mantığı: edl()'i JSON kopyala, pendingEdlPatch'i frontend'de manuel uygula
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
    
    // Geri sarıp göstersin
    if (this.videoRef?.nativeElement) {
      // Eğer patch'te belirli bir timestamp varsa, oraya sarsın (kabaca ilk elemanın süresi)
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
    this.previewEdl.set(null); // Preview temizle
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
    '#FFFFFF', // Beyaz
    '#FACC15', // Canlı Sarı
    '#06B6D4', // Turkuaz / Cyan
    '#EF4444', // Vurgu Kırmızı
    '#10B981', // Neon Yeşil
    '#A855F7', // Mor
    '#F97316', // Turuncu
    '#000000'  // Siyah
  ];

  getPresetCoords(preset: string): { x: number; y: number } {
    switch (preset) {
      case 'top-left': return { x: 18, y: 15 };
      case 'top-center': return { x: 50, y: 15 };
      case 'top-right': return { x: 82, y: 15 };
      case 'center-left': return { x: 18, y: 50 };
      case 'center': return { x: 50, y: 50 };
      case 'center-right': return { x: 82, y: 50 };
      case 'bottom-left': return { x: 18, y: 85 };
      case 'bottom-center': return { x: 50, y: 85 };
      case 'bottom-right': return { x: 82, y: 85 };
      default: return { x: 50, y: 85 };
    }
  }

  getMarkerPosition(msg: ChatMessageDto, field: FormFieldDto): { x: number; y: number } {
    if (msg.formData?.['positionX'] !== undefined && msg.formData?.['positionY'] !== undefined) {
      return { x: Number(msg.formData['positionX']), y: Number(msg.formData['positionY']) };
    }
    const pos = msg.formData?.[field.id] || field.defaultValue || 'bottom-center';
    return this.getPresetCoords(String(pos));
  }

  onMiniStageClick(event: MouseEvent, msg: ChatMessageDto, fieldId: string): void {
    const target = event.currentTarget as HTMLElement;
    if (!target) return;
    const rect = target.getBoundingClientRect();
    const clickX = event.clientX - rect.left;
    const clickY = event.clientY - rect.top;
    const posX = Math.max(5, Math.min(95, Math.round((clickX / rect.width) * 100)));
    const posY = Math.max(5, Math.min(95, Math.round((clickY / rect.height) * 100)));

    if (!msg.formData) msg.formData = {};
    msg.formData[fieldId] = `X: %${posX}, Y: %${posY}`;
    msg.formData['positionX'] = posX;
    msg.formData['positionY'] = posY;
    this.chatMessages.update(msgs => [...msgs]);
  }

  setPresetPosition(msg: ChatMessageDto, fieldId: string, preset: string): void {
    const coords = this.getPresetCoords(preset);
    if (!msg.formData) msg.formData = {};
    msg.formData[fieldId] = preset;
    msg.formData['positionX'] = coords.x;
    msg.formData['positionY'] = coords.y;
    this.chatMessages.update(msgs => [...msgs]);
  }

  getOptValue(opt: any): string {
    if (typeof opt === 'string') return opt;
    return opt?.value ?? opt?.label ?? String(opt);
  }

  getOptLabel(opt: any): string {
    if (typeof opt === 'string') return opt;
    return opt?.label ?? opt?.value ?? String(opt);
  }
  
  updateFormData(msg: ChatMessageDto, fieldId: string, value: any): void {
     if (!msg.formData) {
        msg.formData = {};
        if (msg.formFields) {
           msg.formFields.forEach(f => {
              msg.formData[f.id] = f.defaultValue;
           });
        }
     }
     msg.formData[fieldId] = value;
     this.chatMessages.update(msgs => [...msgs]);
  }
  
  submitForm(msg: ChatMessageDto): void {
     if (!msg.formFields) return;
     
     // Varsayılan değerleri tanımla
     if (!msg.formData) msg.formData = {};
     msg.formFields.forEach(f => {
         if (msg.formData[f.id] === undefined) {
             msg.formData[f.id] = f.defaultValue;
         }
     });
     
     // Kullanıcı yanıtını oluştur
     let responseText = "Belirttiğim özellikler ile katmanı ekle:\n";
     msg.formFields.forEach(f => {
         responseText += `- ${f.label}: ${msg.formData[f.id]}\n`;
     });
     if (msg.formData['positionX'] !== undefined && msg.formData['positionY'] !== undefined) {
         responseText += `[Koordinatlar: positionX=${msg.formData['positionX']}, positionY=${msg.formData['positionY']}]\n`;
     }
     
     this.userPrompt = responseText;
     
     // Formu cevaplandı olarak işaretle
     msg.patchDurumu = 'answered';
     this.chatMessages.update(msgs => [...msgs]);
     
     this.sendChatMessage();
  }

  // B.1 Undo / Redo (Basit)& Shortcuts
  @HostListener('window:keydown', ['$event'])
  handleKeyboardEvent(event: KeyboardEvent) {
    const target = event.target as HTMLElement;
    if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA') return;

    if (event.ctrlKey && event.key.toLowerCase() === 'z') {
      event.preventDefault();
      this.undo();
    } else if (event.ctrlKey && event.key.toLowerCase() === 'y') {
      event.preventDefault();
      this.redo();
    } else if (event.key.toLowerCase() === 'b') {
      event.preventDefault();
      this.addSplitMarker();
    } else if (event.key === 'Delete' || event.key === 'Backspace') {
      if (this.selectedClipIds().length > 0) {
         event.preventDefault();
         this.deleteSelectedClips();
      }
    } else if (event.key.toLowerCase() === 'c') {
      event.preventDefault();
      this.toggleSubtitles();
    }
  }

  undo(): void {
    this.edlService.undoEdl(this.projectId).subscribe({
      next: (res) => { 
        this.edl.set(res.edl); 
        console.log('Geri alındı (Undo)'); 
      },
      error: (err) => console.log('Geri alınacak işlem yok veya hata: ', err)
    });
  }

  redo(): void {
    this.edlService.redoEdl(this.projectId).subscribe({
      next: (res) => { 
        this.edl.set(res.edl); 
        console.log('İleri alındı (Redo)'); 
      },
      error: (err) => console.log('İleri alınacak işlem yok veya hata: ', err)
    });
  }



  removeCut(cutId: string): void {
    if (confirm('Bu kesimi iptal edip sahneyi geri getirmek istiyor musunuz?')) {
      this.edlService.patchEdl(this.projectId, {
        cuts: [{ id: cutId, start: 0, end: 0, action: 'remove' } as any]
      }).subscribe(() => this.loadEdl());
    }
  }

  // --- Drag & Drop Methods ---

  onOverlayDragStart(event: MouseEvent, overlayId: string): void {
     event.stopPropagation();
     this.selectOverlay(overlayId);
     this.isDraggingOverlay = true;
     this.dragStartX = event.clientX;
     const ov = this.activeEdl()?.overlays?.find(o => o.id === overlayId);
     if (ov) {
        this.dragOverlayOriginalStart = ov.timestamp;
     }
  }

  onOverlayResizeStart(event: MouseEvent, overlayId: string, edge: 'left' | 'right'): void {
     event.stopPropagation();
     this.selectOverlay(overlayId);
     this.isResizingOverlay = true;
     this.resizeEdge = edge;
     this.dragStartX = event.clientX;
     const ov = this.activeEdl()?.overlays?.find(o => o.id === overlayId);
     if (ov) {
        this.dragOverlayOriginalStart = ov.timestamp;
        this.dragOverlayOriginalDuration = ov.duration;
     }
  }

  onCanvasResizeStart(event: MouseEvent, overlayId: string): void {
      event.preventDefault();
      event.stopPropagation();
      if (this.selectedOverlayId() !== overlayId) {
        this.selectOverlay(overlayId);
      }
      this.isCanvasResizing = true;
      this.canvasResizeOverlayId = overlayId;
      this.canvasResizeStartX = event.clientX;
      this.canvasResizeStartY = event.clientY;
      const ov = this.activeEdl()?.overlays?.find(o => o.id === overlayId);
      if (ov) {
          this.canvasResizeOriginalScale = ov.scale || 1.0;
          this.canvasResizeOriginalFontSize = ov.fontSize || 48;
      }
  }

  @HostListener('window:mousemove', ['$event'])
  onGlobalMouseMove(event: MouseEvent): void {
     if (this.isCanvasDragging) {
         const video = this.videoRef?.nativeElement;
         if (!video) return;
         
         const rect = video.getBoundingClientRect();
         const deltaX = event.clientX - this.canvasDragStartX;
         const deltaY = event.clientY - this.canvasDragStartY;
         
         // Convert pixels to percentage of the video container
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
         }
         return;
     }

     if (this.isCanvasResizing) {
         const deltaX = event.clientX - this.canvasResizeStartX;
         const deltaY = event.clientY - this.canvasResizeStartY;
         // En baskın çekme eksenini (yatay, dikey veya çapraz) algıla:
         const delta = Math.abs(deltaX) >= Math.abs(deltaY) ? deltaX : deltaY;

         const ov = this.activeEdl()?.overlays?.find(o => o.id === this.canvasResizeOverlayId);
         if (ov) {
             if (ov.type === 'image') {
                 let newScale = this.canvasResizeOriginalScale + (delta / 100);
                 if (newScale < 0.2) newScale = 0.2;
                 if (newScale > 5.0) newScale = 5.0;
                 ov.scale = newScale;
                 if (this.inspectorData && this.inspectorData.id === ov.id) {
                     this.inspectorData.scale = parseFloat(newScale.toFixed(2));
                 }
             } else if (ov.type === 'text') {
                 let newSize = this.canvasResizeOriginalFontSize + delta;
                 if (newSize < 10) newSize = 10;
                 if (newSize > 400) newSize = 400;
                 ov.fontSize = newSize;
                 if (this.inspectorData && this.inspectorData.id === ov.id) {
                     this.inspectorData.fontSize = Math.round(newSize);
                 }
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
        if (!this.rippleAi() && !this.rippleManual()) {
           const track = this.timelineTrackRef?.nativeElement;
           if (!track) return;
           const rect = track.getBoundingClientRect();
           const pixelsPerSec = rect.width / this.totalDuration();
           const deltaSec = (event.clientX - this.dragStartX) / (pixelsPerSec * this.timelineZoom());
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
        
        if (this.inspectorData && this.inspectorData.id === ovId) {
            this.inspectorData.timestamp = ov.timestamp;
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

  isWordActive(word: TranscriptWord): boolean {
    const t = this.currentTime();
    return t >= word.start && t <= word.end;
  }

  toggleSubtitles(): void {
    this.showSubtitles.update(v => !v);
  }

  private formatVttTimestamp(seconds: number): string {
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    const ms = Math.floor((seconds % 1) * 1000);
    return `${hrs.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}.${ms.toString().padStart(3, '0')}`;
  }
}
