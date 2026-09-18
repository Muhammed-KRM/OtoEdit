export interface VideoDetailDto {
  id: string;
  projectId: string;
  orijinalDosyaAdi: string;
  dosyaYolu: string;
  sureSaniye: number;
  genislik: number;
  yukseklik: number;
  fps: number;
  dosyaBoyutuBytes: number;
  mimeTipi: string;
  olusturulmaTarihi: string;
  streamUrl?: string;
}

export interface VideoUploadResponseDto {
  videoId: string;
  projectId: string;
  dosyaYolu: string;
  durum: string;
  mesaj: string;
}
