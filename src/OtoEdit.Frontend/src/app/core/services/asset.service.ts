import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from './api.service';
import { ProjectAssetDto } from '../models/asset.model';

@Injectable({
  providedIn: 'root'
})
export class AssetService {
  private api = inject(ApiService);

  getAssets(projectId: string): Observable<ProjectAssetDto[]> {
    return this.api.get<ProjectAssetDto[]>(`/projects/${projectId}/assets`);
  }

  uploadAsset(projectId: string, file: File): Observable<ProjectAssetDto> {
    const formData = new FormData();
    formData.append('file', file, file.name);
    return this.api.post<ProjectAssetDto>(`/projects/${projectId}/assets`, formData);
  }

  deleteAsset(projectId: string, assetId: string): Observable<void> {
    return this.api.delete<void>(`/projects/${projectId}/assets/${assetId}`);
  }
}
