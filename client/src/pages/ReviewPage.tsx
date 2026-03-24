import { useState } from 'react';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { useApi } from '../hooks/useApi';
import { post } from '../api/client';
import type { InvestmentPolicy, ReviewEntry, JournalEntry } from '../types';

const REVIEW_CHECKLIST = [
  'Did my life goals change?',
  'Did my spending needs change?',
  'Did my risk capacity change?',
  'Did my job / human capital risk change?',
  'Did my target portfolio change for a durable reason?',
  'Is tax strategy still appropriate?',
  'Is safe asset runway still sufficient?',
];

const REASON_CATEGORIES = [
  'goal_change', 'spending_change', 'tax_change', 'liquidity_need',
  'anxiety', 'reacting_to_news', 'conviction_change', 'other',
];

export function ReviewPage() {
  const { data: policy } = useApi<InvestmentPolicy>('/policy');
  const { data: reviews, refetch: refetchReviews } = useApi<ReviewEntry[]>('/reviews');
  const { data: journal, refetch: refetchJournal } = useApi<JournalEntry[]>('/journal');

  const [showReviewForm, setShowReviewForm] = useState(false);
  const [reviewForm, setReviewForm] = useState({ summary: '', life_change_flag: false, allocation_changed_flag: false, notes: '' });

  const [showJournalForm, setShowJournalForm] = useState(false);
  const [journalForm, setJournalForm] = useState({
    action_type: '', reason_category: 'other', explanation: '',
    confidence_score: 3, follow_up_date: '',
  });

  if (!policy || !reviews || !journal) {
    return <p className="text-calm-muted text-sm">Loading...</p>;
  }

  const today = new Date().toISOString().split('T')[0];
  const reviewOverdue = policy.next_review_date && policy.next_review_date <= today;

  const saveReview = async () => {
    await post('/reviews', reviewForm);
    setShowReviewForm(false);
    setReviewForm({ summary: '', life_change_flag: false, allocation_changed_flag: false, notes: '' });
    refetchReviews();
  };

  const saveJournal = async () => {
    await post('/journal', {
      ...journalForm,
      follow_up_date: journalForm.follow_up_date || null,
    });
    setShowJournalForm(false);
    setJournalForm({ action_type: '', reason_category: 'other', explanation: '', confidence_score: 3, follow_up_date: '' });
    refetchJournal();
  };

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-semibold tracking-tight">Review</h2>

      {/* Schedule */}
      <Card>
        <h3 className="text-sm font-medium text-calm-muted uppercase tracking-wide mb-3">Review Schedule</h3>
        <div className="grid grid-cols-3 gap-4 text-sm">
          <div>
            <span className="text-calm-muted">Next review:</span>
            <span className="ml-2 font-medium">{policy.next_review_date || 'Not set'}</span>
            {reviewOverdue && <Badge status="action" >Overdue</Badge>}
          </div>
          <div>
            <span className="text-calm-muted">Last review:</span>
            <span className="ml-2 font-medium">{policy.last_review_date || 'Never'}</span>
          </div>
          <div>
            <span className="text-calm-muted">Cadence:</span>
            <span className="ml-2 font-medium capitalize">{policy.review_cadence}</span>
          </div>
        </div>
      </Card>

      {/* Checklist */}
      <Card>
        <h3 className="text-sm font-medium text-calm-muted uppercase tracking-wide mb-3">Review Checklist</h3>
        <ul className="space-y-2">
          {REVIEW_CHECKLIST.map((item, i) => (
            <li key={i} className="flex items-center gap-2 text-sm">
              <input type="checkbox" className="rounded" />
              {item}
            </li>
          ))}
        </ul>
        <div className="mt-4">
          <Button variant="secondary" onClick={() => setShowReviewForm(true)}>Complete Review</Button>
        </div>
      </Card>

      {/* Review form */}
      {showReviewForm && (
        <Card>
          <h3 className="text-sm font-medium text-calm-muted uppercase tracking-wide mb-3">Log Review</h3>
          <div className="space-y-3">
            <textarea
              placeholder="Summary of review..."
              value={reviewForm.summary}
              onChange={(e) => setReviewForm({ ...reviewForm, summary: e.target.value })}
              className="w-full p-3 text-sm border border-calm-border rounded bg-calm-surface min-h-[80px]"
            />
            <div className="flex gap-4">
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={reviewForm.life_change_flag}
                  onChange={(e) => setReviewForm({ ...reviewForm, life_change_flag: e.target.checked })} />
                Life change
              </label>
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={reviewForm.allocation_changed_flag}
                  onChange={(e) => setReviewForm({ ...reviewForm, allocation_changed_flag: e.target.checked })} />
                Allocation changed
              </label>
            </div>
            <textarea
              placeholder="Notes (optional)"
              value={reviewForm.notes}
              onChange={(e) => setReviewForm({ ...reviewForm, notes: e.target.value })}
              className="w-full p-3 text-sm border border-calm-border rounded bg-calm-surface min-h-[60px]"
            />
            <div className="flex gap-2">
              <Button onClick={saveReview}>Save Review</Button>
              <Button variant="ghost" onClick={() => setShowReviewForm(false)}>Cancel</Button>
            </div>
          </div>
        </Card>
      )}

      {/* Review log */}
      {reviews.length > 0 && (
        <Card>
          <h3 className="text-sm font-medium text-calm-muted uppercase tracking-wide mb-3">Review History</h3>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-calm-border text-left text-xs text-calm-muted uppercase tracking-wide">
                <th className="pb-2 pr-4">Date</th>
                <th className="pb-2 pr-4">Summary</th>
                <th className="pb-2">Flags</th>
              </tr>
            </thead>
            <tbody>
              {reviews.map((r) => (
                <tr key={r.id} className="border-b border-calm-border/50">
                  <td className="py-2 pr-4">{r.review_date}</td>
                  <td className="py-2 pr-4 text-calm-muted">{r.summary}</td>
                  <td className="py-2 space-x-2">
                    {r.life_change_flag && <Badge status="watch">Life change</Badge>}
                    {r.allocation_changed_flag && <Badge status="action">Allocation changed</Badge>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}

      {/* Decision journal */}
      <Card>
        <div className="flex justify-between items-center mb-3">
          <h3 className="text-sm font-medium text-calm-muted uppercase tracking-wide">Decision Journal</h3>
          <Button variant="secondary" onClick={() => setShowJournalForm(true)}>Add Entry</Button>
        </div>

        {showJournalForm && (
          <div className="mb-4 p-4 bg-calm-bg rounded-lg space-y-3">
            <input placeholder="Action taken" value={journalForm.action_type}
              onChange={(e) => setJournalForm({ ...journalForm, action_type: e.target.value })}
              className="w-full px-3 py-1.5 text-sm border border-calm-border rounded bg-calm-surface" />
            <div className="grid grid-cols-2 gap-3">
              <select value={journalForm.reason_category}
                onChange={(e) => setJournalForm({ ...journalForm, reason_category: e.target.value })}
                className="px-3 py-1.5 text-sm border border-calm-border rounded bg-calm-surface">
                {REASON_CATEGORIES.map((c) => (
                  <option key={c} value={c}>{c.replace('_', ' ')}</option>
                ))}
              </select>
              <div className="flex items-center gap-2">
                <label className="text-xs text-calm-muted">Confidence:</label>
                <input type="range" min={1} max={5} value={journalForm.confidence_score}
                  onChange={(e) => setJournalForm({ ...journalForm, confidence_score: Number(e.target.value) })} />
                <span className="text-sm font-medium">{journalForm.confidence_score}/5</span>
              </div>
            </div>
            <textarea placeholder="Explanation..." value={journalForm.explanation}
              onChange={(e) => setJournalForm({ ...journalForm, explanation: e.target.value })}
              className="w-full p-3 text-sm border border-calm-border rounded bg-calm-surface min-h-[60px]" />
            <div className="flex gap-2">
              <Button onClick={saveJournal}>Save</Button>
              <Button variant="ghost" onClick={() => setShowJournalForm(false)}>Cancel</Button>
            </div>
          </div>
        )}

        {journal.length > 0 ? (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-calm-border text-left text-xs text-calm-muted uppercase tracking-wide">
                <th className="pb-2 pr-4">Date</th>
                <th className="pb-2 pr-4">Action</th>
                <th className="pb-2 pr-4">Reason</th>
                <th className="pb-2">Confidence</th>
              </tr>
            </thead>
            <tbody>
              {journal.map((j) => (
                <tr key={j.id} className="border-b border-calm-border/50">
                  <td className="py-2 pr-4">{j.entry_date}</td>
                  <td className="py-2 pr-4">{j.action_type}</td>
                  <td className="py-2 pr-4 text-calm-muted">{j.reason_category.replace('_', ' ')}</td>
                  <td className="py-2">{j.confidence_score}/5</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="text-sm text-calm-muted">No journal entries yet.</p>
        )}
      </Card>
    </div>
  );
}
