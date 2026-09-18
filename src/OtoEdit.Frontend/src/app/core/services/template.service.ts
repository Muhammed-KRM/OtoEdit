import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from './api.service';
import { TemplateDto } from '../models/template.model';

@Injectable({
  providedIn: 'root'
})
export class TemplateService {
  private api = inject(ApiService);

  getAll(): Observable<TemplateDto[]> {
    return this.api.get<TemplateDto[]>('/templates');
  }

  getById(id: string): Observable<TemplateDto> {
    return this.api.get<TemplateDto>(`/templates/${id}`);
  }
}
