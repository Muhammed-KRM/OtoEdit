import { EdlPatchDto } from './edl.model';

export interface FormFieldDto {
  id: string;
  type: 'text' | 'color' | 'select' | 'number' | 'position';
  label: string;
  options?: ({ label: string; value: string } | string)[];
  defaultValue?: string | number;
  required?: boolean;
}

export interface ChatMessageDto {
  id?: string;
  projectId: string;
  rol: 'user' | 'assistant';
  mesaj: string;
  intent?: string;
  patchDurumu?: string;
  olusturulmaZamani: string;
  edlPatch?: EdlPatchDto;
  pendingEdlPatch?: EdlPatchDto;
  formFields?: FormFieldDto[];
  formData?: any; // To store filled data locally
}

export interface ChatSendMessageDto {
  mesaj: string;
}

export interface ChatResponseDto {
  id?: string;
  rol?: string;
  mesaj: string;
  intent?: string;
  patchDurumu?: string;
  edlPatch?: EdlPatchDto;
  pendingEdlPatch?: EdlPatchDto;
  formFields?: FormFieldDto[];
  yeniVersiyon?: number;
}
