import { Injectable, signal } from '@angular/core';
import * as signalR from '@microsoft/signalr';
import { Subject } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface AnalysisProgressEvent {
  projectId: string;
  asama: string;
  yuzde: number;
  mesaj?: string;
}

export interface AnalysisCompletedEvent {
  projectId: string;
  edlVersiyon: number;
}

export interface RenderProgressEvent {
  renderJobId: string;
  projectId: string;
  yuzde: number;
  mesaj?: string;
}

export interface RenderCompletedEvent {
  renderJobId: string;
  projectId: string;
  indirmeUrl: string;
}

export interface PipelineErrorEvent {
  projectId: string;
  videoId?: string;
  hataMesaji: string;
}

@Injectable({
  providedIn: 'root'
})
export class SignalrService {
  private hubConnection: signalR.HubConnection | null = null;

  // Angular 18+ Signals
  readonly isConnected = signal<boolean>(false);
  readonly currentAnalysisProgress = signal<AnalysisProgressEvent | null>(null);
  readonly currentRenderProgress = signal<RenderProgressEvent | null>(null);

  // RxJS Subjects
  readonly analysisCompleted$ = new Subject<AnalysisCompletedEvent>();
  readonly renderProgress$ = new Subject<RenderProgressEvent>();
  readonly renderCompleted$ = new Subject<RenderCompletedEvent>();
  readonly pipelineError$ = new Subject<PipelineErrorEvent>();

  private activeProjectGroups = new Set<string>();

  constructor() {
    this.initConnection();
  }

  private initConnection(): void {
    const hubUrl = environment.hubUrl.startsWith('http')
      ? environment.hubUrl
      : `${window.location.origin}${environment.hubUrl}`;

    this.hubConnection = new signalR.HubConnectionBuilder()
      .withUrl(hubUrl, {
        skipNegotiation: false,
        transport: signalR.HttpTransportType.WebSockets | signalR.HttpTransportType.LongPolling
      })
      .withAutomaticReconnect([0, 2000, 5000, 10000, 30000])
      .configureLogging(signalR.LogLevel.Information)
      .build();

    this.registerHandlers();
    this.startConnection();
  }

  private registerHandlers(): void {
    if (!this.hubConnection) return;

    this.hubConnection.on('AnalysisProgress', (data: AnalysisProgressEvent) => {
      this.currentAnalysisProgress.set(data);
    });

    this.hubConnection.on('AnalysisCompleted', (data: AnalysisCompletedEvent) => {
      this.analysisCompleted$.next(data);
    });

    this.hubConnection.on('RenderProgress', (data: RenderProgressEvent) => {
      this.currentRenderProgress.set(data);
      this.renderProgress$.next(data);
    });

    this.hubConnection.on('RenderCompleted', (data: RenderCompletedEvent) => {
      this.renderCompleted$.next(data);
    });

    this.hubConnection.on('PipelineError', (data: PipelineErrorEvent) => {
      this.pipelineError$.next(data);
    });

    this.hubConnection.onreconnecting(() => {
      this.isConnected.set(false);
    });

    this.hubConnection.onreconnected(async () => {
      this.isConnected.set(true);
      await this.rejoinActiveGroups();
    });

    this.hubConnection.onclose(() => {
      this.isConnected.set(false);
    });
  }

  private async startConnection(): Promise<void> {
    if (!this.hubConnection) return;
    try {
      await this.hubConnection.start();
      this.isConnected.set(true);
      console.log('SignalR Hub bağlantısı başarılı.');
      await this.rejoinActiveGroups();
    } catch (err) {
      console.warn('SignalR bağlantı hatası, tekrar denenecek...', err);
      setTimeout(() => this.startConnection(), 5000);
    }
  }

  private async rejoinActiveGroups(): Promise<void> {
    if (this.hubConnection?.state !== signalR.HubConnectionState.Connected) return;
    for (const projectId of this.activeProjectGroups) {
      try {
        await this.hubConnection.invoke('JoinProjectGroup', projectId);
      } catch (err) {
        console.warn(`JoinProjectGroup (${projectId}) hatası:`, err);
      }
    }
  }

  async joinProjectGroup(projectId: string): Promise<void> {
    if (!projectId) return;
    this.activeProjectGroups.add(projectId);
    if (this.hubConnection?.state === signalR.HubConnectionState.Connected) {
      try {
        await this.hubConnection.invoke('JoinProjectGroup', projectId);
      } catch (err) {
        console.warn(`JoinProjectGroup (${projectId}) hatası:`, err);
      }
    }
  }

  async leaveProjectGroup(projectId: string): Promise<void> {
    if (!projectId) return;
    this.activeProjectGroups.delete(projectId);
    if (this.hubConnection?.state === signalR.HubConnectionState.Connected) {
      try {
        await this.hubConnection.invoke('LeaveProjectGroup', projectId);
      } catch (err) {
        console.warn(`LeaveProjectGroup (${projectId}) hatası:`, err);
      }
    }
  }
}
