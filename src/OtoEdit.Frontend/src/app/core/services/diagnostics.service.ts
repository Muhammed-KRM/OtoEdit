import { Injectable } from '@angular/core';

export interface TraceEvent {
  traceId: string;
  timestamp: string;
  stage: string;
  component: string;
  action: string;
  input: any;
  output?: any;
  persistedState?: any;
}

@Injectable({
  providedIn: 'root'
})
export class DiagnosticsService {
  private traces: TraceEvent[] = [];

  constructor() {
    if (typeof window !== 'undefined') {
      (window as any).__OTOEDIT_DIAGNOSTICS__ = {
        getTraces: () => this.traces,
        clearTraces: () => { this.traces = []; console.log('🧹 OtoEdit Diagnostics temizlendi.'); },
        inspectLast: () => this.traces[this.traces.length - 1],
        printSummary: () => this.printSummary()
      };
      console.log('🩺 [OtoEdit:Diagnostics] Aktif. Konsoldan window.__OTOEDIT_DIAGNOSTICS__ ile erişebilirsiniz.');
    }
  }

  logTrace(stage: string, action: string, input: any, output?: any, persistedState?: any): void {
    const traceId = `trc_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`;
    const event: TraceEvent = {
      traceId,
      timestamp: new Date().toISOString(),
      stage,
      component: 'Frontend.Editor',
      action,
      input,
      output,
      persistedState
    };
    this.traces.push(event);
    if (this.traces.length > 500) this.traces.shift();

    console.groupCollapsed(`🔍 [OtoEdit:${stage}] ${action} (${traceId})`);
    console.log('📥 Girdi (Input):', input);
    if (output !== undefined) console.log('📤 Çıktı (Output):', output);
    if (persistedState !== undefined) console.log('💾 Kalıcı Durum (State):', persistedState);
    console.groupEnd();
  }

  printSummary(): void {
    console.table(this.traces.map(t => ({
      Zaman: t.timestamp.split('T')[1].slice(0, 8),
      Süreç: t.stage,
      Aksiyon: t.action,
      Girdi: JSON.stringify(t.input).slice(0, 60),
      Çıktı: JSON.stringify(t.output || '').slice(0, 60)
    })));
  }
}
