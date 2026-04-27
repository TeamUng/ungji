import type { ImageCardMessage as ImageCardMessageType } from "@/types/chat";

type ImageCardMessageProps = {
  message: ImageCardMessageType;
};

export function ImageCardMessage({ message }: ImageCardMessageProps) {
  return (
    <figure className="image-card-message">
      <img src={message.image_url} alt={message.caption} />
      <figcaption>{message.caption}</figcaption>
    </figure>
  );
}
