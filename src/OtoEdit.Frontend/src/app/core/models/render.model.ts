export enum RenderDurumu {
  Kuyrukta = 'Kuyrukta',
  RenderEdiliyor = 'RenderEdiliyor',
  Tamamlandi = 'Tamamlandi',
  Hata = 'Hata'
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
