import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from './api.service';
import { RenderRequestDto, RenderStatusDto } from '../models/render.model';

@Injectable({
  providedIn: 'root'
})
export class RenderService {
  private api = inject(ApiService);

  requestRender(projectId: string, dto?: RenderRequestDto): Observable<RenderStatusDto> {
    return this.api.post<RenderStatusDto>(`/projects/${projectId}/render`, dto || {});
  }

  getRenderStatus(projectId: string, renderJobId: string): Observable<RenderStatusDto> {
    return this.api.get<RenderStatusDto>(`/projects/${projectId}/render/${renderJobId}`);
  }

  getDownloadUrl(projectId: string, renderJobId: string): Observable<{ downloadUrl: string }> {
    return this.api.get<{ downloadUrl: string }>(`/projects/${projectId}/render/${renderJobId}/download`);
  }
}
