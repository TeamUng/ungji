import type {
  ChatAdapter,
  ChatResponse,
  ResponseMessage,
} from "@/types/chat";

export const liveChatAdapter: ChatAdapter = async function* (request) {
  const response = await fetch("/backend/chat", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(`코치 응답 요청 실패 (${response.status})`);
  }

  if (!response.body) {
    throw new Error("코치 응답 스트림이 비어 있어요.");
  }

  for await (const chatResponse of readChatResponses(response.body)) {
    for (const message of chatResponse.messages) {
      yield message;
    }
  }
};

async function* readChatResponses(
  stream: ReadableStream<Uint8Array>,
): AsyncGenerator<ChatResponse> {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) {
      break;
    }

    buffer += decoder.decode(value, { stream: true });
    const events = buffer.split(/\r?\n\r?\n/);
    buffer = events.pop() ?? "";

    for (const event of events) {
      const parsed = parseSseEvent(event);
      if (parsed) {
        yield parsed;
      }
    }
  }

  buffer += decoder.decode();
  const parsed = parseSseEvent(buffer);
  if (parsed) {
    yield parsed;
  }
}

function parseSseEvent(event: string): ChatResponse | null {
  const data = event
    .split(/\r?\n/)
    .filter((line) => line.startsWith("data:"))
    .map((line) => line.replace(/^data:\s?/, ""))
    .join("\n")
    .trim();

  if (!data || data === "[DONE]") {
    return null;
  }

  return JSON.parse(data) as ChatResponse;
}

export function responseMessagesFromChatResponse(
  response: ChatResponse,
): ResponseMessage[] {
  return response.messages;
}
