export interface VideoDetailDto {
  id: string;
  projectId: string;
  baslik: string;
  dosyaYolu: string;
  temizSesYolu?: string;
  sure?: string; // TimeSpan is serialized as string in JSON
  dosyaBoyutu: number;
  islemDurumu: number | string; // Adjust depending on if it's string enum
  transkriptVar: boolean;
  olusturmaTarihi: string;
  islemTamamlanmaTarihi?: string;
  streamUrl?: string; // Keep for fallback logic if needed
}

export interface VideoUploadResponseDto {
  videoId: string;
  projectId: string;
  dosyaYolu: string;
  durum: string;
  mesaj: string;
}
