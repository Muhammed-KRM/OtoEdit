import { EdlPatchDto } from './edl.model';

export interface ChatMessageDto {
  id?: string;
  projectId: string;
  rol: 'user' | 'assistant';
  mesaj: string;
  olusturulmaZamani: string;
  edlPatch?: EdlPatchDto;
}

export interface ChatSendMessageDto {
  mesaj: string;
}

export interface ChatResponseDto {
  mesaj: string;
  edlPatch?: EdlPatchDto;
  yeniVersiyon?: number;
}
