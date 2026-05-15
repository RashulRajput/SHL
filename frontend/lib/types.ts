export type ChatRole = "user" | "assistant";

export type Recommendation = {
  name: string;
  url: string;
  test_type: string;
};

export type ChatMessage = {
  role: ChatRole;
  content: string;
  recommendations?: Recommendation[];
};

export type ChatResponse = {
  reply: string;
  recommendations: Recommendation[];
  end_of_conversation: boolean;
};

