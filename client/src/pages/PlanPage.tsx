import { useEffect, useState } from 'react';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { useApi } from '../hooks/useApi';
import { put, post, del } from '../api/client';
import type { InvestmentPolicy, PortfolioSleeve } from '../types';

const EMPTY_SLEEVE_FORM = {
  ticker: '', label: '', target_percent: 0, asset_class: 'equity',
  geography: '', is_safe_asset: false, is_cash_like: false,
  region_us_pct: 0, region_developed_pct: 0, region_emerging_pct: 0,
  factor_value: '', factor_size: '',
};

export function PlanPage() {
  const { data: policy, refetch: refetchPolicy } = useApi<InvestmentPolicy>('/policy');
  const { data: sleeves, refetch: refetchSleeves } = useApi<PortfolioSleeve[]>('/policy/sleeves');

  const [editingObjective, setEditingObjective] = useState(false);
  const [objectiveText, setObjectiveText] = useState('');
  const [showSleeveForm, setShowSleeveForm] = useState(false);
  const [editingSleeveId, setEditingSleeveId] = useState<number | null>(null);
  const [sleeveForm, setSleeveForm] = useState(EMPTY_SLEEVE_FORM);
  const [editingCategories, setEditingCategories] = useState(false);
  const [catForm, setCatForm] = useState({
    target_equity_pct: null as number | null,
    target_international_pct: null as number | null,
    target_value_tilted_pct: null as number | null,
    target_small_cap_pct: null as number | null,
  });

  useEffect(() => {
    if (policy) {
      setObjectiveText(policy.objective_text);
      setCatForm({
        target_equity_pct: policy.target_equity_pct,
        target_international_pct: policy.target_international_pct,
        target_value_tilted_pct: policy.target_value_tilted_pct,
        target_small_cap_pct: policy.target_small_cap_pct,
      });
    }
  }, [policy]);

  if (!policy || !sleeves) {
    return <p className="text-calm-muted text-sm">Loading...</p>;
  }

  const totalPercent = sleeves.reduce((sum, s) => sum + s.target_percent, 0);

  const saveObjective = async () => {
    await put('/policy', { objective_text: objectiveText });
    setEditingObjective(false);
    refetchPolicy();
  };

  const saveCategories = async () => {
    await put('/policy', catForm);
    setEditingCategories(false);
    refetchPolicy();
  };

  const startEditSleeve = (s: PortfolioSleeve) => {
    setEditingSleeveId(s.id);
    setSleeveForm({
      ticker: s.ticker,
      label: s.label,
      target_percent: s.target_percent,
      asset_class: s.asset_class,
      geography: s.geography || '',
      is_safe_asset: s.is_safe_asset,
      is_cash_like: s.is_cash_like,
      region_us_pct: s.region_us_pct,
      region_developed_pct: s.region_developed_pct,
      region_emerging_pct: s.region_emerging_pct,
      factor_value: s.factor_value || '',
      factor_size: s.factor_size || '',
    });
    setShowSleeveForm(false);
  };

  const cancelEdit = () => {
    setEditingSleeveId(null);
    setShowSleeveForm(false);
    setSleeveForm(EMPTY_SLEEVE_FORM);
  };

  const saveSleeve = async () => {
    const payload = {
      ...sleeveForm,
      geography: sleeveForm.geography || null,
      factor_value: sleeveForm.factor_value || null,
      factor_size: sleeveForm.factor_size || null,
    };

    if (editingSleeveId) {
      await put(`/policy/sleeves/${editingSleeveId}`, payload);
    } else {
      await post('/policy/sleeves', payload);
    }
    cancelEdit();
    refetchSleeves();
  };

  const deleteSleeve = async (id: number) => {
    await del(`/policy/sleeves/${id}`);
    refetchSleeves();
  };

  const thingsIDoNotDo: string[] = policy.things_i_do_not_do
    ? JSON.parse(policy.things_i_do_not_do)
    : [];

  const sleeveFormUI = (
    <div className="mt-4 p-4 bg-calm-bg rounded-lg space-y-3">
      <p className="text-xs text-calm-muted font-medium uppercase">
        {editingSleeveId ? 'Edit Sleeve' : 'Add Sleeve'}
      </p>
      <div className="grid grid-cols-4 gap-3">
        <input placeholder="Ticker" value={sleeveForm.ticker}
          onChange={(e) => setSleeveForm({ ...sleeveForm, ticker: e.target.value.toUpperCase() })}
          className="px-3 py-1.5 text-sm border border-calm-border rounded bg-calm-surface" />
        <input placeholder="Label" value={sleeveForm.label}
          onChange={(e) => setSleeveForm({ ...sleeveForm, label: e.target.value })}
          className="px-3 py-1.5 text-sm border border-calm-border rounded bg-calm-surface col-span-2" />
        <input type="number" placeholder="Target %" value={sleeveForm.target_percent || ''}
          onChange={(e) => setSleeveForm({ ...sleeveForm, target_percent: Number(e.target.value) })}
          className="px-3 py-1.5 text-sm border border-calm-border rounded bg-calm-surface" />
      </div>
      <div className="grid grid-cols-4 gap-3">
        <select value={sleeveForm.asset_class}
          onChange={(e) => setSleeveForm({ ...sleeveForm, asset_class: e.target.value })}
          className="px-3 py-1.5 text-sm border border-calm-border rounded bg-calm-surface">
          <option value="equity">Equity</option>
          <option value="nominal_bond">Nominal Bond</option>
          <option value="tips">TIPS</option>
          <option value="cash_like">Cash-like</option>
        </select>
        <input placeholder="Geography" value={sleeveForm.geography}
          onChange={(e) => setSleeveForm({ ...sleeveForm, geography: e.target.value })}
          className="px-3 py-1.5 text-sm border border-calm-border rounded bg-calm-surface" />
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={sleeveForm.is_safe_asset}
            onChange={(e) => setSleeveForm({ ...sleeveForm, is_safe_asset: e.target.checked })} />
          Safe asset
        </label>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={sleeveForm.is_cash_like}
            onChange={(e) => setSleeveForm({ ...sleeveForm, is_cash_like: e.target.checked })} />
          Cash-like
        </label>
      </div>
      <p className="text-xs text-calm-muted font-medium uppercase mt-2">Region Weights (must sum to 100%)</p>
      <div className="grid grid-cols-3 gap-3">
        <label className="text-xs text-calm-muted">
          US %
          <input type="number" value={sleeveForm.region_us_pct || ''} placeholder="0"
            onChange={(e) => setSleeveForm({ ...sleeveForm, region_us_pct: Number(e.target.value) })}
            className="w-full px-3 py-1.5 text-sm border border-calm-border rounded bg-calm-surface mt-1" />
        </label>
        <label className="text-xs text-calm-muted">
          Developed %
          <input type="number" value={sleeveForm.region_developed_pct || ''} placeholder="0"
            onChange={(e) => setSleeveForm({ ...sleeveForm, region_developed_pct: Number(e.target.value) })}
            className="w-full px-3 py-1.5 text-sm border border-calm-border rounded bg-calm-surface mt-1" />
        </label>
        <label className="text-xs text-calm-muted">
          Emerging %
          <input type="number" value={sleeveForm.region_emerging_pct || ''} placeholder="0"
            onChange={(e) => setSleeveForm({ ...sleeveForm, region_emerging_pct: Number(e.target.value) })}
            className="w-full px-3 py-1.5 text-sm border border-calm-border rounded bg-calm-surface mt-1" />
        </label>
      </div>
      {(() => {
        const sum = sleeveForm.region_us_pct + sleeveForm.region_developed_pct + sleeveForm.region_emerging_pct;
        return sum > 0 && Math.abs(sum - 100) > 0.01 ? (
          <p className="text-xs text-calm-red">Region weights sum to {sum}% (should be 100%)</p>
        ) : null;
      })()}

      <p className="text-xs text-calm-muted font-medium uppercase mt-2">Factor Exposure</p>
      <div className="grid grid-cols-2 gap-3">
        <label className="text-xs text-calm-muted">
          Value Exposure
          <select value={sleeveForm.factor_value}
            onChange={(e) => setSleeveForm({ ...sleeveForm, factor_value: e.target.value })}
            className="w-full px-3 py-1.5 text-sm border border-calm-border rounded bg-calm-surface mt-1">
            <option value="">—</option>
            <option value="blend">Blend</option>
            <option value="tilted">Tilted</option>
          </select>
        </label>
        <label className="text-xs text-calm-muted">
          Market Cap
          <select value={sleeveForm.factor_size}
            onChange={(e) => setSleeveForm({ ...sleeveForm, factor_size: e.target.value })}
            className="w-full px-3 py-1.5 text-sm border border-calm-border rounded bg-calm-surface mt-1">
            <option value="">—</option>
            <option value="large">Large</option>
            <option value="blend">Blend</option>
            <option value="small">Small</option>
          </select>
        </label>
      </div>

      <div className="flex gap-2">
        <Button onClick={saveSleeve}>{editingSleeveId ? 'Save' : 'Add'}</Button>
        <Button variant="ghost" onClick={cancelEdit}>Cancel</Button>
      </div>
    </div>
  );

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-semibold tracking-tight">Investment Plan</h2>

      {/* Objective */}
      <Card>
        <h3 className="text-sm font-medium text-calm-muted uppercase tracking-wide mb-3">Objective</h3>
        {editingObjective ? (
          <div className="space-y-3">
            <textarea
              value={objectiveText}
              onChange={(e) => setObjectiveText(e.target.value)}
              className="w-full p-3 text-sm border border-calm-border rounded bg-calm-surface min-h-[80px]"
            />
            <div className="flex gap-2">
              <Button onClick={saveObjective}>Save</Button>
              <Button variant="ghost" onClick={() => setEditingObjective(false)}>Cancel</Button>
            </div>
          </div>
        ) : (
          <div className="flex justify-between items-start">
            <p className="text-sm text-calm-text leading-relaxed">{policy.objective_text}</p>
            <Button variant="ghost" onClick={() => setEditingObjective(true)}>Edit</Button>
          </div>
        )}
      </Card>

      {/* Targeting Mode Toggle */}
      <Card>
        <div className="flex justify-between items-center">
          <h3 className="text-sm font-medium text-calm-muted uppercase tracking-wide">Targeting Mode</h3>
          <div className="flex bg-calm-bg rounded-lg p-0.5">
            <button
              className={`px-4 py-1.5 text-sm rounded-md transition-colors ${
                policy.targeting_mode === 'fund' ? 'bg-calm-surface font-medium shadow-sm' : 'text-calm-muted'
              }`}
              onClick={async () => { await put('/policy', { targeting_mode: 'fund' }); refetchPolicy(); }}
            >
              By Fund
            </button>
            <button
              className={`px-4 py-1.5 text-sm rounded-md transition-colors ${
                policy.targeting_mode === 'category' ? 'bg-calm-surface font-medium shadow-sm' : 'text-calm-muted'
              }`}
              onClick={async () => { await put('/policy', { targeting_mode: 'category' }); refetchPolicy(); }}
            >
              By Category
            </button>
          </div>
        </div>
        <p className="text-xs text-calm-muted mt-2">
          {policy.targeting_mode === 'fund'
            ? 'Set target percentages per fund. Drift and bands are computed at the fund level.'
            : 'Set high-level category targets (equity %, international %, etc.). Drift is computed at the category level — swap funds without changing your targets.'}
        </p>
      </Card>

      {/* Category Targets (category mode) */}
      {policy.targeting_mode === 'category' && (
        <Card>
          <div className="flex justify-between items-center mb-3">
            <h3 className="text-sm font-medium text-calm-muted uppercase tracking-wide">Category Targets</h3>
            {!editingCategories && (
              <Button variant="ghost" onClick={() => setEditingCategories(true)}>Edit</Button>
            )}
          </div>
          {editingCategories ? (
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-4">
                <label className="text-xs text-calm-muted">
                  Equity % (of total portfolio)
                  <input type="number" value={catForm.target_equity_pct ?? ''}
                    onChange={(e) => setCatForm({ ...catForm, target_equity_pct: e.target.value ? Number(e.target.value) : null })}
                    className="w-full px-3 py-1.5 text-sm border border-calm-border rounded bg-calm-surface mt-1" />
                </label>
                <label className="text-xs text-calm-muted">
                  International % (of equities)
                  <input type="number" value={catForm.target_international_pct ?? ''}
                    onChange={(e) => setCatForm({ ...catForm, target_international_pct: e.target.value ? Number(e.target.value) : null })}
                    className="w-full px-3 py-1.5 text-sm border border-calm-border rounded bg-calm-surface mt-1" />
                </label>
                <label className="text-xs text-calm-muted">
                  Value-tilted % (of equities)
                  <input type="number" value={catForm.target_value_tilted_pct ?? ''}
                    onChange={(e) => setCatForm({ ...catForm, target_value_tilted_pct: e.target.value ? Number(e.target.value) : null })}
                    className="w-full px-3 py-1.5 text-sm border border-calm-border rounded bg-calm-surface mt-1" />
                </label>
                <label className="text-xs text-calm-muted">
                  Small cap % (of equities)
                  <input type="number" value={catForm.target_small_cap_pct ?? ''}
                    onChange={(e) => setCatForm({ ...catForm, target_small_cap_pct: e.target.value ? Number(e.target.value) : null })}
                    className="w-full px-3 py-1.5 text-sm border border-calm-border rounded bg-calm-surface mt-1" />
                </label>
              </div>
              <div className="flex gap-2">
                <Button onClick={saveCategories}>Save</Button>
                <Button variant="ghost" onClick={() => { setEditingCategories(false); setCatForm({ target_equity_pct: policy.target_equity_pct, target_international_pct: policy.target_international_pct, target_value_tilted_pct: policy.target_value_tilted_pct, target_small_cap_pct: policy.target_small_cap_pct }); }}>Cancel</Button>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-calm-muted">Equity:</span>
                <span className="ml-2 font-medium">{policy.target_equity_pct != null ? `${policy.target_equity_pct}%` : '—'}</span>
              </div>
              <div>
                <span className="text-calm-muted">International:</span>
                <span className="ml-2 font-medium">{policy.target_international_pct != null ? `${policy.target_international_pct}% of equities` : '—'}</span>
              </div>
              <div>
                <span className="text-calm-muted">Value-tilted:</span>
                <span className="ml-2 font-medium">{policy.target_value_tilted_pct != null ? `${policy.target_value_tilted_pct}% of equities` : '—'}</span>
              </div>
              <div>
                <span className="text-calm-muted">Small cap:</span>
                <span className="ml-2 font-medium">{policy.target_small_cap_pct != null ? `${policy.target_small_cap_pct}% of equities` : '—'}</span>
              </div>
            </div>
          )}
        </Card>
      )}

      {/* Fund Targets (fund mode) */}
      {policy.targeting_mode === 'fund' && (
        <Card>
          <div className="flex justify-between items-center mb-3">
            <h3 className="text-sm font-medium text-calm-muted uppercase tracking-wide">Target Portfolio</h3>
            <div className="flex items-center gap-3">
              <span className={`text-sm ${Math.abs(totalPercent - 100) < 0.01 ? 'text-calm-green' : 'text-calm-red'}`}>
                Total: {totalPercent.toFixed(0)}%
              </span>
              <Button variant="secondary" onClick={() => { setShowSleeveForm(true); setEditingSleeveId(null); setSleeveForm(EMPTY_SLEEVE_FORM); }}>
                Add Sleeve
              </Button>
            </div>
          </div>

          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-calm-border text-left text-xs text-calm-muted uppercase tracking-wide">
                <th className="pb-2 pr-4">Ticker</th>
                <th className="pb-2 pr-4">Label</th>
                <th className="pb-2 pr-4 text-right">Target %</th>
                <th className="pb-2 pr-4">Class</th>
                <th className="pb-2"></th>
              </tr>
            </thead>
            <tbody>
              {sleeves.map((s) => (
                <tr key={s.id} className={`border-b border-calm-border/50 ${editingSleeveId === s.id ? 'bg-calm-blue/5' : 'hover:bg-calm-bg cursor-pointer'}`}
                  onClick={() => { if (editingSleeveId !== s.id) startEditSleeve(s); }}>
                  <td className="py-2 pr-4 font-medium">{s.ticker}</td>
                  <td className="py-2 pr-4 text-calm-muted">{s.label}</td>
                  <td className="py-2 pr-4 text-right">{s.target_percent}%</td>
                  <td className="py-2 pr-4 text-calm-muted">{s.asset_class}</td>
                  <td className="py-2" onClick={(e) => e.stopPropagation()}>
                    <Button variant="ghost" className="text-xs text-calm-red" onClick={() => deleteSleeve(s.id)}>
                      Remove
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {(showSleeveForm || editingSleeveId) && sleeveFormUI}

          {!showSleeveForm && !editingSleeveId && (
            <p className="text-xs text-calm-muted mt-3">Click a row to edit it.</p>
          )}
        </Card>
      )}

      {/* Fund list (category mode - read-only, for reference) */}
      {policy.targeting_mode === 'category' && (
        <Card>
          <div className="flex justify-between items-center mb-3">
            <h3 className="text-sm font-medium text-calm-muted uppercase tracking-wide">Funds</h3>
            <Button variant="secondary" onClick={() => { setShowSleeveForm(true); setEditingSleeveId(null); setSleeveForm(EMPTY_SLEEVE_FORM); }}>
              Add Fund
            </Button>
          </div>
          <p className="text-xs text-calm-muted mb-3">
            Your funds and their metadata. In category mode, per-fund target % is not used for drift — category targets drive allocation.
          </p>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-calm-border text-left text-xs text-calm-muted uppercase tracking-wide">
                <th className="pb-2 pr-4">Ticker</th>
                <th className="pb-2 pr-4">Label</th>
                <th className="pb-2 pr-4">Class</th>
                <th className="pb-2"></th>
              </tr>
            </thead>
            <tbody>
              {sleeves.map((s) => (
                <tr key={s.id} className={`border-b border-calm-border/50 ${editingSleeveId === s.id ? 'bg-calm-blue/5' : 'hover:bg-calm-bg cursor-pointer'}`}
                  onClick={() => { if (editingSleeveId !== s.id) startEditSleeve(s); }}>
                  <td className="py-2 pr-4 font-medium">{s.ticker}</td>
                  <td className="py-2 pr-4 text-calm-muted">{s.label}</td>
                  <td className="py-2 pr-4 text-calm-muted">{s.asset_class}</td>
                  <td className="py-2" onClick={(e) => e.stopPropagation()}>
                    <Button variant="ghost" className="text-xs text-calm-red" onClick={() => deleteSleeve(s.id)}>
                      Remove
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {(showSleeveForm || editingSleeveId) && sleeveFormUI}

          {!showSleeveForm && !editingSleeveId && (
            <p className="text-xs text-calm-muted mt-3">Click a row to edit metadata (region weights, factors).</p>
          )}
        </Card>
      )}

      {/* Rebalancing Policy */}
      <Card>
        <h3 className="text-sm font-medium text-calm-muted uppercase tracking-wide mb-3">Rebalancing Policy</h3>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-calm-muted">Review cadence:</span>
            <span className="ml-2 font-medium capitalize">{policy.review_cadence}</span>
          </div>
          <div>
            <span className="text-calm-muted">Rebalance method:</span>
            <span className="ml-2 font-medium capitalize">{policy.rebalance_method}</span>
          </div>
          <div>
            <span className="text-calm-muted">Use cash flows first:</span>
            <span className="ml-2 font-medium">{policy.use_cash_flows_first ? 'Yes' : 'No'}</span>
          </div>
          <div>
            <span className="text-calm-muted">Avoid taxable sales:</span>
            <span className="ml-2 font-medium">{policy.avoid_taxable_sales ? 'Yes' : 'No'}</span>
          </div>
        </div>
      </Card>

      {/* Band explanation */}
      <Card>
        <h3 className="text-sm font-medium text-calm-muted uppercase tracking-wide mb-3">Tolerance Bands</h3>
        <p className="text-sm text-calm-muted leading-relaxed">
          Bands are computed automatically using relative thresholds (Daryanani 2008).
          The hard band is 25% of the target weight (minimum 2pp), and the soft band is half of that.
          See the Allocation page for current band status.
        </p>
      </Card>

      {/* Things I Do Not Do */}
      {thingsIDoNotDo.length > 0 && (
        <Card>
          <h3 className="text-sm font-medium text-calm-muted uppercase tracking-wide mb-3">Things I Do Not Do</h3>
          <ul className="space-y-2">
            {thingsIDoNotDo.map((item, i) => (
              <li key={i} className="text-sm text-calm-text flex items-start gap-2">
                <span className="text-calm-muted mt-0.5">&#x2014;</span>
                {item}
              </li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  );
}
