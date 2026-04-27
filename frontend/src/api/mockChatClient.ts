import { createMockResponse } from "@/data/mockResponses";
import type { ChatRequest, ChatResponse } from "@/types/chat";
import type { StudentCase } from "@/types/learning";

const MOCK_LATENCY_MS = 180;

export async function mockChatClient(
  request: ChatRequest,
  studentCase: StudentCase,
): Promise<ChatResponse> {
  await new Promise((resolve) => window.setTimeout(resolve, MOCK_LATENCY_MS));
  return createMockResponse(request, studentCase);
}
