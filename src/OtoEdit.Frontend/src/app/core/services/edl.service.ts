import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from './api.service';
import { EdlDto, EdlPatchDto } from '../models/edl.model';

@Injectable({
  providedIn: 'root'
})
export class EdlService {
  private api = inject(ApiService);

  getEdl(projectId: string): Observable<EdlDto> {
    return this.api.get<EdlDto>(`/projects/${projectId}/edl`);
  }

  patchEdl(projectId: string, patch: EdlPatchDto): Observable<{ versiyon: number }> {
    return this.api.patch<{ versiyon: number }>(`/projects/${projectId}/edl`, patch);
  }

  undoEdl(projectId: string): Observable<EdlDto> {
    return this.api.post<EdlDto>(`/projects/${projectId}/edl/undo`, {});
  }

  redoEdl(projectId: string): Observable<EdlDto> {
    return this.api.post<EdlDto>(`/projects/${projectId}/edl/redo`, {});
  }
}
