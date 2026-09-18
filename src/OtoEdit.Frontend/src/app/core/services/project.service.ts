import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from './api.service';
import { ProjectCreateDto, ProjectDetailDto, ProjectListDto, ProjectUpdateDto } from '../models/project.model';

@Injectable({
  providedIn: 'root'
})
export class ProjectService {
  private api = inject(ApiService);

  getAll(): Observable<ProjectListDto[]> {
    return this.api.get<ProjectListDto[]>('/projects');
  }

  getById(id: string): Observable<ProjectDetailDto> {
    return this.api.get<ProjectDetailDto>(`/projects/${id}`);
  }

  create(dto: ProjectCreateDto): Observable<ProjectDetailDto> {
    return this.api.post<ProjectDetailDto>('/projects', dto);
  }

  update(id: string, dto: ProjectUpdateDto): Observable<ProjectDetailDto> {
    return this.api.put<ProjectDetailDto>(`/projects/${id}`, dto);
  }

  delete(id: string): Observable<void> {
    return this.api.delete<void>(`/projects/${id}`);
  }
}
