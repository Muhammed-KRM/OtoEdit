export enum RenderDurumu {
  Kuyrukta = 0,
  RenderEdiliyor = 1,
  Tamamlandi = 2,
  Hata = 99
}

export interface RenderStatusDto {
  renderJobId: string;
  projectId: string;
  durum: RenderDurumu;
  ciktiYolu?: string;
  baslangicZamani?: string;
  bitisZamani?: string;
  sureMs?: number;
  hataMesaji?: string;
}

export interface RenderRequestDto {
  targetFormat?: string;
  templateId?: string;
}

export interface RenderCompletedSignalDto {
  renderJobId: string;
  projectId: string;
  indirmeUrl: string;
}
