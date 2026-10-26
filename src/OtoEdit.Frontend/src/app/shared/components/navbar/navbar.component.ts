import { Component, Input, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { SignalrService } from '../../../core/services/signalr.service';
import { SettingsService } from '../../../core/services/settings.service';
import { SettingsModalComponent } from '../settings-modal/settings-modal.component';

@Component({
  selector: 'app-navbar',
  standalone: true,
  imports: [CommonModule, RouterLink, SettingsModalComponent],
  template: `
    <header class="sticky top-0 z-50 glass-panel border-b border-slate-800/80 px-6 py-3.5">
      <div class="max-w-7xl mx-auto flex items-center justify-between">
        <!-- Logo & Brand -->
        <a routerLink="/" class="flex items-center gap-3 group">
          <div class="w-9 h-9 rounded-xl bg-gradient-to-tr from-brand-blue to-brand-purple flex items-center justify-center shadow-glow-sm group-hover:scale-105 transition-transform">
            <svg class="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
            </svg>
          </div>
          <div>
            <span class="text-lg font-display font-extrabold tracking-tight text-white group-hover:text-brand-cyan transition-colors">OtoEdit</span>
            <span class="ml-2 text-xs font-semibold px-2 py-0.5 rounded-md bg-brand-indigo/20 text-brand-cyan border border-brand-cyan/30">AI MVP</span>
          </div>
        </a>

        <!-- Project Title (varsa) -->
        <div *ngIf="projectTitle" class="hidden md:flex items-center gap-2 text-sm text-slate-300">
          <span class="text-slate-500">/</span>
          <span class="font-medium text-white max-w-xs truncate">{{ projectTitle }}</span>
        </div>

        <!-- Connection Status & Actions -->
        <div class="flex items-center gap-3">
          <!-- AYARLAR & API MENÜSÜ BUTONU (GLOBAL ANA MENÜ & HER YERDE) -->
          <button 
            type="button" 
            (click)="settingsService.openModal()" 
            class="px-2.5 py-1.5 rounded-lg bg-dark-800 hover:bg-slate-700 border text-xs flex items-center gap-1.5 transition-all cursor-pointer shadow-sm group"
            [ngClass]="settingsService.activeProvider() === 'openrouter' ? 'border-brand-cyan/50 text-brand-cyan bg-brand-cyan/10 hover:border-brand-cyan' : 'border-purple-500/40 text-purple-300 bg-purple-500/10 hover:border-purple-400'"
            title="Yapay Zeka API Ayarları (Antigravity / OpenRouter)">
            <span class="text-xs">⚙️</span>
            <span class="text-xs font-semibold">Ayarlar</span>
            <span class="text-[10px] px-1.5 py-0.5 rounded font-mono font-bold uppercase tracking-wider flex items-center gap-1"
              [ngClass]="settingsService.activeProvider() === 'openrouter' ? 'bg-brand-cyan/20 text-brand-cyan border border-brand-cyan/30' : 'bg-purple-500/20 text-purple-300 border border-purple-500/30'">
              <span class="w-1.5 h-1.5 rounded-full" [ngClass]="settingsService.activeProvider() === 'openrouter' ? 'bg-brand-cyan animate-pulse' : 'bg-purple-400'"></span>
              API: {{ settingsService.activeProvider() === 'openrouter' ? 'OpenRouter' : 'Antigravity' }}
            </span>
            <span class="text-[9px] px-1.5 py-0.5 rounded bg-dark-900/80 border border-slate-700/60 text-slate-300 font-mono hidden sm:inline-block truncate max-w-[150px]" [title]="settingsService.activeModel()">
              {{ settingsService.activeModelShortName() }}
            </span>
          </button>

          <!-- SignalR Status Indicator -->
          <div class="flex items-center gap-2 text-xs" [title]="signalr.isConnected() ? 'SignalR Bağlı' : 'Bağlantı Kuruluyor...'">
            <span class="w-2 h-2 rounded-full" [ngClass]="signalr.isConnected() ? 'bg-emerald-400 shadow-glow-sm' : 'bg-amber-400 animate-ping'"></span>
            <span class="text-slate-400 hidden sm:inline">{{ signalr.isConnected() ? 'Canlı Senkron' : 'Bağlanıyor...' }}</span>
          </div>

          <a routerLink="/" class="px-3.5 py-1.5 rounded-lg text-xs font-medium text-slate-300 hover:text-white hover:bg-slate-800 transition-colors">
            Projelerim
          </a>
        </div>
      </div>
    </header>

    <!-- Global Ayarlar Modalı -->
    <app-settings-modal></app-settings-modal>
  `
})
export class NavbarComponent {
  @Input() projectTitle?: string;
  readonly signalr = inject(SignalrService);
  readonly settingsService = inject(SettingsService);
}
