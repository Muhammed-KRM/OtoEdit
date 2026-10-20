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

  uploadVideo(
    projectId: string, 
    file: File, 
    options?: {
      autoJumpcut?: boolean;
      autoRetake?: boolean;
      autoBroll?: boolean;
      autoSubtitles?: boolean;
      audioEnhancementEnabled?: boolean;
      gestureCommandsEnabled?: boolean;
      autoDirectorEnabled?: boolean;
      directToEditor?: boolean;
    }
  ): Observable<HttpEvent<VideoUploadResponseDto>> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('autoJumpcut', String(options?.autoJumpcut ?? true));
    formData.append('autoRetake', String(options?.autoRetake ?? true));
    formData.append('autoBroll', String(options?.autoBroll ?? true));
    formData.append('autoSubtitles', String(options?.autoSubtitles ?? true));
    if (options?.audioEnhancementEnabled !== undefined) {
      formData.append('audioEnhancementEnabled', String(options.audioEnhancementEnabled));
    }
    if (options?.gestureCommandsEnabled !== undefined) {
      formData.append('gestureCommandsEnabled', String(options.gestureCommandsEnabled));
    }
    if (options?.autoDirectorEnabled !== undefined) {
      formData.append('autoDirectorEnabled', String(options.autoDirectorEnabled));
    }
    if (options?.directToEditor !== undefined) {
      formData.append('directToEditor', String(options.directToEditor));
    }

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
    return this.http.get<VideoDetailDto>(`${this.baseUrl}/projects/${projectId}/video`);
  }

  reanalyzeProject(
    projectId: string,
    options: {
      autoJumpcut?: boolean;
      autoRetake?: boolean;
      autoBroll?: boolean;
      autoSubtitles?: boolean;
      audioEnhancementEnabled?: boolean;
      gestureCommandsEnabled?: boolean;
      autoDirectorEnabled?: boolean;
    }
  ): Observable<any> {
    return this.http.post(`${this.baseUrl}/projects/${projectId}/reanalyze`, options);
  }
}
