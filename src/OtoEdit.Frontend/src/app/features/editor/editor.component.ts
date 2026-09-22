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
  imports: [CommonModule, RouterLink, FormsModule, NavbarComponent, DurationPipe],
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
              class="flex-1 py-2.5 text-[11px] border-b-2 transition-all flex items-center justify-center gap-1.5 cursor-pointer">
              <span>📁</span>
              <span>Medya</span>
            </button>
            <button 
              (click)="activeTab.set('chat')"
              [ngClass]="activeTab() === 'chat' ? 'text-brand-cyan border-brand-cyan bg-dark-950 font-bold' : 'text-slate-400 hover:text-slate-200 border-transparent'"
              class="flex-1 py-2.5 text-[11px] border-b-2 transition-all flex items-center justify-center gap-1.5 cursor-pointer">
              <span>🤖</span>
              <span>AI Kurgu</span>
            </button>
            <button 
              (click)="activeTab.set('transcript')"
              [ngClass]="activeTab() === 'transcript' ? 'text-brand-cyan border-brand-cyan bg-dark-950 font-bold' : 'text-slate-400 hover:text-slate-200 border-transparent'"
              class="flex-1 py-2.5 text-[11px] border-b-2 transition-all flex items-center justify-center gap-1.5 cursor-pointer">
              <span>📝</span>
              <span>Metin</span>
            </button>
            <button 
              (click)="activeTab.set('overlays')"
              [ngClass]="activeTab() === 'overlays' ? 'text-brand-cyan border-brand-cyan bg-dark-950 font-bold' : 'text-slate-400 hover:text-slate-200 border-transparent'"
              class="flex-1 py-2.5 text-[11px] border-b-2 transition-all flex items-center justify-center gap-1.5 cursor-pointer">
              <span>🥞</span>
              <span>Katman ({{ activeEdl()?.overlays?.length || 0 }})</span>
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

            <!-- Örnek Stok Görseller -->
            <div class="pt-2 border-t border-slate-800/80">
              <span class="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1.5">Pexels Stok (Örnek)</span>
              <div class="grid grid-cols-2 gap-2">
                <div class="aspect-video bg-dark-800 border border-slate-700 rounded overflow-hidden relative group hover:border-brand-cyan">
                  <img src="https://images.pexels.com/photos/1181675/pexels-photo-1181675.jpeg?auto=compress&cs=tinysrgb&w=150" class="w-full h-full object-cover" />
                  <div class="absolute inset-0 bg-dark-950/85 opacity-0 group-hover:opacity-100 transition-opacity flex flex-col items-center justify-center gap-1 p-1">
                    <button (click)="$event.stopPropagation(); addImageOverlayFromUrl('https://images.pexels.com/photos/1181675/pexels-photo-1181675.jpeg', 'Yazılım')" class="px-2 py-0.5 bg-brand-cyan text-slate-950 text-[9px] rounded font-bold w-full">+ Katman</button>
                  </div>
                </div>
                <div class="aspect-video bg-dark-800 border border-slate-700 rounded overflow-hidden relative group hover:border-brand-cyan">
                  <img src="https://images.pexels.com/photos/3183150/pexels-photo-3183150.jpeg?auto=compress&cs=tinysrgb&w=150" class="w-full h-full object-cover" />
                  <div class="absolute inset-0 bg-dark-950/85 opacity-0 group-hover:opacity-100 transition-opacity flex flex-col items-center justify-center gap-1 p-1">
                    <button (click)="$event.stopPropagation(); addImageOverlayFromUrl('https://images.pexels.com/photos/3183150/pexels-photo-3183150.jpeg', 'Ekip')" class="px-2 py-0.5 bg-brand-cyan text-slate-950 text-[9px] rounded font-bold w-full">+ Katman</button>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Sekme 2: AI Kurgu Sohbeti -->
          <div *ngIf="activeTab() === 'chat'" class="flex-1 flex flex-col h-full overflow-hidden">
            <div #chatMessagesContainer class="flex-1 p-3 overflow-y-auto space-y-3">
              <div *ngIf="chatMessages().length === 0" class="text-center py-6 text-slate-500 text-xs">
                <p class="mb-2 font-medium">💡 AI ile videonuzu düzenleyin:</p>
                <div class="space-y-1.5 text-slate-300 text-[11px]">
                  <p class="p-2 rounded-lg bg-dark-900 border border-slate-800 cursor-pointer hover:border-brand-cyan/60 transition-colors" (click)="setPrompt('Girişteki sessizlikleri kes')">"Girişteki sessizlikleri kes"</p>
                  <p class="p-2 rounded-lg bg-dark-900 border border-slate-800 cursor-pointer hover:border-brand-cyan/60 transition-colors" (click)="setPrompt('10. saniyeye Kanala Abone Ol yazısı koy')">"10. saniyeye Kanala Abone Ol yazısı koy"</p>
                  <p class="p-2 rounded-lg bg-dark-900 border border-slate-800 cursor-pointer hover:border-brand-cyan/60 transition-colors" (click)="setPrompt('20. saniyeye kedi görseli ekle')">"20. saniyeye kedi görseli ekle"</p>
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
              (click)="seekToTranscript(seg.start)"
              class="p-2 rounded-lg border border-slate-800 bg-dark-900/60 hover:bg-dark-800 hover:border-brand-cyan/50 cursor-pointer transition-all space-y-1 group">
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
          <!-- Monitör Sahnesi -->
          <div class="relative w-full flex-1 max-w-[860px] bg-black rounded-xl overflow-hidden shadow-2xl border border-slate-800/80 flex items-center justify-center min-h-0">
            <video 
              #videoPlayer
              [src]="videoUrl()"
              (timeupdate)="onTimeUpdate()"
              (loadedmetadata)="onMetadataLoaded()"
              (play)="isPlaying.set(true)"
              (pause)="isPlaying.set(false)"
              class="w-full h-full object-contain max-h-[460px]">
              
            </video>

            <!-- Dinamik Aktif Metin & Görsel Overlay Önizlemesi -->
            <div 
              *ngFor="let ov of activeOverlays()" 
              (mousedown)="onCanvasDragStart($event, ov.id)"
              (click)="$event.stopPropagation(); selectOverlay(ov.id)"
              (contextmenu)="openOverlayContextMenu($event, ov)"
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
                
                <div *ngIf="!ov.source" class="px-3 py-2 rounded-lg bg-dark-800/90 border border-brand-cyan/40 text-brand-cyan text-xs font-bold flex items-center gap-1.5">
                  <span>🖼️</span>
                  <span>{{ ov.content || 'B-Roll Görseli' }}</span>
                </div>
              </div>

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

            <!-- TikTok / Reels Karaoke Altyazı -->
            <div 
              *ngIf="showSubtitles() && currentSubtitleSegment() as seg" 
              class="absolute bottom-5 left-1/2 -translate-x-1/2 z-25 max-w-[85%] text-center pointer-events-none select-none px-4 py-1.5 rounded-xl bg-black/75 backdrop-blur-md border border-white/10 shadow-2xl">
              <div class="flex flex-wrap items-center justify-center gap-x-1.5 gap-y-0.5" [style.fontFamily]="subtitleFont()" [style.color]="subtitleColor()">
                <ng-container *ngIf="seg.words && seg.words.length > 0; else plainText">
                  <span 
                    *ngFor="let w of seg.words"
                    class="transition-all duration-100 inline-block px-0.5 rounded text-sm md:text-base"
                    [ngClass]="isWordActive(w) ? 'text-amber-300 font-black scale-110 bg-amber-400/20 shadow-glow-sm' : 'text-slate-100 font-semibold opacity-90'">
                    {{ w.word }}
                  </span>
                </ng-container>
                <ng-template #plainText>
                  <span class="font-bold text-slate-100 text-sm md:text-base drop-shadow">{{ seg.text }}</span>
                </ng-template>
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

            <!-- Sağ: Altyazı ve Tam Ekran -->
            <div class="flex items-center gap-2">
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

        <!-- 3. SAĞ PANEL: Context-Aware Inspector (Özellikler) -->
        <aside class="w-[290px] xl:w-[330px] shrink-0 flex flex-col border-l border-slate-800 bg-dark-900 overflow-y-auto p-4 space-y-4">
          <!-- 1. Durum: Katman Seçili -->
          <div *ngIf="selectedOverlay()" class="space-y-4">
            <div class="flex items-center justify-between border-b border-slate-800 pb-2">
              <h3 class="text-xs font-bold text-slate-200 uppercase tracking-wider">Katman Özellikleri</h3>
              <span [ngClass]="inspectorData.type === 'text' ? 'bg-sky-500/20 text-sky-400 border-sky-500/30' : 'bg-purple-500/20 text-purple-400 border-purple-500/30'" class="px-2 py-0.5 rounded text-[10px] font-bold uppercase border">
                {{ inspectorData.type === 'text' ? 'Metin Katmanı' : 'Görsel Katmanı' }}
              </span>
            </div>

            <!-- İçerik -->
            <div class="space-y-1">
              <label class="text-[10px] text-slate-400 uppercase font-semibold">
                {{ inspectorData.type === 'image' ? 'Görsel Başlığı / Açıklaması' : 'Metin İçeriği' }}
              </label>
              <textarea 
                [(ngModel)]="inspectorData.content" 
                (ngModelChange)="onInspectorChange()"
                class="w-full bg-dark-950 border border-slate-700 rounded-lg p-2 text-xs text-white focus:border-brand-cyan focus:outline-none"
                rows="2"></textarea>
            </div>

            <!-- Görsel Kaynağı (Image ise) -->
            <div class="space-y-1" *ngIf="inspectorData.type === 'image'">
              <div class="flex items-center justify-between">
                <label class="text-[10px] text-slate-400 uppercase font-semibold">Görsel URL / Stok</label>
                <button type="button" (click)="activeTab.set('media')" class="text-[10px] font-bold text-brand-cyan hover:underline cursor-pointer">📁 Medyadan Seç</button>
              </div>
              <input type="text" [(ngModel)]="inspectorData.source" (ngModelChange)="onInspectorChange()" class="w-full bg-dark-950 border border-slate-700 rounded-lg p-1.5 text-xs text-white focus:border-brand-cyan focus:outline-none" placeholder="https://..." />
            </div>

            <!-- Ölçek (Image ise) -->
            <div class="space-y-1" *ngIf="inspectorData.type === 'image'">
              <div class="flex justify-between items-center text-[10px] text-slate-400 uppercase font-semibold">
                <span>Ölçek / Boyut</span>
                <span class="text-brand-cyan font-bold">{{ inspectorData.scale || 1.0 }}x</span>
              </div>
              <input type="range" min="0.2" max="2.5" step="0.05" [(ngModel)]="inspectorData.scale" (ngModelChange)="onInspectorChange()" class="w-full accent-brand-cyan cursor-pointer" />
            </div>

            <!-- Zamanlar -->
            <div class="grid grid-cols-2 gap-2.5">
              <div class="space-y-1">
                <label class="text-[10px] text-slate-400 uppercase font-semibold">Başlangıç (sn)</label>
                <input type="number" step="0.1" [(ngModel)]="inspectorData.timestamp" (ngModelChange)="onInspectorChange()" class="w-full bg-dark-950 border border-slate-700 rounded-lg p-1.5 text-xs text-white focus:border-brand-cyan font-mono" />
              </div>
              <div class="space-y-1">
                <label class="text-[10px] text-slate-400 uppercase font-semibold">Süre (sn)</label>
                <input type="number" step="0.1" [(ngModel)]="inspectorData.duration" (ngModelChange)="onInspectorChange()" class="w-full bg-dark-950 border border-slate-700 rounded-lg p-1.5 text-xs text-white focus:border-brand-cyan font-mono" />
              </div>
            </div>

            <!-- Tipografi & Renk (Text ise) -->
            <div class="grid grid-cols-2 gap-2.5" *ngIf="inspectorData.type === 'text'">
              <div class="space-y-1">
                <label class="text-[10px] text-slate-400 uppercase font-semibold">Yazı Rengi</label>
                <div class="flex items-center gap-1.5">
                  <input type="color" [(ngModel)]="inspectorData.color" (ngModelChange)="onInspectorChange()" class="w-7 h-7 rounded border border-slate-700 bg-transparent p-0 cursor-pointer" />
                  <input type="text" [(ngModel)]="inspectorData.color" (ngModelChange)="onInspectorChange()" class="flex-1 bg-dark-950 border border-slate-700 rounded-lg p-1.5 text-xs text-white font-mono" />
                </div>
              </div>
              <div class="space-y-1">
                <label class="text-[10px] text-slate-400 uppercase font-semibold">Boyut (px)</label>
                <input type="number" [(ngModel)]="inspectorData.fontSize" (ngModelChange)="onInspectorChange()" class="w-full bg-dark-950 border border-slate-700 rounded-lg p-1.5 text-xs text-white font-mono" />
              </div>
            </div>

            <div class="space-y-1" *ngIf="inspectorData.type === 'text'">
              <label class="text-[10px] text-slate-400 uppercase font-semibold">Yazı Tipi (Font)</label>
              <select [(ngModel)]="inspectorData.font" (ngModelChange)="onInspectorChange()" class="w-full bg-dark-950 border border-slate-700 rounded-lg p-1.5 text-xs text-white focus:border-brand-cyan outline-none">
                <option value="Bebas Neue">Bebas Neue (Büyük & Vurucu)</option>
                <option value="Montserrat">Montserrat (Modern Kalın)</option>
                <option value="Anton">Anton (Dikkat Çekici)</option>
                <option value="Poppins">Poppins (Temiz & Yuvarlak)</option>
                <option value="Outfit">Outfit (Fütüristik Sans)</option>
                <option value="Inter">Inter (Ultra Okunabilir UI)</option>
                <option value="Arial">Arial (Sade & Klasik)</option>
                <option value="Cinzel">Cinzel (Sinematik Serif)</option>
              </select>
            </div>

            <!-- Pozisyon X & Y -->
            <div class="grid grid-cols-2 gap-2.5">
              <div class="space-y-1">
                <label class="text-[10px] text-slate-400 uppercase font-semibold">X Konum (%)</label>
                <input type="number" step="0.5" [(ngModel)]="inspectorData.positionX" (ngModelChange)="onInspectorChange()" class="w-full bg-dark-950 border border-slate-700 rounded-lg p-1.5 text-xs text-white font-mono" />
              </div>
              <div class="space-y-1">
                <label class="text-[10px] text-slate-400 uppercase font-semibold">Y Konum (%)</label>
                <input type="number" step="0.5" [(ngModel)]="inspectorData.positionY" (ngModelChange)="onInspectorChange()" class="w-full bg-dark-950 border border-slate-700 rounded-lg p-1.5 text-xs text-white font-mono" />
              </div>
            </div>

            <!-- Katman Sırası / Track Kanalı -->
            <div class="p-2.5 bg-dark-950 rounded-xl border border-slate-800 space-y-2">
              <div class="flex items-center justify-between">
                <span class="text-[10px] text-slate-400 uppercase font-semibold">🥞 Katman Kanalı</span>
                <span class="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-brand-cyan/20 text-brand-cyan">
                  T{{ inspectorData.trackId || 1 }}
                </span>
              </div>
              <div class="flex items-center gap-1 flex-wrap">
                <button 
                  *ngFor="let t of overlayTrackNumbers()" 
                  type="button"
                  (click)="setOverlayTrack(selectedOverlayId()!, t)"
                  [ngClass]="(inspectorData.trackId || 1) === t ? 'bg-sky-500 text-white font-bold border-sky-400' : 'bg-dark-800 text-slate-400 hover:text-white border-slate-700'"
                  class="px-2 py-0.5 rounded text-[10px] border transition-all cursor-pointer font-mono">
                  T{{ t }}
                </button>
                <button type="button" (click)="addTrackLane()" class="px-2 py-0.5 rounded text-[10px] bg-dark-800 text-sky-400 border border-slate-700 font-semibold cursor-pointer">+ Yeni</button>
              </div>
            </div>

            <!-- Animasyonlar -->
            <div class="grid grid-cols-2 gap-2.5">
              <div class="space-y-1">
                <label class="text-[10px] text-slate-400 uppercase font-semibold">Giriş</label>
                <select [(ngModel)]="inspectorData.animation" (ngModelChange)="onInspectorChange()" class="w-full bg-dark-950 border border-slate-700 rounded-lg p-1.5 text-xs text-white outline-none">
                  <option value="none">Yok</option>
                  <option value="fade">Fade In</option>
                  <option value="pop-up">Pop Up</option>
                  <option value="slide-up">Slide Up</option>
                </select>
              </div>
              <div class="space-y-1">
                <label class="text-[10px] text-slate-400 uppercase font-semibold">Çıkış</label>
                <select [(ngModel)]="inspectorData.exitAnimation" (ngModelChange)="onInspectorChange()" class="w-full bg-dark-950 border border-slate-700 rounded-lg p-1.5 text-xs text-white outline-none">
                  <option value="none">Yok</option>
                  <option value="fade">Fade Out</option>
                  <option value="scale-out">Scale Out</option>
                  <option value="slide-down">Slide Down</option>
                </select>
              </div>
            </div>

            <!-- Butonlar -->
            <div class="pt-2 border-t border-slate-800 flex flex-col gap-1.5">
              <button (click)="saveInspector()" class="w-full py-2 bg-brand-cyan hover:bg-cyan-400 text-slate-900 font-bold rounded-lg transition-colors shadow-glow-sm cursor-pointer text-xs">
                Kaydet
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

          <!-- 2. Durum: Klip Seçili -->
          <div *ngIf="!selectedOverlay() && selectedClipIds().length > 0" class="space-y-3.5">
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
                <span class="font-mono text-brand-cyan">Del / B / M</span>
              </div>
            </div>

            <div class="space-y-2 pt-1">
              <button *ngIf="selectedHasKeep()" (click)="deleteSelectedClips()" class="w-full py-2 bg-rose-600/80 hover:bg-rose-500 text-white font-bold rounded-lg text-xs transition-colors flex items-center justify-center gap-1.5 shadow-glow-sm">
                <span>✕</span> Bu Klipleri Kes / Çıkar (Del)
              </button>
              <button *ngIf="selectedHasCuts()" (click)="restoreSelectedCuts()" class="w-full py-2 bg-sky-600/80 hover:bg-sky-500 text-white font-bold rounded-lg text-xs transition-colors flex items-center justify-center gap-1.5 shadow-glow-sm">
                <span>↩</span> Kesimi İptal Et ve Geri Al
              </button>
              <button *ngIf="selectedClipIds().length > 1" (click)="mergeSelectedClips()" class="w-full py-2 bg-emerald-600/80 hover:bg-emerald-500 text-white font-bold rounded-lg text-xs transition-colors flex items-center justify-center gap-1.5 shadow-glow-sm">
                <span>🔗</span> Seçili Klipleri Birleştir (M)
              </button>
              <button (click)="selectedClipIds.set([])" class="w-full py-1.5 bg-dark-800 text-slate-400 hover:text-white rounded-lg text-xs border border-slate-700">
                Seçimi Temizle (Esc)
              </button>
            </div>
          </div>

          <!-- 3. Durum: Hiçbir Şey Seçili Değil -->
          <div *ngIf="!selectedOverlay() && selectedClipIds().length === 0" class="text-center py-8 space-y-4">
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
                max="6" 
                step="0.2" 
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
              <button (click)="addTrackLane()" class="px-1.5 py-0.5 rounded bg-dark-800 hover:bg-slate-700 text-sky-400 border border-slate-700 hover:text-white transition-colors text-[9px] font-bold cursor-pointer" title="Yeni Katman Kanalı Ekle">
                + Katman
              </button>
            </div>

            <!-- Overlay Katman Başlıkları (T3, T2, T1) -->
            <div 
              *ngFor="let trackNum of overlayTrackNumbers()" 
              class="h-10 border-b border-slate-800/70 px-2.5 flex items-center justify-between text-xs bg-dark-900/90 hover:bg-dark-800/60 transition-colors">
              <div class="flex items-center gap-1.5 min-w-0">
                <span class="w-5 h-5 rounded flex items-center justify-center text-[10px] font-black shrink-0 bg-sky-500/20 text-sky-300 border border-sky-500/30">
                  T{{ trackNum }}
                </span>
                <span class="text-[11px] font-semibold text-slate-300 truncate">Katman #{{ trackNum }}</span>
              </div>
              <span *ngIf="getOverlaysForTrack(trackNum).length > 0" class="text-[9px] font-mono font-bold px-1.5 py-0.5 rounded-full bg-slate-800 text-slate-400">
                {{ getOverlaysForTrack(trackNum).length }}
              </span>
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
          </div>

          <!-- 2. SAĞ KAYDIRILABİLİR ZAMAN ÇİZELGESİ (Scrollable Timeline Canvas) -->
          <div 
            #timelineScrollContainer
            (wheel)="onTimelineWheel($event)"
            class="flex-1 overflow-x-auto overflow-y-auto relative pb-2 scrollbar-thin scrollbar-thumb-slate-700 scrollbar-track-dark-900">
            <div 
              #timelineTrack
              (click)="seekTimeline($event)"
              (contextmenu)="openTimelineContextMenu($event)"
              [style.width.%]="100 * timelineZoom()"
              class="relative min-w-full flex flex-col select-none cursor-pointer bg-dark-950 min-h-full">
              
              <!-- Zaman Cetveli (Timecode Ruler with Ticks) -->
              <div class="relative h-7 bg-dark-950 border-b border-slate-800 overflow-hidden select-none">
                <div class="absolute inset-0 bg-[linear-gradient(to_right,#334155_1px,transparent_1px)] bg-[size:10px_100%] opacity-20"></div>
                <ng-container *ngFor="let mark of timelineRulerMarks()">
                  <div class="absolute top-0 bottom-0 flex flex-col items-center pointer-events-none -translate-x-1/2" [style.left.%]="mark.percent">
                    <span class="text-[9px] font-mono text-slate-400 font-semibold pt-0.5 tracking-tight">{{ mark.label }}</span>
                    <div class="w-px flex-1 bg-slate-700/80 mt-0.5"></div>
                  </div>
                </ng-container>
              </div>

              
              <!-- Altyazı Kanalı (Subtitle Track) -->
              <div class="relative h-10 bg-dark-900/40 border-b border-slate-800/60 overflow-hidden flex items-center hover:bg-dark-900/70 transition-colors">
                <div class="absolute inset-0 bg-[linear-gradient(to_right,#1e293b_1px,transparent_1px)] bg-[size:50px_100%] opacity-15 pointer-events-none"></div>
                <div class="absolute left-0 top-0 bottom-0 w-[120px] bg-dark-950 border-r border-slate-700 flex items-center px-2 z-10 shadow-md">
                  <span class="text-[10px] font-bold text-amber-400">💬 Altyazı</span>
                </div>
                
                <div class="absolute left-[120px] right-0 top-0 bottom-0 overflow-hidden">
                  <div *ngFor="let seg of activeEdl()?.transcript?.segments"
                       class="absolute top-1 bottom-1 bg-amber-500/20 border border-amber-500/50 rounded flex items-center px-1 text-[8px] text-amber-100 overflow-hidden hover:bg-amber-500/40 z-20 cursor-pointer"
                       [style.left.%]="(seg.start / totalDuration()) * 100"
                       [style.width.%]="((seg.end - seg.start) / totalDuration()) * 100"
                       [title]="seg.text">
                       <span class="truncate font-semibold">{{ seg.text }}</span>
                  </div>
                </div>
              </div>

              <!-- Katman Şeritleri (T3, T2, T1) -->
              <div 
                *ngFor="let trackNum of overlayTrackNumbers()" 
                class="relative h-10 bg-dark-900/40 border-b border-slate-800/60 overflow-hidden flex items-center hover:bg-dark-900/70 transition-colors">
                <div class="absolute inset-0 bg-[linear-gradient(to_right,#1e293b_1px,transparent_1px)] bg-[size:50px_100%] opacity-15 pointer-events-none"></div>

                <div *ngIf="getOverlaysForTrack(trackNum).length === 0" class="absolute inset-0 flex items-center justify-center text-[10px] text-slate-600/40 italic pointer-events-none select-none">
                  Katman #{{ trackNum }} (Boş)
                </div>

                <!-- Katman Öğeleri (Pill'ler) -->
                <div 
                  *ngFor="let ov of getOverlaysForTrack(trackNum)"
                  (mousedown)="onOverlayDragStart($event, ov.id)"
                  (click)="$event.stopPropagation(); selectOverlay(ov.id)"
                  (contextmenu)="openOverlayContextMenu($event, ov)"
                  class="absolute top-1 bottom-1 rounded-lg px-2.5 flex items-center justify-between text-[11px] font-bold cursor-grab active:cursor-grabbing z-20 group transition-all select-none shadow-lg overflow-hidden min-w-[70px] border"
                  [ngClass]="[
                     ov.type === 'text' 
                       ? 'bg-gradient-to-r from-[#ba5748] to-[#994033] text-white border-[#e07567]/70 hover:brightness-110 shadow-rose-950/50' 
                       : 'bg-gradient-to-r from-purple-700 to-indigo-700 text-white border-purple-400/70 hover:brightness-110 shadow-purple-950/50',
                     selectedOverlayId() === ov.id 
                       ? 'ring-2 ring-white shadow-[0_0_12px_rgba(255,255,255,0.95)] z-30 brightness-115 scale-[1.01]' 
                       : ''
                  ]"
                  [ngStyle]="getOverlayStyle(ov)"
                  [title]="(ov.type === 'text' ? 'Metin: ' : 'Görsel: ') + (ov.content || ov.source || ov.id) + ' (Katman #' + trackNum + ')'">
                  
                  <!-- Sol Boyutlandırma Kolu -->
                  <div (mousedown)="onOverlayResizeStart($event, ov.id, 'left')" class="absolute left-0 top-0 bottom-0 w-3 cursor-ew-resize opacity-0 group-hover:opacity-100 hover:bg-white/50 bg-white/20 rounded-l flex items-center justify-center z-30 transition-opacity">
                    <div class="w-0.5 h-3.5 bg-white/90 rounded"></div>
                  </div>

                  <!-- İçerik -->
                  <div class="truncate px-2 pointer-events-none font-semibold flex items-center gap-1.5 drop-shadow-sm">
                    <span class="w-4 h-4 rounded text-[9px] font-black flex items-center justify-center bg-black/30 border border-white/20">
                      {{ ov.type === 'text' ? 'T' : '🖼️' }}
                    </span>
                    <span class="truncate">{{ ov.content || (ov.type === 'text' ? 'Metin' : 'Görsel') }}</span>
                    <span class="text-[9px] font-mono opacity-80 font-normal ml-1">({{ ov.duration }}s)</span>
                  </div>

                  <!-- Sağ Boyutlandırma Kolu -->
                  <div (mousedown)="onOverlayResizeStart($event, ov.id, 'right')" class="absolute right-0 top-0 bottom-0 w-3 cursor-ew-resize opacity-0 group-hover:opacity-100 hover:bg-white/50 bg-white/20 rounded-r flex items-center justify-center z-30 transition-opacity">
                    <div class="w-0.5 h-3.5 bg-white/90 rounded"></div>
                  </div>
                </div>
              </div>

              <!-- Video Klipleri Şeridi (V1 - Ana Video Kanalı & Gerçek Ses Dalgası) -->
              <div class="relative h-14 bg-dark-950 flex overflow-hidden border-b border-slate-800">
                <!-- Gerçek Ses Dalga Formu (Web Audio API Waveform SVG Arka Planı) -->
                <div *ngIf="audioPeaks()?.length" class="absolute inset-0 flex items-center pointer-events-none z-0">
                  <svg class="w-full h-full" preserveAspectRatio="none" viewBox="0 0 1000 56">
                    <defs>
                      <linearGradient id="waveGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                        <stop offset="0%" stop-color="#38bdf8" stop-opacity="0.85" />
                        <stop offset="50%" stop-color="#06b6d4" stop-opacity="0.95" />
                        <stop offset="100%" stop-color="#0284c7" stop-opacity="0.85" />
                      </linearGradient>
                    </defs>
                    <path [attr.d]="getWaveformPath()" fill="url(#waveGradient)" />
                    <line x1="0" y1="28" x2="1000" y2="28" stroke="#0ea5e9" stroke-opacity="0.3" stroke-width="1" />
                  </svg>
                </div>

                <!-- Klipler (Flexbox ile ardışık dizilir) -->
                <ng-container *ngFor="let clip of clips()">
                  <div 
                    *ngIf="isVisible(clip)"
                    (click)="selectClip(clip.id, $event)"
                    (dblclick)="toggleClip(clip, $event)"
                    (contextmenu)="openClipContextMenu($event, clip)"
                    class="absolute top-0 bottom-0 transition-all border-r border-white/20 box-border group flex flex-col justify-between p-1 select-none z-10 cursor-pointer"
                    [ngClass]="{
                       'bg-amber-500/70 hover:bg-amber-500/80 backdrop-blur-xs': isRetakeClip(clip),
                       'bg-rose-500/70 hover:bg-rose-500/80 backdrop-blur-xs': isManualClip(clip),
                       'bg-rose-950/75 hover:bg-rose-900/85 backdrop-blur-xs': clip.isCut && !isRetakeClip(clip) && !isManualClip(clip),
                       'bg-emerald-600/20 hover:bg-emerald-500/35': !clip.isCut,
                       'ring-2 ring-inset ring-brand-yellow shadow-[0_0_12px_rgba(250,204,21,0.6)] z-20': selectedClipIds().includes(clip.id)
                    }"
                    [style.left.%]="(clip.start / totalDuration()) * 100"
                    [style.width.%]="((clip.end - clip.start) / totalDuration()) * 100"
                    [title]="getClipTooltip(clip)">
                    
                    <!-- Üst Klip Başlığı -->
                    <div class="flex items-center justify-between text-[9px] text-white/90 font-mono truncate pointer-events-none">
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
              </div>

              <!-- Ortak Zaman İmleci (Playhead) -->
              <div 
                (mousedown)="onPlayheadDragStart($event)"
                class="absolute top-0 bottom-0 w-0.5 bg-white shadow-[0_0_8px_white] z-50 cursor-ew-resize pointer-events-auto"
                [style.left.%]="getPlayheadPosition()">
                <div class="w-3.5 h-3.5 bg-white rotate-45 -translate-x-[6px] -translate-y-[2px] shadow-lg rounded-sm border border-slate-300"></div>
              </div>
            </div>
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
    </main>
  `
})
export class EditorComponent implements OnInit, OnDestroy {
  isScrubbing = false;

  @HostListener('window:mousemove', ['$event'])
  onWindowMouseMove(event: MouseEvent) {
    if (!this.isScrubbing || !this.timelineScrollContainerRef) return;
    
    const container = this.timelineScrollContainerRef.nativeElement;
    const rect = container.getBoundingClientRect();
    const scrollLeft = container.scrollLeft;
    
    let x = event.clientX - rect.left + scrollLeft;
    const totalW = container.scrollWidth;
    x = Math.max(0, Math.min(x, totalW));
    
    const percentage = x / totalW;
    const targetTime = percentage * this.totalDuration();
    
    if (this.videoRef && this.videoRef.nativeElement) {
      this.videoRef.nativeElement.currentTime = targetTime;
    }
    this.currentTime.set(targetTime);
  }

  @HostListener('window:mouseup')
  onWindowMouseUp() {
    if (this.isScrubbing) {
      this.isScrubbing = false;
    }
  }

  onPlayheadDragStart(event: MouseEvent) {
    this.isScrubbing = true;
    event.preventDefault();
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

  @ViewChild('videoPlayer') videoRef!: ElementRef<HTMLVideoElement>;
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
  readonly currentTime = signal<number>(0);
  readonly totalDuration = signal<number>(100);

  // Ses Dalga Formu (Web Audio API Waveform)
  readonly audioPeaks = signal<number[] | null>(null);
  readonly isWaveformLoading = signal<boolean>(false);

  // Oynatma Durumu
  readonly isPlaying = signal<boolean>(false);

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

  // Sol Panel Aktif Sekmesi
  readonly activeTab = signal<'chat' | 'overlays' | 'inspector' | 'media' | 'transcript'>('chat');
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

  readonly timelineZoom = signal<number>(1);
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
    const dur = Math.max(1, this.totalDuration() || 60);
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

  // Clips hesaplaması
  readonly clips = computed(() => {
    const total = this.totalDuration();
    const edl = this.activeEdl();
    const cuts = edl?.cuts || [];
    const splits = [...this.splitMarkers(), total].sort((a,b) => a-b);
    
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
      if (end - start < 0.05) continue;
      
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

  readonly visibleDuration = computed(() => {
     const allClips = this.clips(); 
     let totalCut = 0;
     for (const c of allClips) {
         if (c.isCut && (this.isRetakeClip(c) || c.cutObj?.reason?.includes('silence') || c.cutObj?.reason?.includes('manuel'))) {
             totalCut += c.duration;
         }
     }
     return Math.max(0, this.totalDuration() - totalCut);
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
          this.loadAudioWaveform(streamUrl);
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
        this.edl.set(res.edl);
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
        // Eğer waveform henüz yüklenmediyse ve transcript varsa fallback üret
        if (!this.audioPeaks()) {
          this.generateFallbackWaveform();
        }
      },
      error: (err) => console.error('EDL yüklenemedi:', err)
    });
  }

  // --- GERÇEK SES DALGASI (WEB AUDIO API) ---
  loadAudioWaveform(url: string): void {
    if (!url) return;
    this.isWaveformLoading.set(true);

    fetch(url)
      .then(res => {
        if (!res.ok) throw new Error('Audio stream fetch error: ' + res.status);
        return res.arrayBuffer();
      })
      .then(arrayBuffer => {
        const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
        if (!AudioContextClass) throw new Error('AudioContext not supported in this browser');
        const audioCtx = new AudioContextClass();
        return audioCtx.decodeAudioData(arrayBuffer);
      })
      .then(audioBuffer => {
        const raw = audioBuffer.getChannelData(0);
        const dur = Math.max(1, audioBuffer.duration || this.totalDuration() || 60);
        const totalPoints = Math.min(800, Math.max(160, Math.round(dur * 6)));
        const blockSize = Math.floor(raw.length / totalPoints);
        const peaks: number[] = [];

        for (let i = 0; i < totalPoints; i++) {
          const start = i * blockSize;
          let max = 0;
          let sum = 0;
          const step = Math.max(1, Math.floor(blockSize / 20));
          let count = 0;
          for (let j = 0; j < blockSize; j += step) {
            const val = Math.abs(raw[start + j] || 0);
            if (val > max) max = val;
            sum += val * val;
            count++;
          }
          const rms = Math.sqrt(sum / (count || 1));
          const peak = Math.min(0.95, Math.max(0.05, max * 0.7 + rms * 1.6));
          peaks.push(parseFloat(peak.toFixed(3)));
        }
        this.audioPeaks.set(peaks);
        this.isWaveformLoading.set(false);
      })
      .catch(err => {
        console.warn('[Waveform] Real decode fallback:', err);
        this.generateFallbackWaveform();
        this.isWaveformLoading.set(false);
      });
  }

  generateFallbackWaveform(): void {
    const dur = Math.max(1, this.totalDuration() || 60);
    const totalPoints = Math.min(600, Math.max(120, Math.round(dur * 4)));
    const edl = this.activeEdl();
    const cuts = edl?.cuts || [];
    const segments = edl?.transcript?.segments || [];
    const peaks: number[] = [];

    for (let i = 0; i < totalPoints; i++) {
      const time = (i / totalPoints) * dur;
      const isCut = cuts.some(c => time >= c.start && time <= c.end);
      const isSpeech = segments.some(s => time >= s.start && time <= s.end);

      if (isCut) {
        peaks.push(0.04 + Math.random() * 0.03);
      } else if (isSpeech) {
        const seed = Math.sin(i * 0.8) * Math.cos(i * 0.3);
        const val = 0.35 + Math.abs(seed) * 0.55 + Math.random() * 0.1;
        peaks.push(parseFloat(Math.min(0.95, val).toFixed(3)));
      } else {
        peaks.push(0.12 + Math.random() * 0.1);
      }
    }
    this.audioPeaks.set(peaks);
  }

  getWaveformPath(): string {
    const peaks = this.audioPeaks();
    if (!peaks || peaks.length === 0) return '';
    
    const width = 1000;
    const height = 56;
    const midY = height / 2;
    const numPoints = peaks.length;
    const dx = width / (numPoints - 1);
    
    let topPath = `M 0 ${midY}`;
    for (let i = 0; i < numPoints; i++) {
      const x = i * dx;
      const peakH = peaks[i] * (height / 2 - 3);
      const y = midY - peakH;
      topPath += ` L ${x.toFixed(1)} ${y.toFixed(1)}`;
    }
    
    let bottomPath = '';
    for (let i = numPoints - 1; i >= 0; i--) {
      const x = i * dx;
      const peakH = peaks[i] * (height / 2 - 3);
      const y = midY + peakH;
      bottomPath += ` L ${x.toFixed(1)} ${y.toFixed(1)}`;
    }
    
    return `${topPath} ${bottomPath} Z`;
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
    } else if (event.shiftKey) {
      const container = this.timelineScrollContainerRef?.nativeElement;
      if (container) {
        container.scrollLeft += event.deltaY;
      }
    }
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

  // --- CANLI EDL SİMÜLASYONU ---
  onTimeUpdate(): void {
    const video = this.videoRef?.nativeElement;
    if (!video) return;

    const t = video.currentTime;
    this.currentTime.set(t);

    const cuts = this.activeEdl()?.cuts || [];
    for (const cut of cuts) {
      if (t >= cut.start && t < cut.end) {
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
    if (!this.audioPeaks()) {
      const url = this.videoUrl();
      if (url) this.loadAudioWaveform(url);
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
       if (current.length === 1 && current[0] === clipId) {
          this.selectedClipIds.set([]);
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
    this.timelineZoom.update(z => Math.min(8, parseFloat((z + 0.25).toFixed(2))));
  }

  zoomOut(): void {
    this.timelineZoom.update(z => Math.max(1, parseFloat((z - 0.25).toFixed(2))));
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
    
    if (t < ov.timestamp + 0.5) {
      if (anim === 'fade') return 'animate-fade-in';
      if (anim === 'pop-up') return 'animate-pop-up';
      if (anim === 'slide-up') return 'animate-slide-up';
      return '';
    }
    
    if (t > (ov.timestamp + ov.duration - 0.5)) {
      if (exitAnim === 'fade') return 'animate-fade-out';
      if (exitAnim === 'scale-out') return 'animate-scale-out';
      if (exitAnim === 'slide-down') return 'animate-slide-down';
      return '';
    }
    
    return '';
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
     if (!this.rippleAi() && !this.rippleManual()) {
        return {
           left: `${(ov.timestamp / totalDur) * 100}%`,
           width: `${Math.max(1.0, (ov.duration / totalDur) * 100)}%`
        };
     }

     const startVis = this.getVisTimeFromRawTime(ov.timestamp);
     const endVis = this.getVisTimeFromRawTime(ov.timestamp + ov.duration);
     const visDur = this.visibleDuration();
     
     if (visDur <= 0 || endVis <= startVis) return { display: 'none' };
     
     return {
        left: `${(startVis / visDur) * 100}%`,
        width: `${Math.max(1.0, ((endVis - startVis) / visDur) * 100)}%`
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
     this.selectOverlay(overlayId);
     this.isDraggingOverlay = true;
     this.dragStartX = event.clientX;
     this.dragStartY = event.clientY;
     
     const ov = this.activeEdl()?.overlays?.find(o => o.id === overlayId);
     if (ov) {
        this.dragOverlayOriginalStart = ov.timestamp;
        this.dragOverlayOriginalDuration = ov.duration;
        this.dragOverlayOriginalTrack = Number(ov.trackId) || 1;
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
         }
         return;
     }

     if (this.isCanvasResizing) {
         const deltaX = event.clientX - this.canvasResizeStartX;
         const deltaY = event.clientY - this.canvasResizeStartY;
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
