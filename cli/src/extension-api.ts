/** Official extension contract. No terminal stream or session credential is exposed. */
export const EXTENSION_API = 4;
export interface ExtensionKey { name?: string; ctrl?: boolean; meta?: boolean; shift?: boolean; value?: string; /** Raw input, e.g. `\n` for an LF Enter. */ sequence?: string }
export type ExtensionMouseButton = 'left' | 'middle' | 'right' | 'wheel-up' | 'wheel-down' | 'none';
/** Frame coordinates: 0-based column inside the frame, 0-based frame row. */
export interface ExtensionMouse { x: number; y: number; button: ExtensionMouseButton; action: 'press' | 'release' | 'move' }
/** focusColumn points to content; the host draws a marker in the preceding blank cell. */
export interface ExtensionRow {
  text: string;
  focusColumn?: number;
  /** Native terminal caret for active text input, in 0-based display cells. */
  cursorColumn?: number;
  /** Use the host Chat input rule across the terminal width; value is its context label. */
  inputRule?: string;
  /** Draw Chat's prompt in the existing left inset, without indenting content. */
  inputPrompt?: boolean;
  tone?: 'text' | 'title' | 'muted' | 'selected' | 'error';
}
export interface ExtensionScreen {
  render(columns: number, rows: number): ExtensionRow[];
  key(key: ExtensionKey): void;
  /** Bracketed paste is data, never a sequence of game shortcuts. */
  paste?(text: string): void;
  /** Optional: the frame is line based, so a screen decides what its own rows mean. */
  mouse?(event: ExtensionMouse): void;
  /**
   * Optional: return a header to keep the host's fixed header above the frame, or
   * nothing for a fullscreen frame. `render` then gets the rows below the header.
   * `logo` is three rows of at most 16 cells; only SGR colours pass through.
   */
  header?(): ExtensionHeader | undefined;
}
export interface ExtensionHeader { logo?: string[]; title: string; version?: string; subtitle?: string }
export interface ExtensionContext {
  user: { id: string; name: string };
  /** The channel the user came from, if any. Games are not bound to it. */
  channel?: { id: string; name: string };
  signal: AbortSignal;
  request(path: string, method?: 'GET' | 'POST', body?: unknown): Promise<unknown>;
  /** Optional support for explicit delegation reconnects after a replaced control lease. */
  supportsControlHandoff?: boolean;
  connect(path: string, event: (value: unknown) => void, status: (connected: boolean) => void, options?: { onReplaced(): boolean }): { close(): void; reconnect(): void; send(value: unknown): boolean };
  recordTiming?(sample: { actionId: string; totalMs: number; serverMs?: number; outcome: string }): void;
  openScreen(screen: ExtensionScreen): Promise<void>;
  redraw(): void;
  wrap(text: string, width: number): string[];
  closeScreen(): void;
  /** Close the game and return to channel selection when supported by the host. */
  openChannels?(): void;
}
export interface ExtensionModule { run(context: ExtensionContext): Promise<void> }
