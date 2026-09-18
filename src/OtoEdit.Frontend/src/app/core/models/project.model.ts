export enum ProjectDurumu {
  Taslak = 0,
  VideoYuklendi = 1,
  AnalizEdiliyor = 2,
  AnalizTamamlandi = 3,
  RenderEdiliyor = 4,
  Tamamlandi = 5,
  Hata = 99
}

export enum VideoFormati {
  Yatay_16_9 = 0,
  Dikey_9_16 = 1,
  Kare_1_1 = 2
}

export interface ProjectListDto {
  id: string;
  ad: string;
  aciklama?: string;
  durum: ProjectDurumu;
  videoFormati: VideoFormati;
  videoSayisi: number;
  olusturulmaTarihi: string;
  guncellenmeTarihi?: string;
}

export interface ProjectDetailDto {
  id: string;
  ad: string;
  aciklama?: string;
  durum: ProjectDurumu;
  videoFormati: VideoFormati;
  templateId?: string;
  templateAdi?: string;
  gestureCommandsEnabled: boolean;
  audioEnhancementEnabled: boolean;
  olusturulmaTarihi: string;
  guncellenmeTarihi?: string;
  hasEdl: boolean;
  hasVideo: boolean;
  hasRenderOutput: boolean;
}

export interface ProjectCreateDto {
  ad: string;
  aciklama?: string;
  videoFormati?: VideoFormati;
  templateId?: string;
  gestureCommandsEnabled?: boolean;
  audioEnhancementEnabled?: boolean;
}

export interface ProjectUpdateDto {
  ad: string;
  aciklama?: string;
  videoFormati?: VideoFormati;
  templateId?: string;
  gestureCommandsEnabled?: boolean;
  audioEnhancementEnabled?: boolean;
}
