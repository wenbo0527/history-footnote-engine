/**
 * 🆕 v2.9.x W39: SSE 客户端 + 事件类型
 *
 * 后端 /api/input_stream 返回 text/event-stream，包含 5 类事件：
 * - thinking: {"message": "DM 思考中..."}        — LLM 思考阶段
 * - token:    {"delta": "今晚"}                    — LLM 文本流
 * - metadata: {"state_changes": {...}, ...}        — 状态变更（最终）
 * - options:  {"voices": [...]}                    — 命运卡选项
 * - done:     {"ok": true}                          — 完成
 * - error:    {"message": "..."}                   — 错误
 */

export interface StreamingCallbacks {
  onThinking?: (msg: string) => void;
  onToken?: (delta: string) => void;
  onMetadata?: (state: any) => void;
  onOptions?: (voices: any[]) => void;
  onDone?: () => void;
  onError?: (err: string) => void;
}

export interface StreamInputRequest {
  session_id: string;
  text?: string;
  voice_id?: string;
  voice_name?: string;
  intent_text?: string;
}

/**
 * 解析 SSE 事件流（一行 = "event: type\ndata: {...}\n\n"）
 * 一次 fetch 拿到整段 stream，逐块 parse
 */
export async function streamInput(
  req: StreamInputRequest,
  callbacks: StreamingCallbacks,
  signal?: AbortSignal
): Promise<void> {
  const body: Record<string, any> = {
    session_id: req.session_id,
    voice_id: req.voice_id,
    voice_name: req.voice_name,
  };
  // 🆕 W39: 优先用 intent_text（语义化行动），fallback text
  const input = req.intent_text || req.text || '';
  if (input) body.input = input;

  let res: Response;
  try {
    res = await fetch('/api/input_stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal,
    });
  } catch (e: any) {
    // fetch 失败（网络/DNS/CORS 等）— 不让异常逃出
    callbacks.onError?.(e?.message || String(e));
    return;
  }

  if (!res.ok) {
    let errMsg = `HTTP ${res.status}`;
    try {
      const data = await res.json();
      errMsg = data.error || data.message || errMsg;
    } catch {}
    callbacks.onError?.(errMsg);
    return;
  }

  if (!res.body) {
    callbacks.onError?.('No response body (stream)');
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder('utf-8');
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      // SSE 事件以 \n\n 分割
      const events = buffer.split('\n\n');
      buffer = events.pop() || ''; // 最后一段可能不完整，保留

      for (const event of events) {
        if (!event.trim()) continue;
        const eventName = extractField(event, 'event') || 'message';
        const dataStr = extractField(event, 'data');
        if (!dataStr) continue;
        let data: any = dataStr;
        try {
          data = JSON.parse(dataStr);
        } catch {
          // 非 JSON 数据，原样传递
        }
        dispatchEvent(eventName, data, callbacks);
      }
    }
  } catch (e: any) {
    if (e.name === 'AbortError') {
      callbacks.onError?.('aborted');
    } else {
      callbacks.onError?.(e?.message || String(e));
    }
  }
}

function extractField(event: string, field: string): string | null {
  const lines = event.split('\n');
  for (const line of lines) {
    if (line.startsWith(`${field}:`)) {
      return line.slice(field.length + 1).trim();
    }
  }
  return null;
}

function dispatchEvent(
  eventName: string,
  data: any,
  cb: StreamingCallbacks
): void {
  switch (eventName) {
    case 'thinking':
      cb.onThinking?.(data.message || '思考中...');
      break;
    case 'token':
      cb.onToken?.(data.delta || '');
      break;
    case 'metadata':
      cb.onMetadata?.(data);
      break;
    case 'options':
      cb.onOptions?.(data.voices || []);
      break;
    case 'done':
      cb.onDone?.();
      break;
    case 'error':
      cb.onError?.(data.message || 'unknown error');
      break;
    default:
      // 未知事件忽略
      break;
  }
}

// 🆕 W39: 导出供测试用
export { extractField, dispatchEvent };
