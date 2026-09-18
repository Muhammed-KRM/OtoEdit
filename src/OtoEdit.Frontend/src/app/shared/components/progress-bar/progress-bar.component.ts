import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-progress-bar',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="w-full">
      <div class="flex justify-between items-center text-xs mb-1.5">
        <span class="text-slate-300 font-medium flex items-center gap-2">
          <span class="w-2 h-2 rounded-full bg-brand-cyan animate-ping"></span>
          {{ label || 'İşlem Sürüyor...' }}
        </span>
        <span class="text-brand-cyan font-bold font-mono">{{ percentage }}%</span>
      </div>
      <div class="w-full h-2.5 bg-dark-700 rounded-full overflow-hidden p-0.5 border border-slate-700/50">
        <div 
          class="h-full bg-gradient-to-r from-brand-blue via-brand-indigo to-brand-cyan rounded-full transition-all duration-300 ease-out shadow-glow-sm"
          [style.width.%]="percentage">
        </div>
      </div>
    </div>
  `
})
export class ProgressBarComponent {
  @Input() percentage = 0;
  @Input() label = '';
}
