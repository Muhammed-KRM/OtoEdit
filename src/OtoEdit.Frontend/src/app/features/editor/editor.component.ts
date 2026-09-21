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
import { SignalrService } from '../../core/services/signalr.service';
import { ProjectDetailDto } from '../../core/models/project.model';
import { VideoDetailDto } from '../../core/models/video.model';
import { CutItem, EdlContent, EdlDto, OverlayItem, SuggestionItem } from '../../core/models/edl.model';
import { ChatMessageDto } from '../../core/models/chat.model';
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
            </video>

              <!-- Dinamik Aktif Metin Overlay Önizlemesi -->
              <div 
                *ngFor="let ov of activeOverlays()" 
                (mousedown)="onCanvasDragStart($event, ov.id)"
                (click)="selectOverlay(ov.id)"
                [style.top]="getOverlayTop(ov)"
                [style.left]="getOverlayLeft(ov)"
                class="absolute transition-none z-20 cursor-move hover:ring-2 hover:ring-brand-cyan rounded p-1 -translate-x-1/2 -translate-y-1/2"
                [style.color]="ov.color || '#FFFFFF'"
                [style.backgroundColor]="ov.backgroundColor || 'transparent'"
                [style.fontFamily]="ov.font || 'Inter, sans-serif'">
                <span *ngIf="ov.type === 'text'" class="px-3 py-1 rounded font-bold" [style.fontSize.px]="(ov.fontSize || 48) / 2">
                  {{ ov.content }}
                </span>
              </div>
          </div>

          <!-- Video Zaman Kontrolleri -->
          <div class="flex items-center justify-between text-xs font-mono text-slate-400 px-2">
            <div class="flex gap-4">
              <span>İzlenen: {{ currentTime() | duration }} / {{ totalDuration() | duration }}</span>
              <span class="text-brand-cyan font-bold">Net Süre: {{ visibleDuration() | duration }}</span>
            </div>
            <div class="flex items-center gap-4">
              <span class="flex items-center gap-1.5"><span class="w-2.5 h-2.5 rounded-sm bg-emerald-500"></span> Korunan</span>
              <span class="flex items-center gap-1.5"><span class="w-2.5 h-2.5 rounded-sm bg-rose-500"></span> Kesilen (Jump-Cut)</span>
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
                <button (click)="rippleManual.set(!rippleManual())" class="p-1 px-2 rounded bg-dark-800 text-slate-400 hover:text-sky-400 border border-slate-700" title="Manuel Kesimleri Sıkıştır/Genişlet">
                  {{ rippleManual() ? '🖐 Manuel Sıkıştırılmış' : '🖐 Manuel Geniş' }}
                </button>
                <button (click)="deleteSelectedClip()" *ngIf="selectedClipId()" class="p-1 px-2 rounded bg-rose-600/80 text-white font-bold hover:bg-rose-500 border border-rose-500 shadow-glow-sm" title="Seçili Klibi Sil (Del)">✕ Sil (Del)</button>
                <button (click)="addOverlayToSelected()" *ngIf="selectedClipId()" class="p-1 px-2 rounded bg-brand-cyan text-slate-900 font-bold hover:bg-cyan-400 border border-cyan-500 shadow-glow-sm" title="Seçili Klibe Yazı Ekle">T Yazı Ekle</button>
                <span class="text-slate-400 ml-2 text-[10px]" *ngIf="!selectedClipId()">Kesmek/silmek için yeşil klibe çift tıklayın.</span>
              </div>
            </div>

            <!-- Interaktif Timeline Track -->
            <div class="overflow-x-auto pb-4 w-full scrollbar-thin scrollbar-thumb-slate-700 scrollbar-track-dark-900">
              <div 
                #timelineTrack
                (click)="seekTimeline($event)"
                [style.width.%]="100 * timelineZoom()"
                class="relative h-14 bg-dark-900 rounded-xl overflow-hidden cursor-pointer border border-slate-700/60 select-none min-w-full flex">
                
                <!-- Klipler (Flexbox ile sıralanır) -->
                <ng-container *ngFor="let clip of clips()">
                  <div 
                    *ngIf="isVisible(clip)"
                    (click)="selectClip(clip.id, $event)"
                    (dblclick)="toggleClip(clip, $event)"
                    class="relative h-full transition-colors border-r border-white/40 box-border group"
                    [ngClass]="{
                       'bg-rose-900/80 hover:bg-rose-800': clip.isCut && clip.cutObj?.reason !== 'Manuel kesim',
                       'bg-rose-500/80 hover:bg-rose-400': clip.isCut && clip.cutObj?.reason === 'Manuel kesim',
                       'bg-emerald-600/40 hover:bg-emerald-500/60': !clip.isCut,
                       'ring-2 ring-inset ring-brand-yellow shadow-[0_0_10px_rgba(250,204,21,0.5)] z-10': selectedClipId() === clip.id
                    }"
                    [style.width.%]="(clip.duration / ( (rippleAi() || rippleManual()) ? visibleDuration() : totalDuration() )) * 100"
                    [title]="'Klip (' + (clip.start | number:'1.1-1') + 's - ' + (clip.end | number:'1.1-1') + 's) - İşlem için çift tıkla'">
                    
                    <!-- Kırmızı kısımları silme (Gizle modu kapalıyken) -->
                    <div *ngIf="clip.isCut" class="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100">
                      <span class="text-[10px] text-white font-bold">✕ İptal</span>
                    </div>
                  </div>
                </ng-container>

              <!-- Overlay Marker'ları (Yazı ve Görsel İşaretleri) -->
              <div 
                *ngFor="let ov of activeEdl()?.overlays"
                (mousedown)="onOverlayDragStart($event, ov.id)"
                (click)="$event.stopPropagation(); selectOverlay(ov.id)"
                class="absolute top-1 bottom-1 rounded-md opacity-90 transition-shadow cursor-grab active:cursor-grabbing z-20 group"
                [ngClass]="[
                   ov.type === 'text' ? 'bg-sky-400/80 border border-sky-300' : 'bg-purple-500/80 border border-purple-300',
                   selectedOverlayId() === ov.id ? 'ring-2 ring-white shadow-[0_0_8px_white]' : ''
                ]"
                [ngStyle]="getOverlayStyle(ov)"
                [title]="ov.type + ': ' + (ov.content || ov.id)">
                
                <!-- Sol Kenar (Resize Handle) -->
                <div 
                  (mousedown)="onOverlayResizeStart($event, ov.id, 'left')"
                  class="absolute left-0 top-0 bottom-0 w-2.5 cursor-ew-resize opacity-0 group-hover:opacity-100 hover:bg-white/50 bg-white/30 rounded-l-md z-30">
                </div>
                <!-- Sağ Kenar (Resize Handle) -->
                <div 
                  (mousedown)="onOverlayResizeStart($event, ov.id, 'right')"
                  class="absolute right-0 top-0 bottom-0 w-2.5 cursor-ew-resize opacity-0 group-hover:opacity-100 hover:bg-white/50 bg-white/30 rounded-r-md z-30">
                </div>
              </div>

              <!-- Zaman İmleci (Playhead) -->
              <div 
                class="absolute top-0 bottom-0 w-0.5 bg-white shadow-[0_0_8px_white] z-30 pointer-events-none"
                [style.left.%]="getPlayheadPosition()">
                <div class="w-3 h-3 bg-white rotate-45 -translate-x-[5px] -translate-y-[4px]"></div>
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
              *ngIf="selectedOverlay()"
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
                  
                  <!-- Dinamik Form (Clarification) -->
                  <div *ngIf="msg.patchDurumu === 'clarification' && msg.formFields" class="mt-3 p-3 bg-dark-900 border border-brand-cyan/30 rounded-xl space-y-3">
                     <p class="text-[10px] text-brand-cyan font-bold uppercase">Devam Etmek İçin Seçim Yapın</p>
                     
                     <div *ngFor="let field of msg.formFields" class="space-y-1">
                        <label class="text-[10px] text-slate-400">{{ field.label }}</label>
                        
                        <input *ngIf="field.type === 'text'" type="text"
                               [ngModel]="msg.formData?.[field.id] || field.defaultValue"
                               (ngModelChange)="updateFormData(msg, field.id, $event)"
                               class="w-full bg-dark-800 border border-slate-700 rounded p-1.5 text-xs focus:border-brand-cyan outline-none" />
                               
                        <input *ngIf="field.type === 'number'" type="number"
                               [ngModel]="msg.formData?.[field.id] || field.defaultValue"
                               (ngModelChange)="updateFormData(msg, field.id, $event)"
                               class="w-full bg-dark-800 border border-slate-700 rounded p-1.5 text-xs focus:border-brand-cyan outline-none" />
                               
                        <div *ngIf="field.type === 'color'" class="flex gap-2 items-center">
                           <input type="color" 
                                  [ngModel]="msg.formData?.[field.id] || field.defaultValue || '#ffffff'"
                                  (ngModelChange)="updateFormData(msg, field.id, $event)"
                                  class="w-8 h-8 rounded cursor-pointer border border-slate-700 p-0 bg-transparent" />
                           <span class="text-xs font-mono text-slate-400">{{ msg.formData?.[field.id] || field.defaultValue || '#ffffff' }}</span>
                        </div>
                        
                        <select *ngIf="field.type === 'select'"
                                [ngModel]="msg.formData?.[field.id] || field.defaultValue"
                                (ngModelChange)="updateFormData(msg, field.id, $event)"
                                class="w-full bg-dark-800 border border-slate-700 rounded p-1.5 text-xs focus:border-brand-cyan outline-none">
                            <option *ngFor="let opt of field.options" [value]="opt.value">{{ opt.label }}</option>
                        </select>
                     </div>
                     
                     <button (click)="submitForm(msg)" class="w-full py-2 bg-brand-cyan text-slate-900 font-bold rounded hover:bg-cyan-400 transition-colors mt-2">
                        Seçimleri Gönder
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

              <button 
                (click)="$event.stopPropagation(); removeOverlay(ov.id)" 
                title="Katmanı Sil"
                class="text-slate-500 hover:text-rose-400 p-1.5 rounded-lg hover:bg-rose-500/10 transition-colors">
                ✕
              </button>
            </div>
          </div>

          <!-- Sekme 3: Özellikler (Inspector) -->
          <div *ngIf="activeTab() === 'inspector' && selectedOverlay()" class="flex-1 p-5 overflow-y-auto space-y-4">
             <h3 class="text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">Katman Özellikleri</h3>
             
             <!-- Content Edit -->
             <div class="space-y-1">
                <label class="text-[10px] text-slate-400 uppercase">Metin İçeriği</label>
                <textarea 
                   [(ngModel)]="inspectorData.content" 
                   class="w-full bg-dark-900 border border-slate-700 rounded-lg p-2 text-xs text-white focus:border-brand-cyan focus:outline-none"
                   rows="3"></textarea>
             </div>

             <!-- Times -->
             <div class="grid grid-cols-2 gap-3">
                <div class="space-y-1">
                   <label class="text-[10px] text-slate-400 uppercase">Başlangıç (sn)</label>
                   <input type="number" step="0.1" [(ngModel)]="inspectorData.timestamp" class="w-full bg-dark-900 border border-slate-700 rounded-lg p-2 text-xs text-white" />
                </div>
                <div class="space-y-1">
                   <label class="text-[10px] text-slate-400 uppercase">Süre (sn)</label>
                   <input type="number" step="0.1" [(ngModel)]="inspectorData.duration" class="w-full bg-dark-900 border border-slate-700 rounded-lg p-2 text-xs text-white" />
                </div>
             </div>

             <!-- Appearance -->
             <div class="grid grid-cols-2 gap-3" *ngIf="inspectorData.type === 'text'">
                <div class="space-y-1">
                   <label class="text-[10px] text-slate-400 uppercase">Yazı Rengi (Hex)</label>
                   <div class="flex items-center gap-2">
                     <input type="color" [(ngModel)]="inspectorData.color" class="w-8 h-8 rounded border border-slate-700 bg-transparent p-0 cursor-pointer" />
                     <input type="text" [(ngModel)]="inspectorData.color" class="flex-1 bg-dark-900 border border-slate-700 rounded-lg p-2 text-xs text-white" placeholder="#FFFFFF" />
                   </div>
                </div>
                <div class="space-y-1">
                   <label class="text-[10px] text-slate-400 uppercase">Boyut (px)</label>
                   <input type="number" [(ngModel)]="inspectorData.fontSize" class="w-full bg-dark-900 border border-slate-700 rounded-lg p-2 text-xs text-white" />
                </div>
             </div>

             <div class="space-y-1" *ngIf="inspectorData.type === 'text'">
                <label class="text-[10px] text-slate-400 uppercase">Font</label>
                <select [(ngModel)]="inspectorData.font" class="w-full bg-dark-900 border border-slate-700 rounded-lg p-2 text-xs text-white">
                  <option value="Inter">Inter (Varsayılan)</option>
                  <option value="Arial">Arial</option>
                  <option value="Roboto">Roboto</option>
                  <option value="Montserrat">Montserrat</option>
                  <option value="Impact">Impact</option>
                  <option value="Comic Sans MS">Comic Sans (Eğlenceli)</option>
                </select>
             </div>

             <!-- Animation & Position -->
             <div class="grid grid-cols-2 gap-3">
                <div class="space-y-1">
                   <label class="text-[10px] text-slate-400 uppercase">X Konumu (%)</label>
                   <input type="number" step="0.1" [(ngModel)]="inspectorData.positionX" class="w-full bg-dark-900 border border-slate-700 rounded-lg p-2 text-xs text-white" />
                </div>
                <div class="space-y-1">
                   <label class="text-[10px] text-slate-400 uppercase">Y Konumu (%)</label>
                   <input type="number" step="0.1" [(ngModel)]="inspectorData.positionY" class="w-full bg-dark-900 border border-slate-700 rounded-lg p-2 text-xs text-white" />
                </div>
             </div>
             
             <div class="grid grid-cols-2 gap-3 mt-3">
                <div class="space-y-1">
                   <label class="text-[10px] text-slate-400 uppercase">Giriş Animasyonu</label>
                   <select [(ngModel)]="inspectorData.animation" class="w-full bg-dark-900 border border-slate-700 rounded-lg p-2 text-xs text-white">
                     <option value="none">Yok</option>
                     <option value="fade">Fade In</option>
                     <option value="pop-up">Pop Up</option>
                     <option value="slide-up">Slide Up</option>
                   </select>
                </div>
             </div>

             <!-- Actions -->
             <div class="pt-4 border-t border-slate-800 flex gap-2">
                <button (click)="saveInspector()" class="flex-1 py-2 bg-brand-cyan hover:bg-cyan-400 text-slate-900 font-bold rounded-lg transition-colors">Kaydet</button>
                <button (click)="cancelInspector()" class="flex-1 py-2 bg-dark-800 hover:bg-dark-700 text-white border border-slate-700 font-bold rounded-lg transition-colors">İptal</button>
             </div>
          </div>

          <!-- Sekme 4: Medya (Assets) -->
          <div *ngIf="activeTab() === 'media'" class="flex-1 p-5 overflow-y-auto space-y-4">
             <h3 class="text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">Medya Kütüphanesi</h3>
             
             <div class="p-4 rounded-xl bg-dark-800 border border-slate-700 text-center space-y-3">
               <svg class="w-8 h-8 mx-auto text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                 <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
               </svg>
               <p class="text-xs text-slate-400">Yeni bir görsel veya ses yüklemek için tıklayın.</p>
               <button class="px-4 py-2 bg-brand-cyan/20 text-brand-cyan font-bold text-xs rounded hover:bg-brand-cyan/30">Dosya Yükle</button>
             </div>
             
             <div class="mt-4">
               <h4 class="text-[10px] font-bold text-slate-400 uppercase mb-2">Stok Görseller (Pexels)</h4>
               <div class="flex gap-2 mb-3">
                 <input type="text" placeholder="Arama yap..." class="flex-1 bg-dark-900 border border-slate-700 rounded-lg p-2 text-xs text-white" />
                 <button class="px-3 bg-dark-700 text-white rounded text-xs">Ara</button>
               </div>
               <div class="grid grid-cols-2 gap-2">
                 <div class="aspect-video bg-dark-800 border border-slate-700 rounded overflow-hidden relative group cursor-pointer hover:border-brand-cyan">
                   <div class="absolute inset-0 flex items-center justify-center text-slate-500 text-xs">Stok 1</div>
                   <div class="absolute inset-0 bg-brand-cyan/20 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                     <span class="bg-black/50 text-white text-[10px] px-2 py-1 rounded">Ekle +</span>
                   </div>
                 </div>
                 <div class="aspect-video bg-dark-800 border border-slate-700 rounded overflow-hidden relative group cursor-pointer hover:border-brand-cyan">
                   <div class="absolute inset-0 flex items-center justify-center text-slate-500 text-xs">Stok 2</div>
                   <div class="absolute inset-0 bg-brand-cyan/20 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                     <span class="bg-black/50 text-white text-[10px] px-2 py-1 rounded">Ekle +</span>
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
  private signalr = inject(SignalrService);

  @ViewChild('videoPlayer') videoRef!: ElementRef<HTMLVideoElement>;
  @ViewChild('chatMessagesContainer') chatContainer!: ElementRef<HTMLDivElement>;
  @ViewChild('timelineTrack') timelineTrackRef!: ElementRef<HTMLDivElement>;

  projectId = '';
  readonly project = signal<ProjectDetailDto | null>(null);
  readonly edl = signal<EdlContent | null>(null);
  readonly videoUrl = signal<string>('');
  readonly currentTime = signal<number>(0);
  readonly totalDuration = signal<number>(100);
  readonly activeOverlays = signal<OverlayItem[]>([]);
  readonly activeTab = signal<'chat' | 'overlays' | 'inspector' | 'media'>('chat');
  readonly rendering = signal<boolean>(false);
  readonly rippleAi = signal<boolean>(true); // Varsayılan: AI kısımları Sıkıştırılmış
  readonly rippleManual = signal<boolean>(true); // Varsayılan: Manuel kısımlar Sıkıştırılmış
  readonly timelineZoom = signal<number>(1);
  readonly splitMarkers = signal<number[]>([]);
  readonly selectedClipId = signal<string | null>(null);
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
  
  readonly selectedOverlay = computed(() => {
    const id = this.selectedOverlayId();
    if (!id) return null;
    return this.activeEdl()?.overlays?.find(o => o.id === id) || null;
  });

  // Preview Logic
  readonly previewEdl = signal<EdlContent | null>(null);
  readonly previewMessageId = signal<string | null>(null);
  readonly activeEdl = computed(() => this.previewEdl() || this.edl());

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

  isVisible(clip: any): boolean {
    if (!clip.isCut) return true;
    if (clip.cutObj.reason === 'Manuel kesim') {
       return !this.rippleManual();
    }
    return !this.rippleAi();
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

    // 2. Aktif metin overlay'lerini güncelle
    const overlays = this.activeEdl()?.overlays || [];
    const active = overlays.filter(ov => t >= ov.timestamp && t <= (ov.timestamp + ov.duration));
    this.activeOverlays.set(active);
  }

  onMetadataLoaded(): void {
    const video = this.videoRef?.nativeElement;
    if (video && video.duration && !isNaN(video.duration)) {
      this.totalDuration.set(video.duration);
    }
  }

  getPlayheadPosition(): number {
    const t = this.currentTime();
    if (!this.rippleAi() && !this.rippleManual()) {
       return (t / this.totalDuration()) * 100;
    }

    let passedDuration = 0;
    for (const c of this.clips()) {
       if (t >= c.start && t <= c.end) {
          if (this.isVisible(c)) {
             passedDuration += (t - c.start);
          }
          break;
       }
       if (this.isVisible(c)) {
          passedDuration += c.duration;
       }
    }
    
    const visDur = this.visibleDuration();
    if (visDur === 0) return 0;
    return (passedDuration / visDur) * 100;
  }

  getTimelineTime(event: MouseEvent): number {
    const target = event.currentTarget as HTMLElement;
    const rect = target.getBoundingClientRect();
    const clickX = event.clientX - rect.left;
    const percentage = Math.max(0, Math.min(1, clickX / rect.width));
    
    if (!this.rippleAi() && !this.rippleManual()) {
       return percentage * this.totalDuration();
    }

    const targetVisDuration = percentage * this.visibleDuration();
    let accumulated = 0;
    let targetTime = 0;
    
    for (const c of this.clips()) {
       if (this.isVisible(c)) {
          if (accumulated + c.duration >= targetVisDuration) {
             targetTime = c.start + (targetVisDuration - accumulated);
             break;
          }
          accumulated += c.duration;
       }
    }
    return targetTime;
  }

  seekTimeline(event: MouseEvent): void {
    const targetTime = this.getTimelineTime(event);
    if (this.videoRef?.nativeElement) {
      this.videoRef.nativeElement.currentTime = targetTime;
    }
  }

  selectClip(clipId: string, event: MouseEvent): void {
    event.stopPropagation();
    if (this.selectedClipId() === clipId) {
      this.selectedClipId.set(null); // Tekrar tıklanınca seçimi kaldır
    } else {
      this.selectedClipId.set(clipId);
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
          this.selectedClipId.set(null); // Kesilen klibin seçimini iptal et
          this.loadEdl();
        });
     }
  }

  deleteSelectedClip(): void {
    const selId = this.selectedClipId();
    if (!selId) return;
    const clip = this.clips().find(c => c.id === selId);
    if (!clip || clip.isCut) return; // Zaten kesikse silinmez

    const newCut = { 
      id: `manual_cut_${Date.now()}`, 
      start: clip.start, 
      end: clip.end, 
      reason: 'Manuel kesim' 
    };
    this.edlService.patchEdl(this.projectId, {
      cuts: [{ ...newCut, action: 'add' } as any]
    }).subscribe(() => {
      this.selectedClipId.set(null);
      this.loadEdl();
    });
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
  
  onCanvasDragStart(event: MouseEvent, overlayId: string): void {
     event.preventDefault(); // Prevent text selection
     event.stopPropagation();
     this.selectOverlay(overlayId);
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

     const getVisTime = (t: number) => {
        let passed = 0;
        for (const c of this.clips()) {
           if (t >= c.start && t <= c.end) {
              if (this.isVisible(c)) passed += (t - c.start);
              break;
           }
           if (this.isVisible(c)) passed += c.duration;
        }
        return passed;
     };

     const startVis = getVisTime(ov.timestamp);
     const endVis = getVisTime(ov.timestamp + ov.duration);
     const visDur = this.visibleDuration();
     
     if (visDur === 0) return { display: 'none' };
     
     return {
        left: `${(startVis / visDur) * 100}%`,
        width: `${((endVis - startVis) / visDur) * 100}%`
     };
  }

  addOverlayToSelected(): void {
    const selId = this.selectedClipId();
    if (!selId) return;
    const clip = this.clips().find(c => c.id === selId);
    if (!clip) return;

    const text = prompt('Klibe eklenecek yazıyı girin:');
    if (text) {
      const newOvId = `ov_${Date.now()}`;
      this.edlService.patchEdl(this.projectId, {
        overlays: [{
          id: newOvId,
          type: 'text',
          content: text,
          timestamp: clip.start,
          duration: clip.duration,
          color: '#FFFFFF',
          fontSize: 64,
          font: 'Inter',
          action: 'add'
        }]
      }).subscribe(() => {
         this.loadEdl();
         this.selectOverlay(newOvId);
      });
    }
  }

  selectOverlay(id: string): void {
     this.selectedOverlayId.set(id);
     const ov = this.activeEdl()?.overlays?.find(o => o.id === id);
     if (ov) {
        this.inspectorData = { ...ov }; // clone for form binding
        this.activeTab.set('inspector');
     }
  }

  saveInspector(): void {
     if (!this.selectedOverlayId() || !this.inspectorData) return;
     
     // Update the backend EDL with the modified overlay
     this.edlService.patchEdl(this.projectId, {
        overlays: [{ ...this.inspectorData, action: 'update' } as any]
     }).subscribe(() => {
        this.loadEdl();
        // optionally show toast "Saved"
     });
  }

  cancelInspector(): void {
     this.selectedOverlayId.set(null);
     this.activeTab.set('overlays');
  }

  setPrompt(p: string): void {
    this.userPrompt = p;
  }

  sendChatMessage(): void {
    if (!this.userPrompt.trim() || this.chatLoading()) return;

    let msgText = this.userPrompt.trim();
    
    // Seçili klip varsa prompt'a context ekle
    const selId = this.selectedClipId();
    if (selId) {
       const clip = this.clips().find(c => c.id === selId);
       if (clip) {
          msgText = `[Seçili Klip: ${clip.start.toFixed(1)}s - ${clip.end.toFixed(1)}s arası] ` + msgText;
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
    this.previewMessageId.set(msg.id);
    
    // Geri sarıp göstersin
    if (this.videoRef?.nativeElement) {
      // Eğer patch'te belirli bir timestamp varsa, oraya sarsın (kabaca ilk elemanın süresi)
      let seekTo = 0;
      if (patch.cuts?.length > 0) seekTo = Math.max(0, patch.cuts[0].start - 2);
      else if (patch.overlays?.length > 0) seekTo = Math.max(0, patch.overlays[0].timestamp - 2);
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

  // --- Dynamic Form Methods ---
  
  updateFormData(msg: ChatMessageDto, fieldId: string, value: any): void {
     if (!msg.formData) {
        msg.formData = {};
        // Initialize defaults
        if (msg.formFields) {
           msg.formFields.forEach(f => {
              msg.formData[f.id] = f.defaultValue;
           });
        }
     }
     msg.formData[fieldId] = value;
  }
  
  submitForm(msg: ChatMessageDto): void {
     if (!msg.formFields) return;
     
     // Initialize defaults for untouched fields
     if (!msg.formData) msg.formData = {};
     msg.formFields.forEach(f => {
         if (msg.formData[f.id] === undefined) {
             msg.formData[f.id] = f.defaultValue;
         }
     });
     
     // Build user response
     let responseText = "İstediğim özellikler:\n";
     msg.formFields.forEach(f => {
         responseText += `- ${f.label}: ${msg.formData[f.id]}\n`;
     });
     
     this.userPrompt = responseText;
     
     // Mark the form as answered (hide it)
     msg.patchDurumu = 'answered';
     
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
    } else if (event.key === 'Delete') {
      if (this.selectedClipId()) {
         event.preventDefault();
         this.deleteSelectedClip();
      }
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
             
             // Clamping between 0 and 100
             if (newX < 0) newX = 0; if (newX > 100) newX = 100;
             if (newY < 0) newY = 0; if (newY > 100) newY = 100;
             
             ov.positionX = newX;
             ov.positionY = newY;
             
             if (this.inspectorData && this.inspectorData.id === ov.id) {
                 this.inspectorData.positionX = parseFloat(newX.toFixed(2));
                 this.inspectorData.positionY = parseFloat(newY.toFixed(2));
             }
         }
         return; // Skip timeline drag logic
     }
     
     if (!this.isDraggingOverlay && !this.isResizingOverlay) return;
     
     const track = this.timelineTrackRef?.nativeElement;
     if (!track) return;
     
     const rect = track.getBoundingClientRect();
     // Pixel to seconds
     const totalDur = (this.rippleAi() || this.rippleManual()) ? this.visibleDuration() : this.totalDuration();
     if (totalDur <= 0) return;
     
     const pixelsPerSecond = rect.width / totalDur;
     const deltaX = event.clientX - this.dragStartX;
     const deltaSeconds = deltaX / (pixelsPerSecond * this.timelineZoom());
     
     const ovId = this.selectedOverlayId();
     if (!ovId) return;
     
     const overlays = this.activeEdl()?.overlays || [];
     const ov = overlays.find(o => o.id === ovId);
     if (!ov) return;
     
     if (this.isDraggingOverlay) {
        let newStart = this.dragOverlayOriginalStart + deltaSeconds;
        if (newStart < 0) newStart = 0;
        
        ov.timestamp = newStart;
        if (this.inspectorData && this.inspectorData.id === ovId) {
            this.inspectorData.timestamp = parseFloat(newStart.toFixed(2));
        }
     } else if (this.isResizingOverlay) {
        if (this.resizeEdge === 'left') {
           let newStart = this.dragOverlayOriginalStart + deltaSeconds;
           let newDuration = this.dragOverlayOriginalDuration - deltaSeconds;
           
           if (newDuration < 0.5) {
              newDuration = 0.5;
              newStart = this.dragOverlayOriginalStart + (this.dragOverlayOriginalDuration - 0.5);
           }
           if (newStart < 0) {
              newStart = 0;
              newDuration = this.dragOverlayOriginalDuration + this.dragOverlayOriginalStart;
           }
           ov.timestamp = newStart;
           ov.duration = newDuration;
           
           if (this.inspectorData && this.inspectorData.id === ovId) {
              this.inspectorData.timestamp = parseFloat(newStart.toFixed(2));
              this.inspectorData.duration = parseFloat(newDuration.toFixed(2));
           }
        } else if (this.resizeEdge === 'right') {
           let newDuration = this.dragOverlayOriginalDuration + deltaSeconds;
           if (newDuration < 0.5) newDuration = 0.5;
           ov.duration = newDuration;
           
           if (this.inspectorData && this.inspectorData.id === ovId) {
              this.inspectorData.duration = parseFloat(newDuration.toFixed(2));
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
         
         if (ovId) {
             const ov = this.activeEdl()?.overlays?.find(o => o.id === ovId);
             if (ov) {
                 this.edlService.patchEdl(this.projectId, {
                     overlays: [{ id: ov.id, positionX: ov.positionX, positionY: ov.positionY, action: 'update' } as any]
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
               // Update Backend with the new time
               this.edlService.patchEdl(this.projectId, {
                  overlays: [{ id: ov.id, timestamp: ov.timestamp, duration: ov.duration, type: ov.type, action: 'update' } as any]
               }).subscribe(() => {
                  this.loadEdl(); // Reload to ensure sync
               });
            }
         }
     }
  }
}
