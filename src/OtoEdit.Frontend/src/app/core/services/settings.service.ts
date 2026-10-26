import { Injectable, inject, signal, computed } from '@angular/core';
import { Observable, tap } from 'rxjs';
import { ApiService } from './api.service';

export interface AiProviderSettings {
  activeProvider: 'antigravity' | 'openrouter';
  openRouterApiKey: string;
  openRouterBaseUrl: string;
  openRouterModel: string;
  antigravityProxyUrl: string;
  antigravityProxyKey: string;
  antigravityProxyModel: string;
}

export interface TestConnectionResult {
  success: boolean;
  message: string;
  latencyMs?: number;
}

export interface ModelOption {
  id: string;
  name: string;
  description?: string;
  contextLength?: number;
}

@Injectable({
  providedIn: 'root'
})
export class SettingsService {
  private api = inject(ApiService);

  // Global Reaktif State (Tüm sayfalarda canlı paylaşılır)
  readonly activeProvider = signal<'antigravity' | 'openrouter'>('antigravity');
  readonly isModalOpen = signal<boolean>(false);
  readonly currentSettings = signal<AiProviderSettings | null>(null);
  readonly isTesting = signal<boolean>(false);
  readonly testResult = signal<TestConnectionResult | null>(null);
  readonly isSaving = signal<boolean>(false);

  readonly activeModel = computed<string>(() => {
    const prov = this.activeProvider();
    if (prov === 'antigravity') {
      return this.currentSettings()?.antigravityProxyModel || 'gemini-3.8-flash-tiered';
    }
    const saved = this.currentSettings()?.openRouterModel;
    if (saved) return saved;
    try {
      const local = localStorage.getItem('otoedit_openrouter_model');
      if (local) return local;
    } catch { }
    return 'google/gemini-3.8-flash';
  });

  readonly activeModelShortName = computed<string>(() => {
    const m = this.activeModel();
    if (m === 'gemini-3.8-flash-tiered') return 'Gemini 3.8 Flash';
    if (m.includes('/')) {
      const parts = m.split('/');
      return parts[1]; // e.g. "ling-3.1-flash" from "inclusionai/ling-3.1-flash"
    }
    return m;
  });

  constructor() {
    this.initFromLocalAndRemote();
  }

  private initFromLocalAndRemote(): void {
    try {
      const local = localStorage.getItem('otoedit_ai_provider') as 'antigravity' | 'openrouter';
      if (local === 'antigravity' || local === 'openrouter') {
        this.activeProvider.set(local);
      }
    } catch { }

    this.getAiProviderSettings().subscribe({
      next: (cfg) => {
        if (cfg) {
          this.currentSettings.set(cfg);
          if (cfg.activeProvider === 'antigravity' || cfg.activeProvider === 'openrouter') {
            this.activeProvider.set(cfg.activeProvider);
          }
        }
      },
      error: (err) => console.warn('AI ayarları servisten alınamadı, yerel ayar kullanılıyor:', err)
    });
  }

  getAiProviderSettings(): Observable<AiProviderSettings> {
    return this.api.get<AiProviderSettings>('/settings/ai-provider').pipe(
      tap((cfg) => {
        if (cfg) {
          this.currentSettings.set(cfg);
          if (cfg.activeProvider === 'antigravity' || cfg.activeProvider === 'openrouter') {
            this.activeProvider.set(cfg.activeProvider);
          }
        }
      })
    );
  }

  updateAiProviderSettings(settings: Partial<AiProviderSettings>): Observable<AiProviderSettings> {
    this.isSaving.set(true);
    return this.api.post<AiProviderSettings>('/settings/ai-provider', settings).pipe(
      tap({
        next: (updated) => {
          this.isSaving.set(false);
          this.currentSettings.set(updated);
          if (updated.activeProvider) {
            this.activeProvider.set(updated.activeProvider);
            try {
              localStorage.setItem('otoedit_ai_provider', updated.activeProvider);
              if (updated.openRouterApiKey) localStorage.setItem('otoedit_openrouter_key', updated.openRouterApiKey);
              if (updated.openRouterModel) localStorage.setItem('otoedit_openrouter_model', updated.openRouterModel);
            } catch { }
          }
        },
        error: () => this.isSaving.set(false)
      })
    );
  }

  testAiProvider(provider: 'antigravity' | 'openrouter'): Observable<TestConnectionResult> {
    this.isTesting.set(true);
    this.testResult.set(null);
    return this.api.post<TestConnectionResult>('/settings/ai-provider/test', { provider }).pipe(
      tap({
        next: (res) => {
          this.isTesting.set(false);
          this.testResult.set(res);
        },
        error: (err) => {
          this.isTesting.set(false);
          this.testResult.set({
            success: false,
            message: `Bağlantı hatası: ${err.message || 'Sunucuya ulaşılamadı'}`
          });
        }
      })
    );
  }

  getAvailableModels(provider: string = 'openrouter'): Observable<ModelOption[]> {
    return this.api.get<ModelOption[]>(`/settings/ai-provider/models?provider=${encodeURIComponent(provider)}`);
  }

  quickSwitchProvider(provider: 'antigravity' | 'openrouter'): void {
    this.activeProvider.set(provider);
    try {
      localStorage.setItem('otoedit_ai_provider', provider);
    } catch { }

    const cur = this.currentSettings();
    this.updateAiProviderSettings({
      activeProvider: provider,
      openRouterApiKey: cur?.openRouterApiKey,
      openRouterModel: cur?.openRouterModel || 'google/gemini-3.8-flash'
    }).subscribe({
      next: () => {},
      error: (err) => console.warn('Hızlı AI sağlayıcı geçişi backend hatası:', err)
    });
  }

  openModal(): void {
    this.testResult.set(null);
    this.isModalOpen.set(true);
  }

  closeModal(): void {
    this.isModalOpen.set(false);
    this.testResult.set(null);
  }
}
