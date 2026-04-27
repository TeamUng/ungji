import { FormEvent, useState } from "react";

type CoachComposerProps = {
  disabled: boolean;
  onSendText: (content: string) => void;
};

export function CoachComposer({ disabled, onSendText }: CoachComposerProps) {
  const [content, setContent] = useState("");

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = content.trim();
    if (!trimmed) {
      return;
    }

    onSendText(trimmed);
    setContent("");
  }

  return (
    <form className="coach-composer" onSubmit={handleSubmit}>
      <input
        value={content}
        onChange={(event) => setContent(event.target.value)}
        placeholder="생각을 짧게 적어보기"
        disabled={disabled}
      />
      <button type="submit" disabled={disabled || content.trim().length === 0}>
        보내기
      </button>
    </form>
  );
}
