import type { ReactNode, SVGProps } from "react";

export type IconeNome =
  | "home"
  | "briefcase"
  | "chart"
  | "dollar"
  | "handshake"
  | "landmark"
  | "transfer"
  | "wallet"
  | "scale"
  | "target"
  | "telescope"
  | "bitcoin"
  | "search"
  | "receipt"
  | "calculator"
  | "folder"
  | "file"
  | "settings"
  | "panelOpen"
  | "panelClose"
  | "chevronDown"
  | "info";

const desenhos: Record<IconeNome, ReactNode> = {
  home: <><path d="m3 10 9-7 9 7" /><path d="M5 9v11h14V9M9 20v-6h6v6" /></>,
  briefcase: <><rect x="3" y="7" width="18" height="13" rx="2" /><path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M3 12h18M10 12v2h4v-2" /></>,
  chart: <><path d="M3 3v18h18" /><path d="m7 14 4-4 4 3 6-7" /></>,
  dollar: <><circle cx="12" cy="12" r="9" /><path d="M16 8.5c-.7-.8-1.8-1.2-3.2-1.2-1.7 0-2.8.8-2.8 2s1 1.8 3 2.2 3 1 3 2.3-1.2 2.2-3 2.2c-1.5 0-2.8-.5-3.7-1.5M12 5v14" /></>,
  handshake: <><path d="m3 12 4-4 4 1 2-1 4 1 4 3-5 5-3-1-2 1-4-2-2-2-2-1Z" /><path d="m7 8 3-3 4 1 3-1 4 4M8 14l3 2m1-3 3 2m1-4 3 2" /></>,
  landmark: <><path d="m3 9 9-6 9 6M4 10h16M5 10v9m4-9v9m6-9v9m4-9v9M3 21h18" /></>,
  transfer: <><path d="M4 7h15l-4-4m5 14H5l4 4" /></>,
  wallet: <><path d="M4 6.5A2.5 2.5 0 0 1 6.5 4H20v16H6.5A2.5 2.5 0 0 1 4 17.5zM4 7h16" /><path d="M20 11h-5a2 2 0 0 0 0 4h5m-5-2h.01" /></>,
  scale: <><path d="M12 3v18M5 7h14M7 7l-4 7h8L7 7Zm10 0-4 7h8l-4-7ZM5 21h14" /></>,
  target: <><circle cx="12" cy="12" r="9" /><circle cx="12" cy="12" r="5" /><circle cx="12" cy="12" r="1" /></>,
  telescope: <><path d="m4 8 11-4 3 7-11 4zM15 5l2-2 4 9-3 1M9 15l-2 6m5-7 3 7m-9-5 6-2" /></>,
  bitcoin: <><path d="M8 4h5a3 3 0 0 1 0 6H8zm0 6h6a3.5 3.5 0 0 1 0 7H8zM10 2v20m4-20v2m0 16v2" /></>,
  search: <><circle cx="10.8" cy="10.8" r="7" /><path d="m16 16 5 5" /></>,
  receipt: <><path d="M5 3h14v18l-3-2-4 2-4-2-3 2zM8 8h8m-8 4h8m-8 4h5" /></>,
  calculator: <><rect x="4" y="3" width="16" height="18" rx="2" /><path d="M8 7h8v3H8zm1 7h.01M15 14h.01M9 18h.01M15 18h.01" /></>,
  folder: <><path d="M3 6a2 2 0 0 1 2-2h5l2 2h7a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" /><path d="M3 9h18" /></>,
  file: <><path d="M6 3h8l4 4v14H6z" /><path d="M14 3v5h5m-10 4h6m-6 4h6" /></>,
  settings: <><circle cx="12" cy="12" r="3" /><path d="m19.4 15 .1.1 1.4 1.1-1.4 2.4-1.7-.7a8 8 0 0 1-1.6.9l-.3 1.8h-2.8l-.3-1.8a8 8 0 0 1-1.6-.9l-1.7.7-1.4-2.4L7.5 15a8 8 0 0 1 0-1.9L6.1 12l1.4-2.4 1.7.7a8 8 0 0 1 1.6-.9l.3-1.8h2.8l.3 1.8a8 8 0 0 1 1.6.9l1.7-.7 1.4 2.4-1.4 1.1a8 8 0 0 1-.1 1.9Z" /></>,
  panelOpen: <><rect x="3" y="4" width="18" height="16" rx="2" /><path d="M9 4v16m5-11 3 3-3 3" /></>,
  panelClose: <><rect x="3" y="4" width="18" height="16" rx="2" /><path d="M9 4v16m7-11-3 3 3 3" /></>,
  chevronDown: <path d="m6 9 6 6 6-6" />,
  info: <><circle cx="12" cy="12" r="9" /><path d="M12 11v5m0-8h.01" /></>,
};

interface IconeProps extends SVGProps<SVGSVGElement> {
  nome: IconeNome;
  size?: number;
}

export function Icone({ nome, size = 18, ...props }: IconeProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
      focusable="false"
      {...props}
    >
      {desenhos[nome]}
    </svg>
  );
}
