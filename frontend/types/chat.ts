export type ConversationSummary = {
  id: string;
  title?: string | null;
};

export type Message = {
  id: string;
  text?: string;
  imageUri?: string | null;
  fileUri?: string | null;
  fileName?: string | null;
  fileSize?: number | null;
  fileType?: string | null;
  timestamp: number;
  sender: 'me' | 'other';
};
