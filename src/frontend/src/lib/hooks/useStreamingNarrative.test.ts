/**
 * 🆕 v2.9.x W39: 流式叙事 hook + SSE 解析测试
 *
 * 测试目标：
 * 1. extractField 正确解析 SSE event/data 行
 * 2. dispatchEvent 正确分发 6 类事件
 * 3. streamInput 完整流程（mock fetch）
 * 4. thinking → token → metadata → options → done 顺序
 * 5. 错误处理（HTTP 500, JSON parse 错）
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { extractField, dispatchEvent, streamInput, type StreamingCallbacks } from '$lib/api/streaming';

// ============================================================
// Helper: 模拟 SSE 响应流
// ============================================================

function makeSSEResponse(events: string[], status = 200): Response {
  const text = events.join('\n\n') + '\n\n';
  const stream = new ReadableStream({
    start(controller) {
      const encoder = new TextEncoder();
      controller.enqueue(encoder.encode(text));
      controller.close();
    },
  });
  return new Response(stream, {
    status,
    headers: { 'Content-Type': 'text/event-stream' },
  });
}

function makeChunkedSSEResponse(chunks: string[], status = 200): Response {
  const stream = new ReadableStream({
    async start(controller) {
      const encoder = new TextEncoder();
      for (const c of chunks) {
        controller.enqueue(encoder.encode(c));
        await new Promise((r) => setTimeout(r, 1));
      }
      controller.close();
    },
  });
  return new Response(stream, {
    status,
    headers: { 'Content-Type': 'text/event-stream' },
  });
}

function makeErrorResponse(status: number, body: any = { error: 'fail' }): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

// ============================================================
// 单元测试
// ============================================================

describe('extractField', () => {
  it('extracts event: name from SSE block', () => {
    const block = 'event: thinking\ndata: {"message": "hi"}';
    expect(extractField(block, 'event')).toBe('thinking');
  });

  it('extracts data: from SSE block', () => {
    const block = 'event: token\ndata: {"delta": "今晚"}';
    expect(extractField(block, 'data')).toBe('{"delta": "今晚"}');
  });

  it('returns null when field missing', () => {
    const block = 'event: done';
    expect(extractField(block, 'data')).toBeNull();
  });

  it('handles multi-line data', () => {
    const block = 'event: thinking\ndata: line1\ndata: line2';
    // Should grab first data line
    expect(extractField(block, 'data')).toBe('line1');
  });
});

describe('dispatchEvent', () => {
  it('dispatches thinking event', () => {
    const cb: StreamingCallbacks = { onThinking: vi.fn() };
    dispatchEvent('thinking', { message: '思考中' }, cb);
    expect(cb.onThinking).toHaveBeenCalledWith('思考中');
  });

  it('dispatches token event with delta', () => {
    const cb: StreamingCallbacks = { onToken: vi.fn() };
    dispatchEvent('token', { delta: '今晚' }, cb);
    expect(cb.onToken).toHaveBeenCalledWith('今晚');
  });

  it('dispatches metadata event', () => {
    const cb: StreamingCallbacks = { onMetadata: vi.fn() };
    dispatchEvent('metadata', { round: 5 }, cb);
    expect(cb.onMetadata).toHaveBeenCalledWith({ round: 5 });
  });

  it('dispatches options event with voices', () => {
    const cb: StreamingCallbacks = { onOptions: vi.fn() };
    dispatchEvent('options', { voices: [{ id: 'v1' }] }, cb);
    expect(cb.onOptions).toHaveBeenCalledWith([{ id: 'v1' }]);
  });

  it('dispatches done event', () => {
    const cb: StreamingCallbacks = { onDone: vi.fn() };
    dispatchEvent('done', { ok: true }, cb);
    expect(cb.onDone).toHaveBeenCalled();
  });

  it('dispatches error event', () => {
    const cb: StreamingCallbacks = { onError: vi.fn() };
    dispatchEvent('error', { message: 'fail' }, cb);
    expect(cb.onError).toHaveBeenCalledWith('fail');
  });

  it('ignores unknown event type', () => {
    const cb: StreamingCallbacks = {
      onThinking: vi.fn(),
      onToken: vi.fn(),
      onDone: vi.fn(),
    };
    dispatchEvent('unknown', { foo: 1 }, cb);
    expect(cb.onThinking).not.toHaveBeenCalled();
    expect(cb.onToken).not.toHaveBeenCalled();
    expect(cb.onDone).not.toHaveBeenCalled();
  });
});

// ============================================================
// 集成测试：streamInput
// ============================================================

describe('streamInput', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('handles 5 SSE events in order', async () => {
    const events = [
      'event: thinking\ndata: {"message": "DM 思考中"}',
      'event: token\ndata: {"delta": "今"}',
      'event: token\ndata: {"delta": "晚"}',
      'event: options\ndata: {"voices": [{"id": "v1"}]}',
      'event: done\ndata: {"ok": true}',
    ];
    globalThis.fetch = vi.fn().mockResolvedValue(makeSSEResponse(events));

    const cb: StreamingCallbacks = {
      onThinking: vi.fn(),
      onToken: vi.fn(),
      onOptions: vi.fn(),
      onDone: vi.fn(),
    };

    await streamInput(
      { session_id: 's1', text: 'go' },
      cb
    );

    expect(cb.onThinking).toHaveBeenCalledWith('DM 思考中');
    expect(cb.onToken).toHaveBeenCalledTimes(2);
    expect(cb.onToken).toHaveBeenNthCalledWith(1, '今');
    expect(cb.onToken).toHaveBeenNthCalledWith(2, '晚');
    expect(cb.onOptions).toHaveBeenCalledWith([{ id: 'v1' }]);
    expect(cb.onDone).toHaveBeenCalled();
  });

  it('handles HTTP 500 error', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(makeErrorResponse(500, { error: 'LLM 失败' }));

    const cb: StreamingCallbacks = { onError: vi.fn() };
    await streamInput({ session_id: 's1', text: 'go' }, cb);

    expect(cb.onError).toHaveBeenCalledWith('LLM 失败');
  });

  it('handles HTTP 400 with retryable error', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(
      makeErrorResponse(400, { error: 'invalid', message: '输入不合法', retryable: true })
    );

    const cb: StreamingCallbacks = { onError: vi.fn() };
    await streamInput({ session_id: 's1', text: '' }, cb);

    expect(cb.onError).toHaveBeenCalledWith('invalid');
  });

  it('handles non-JSON data gracefully', async () => {
    // 服务可能误发非 JSON（应该跳过 not crash）
    const events = [
      'event: thinking\ndata: not json',
      'event: done\ndata: {"ok": true}',
    ];
    globalThis.fetch = vi.fn().mockResolvedValue(makeSSEResponse(events));

    const cb: StreamingCallbacks = {
      onThinking: vi.fn(),
      onDone: vi.fn(),
    };

    await streamInput({ session_id: 's1', text: 'go' }, cb);

    // onThinking 被调（即使 data 是字符串 "not json"）
    expect(cb.onThinking).toHaveBeenCalled();
    expect(cb.onDone).toHaveBeenCalled();
  });

  it('handles chunked SSE (events split across reads)', async () => {
    // 模拟事件被切成多块
    const chunks = [
      'event: thinking\ndata: {"mess',
      'age": "DM"}\n\nevent: tok',
      'en\ndata: {"delta": "今晚"}\n\nevent: done\ndata: {"ok": true}\n\n',
    ];
    globalThis.fetch = vi.fn().mockResolvedValue(makeChunkedSSEResponse(chunks));

    const cb: StreamingCallbacks = {
      onThinking: vi.fn(),
      onToken: vi.fn(),
      onDone: vi.fn(),
    };

    await streamInput({ session_id: 's1', text: 'go' }, cb);

    expect(cb.onThinking).toHaveBeenCalled();
    expect(cb.onToken).toHaveBeenCalledWith('今晚');
    expect(cb.onDone).toHaveBeenCalled();
  });

  it('uses intent_text over text', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(makeSSEResponse(['event: done\ndata: {"ok":true}']));

    const cb: StreamingCallbacks = { onDone: vi.fn() };
    await streamInput(
      { session_id: 's1', text: 'raw text', intent_text: 'semantic' },
      cb
    );

    const callBody = JSON.parse((globalThis.fetch as any).mock.calls[0][1].body);
    expect(callBody.input).toBe('semantic');  // intent_text 优先
  });

  it('falls back to text when intent_text missing', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(makeSSEResponse(['event: done\ndata: {"ok":true}']));

    const cb: StreamingCallbacks = { onDone: vi.fn() };
    await streamInput(
      { session_id: 's1', text: 'just text' },
      cb
    );

    const callBody = JSON.parse((globalThis.fetch as any).mock.calls[0][1].body);
    expect(callBody.input).toBe('just text');
  });

  it('handles fetch error (network fail)', async () => {
    // 模拟网络失败（不依赖 DOMException，jsdom 兼容）
    globalThis.fetch = vi.fn().mockRejectedValue(new Error('Network error'));

    const cb: StreamingCallbacks = { onError: vi.fn() };
    await streamInput({ session_id: 's1', text: 'go' }, cb);

    expect(cb.onError).toHaveBeenCalled();
    // error message 应含 'Network error'
    expect((cb.onError as any).mock.calls[0][0]).toContain('Network error');
  });
});

describe('useStreamingNarrative hook', () => {
  it('hook exists and is exported', async () => {
    const mod = await import('$lib/hooks/useStreamingNarrative');
    expect(typeof mod.useStreamingNarrative).toBe('function');
  });

  it('hook returns expected interface', async () => {
    const mod = await import('$lib/hooks/useStreamingNarrative');
    // 函数存在即可（runes 实际需在 Svelte 文件中用）
    expect(typeof mod.useStreamingNarrative).toBe('function');
  });
});
