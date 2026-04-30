import styles from "./SmartAllHome.module.css";

type IconMockProps = {
  kind:
    | "back"
    | "search"
    | "star"
    | "message"
    | "menu"
    | "check"
    | "book"
    | "attendance"
    | "record"
    | "wrong";
  label?: string;
};

export function IconMock({ kind, label }: IconMockProps) {
  return (
    <span
      className={`${styles.iconMock} ${styles[`icon${toPascalCase(kind)}`]}`}
      aria-label={label}
      aria-hidden={label ? undefined : true}
    />
  );
}

function toPascalCase(value: string) {
  return value
    .split("-")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join("");
}
