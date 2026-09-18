import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from './api.service';
import { ChatMessageDto, ChatResponseDto, ChatSendMessageDto } from '../models/chat.model';

@Injectable({
  providedIn: 'root'
})
export class ChatService {
  private api = inject(ApiService);

  sendMessage(projectId: string, mesaj: string): Observable<ChatResponseDto> {
    const body: ChatSendMessageDto = { mesaj };
    return this.api.post<ChatResponseDto>(`/projects/${projectId}/chat`, body);
  }

  getHistory(projectId: string): Observable<ChatMessageDto[]> {
    return this.api.get<ChatMessageDto[]>(`/projects/${projectId}/chat`);
  }
}
