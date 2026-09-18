import { Component, Input, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { SignalrService } from '../../../core/services/signalr.service';

@Component({
  selector: 'app-navbar',
  standalone: true,
  imports: [CommonModule, RouterLink],
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
        <div class="flex items-center gap-4">
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
  `
})
export class NavbarComponent {
  @Input() projectTitle?: string;
  readonly signalr = inject(SignalrService);
}
