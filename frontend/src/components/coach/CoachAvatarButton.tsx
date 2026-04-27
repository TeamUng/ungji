type CoachAvatarButtonProps = {
  onClick?: () => void;
};

export function CoachAvatarButton({ onClick }: CoachAvatarButtonProps) {
  return (
    <button className="coach-face" type="button" aria-label="AI 코치 열기" onClick={onClick}>
      <img src="/assets/coach-avatar.svg" alt="" aria-hidden="true" />
    </button>
  );
}
