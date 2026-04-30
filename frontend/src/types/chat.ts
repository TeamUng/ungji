export type UseCase = "talk" | "learning";

export type Touchpoint = "tp1" | "tp2" | "tp3" | "tp4" | "tp5";

export type IncomingMessageType = "init" | "text" | "choice";

export type IncomingMessage = {
  type: IncomingMessageType;
  content: string;
};

export type TaskRef = {
  subject?: string;
  unit?: string;
  problem_id?: string;
};

export type ChatRequestContext = {
  completed_task_refs?: TaskRef[];
  current_task_ref?: TaskRef;
  current_task_remaining_count?: number;
  current_problem_id?: string;
};

export type ChatRequest = {
  thread_id: string;
  student_id: string;
  use_case: UseCase;
  current_touchpoint: Touchpoint;
  message: IncomingMessage;
  context?: ChatRequestContext;
};

export type TextMessage = {
  type: "text";
  content: string;
};

export type ChoiceItem = {
  id: string;
  label: string;
};

export type ChoicesMessage = {
  type: "choices";
  items: ChoiceItem[];
};

export type ImageCardMessage = {
  type: "image_card";
  image_url: string;
  caption: string;
};

export type HintStep = {
  step: number;
  content: string;
};

export type HintCardMessage = {
  type: "hint_card";
  steps: HintStep[];
};

export type ResponseMessage =
  | TextMessage
  | ChoicesMessage
  | ImageCardMessage
  | HintCardMessage;

export type ChatResponse = {
  thread_id: string;
  messages: ResponseMessage[];
};

export type DemoCaseId = "lower-korean" | "upper-math";

export type DemoStepId =
  | "home"
  | "learning"
  | "help"
  | "complete"
  | "exit"
  | "finish";

export type ChatAdapterContext = {
  caseId: DemoCaseId;
  stepId: DemoStepId;
};

export type ChatMessageStream = AsyncGenerator<
  ResponseMessage,
  void,
  unknown
>;

export type ChatAdapter = (
  request: ChatRequest,
  context: ChatAdapterContext,
) => ChatMessageStream;

export type ChatTurn =
  | {
      id: string;
      role: "coach";
      message: ResponseMessage;
    }
  | {
      id: string;
      role: "student";
      content: string;
    };

export type ChoiceSelection = {
  id: string;
  label: string;
};
