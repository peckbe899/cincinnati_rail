// An incremental text/event-stream parser (the WHATWG "interpret an event stream" rules): fields id, event, data
// and retry; comment lines start with a colon; a blank line dispatches. Feed it decoded text in any chunking.

export interface SseMessage {
  /** The id of this message, or the last id seen (as EventSource keeps it); null when none was ever sent. */
  id: string | null;
  event: string;
  data: string;
}

export class SseParser {
  private buf = "";
  private data: string[] = [];
  private event = "";
  private lastId: string | null = null;
  private sawField = false;
  /** The latest retry: value in milliseconds, if the server sent one. */
  retry: number | null = null;

  push(chunk: string): SseMessage[] {
    this.buf += chunk;
    const out: SseMessage[] = [];
    for (;;) {
      const m = /\r\n|\r|\n/.exec(this.buf);
      if (!m) break;
      // A lone \r at the end of the buffer may be the first half of \r\n: wait for more.
      if (m[0] === "\r" && m.index === this.buf.length - 1) break;
      const line = this.buf.slice(0, m.index);
      this.buf = this.buf.slice(m.index + m[0].length);
      const msg = this.line(line);
      if (msg) out.push(msg);
    }
    return out;
  }

  /** Flush at end of stream: an unterminated message is dropped, as the spec says. */
  end(): void {
    this.buf = "";
    this.data = [];
    this.event = "";
    this.sawField = false;
  }

  private line(line: string): SseMessage | null {
    if (line === "") {
      if (!this.sawField) return null;
      const msg = this.data.length
        ? { id: this.lastId, event: this.event || "message", data: this.data.join("\n") }
        : null;
      this.data = [];
      this.event = "";
      this.sawField = false;
      return msg;
    }
    if (line.startsWith(":")) return null;
    const colon = line.indexOf(":");
    const field = colon < 0 ? line : line.slice(0, colon);
    let value = colon < 0 ? "" : line.slice(colon + 1);
    if (value.startsWith(" ")) value = value.slice(1);
    this.sawField = true;
    switch (field) {
      case "data":
        this.data.push(value);
        break;
      case "event":
        this.event = value;
        break;
      case "id":
        if (!value.includes("\0")) this.lastId = value;
        break;
      case "retry":
        if (/^\d+$/.test(value)) this.retry = Number(value);
        break;
      default:
        break;
    }
    return null;
  }
}
