import { Component, OnInit, OnDestroy, inject, signal, ViewChild, ElementRef } from '@angular/core';
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
              [style.top]="getOverlayTop(ov)"
              [style.left]="getOverlayLeft(ov)"
              class="absolute pointer-events-none transition-all duration-200 z-20"
              [style.color]="ov.color || '#FFFFFF'"
              [style.backgroundColor]="ov.backgroundColor || 'transparent'">
              <span *ngIf="ov.type === 'text'" class="px-3 py-1 rounded font-bold" [style.fontSize.px]="(ov.fontSize || 48) / 2">
                {{ ov.content }}
              </span>
            </div>
          </div>

          <!-- Video Zaman Kontrolleri -->
          <div class="flex items-center justify-between text-xs font-mono text-slate-400 px-2">
            <span>{{ currentTime() | duration }} / {{ totalDuration() | duration }}</span>
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
              <span class="text-slate-400">Tıklayarak o saniyeye atlayın</span>
            </div>

            <!-- Interaktif Timeline Track -->
            <div 
              #timelineTrack
              (click)="seekTimeline($event)"
              class="relative w-full h-14 bg-dark-900 rounded-xl overflow-hidden cursor-pointer border border-slate-700/60 select-none">
              
              <!-- Arka Plan: Korunan Bölgeler (Yeşil) -->
              <div class="absolute inset-0 bg-emerald-950/40"></div>

              <!-- Kesilen Bölgeler (Kırmızı Kısımlar) -->
              <div 
                *ngFor="let cut of edl()?.cuts"
                class="absolute top-0 bottom-0 bg-rose-600/60 border-l border-r border-rose-400"
                [style.left.%]="(cut.start / totalDuration()) * 100"
                [style.width.%]="((cut.end - cut.start) / totalDuration()) * 100"
                [title]="'Kesim: ' + cut.start + 's - ' + cut.end + 's (' + cut.reason + ')'">
              </div>

              <!-- Overlay Marker'ları (Yazı ve Görsel İşaretleri) -->
              <div 
                *ngFor="let ov of edl()?.overlays"
                class="absolute top-1 bottom-1 rounded-md opacity-90 transition-transform hover:scale-105"
                [ngClass]="ov.type === 'text' ? 'bg-sky-400/80 border border-sky-300' : 'bg-purple-500/80 border border-purple-300'"
                [style.left.%]="(ov.timestamp / totalDuration()) * 100"
                [style.width.%]="(ov.duration / totalDuration()) * 100"
                [title]="ov.type + ': ' + (ov.content || ov.id)">
              </div>

              <!-- Zaman İmleci (Playhead) -->
              <div 
                class="absolute top-0 bottom-0 w-0.5 bg-white shadow-[0_0_8px_white] z-30 pointer-events-none"
                [style.left.%]="(currentTime() / totalDuration()) * 100">
                <div class="w-3 h-3 bg-white rotate-45 -translate-x-[5px] -translate-y-[4px]"></div>
              </div>
            </div>

            <!-- Akıllı Öneri Çipleri (AI Suggestions) -->
            <div *ngIf="edl()?.suggestions?.length" class="pt-2">
              <span class="text-[11px] font-bold text-slate-400 uppercase tracking-wider block mb-2">AI B-Roll ve Vurgu Önerileri</span>
              <div class="flex items-center gap-2 overflow-x-auto pb-1">
                <div 
                  *ngFor="let sug of edl()?.suggestions"
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
              Katmanlar ({{ edl()?.overlays?.length || 0 }})
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
                  <span class="text-[10px] opacity-60 block text-right">
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
            <div *ngIf="!edl()?.overlays?.length" class="text-center py-12 text-slate-500 text-xs">
              Henüz eklenmiş bir yazı veya görsel katmanı bulunmuyor.
            </div>

            <div 
              *ngFor="let ov of edl()?.overlays"
              class="p-3.5 rounded-xl bg-dark-800 border border-slate-700 flex items-start justify-between gap-3">
              <div>
                <div class="flex items-center gap-2 mb-1">
                  <span 
                    [ngClass]="ov.type === 'text' ? 'bg-sky-500/20 text-sky-400' : 'bg-purple-500/20 text-purple-400'"
                    class="px-2 py-0.5 rounded text-[10px] font-bold uppercase">
                    {{ ov.type }}
                  </span>
                  <span class="text-xs font-mono text-slate-400">{{ ov.timestamp }}s - {{ ov.timestamp + ov.duration }}s</span>
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
                (click)="removeOverlay(ov.id)" 
                title="Katmanı Sil"
                class="text-slate-500 hover:text-rose-400 p-1.5 rounded-lg hover:bg-rose-500/10 transition-colors">
                ✕
              </button>
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

  projectId = '';
  readonly project = signal<ProjectDetailDto | null>(null);
  readonly edl = signal<EdlContent | null>(null);
  readonly videoUrl = signal<string>('');
  readonly currentTime = signal<number>(0);
  readonly totalDuration = signal<number>(100);
  readonly activeOverlays = signal<OverlayItem[]>([]);
  readonly activeTab = signal<'chat' | 'overlays'>('chat');
  readonly rendering = signal<boolean>(false);

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
        if (res.edl.duration) {
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
    const cuts = this.edl()?.cuts || [];
    for (const cut of cuts) {
      if (t >= cut.start && t < cut.end) {
        console.log(`[EDL Simülasyonu] Kesilen bölge atlanıyor: ${cut.start}s -> ${cut.end}s`);
        video.currentTime = cut.end;
        return;
      }
    }

    // 2. Aktif metin overlay'lerini güncelle
    const overlays = this.edl()?.overlays || [];
    const active = overlays.filter(ov => t >= ov.timestamp && t <= (ov.timestamp + ov.duration));
    this.activeOverlays.set(active);
  }

  onMetadataLoaded(): void {
    const video = this.videoRef?.nativeElement;
    if (video && video.duration && !isNaN(video.duration)) {
      this.totalDuration.set(video.duration);
    }
  }

  seekTimeline(event: MouseEvent): void {
    const target = event.currentTarget as HTMLElement;
    const rect = target.getBoundingClientRect();
    const clickX = event.clientX - rect.left;
    const percentage = clickX / rect.width;
    const targetTime = percentage * this.totalDuration();

    if (this.videoRef?.nativeElement) {
      this.videoRef.nativeElement.currentTime = targetTime;
    }
  }

  getOverlayTop(ov: OverlayItem): string {
    const vPos = ov.position?.[1] || 'bottom';
    if (vPos === 'top') return '10%';
    if (vPos === 'center') return '45%';
    return '80%';
  }

  getOverlayLeft(ov: OverlayItem): string {
    const hPos = ov.position?.[0] || 'center';
    if (hPos === 'left') return '10%';
    if (hPos === 'right') return '70%';
    return '35%';
  }

  setPrompt(p: string): void {
    this.userPrompt = p;
  }

  sendChatMessage(): void {
    if (!this.userPrompt.trim() || this.chatLoading()) return;

    const msgText = this.userPrompt.trim();
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
            edlPatch: res.edlPatch
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
}
