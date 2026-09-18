export enum ProjectDurumu {
  Taslak = 'Taslak',
  VideoYuklendi = 'VideoYuklendi',
  AnalizEdiliyor = 'AnalizEdiliyor',
  AnalizTamamlandi = 'AnalizTamamlandi',
  RenderEdiliyor = 'RenderEdiliyor',
  Tamamlandi = 'Tamamlandi',
  Hata = 'Hata'
}

export enum VideoFormati {
  Yatay_16_9 = 'Yatay_16_9',
  Dikey_9_16 = 'Dikey_9_16',
  Kare_1_1 = 'Kare_1_1'
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
