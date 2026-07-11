/**
 * 🆕 v2.9.x W39: 流式叙事 hook (SvelteKit runes)
 *
 * 用法：
 *   const stream = useStreamingNarrative();
 *   await stream.start({ session_id, text }, {
 *     onToken: (delta) => liveNarrative += delta,
 *   });
 */
import { streamInput, type StreamInputRequest, type StreamingCallbacks } from '$lib/api/streaming';

export interface StreamingState {
  thinking: boolean;
  narrative: string;       // 流式累积的 narrative
  metadata: any;          // 状态变更
  voices: any[];          // 命运卡
  done: boolean;
  error: string | null;
}

export function useStreamingNarrative() {
  let thinking = $state(false);
  let narrative = $state('');
  let metadata = $state<any>(null);
  let voices = $state<any[]>([]);
  let done = $state(false);
  let error = $state<string | null>(null);
  let controller: AbortController | null = null;

  function reset() {
    thinking = false;
    narrative = '';
    metadata = null;
    voices = [];
    done = false;
    error = null;
  }

  async function start(
    req: StreamInputRequest,
    extra?: Partial<StreamingCallbacks>
  ): Promise<void> {
    reset();
    thinking = true;
    controller = new AbortController();

    await streamInput(
      req,
      {
        onThinking: (msg) => {
          thinking = true;
          extra?.onThinking?.(msg);
        },
        onToken: (delta) => {
          thinking = false;
          narrative += delta;
          extra?.onToken?.(delta);
        },
        onMetadata: (state) => {
          metadata = state;
          extra?.onMetadata?.(state);
        },
        onOptions: (vs) => {
          voices = vs;
          extra?.onOptions?.(vs);
        },
        onDone: () => {
          thinking = false;
          done = true;
          extra?.onDone?.();
        },
        onError: (err) => {
          thinking = false;
          error = err;
          done = true;
          extra?.onError?.(err);
        },
      },
      controller.signal
    );
  }

  function abort() {
    controller?.abort();
    controller = null;
  }

  return {
    get thinking() { return thinking; },
    get narrative() { return narrative; },
    get metadata() { return metadata; },
    get voices() { return voices; },
    get done() { return done; },
    get error() { return error; },
    start,
    abort,
    reset,
  };
}
