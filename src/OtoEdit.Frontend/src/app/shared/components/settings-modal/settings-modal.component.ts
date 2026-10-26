import { Component, OnInit, inject, signal, computed, effect } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { SettingsService, ModelOption } from '../../../core/services/settings.service';

@Component({
  selector: 'app-settings-modal',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <!-- SİSTEM VE YAPAY ZEKA API AYARLARI MODALI -->
    <div 
      *ngIf="settingsService.isModalOpen()" 
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-4 animate-in fade-in duration-150"
      (click)="settingsService.closeModal()">
      <div 
        class="bg-dark-900 border border-slate-700/90 rounded-2xl w-full max-w-2xl shadow-2xl overflow-hidden flex flex-col max-h-[92vh]"
        (click)="$event.stopPropagation()">
        
        <!-- Modal Başlığı -->
        <div class="px-6 py-3.5 border-b border-slate-800 flex items-center justify-between bg-dark-950/70 shrink-0">
          <div class="flex items-center gap-2.5">
            <span class="w-8 h-8 rounded-lg bg-gradient-to-tr from-brand-indigo to-purple-600 text-white flex items-center justify-center text-base shadow-sm">
              ⚙️
            </span>
            <div>
              <h3 class="text-sm font-bold text-white tracking-wide">Sistem & Yapay Zeka (API) Ayarları</h3>
              <p class="text-[11px] text-slate-400">Tüm erişilebilir modeller ve sağlayıcı yapılandırması</p>
            </div>
          </div>
          <button 
            type="button"
            (click)="settingsService.closeModal()"
            class="w-7 h-7 rounded-lg flex items-center justify-center text-slate-400 hover:text-white hover:bg-slate-800 transition-colors text-sm cursor-pointer">
            ✕
          </button>
        </div>

        <!-- Sekmeler (Tabs) -->
        <div class="flex border-b border-slate-800 bg-dark-950/40 px-6 pt-2 gap-4 text-xs font-semibold shrink-0">
          <button
            type="button"
            class="text-brand-cyan border-b-2 border-brand-cyan pb-2 flex items-center gap-1.5 transition-colors cursor-pointer">
            <span>🌐</span>
            <span>API & Model Kataloğu</span>
          </button>
        </div>

        <!-- Modal İçeriği: API Sağlayıcı Seçimi -->
        <div class="p-5 space-y-4 overflow-y-auto scrollbar-thin flex-1">
          
          <div class="space-y-1">
            <span class="text-xs font-bold text-slate-200 uppercase tracking-wider block">Yapay Zeka Motoru Tercihi</span>
            <p class="text-[11px] text-slate-400">
              Video analizi, otomatik kurgu, transkript zenginleştirme ve AI sohbet için kullanılacak motoru seçin:
            </p>
          </div>

          <!-- Seçenek Kartları: Antigravity vs OpenRouter -->
          <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
            
            <!-- 1. Antigravity Kartı -->
            <div 
              (click)="selectedProvider = 'antigravity'"
              [ngClass]="selectedProvider === 'antigravity' ? 'border-purple-500 bg-purple-950/20 ring-1 ring-purple-500/60' : 'border-slate-800 bg-dark-800/40 hover:border-slate-700 hover:bg-dark-800/70'"
              class="p-3.5 rounded-xl border text-left flex flex-col justify-between gap-2.5 transition-all cursor-pointer relative group">
              <div class="space-y-1.5">
                <div class="flex items-center justify-between">
                  <div class="flex items-center gap-2">
                    <span class="text-lg">🔮</span>
                    <span class="text-xs font-bold text-white group-hover:text-purple-300 transition-colors">Antigravity AI</span>
                  </div>
                  <span class="text-[9px] px-2 py-0.5 rounded-full font-mono font-semibold"
                    [ngClass]="selectedProvider === 'antigravity' ? 'bg-purple-500/20 text-purple-300 border border-purple-500/40' : 'bg-slate-800 text-slate-400'">
                    {{ selectedProvider === 'antigravity' ? 'Seçili' : 'Mevcut' }}
                  </span>
                </div>
                <p class="text-[11px] text-slate-300 leading-relaxed">
                  Varsayılan yerel Docker & Antigravity Proxy altyapısı (Gemini 3.8 Flash).
                </p>
                <div class="pt-0.5 flex flex-wrap gap-1 text-[9px] font-mono text-slate-400">
                  <span class="px-1.5 py-0.5 rounded bg-dark-900 border border-purple-500/40 font-semibold text-purple-300">gemini-3.8-flash-tiered</span>
                  <span class="px-1.5 py-0.5 rounded bg-dark-900 border border-slate-700/60">localhost:8045</span>
                </div>
              </div>
              <div class="text-[11px] font-semibold flex items-center gap-1.5"
                [ngClass]="selectedProvider === 'antigravity' ? 'text-purple-400' : 'text-slate-500'">
                <span>{{ selectedProvider === 'antigravity' ? '● Aktif Seçenek' : '○ Seçmek için tıkla' }}</span>
              </div>
            </div>

            <!-- 2. OpenRouter Kartı -->
            <div 
              (click)="selectedProvider = 'openrouter'"
              [ngClass]="selectedProvider === 'openrouter' ? 'border-brand-cyan bg-brand-cyan/10 ring-1 ring-brand-cyan/60' : 'border-slate-800 bg-dark-800/40 hover:border-slate-700 hover:bg-dark-800/70'"
              class="p-3.5 rounded-xl border text-left flex flex-col justify-between gap-2.5 transition-all cursor-pointer relative group">
              <div class="space-y-1.5">
                <div class="flex items-center justify-between">
                  <div class="flex items-center gap-2">
                    <span class="text-lg">🌐</span>
                    <span class="text-xs font-bold text-white group-hover:text-brand-cyan transition-colors">OpenRouter API</span>
                  </div>
                  <span class="text-[9px] px-2 py-0.5 rounded-full font-mono font-semibold"
                    [ngClass]="selectedProvider === 'openrouter' ? 'bg-brand-cyan/20 text-brand-cyan border border-brand-cyan/40' : 'bg-slate-800 text-slate-400'">
                    {{ selectedProvider === 'openrouter' ? 'Seçili' : 'Bulut Gateway' }}
                  </span>
                </div>
                <p class="text-[11px] text-slate-300 leading-relaxed">
                  OpenRouter üzerinden tüm küresel modeller (Gemini, Claude, GPT, Ling, DeepSeek).
                </p>
                <div class="pt-0.5 flex flex-wrap gap-1 text-[9px] font-mono text-slate-400">
                  <span class="px-1.5 py-0.5 rounded bg-dark-900 border border-brand-cyan/40 font-semibold text-brand-cyan truncate max-w-[190px]" [title]="openRouterModel">
                    {{ openRouterModel }}
                  </span>
                  <span class="px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">API Key Tanımlı</span>
                </div>
              </div>
              <div class="text-[11px] font-semibold flex items-center gap-1.5"
                [ngClass]="selectedProvider === 'openrouter' ? 'text-brand-cyan' : 'text-slate-500'">
                <span>{{ selectedProvider === 'openrouter' ? '● Aktif Seçenek' : '○ Seçmek için tıkla' }}</span>
              </div>
            </div>

          </div>

          <!-- OpenRouter Parametre Ayarları & Model Kataloğu (OpenRouter seçiliyse) -->
          <div *ngIf="selectedProvider === 'openrouter'" class="p-4 rounded-xl bg-dark-950/80 border border-brand-cyan/30 space-y-3.5 animate-in fade-in duration-200">
            <div class="flex items-center justify-between border-b border-slate-800 pb-2">
              <span class="text-xs font-bold text-brand-cyan uppercase tracking-wider flex items-center gap-1.5">
                <span>⚙️</span> OpenRouter Yapılandırması & Model Kataloğu
              </span>
              <div class="flex items-center gap-2">
                <button 
                  type="button" 
                  (click)="loadModels()"
                  [disabled]="loadingModels()"
                  class="px-2 py-1 rounded-lg bg-dark-800 hover:bg-slate-700 border border-slate-700 text-slate-300 text-[10px] flex items-center gap-1 cursor-pointer">
                  <span [ngClass]="loadingModels() ? 'animate-spin' : ''">🔄</span>
                  <span>{{ loadingModels() ? 'Yenileniyor...' : 'Modelleri Yenile' }}</span>
                </button>
                <button 
                  type="button" 
                  (click)="testConnection('openrouter')"
                  [disabled]="settingsService.isTesting()"
                  class="px-2.5 py-1 rounded-lg bg-dark-800 hover:bg-slate-700 border border-slate-700 text-slate-200 text-xs font-semibold flex items-center gap-1.5 transition-colors cursor-pointer disabled:opacity-50">
                  <span *ngIf="!settingsService.isTesting()">⚡</span>
                  <span *ngIf="settingsService.isTesting()" class="animate-spin text-[10px]">⏳</span>
                  <span>{{ settingsService.isTesting() ? 'Test Ediliyor...' : 'Bağlantıyı Test Et' }}</span>
                </button>
              </div>
            </div>

            <!-- Test Sonucu Bildirimi -->
            <div *ngIf="settingsService.testResult() as test" class="p-2.5 rounded-lg text-xs flex items-center gap-2"
              [ngClass]="test.success ? 'bg-emerald-500/10 text-emerald-300 border border-emerald-500/30' : 'bg-rose-500/10 text-rose-300 border border-rose-500/30'">
              <span>{{ test.success ? '✓' : '⚠️' }}</span>
              <span class="flex-1">{{ test.message }}</span>
              <span *ngIf="test.latencyMs" class="font-mono text-[10px] text-slate-400">{{ test.latencyMs }}ms</span>
            </div>

            <!-- API Key Input -->
            <div class="space-y-1">
              <div class="flex items-center justify-between">
                <label class="text-[10px] font-bold text-slate-300 uppercase tracking-wider">OpenRouter API Anahtarı</label>
                <button type="button" (click)="showApiKey.set(!showApiKey())" class="text-[10px] text-slate-400 hover:text-white">
                  {{ showApiKey() ? 'Gizle' : 'Göster' }}
                </button>
              </div>
              <input 
                [type]="showApiKey() ? 'text' : 'password'"
                [(ngModel)]="openRouterApiKey"
                class="w-full px-3 py-1.5 rounded-lg bg-dark-900 border border-slate-700 text-xs text-white font-mono focus:border-brand-cyan focus:outline-none"
                placeholder="sk-or-v1-..." />
            </div>

            <!-- GELİŞMİŞ TÜM MODELLER ARAMA & SEÇME ALANI -->
            <div class="space-y-2 pt-2 border-t border-slate-800/80">
              <div class="flex items-center justify-between">
                <label class="text-[10px] font-bold text-slate-200 uppercase tracking-wider flex items-center gap-1.5">
                  <span>🧠</span> Model Kataloğu
                  <span class="px-1.5 py-0.2 rounded bg-brand-cyan/20 text-brand-cyan font-mono text-[9px]">
                    {{ modelsList().length > 0 ? (modelsList().length + ' Model Hazır') : 'Yükleniyor...' }}
                  </span>
                </label>
                <span class="text-[10px] text-slate-400">
                  Eşleşen: <b class="text-white font-mono">{{ filteredModels().length }}</b>
                </span>
              </div>

              <!-- Sağlayıcı / Marka Filtreleme Çipleri -->
              <div class="flex items-center gap-1 overflow-x-auto pb-1 text-[10px] no-scrollbar">
                <button
                  type="button"
                  *ngFor="let cat of categories"
                  (click)="selectedCategory.set(cat.id)"
                  [ngClass]="selectedCategory() === cat.id ? 'bg-brand-cyan text-slate-950 font-bold shadow-glow-sm' : 'bg-dark-900 text-slate-400 hover:text-white border border-slate-800'"
                  class="px-2.5 py-0.8 rounded-full whitespace-nowrap cursor-pointer transition-colors">
                  {{ cat.name }}
                </button>
              </div>

              <!-- Akıllı Arama & URL Temizleme Girişi -->
              <div class="relative">
                <input 
                  type="text"
                  [ngModel]="modelSearchQuery()"
                  (ngModelChange)="onSearchInput($event)"
                  placeholder="🔍 Model adı, ID veya OpenRouter linki yapıştırın (örn: ling 3.1 flash, claude, gpt-4o)..."
                  class="w-full px-3 py-2 pl-8 pr-7 rounded-lg bg-dark-900 border border-slate-700 text-xs text-white placeholder-slate-500 focus:border-brand-cyan focus:outline-none" />
                <span class="absolute left-2.5 top-2.5 text-slate-500 text-xs">🔍</span>
                <button 
                  *ngIf="modelSearchQuery()"
                  type="button"
                  (click)="onSearchInput('')"
                  class="absolute right-2.5 top-2 text-xs text-slate-400 hover:text-white cursor-pointer">
                  ✕
                </button>
              </div>

              <!-- Canlı Arama Sonuçları Listesi (Tıklanabilir Kartlar) -->
              <div *ngIf="filteredModels().length > 0" class="space-y-1.5 max-h-52 overflow-y-auto pr-1 scrollbar-thin rounded-lg border border-slate-800 bg-dark-950/70 p-1.5">
                <div 
                  *ngFor="let m of filteredModels().slice(0, 40)"
                  (click)="selectModel(m.id)"
                  [ngClass]="openRouterModel === m.id ? 'border-brand-cyan bg-brand-cyan/15 ring-1 ring-brand-cyan/50' : 'border-slate-800/80 bg-dark-900/60 hover:border-slate-700 hover:bg-dark-800/80'"
                  class="p-2 rounded-lg border flex items-center justify-between gap-2 cursor-pointer transition-all group">
                  <div class="flex-1 min-w-0">
                    <div class="flex items-center gap-2">
                      <span class="text-xs font-bold text-white group-hover:text-brand-cyan transition-colors truncate">
                        {{ m.name }}
                      </span>
                      <span *ngIf="m.contextLength" class="text-[9px] px-1 py-0.2 rounded bg-slate-800 text-slate-400 font-mono shrink-0">
                        {{ (m.contextLength / 1000 | number:'1.0-0') }}k ctx
                      </span>
                    </div>
                    <div class="text-[10px] font-mono text-slate-400 truncate">
                      {{ m.id }}
                    </div>
                    <div *ngIf="m.description" class="text-[10px] text-slate-500 line-clamp-1 mt-0.5">
                      {{ m.description }}
                    </div>
                  </div>
                  <button 
                    type="button"
                    (click)="$event.stopPropagation(); selectModel(m.id)"
                    class="px-2.5 py-1 rounded text-[10px] font-bold shrink-0 transition-colors"
                    [ngClass]="openRouterModel === m.id ? 'bg-brand-cyan text-slate-950 shadow-glow-sm' : 'bg-slate-800 text-slate-300 hover:bg-brand-cyan hover:text-slate-950'">
                    {{ openRouterModel === m.id ? '✓ Seçili' : 'Seç' }}
                  </button>
                </div>
                <div *ngIf="filteredModels().length > 40" class="text-center py-1 text-[10px] text-slate-500">
                  + {{ filteredModels().length - 40 }} model daha var. Arama terimini detaylandırarak listeyi daraltabilirsiniz.
                </div>
              </div>

              <!-- Eşleşme Bulunamadı Bildirimi -->
              <div *ngIf="filteredModels().length === 0 && !loadingModels()" class="p-3 text-center rounded-lg border border-dashed border-slate-800 text-xs text-slate-400">
                Aramanızla eşleşen model bulunamadı. Aşağıdaki kutuya dilediğiniz model ID'sini doğrudan yazabilirsiniz.
              </div>

              <!-- Aktif / Doğrudan Manuel Model ID Girişi -->
              <div class="p-2.5 rounded-lg bg-dark-900 border border-slate-800 space-y-1">
                <div class="flex items-center justify-between">
                  <label class="text-[9px] font-bold text-slate-300 uppercase tracking-wider">
                    Aktif Seçili Model ID (Doğrudan düzenlenebilir veya link yapıştırılabilir):
                  </label>
                  <span class="text-[9px] text-brand-cyan font-mono font-semibold">Aktif</span>
                </div>
                <input 
                  type="text"
                  [ngModel]="openRouterModel"
                  (ngModelChange)="onModelIdDirectChange($event)"
                  class="w-full px-3 py-1.5 rounded-lg bg-dark-950 border border-brand-cyan/40 text-xs text-brand-cyan font-mono focus:border-brand-cyan focus:outline-none"
                  placeholder="inclusionai/ling-3.1-flash" />
              </div>

            </div>
          </div>

          <!-- Antigravity Bilgi Kutusu (Antigravity seçiliyse) -->
          <div *ngIf="selectedProvider === 'antigravity'" class="p-3.5 rounded-xl bg-dark-950/60 border border-purple-500/20 space-y-2 text-xs animate-in fade-in duration-200">
            <div class="flex items-center justify-between">
              <span class="font-bold text-purple-300 flex items-center gap-1.5">
                <span>🔮</span> Antigravity Proxy Detayları
              </span>
              <button 
                type="button" 
                (click)="testConnection('antigravity')"
                [disabled]="settingsService.isTesting()"
                class="px-2.5 py-1 rounded-lg bg-dark-800 hover:bg-slate-700 border border-slate-700 text-slate-200 text-xs font-semibold flex items-center gap-1.5 transition-colors cursor-pointer disabled:opacity-50">
                <span *ngIf="!settingsService.isTesting()">⚡</span>
                <span *ngIf="settingsService.isTesting()" class="animate-spin text-[10px]">⏳</span>
                <span>{{ settingsService.isTesting() ? 'Test Ediliyor...' : 'Proxy Test Et' }}</span>
              </button>
            </div>

            <div *ngIf="settingsService.testResult() as test" class="p-2.5 rounded-lg text-xs flex items-center gap-2"
              [ngClass]="test.success ? 'bg-emerald-500/10 text-emerald-300 border border-emerald-500/30' : 'bg-rose-500/10 text-rose-300 border border-rose-500/30'">
              <span>{{ test.success ? '✓' : '⚠️' }}</span>
              <span class="flex-1">{{ test.message }}</span>
              <span *ngIf="test.latencyMs" class="font-mono text-[10px] text-slate-400">{{ test.latencyMs }}ms</span>
            </div>

            <p class="text-[11px] text-slate-400">
              Antigravity proxy'si yerel ortamınızda veya Docker konteynerında çalışır. Varsayılan olarak <b>gemini-3.8-flash-tiered</b> modeli kullanılır.
            </p>
          </div>

        </div>

        <!-- Modal Alt Butonları -->
        <div class="px-6 py-3.5 border-t border-slate-800 bg-dark-950/80 flex items-center justify-between shrink-0">
          <span class="text-[11px] text-slate-400 truncate max-w-xs">
            Seçilen: <strong class="text-white capitalize">{{ selectedProvider }}</strong> 
            <span *ngIf="selectedProvider === 'openrouter'" class="text-brand-cyan font-mono ml-1 font-semibold truncate">({{ openRouterModel }})</span>
          </span>
          <div class="flex items-center gap-2">
            <button 
              type="button" 
              (click)="settingsService.closeModal()" 
              class="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold cursor-pointer">
              Kapat
            </button>
            <button 
              type="button" 
              (click)="saveSettings()" 
              [disabled]="settingsService.isSaving()"
              class="px-5 py-2 rounded-lg bg-brand-cyan hover:bg-cyan-400 text-slate-950 text-xs font-bold shadow-glow-sm cursor-pointer disabled:opacity-50 flex items-center gap-1.5">
              <span *ngIf="settingsService.isSaving()" class="animate-spin text-xs">⏳</span>
              <span>{{ settingsService.isSaving() ? 'Kaydediliyor...' : '✓ Değişiklikleri Kaydet & Aktif Et' }}</span>
            </button>
          </div>
        </div>

      </div>
    </div>
  `
})
export class SettingsModalComponent implements OnInit {
  readonly settingsService = inject(SettingsService);

  selectedProvider: 'antigravity' | 'openrouter' = 'antigravity';
  openRouterApiKey = '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';
  openRouterModel = 'google/gemini-3.8-flash';
  readonly showApiKey = signal<boolean>(false);

  readonly modelsList = signal<ModelOption[]>([]);
  readonly loadingModels = signal<boolean>(false);
  readonly modelSearchQuery = signal<string>('');
  readonly selectedCategory = signal<string>('all');

  readonly categories = [
    { id: 'all', name: 'Tümü' },
    { id: 'inclusionai', name: 'Ling (InclusionAI)' },
    { id: 'google', name: 'Google Gemini' },
    { id: 'anthropic', name: 'Anthropic Claude' },
    { id: 'openai', name: 'OpenAI GPT' },
    { id: 'deepseek', name: 'DeepSeek' },
    { id: 'meta-llama', name: 'Meta Llama' },
    { id: 'mistralai', name: 'Mistral' },
    { id: 'qwen', name: 'Qwen' }
  ];

  readonly filteredModels = computed(() => {
    let list = this.modelsList();
    const cat = this.selectedCategory();
    if (cat !== 'all') {
      list = list.filter(m => {
        const idLower = m.id.toLowerCase();
        const nameLower = (m.name || '').toLowerCase();
        if (cat === 'inclusionai') {
          return idLower.includes('inclusionai') || idLower.includes('ling') || nameLower.includes('ling');
        }
        return idLower.startsWith(cat + '/') || idLower.includes(cat) || nameLower.includes(cat);
      });
    }

    const q = this.modelSearchQuery().trim().toLowerCase();
    if (q) {
      // Çoklu kelime fuzzy / token parçalama
      const tokens = q.replace(/[-_\\/.]/g, ' ').split(/\s+/).filter(t => t.length > 0);
      list = list.filter(m => {
        const combined = `${m.id} ${m.name || ''} ${m.description || ''}`.toLowerCase();
        const combinedNormalized = combined.replace(/[-_\\/.]/g, ' ');
        return tokens.every(token => combined.includes(token) || combinedNormalized.includes(token));
      });
    }
    return list;
  });

  constructor() {
    this.syncFromSettingsService();
    effect(() => {
      if (this.settingsService.isModalOpen()) {
        this.syncFromSettingsService();
        if (this.modelsList().length === 0) {
          this.loadModels();
        }
      }
    });
  }

  ngOnInit(): void {
    this.syncFromSettingsService();
    this.loadModels();
  }

  private syncFromSettingsService(): void {
    this.selectedProvider = this.settingsService.activeProvider();
    const cur = this.settingsService.currentSettings();
    if (cur) {
      if (cur.openRouterApiKey) this.openRouterApiKey = cur.openRouterApiKey;
      if (cur.openRouterModel) this.openRouterModel = cur.openRouterModel;
    }
  }

  onSearchInput(val: string): void {
    let clean = (val || '').trim();
    // Eğer kullanıcı openrouter linki yapıştırdıysa: https://openrouter.ai/inclusionai/ling-3.1-flash
    if (clean.includes('openrouter.ai/')) {
      clean = clean.split('openrouter.ai/')[1].split('?')[0].split('#')[0].trim();
      this.openRouterModel = clean;
      this.modelSearchQuery.set(clean);
      return;
    }
    this.modelSearchQuery.set(clean);
  }

  onModelIdDirectChange(val: string): void {
    let clean = (val || '').trim();
    if (clean.includes('openrouter.ai/')) {
      clean = clean.split('openrouter.ai/')[1].split('?')[0].split('#')[0].trim();
    }
    this.openRouterModel = clean;
  }

  selectModel(modelId: string): void {
    this.openRouterModel = modelId;
  }

  loadModels(): void {
    this.loadingModels.set(true);
    this.settingsService.getAvailableModels('openrouter').subscribe({
      next: (list) => {
        this.loadingModels.set(false);
        if (list && list.length > 0) {
          this.modelsList.set(list);
          const found = list.some(m => m.id === this.openRouterModel);
          if (!found && this.openRouterModel) {
            this.modelsList.update(cur => [
              { id: this.openRouterModel, name: this.openRouterModel + ' (Mevcut Seçim)' },
              ...cur
            ]);
          }
        }
      },
      error: () => this.loadingModels.set(false)
    });
  }

  testConnection(provider: 'antigravity' | 'openrouter'): void {
    this.settingsService.testAiProvider(provider).subscribe();
  }

  saveSettings(): void {
    this.settingsService.updateAiProviderSettings({
      activeProvider: this.selectedProvider,
      openRouterApiKey: this.openRouterApiKey,
      openRouterModel: this.openRouterModel
    }).subscribe({
      next: () => {
        this.settingsService.closeModal();
      },
      error: () => {
        this.settingsService.closeModal();
      }
    });
  }
}
