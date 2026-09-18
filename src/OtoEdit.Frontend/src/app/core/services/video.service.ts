import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpEvent } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { VideoDetailDto, VideoUploadResponseDto } from '../models/video.model';

@Injectable({
  providedIn: 'root'
})
export class VideoService {
  private http = inject(HttpClient);
  private baseUrl = environment.apiUrl;

  uploadVideo(projectId: string, file: File): Observable<HttpEvent<VideoUploadResponseDto>> {
    const formData = new FormData();
    formData.append('file', file);

    return this.http.post<VideoUploadResponseDto>(
      `${this.baseUrl}/projects/${projectId}/videos`,
      formData,
      {
        reportProgress: true,
        observe: 'events'
      }
    );
  }

  getVideo(projectId: string): Observable<VideoDetailDto> {
    return this.http.get<VideoDetailDto>(`${this.baseUrl}/projects/${projectId}/videos`);
  }
}
