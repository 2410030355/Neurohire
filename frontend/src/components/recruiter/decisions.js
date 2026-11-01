import { jsonFetch } from '@/api/http';

/** The id a candidate is stored under (MongoDB, ranking result, or search result). */
export function candidateId(candidate) {
  return candidate?.mongo_id || candidate?.candidate_id || candidate?.id || null;
}

/** AI recommendation implied by the final-fit band. */
export function aiRecommendation(candidate) {
  const fit = candidate?.final_fit || 'Low';
  return fit === 'High' ? 'hire' : fit === 'Medium' ? 'waitlist' : 'reject';
}

/**
 * Log a recruiter decision (hire / waitlist / reject).
 * The backend looks up SS and AS (from the ranking run or the stored
 * candidate) and applies the feedback rule (paper §IV.H). Scores sent here
 * are only a fallback for candidates that are not stored (e.g. search results).
 * Returns the saved log (with weight_update) or null on failure.
 */
export async function logDecision(candidate, recruiterDecision, rankingId = null) {
  try {
    return await jsonFetch('/api/ai-decision-logs/', {
      method: 'POST',
      body: JSON.stringify({
        candidate: candidateId(candidate),
        ranking_id: rankingId || candidate?.ranking_id || null,
        candidate_name: candidate?.name || 'Unknown',
        ai_recommendation: aiRecommendation(candidate),
        recruiter_decision: recruiterDecision,
        semantic_score: candidate?.semantic_score ?? candidate?.role_match_score ?? null,
        analytical_score: candidate?.analytical_score ?? null,
        final_score: candidate?.final_score ?? null,
        role_match_score: candidate?.role_match_score ?? null,
        consistency_score: candidate?.consistency_score ?? null,
      }),
    });
  } catch (err) {
    console.warn('Decision log failed:', err);
    return null;
  }
}

/** Text for a project that may be a string (old data) or an object (Gemini). */
export function projectText(p) {
  if (!p) return '';
  if (typeof p === 'string') return p;
  const tech = Array.isArray(p.technologies) && p.technologies.length ? ` (${p.technologies.join(', ')})` : '';
  return `${p.name || 'Project'}${tech}${p.description ? ` — ${p.description}` : ''}`;
}

export const fmt = (v) => (v === null || v === undefined ? 'N/A' : Math.round(Number(v)));
