/**
 * /api/feedback - 玩家反馈
 *
 * 🆕 v1.7.30: 对齐后端字段（category, description, session_id, context）
 */
import { call } from './client';

export type FeedbackCategory = 'bug' | 'idea' | 'praise' | 'question' | 'other';

export interface FeedbackRequest {
  session_id?: string;
  category: FeedbackCategory;
  description: string;
  context?: Record<string, any>;
  contact?: string;
}

export interface FeedbackResponse {
  feedback_id: string;
  received_at: string;
}

export async function submitFeedback(req: FeedbackRequest): Promise<FeedbackResponse> {
  return call<FeedbackResponse>('/feedback', { body: req });
}
