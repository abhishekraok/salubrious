import { useRef, useState } from 'react';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { useApi } from '../hooks/useApi';
import { post, put, del } from '../api/client';
import type { Account, Holding } from '../types';

function formatDollars(n: number) {
  return '$' + n.toLocaleString(undefined, { maximumFractionDigits: 0 });
}

export function HoldingsPage() {
  const { data: accounts, refetch: refetchAccounts } = useApi<Account[]>('/accounts');
  const { data: holdings, refetch: refetchHoldings } = useApi<Holding[]>('/holdings');

  const [showAccountForm, setShowAccountForm] = useState(false);
  const [accountForm, setAccountForm] = useState({
    institution_name: '', account_name: '', account_type: 'taxable', is_tax_advantaged: false,
  });

  const [showHoldingForm, setShowHoldingForm] = useState<number | null>(null); // account_id
  const [holdingForm, setHoldingForm] = useState({ ticker: '', quantity: 0, price: 0 });

  const [editingHolding, setEditingHolding] = useState<number | null>(null);
  const [editForm, setEditForm] = useState({ quantity: 0, price: 0 });

  const fileInputRef = useRef<HTMLInputElement>(null);
  const [csvAccountId, setCsvAccountId] = useState<number | null>(null);
  const [csvResult, setCsvResult] = useState<string | null>(null);

  if (!accounts || !holdings) {
    return <p className="text-calm-muted text-sm">Loading...</p>;
  }

  const holdingsByAccount = (accountId: number) =>
    holdings.filter((h) => h.account_id === accountId);

  const totalValue = holdings.reduce((sum, h) => sum + h.market_value, 0);

  const saveAccount = async () => {
    await post('/accounts', accountForm);
    setShowAccountForm(false);
    setAccountForm({ institution_name: '', account_name: '', account_type: 'taxable', is_tax_advantaged: false });
    refetchAccounts();
  };

  const deleteAccount = async (id: number) => {
    await del(`/accounts/${id}`);
    refetchAccounts();
    refetchHoldings();
  };

  const saveHolding = async (accountId: number) => {
    await post(`/accounts/${accountId}/holdings`, holdingForm);
    setShowHoldingForm(null);
    setHoldingForm({ ticker: '', quantity: 0, price: 0 });
    refetchHoldings();
  };

  const saveEditHolding = async (holdingId: number) => {
    await put(`/holdings/${holdingId}`, editForm);
    setEditingHolding(null);
    refetchHoldings();
  };

  const deleteHolding = async (id: number) => {
    await del(`/holdings/${id}`);
    refetchHoldings();
  };

  const handleCsvUpload = async (accountId: number, file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch(`/api/accounts/${accountId}/holdings/csv`, {
      method: 'POST',
      body: formData,
    });
    const result = await res.json();
    setCsvResult(`Imported ${result.imported} holdings`);
    setCsvAccountId(null);
    refetchHoldings();
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-semibold tracking-tight">Holdings</h2>
        <div className="flex items-center gap-3">
          <span className="text-sm text-calm-muted">Total: {formatDollars(totalValue)}</span>
          <Button variant="secondary" onClick={() => {
            window.open('/api/holdings/export', '_blank');
          }}>Export CSV</Button>
          <Button variant="secondary" onClick={() => setShowAccountForm(true)}>Add Account</Button>
        </div>
      </div>

      {csvResult && (
        <div className="p-3 bg-calm-green/10 text-calm-green text-sm rounded">
          {csvResult}
          <button className="ml-2 underline" onClick={() => setCsvResult(null)}>dismiss</button>
        </div>
      )}

      {/* Add account form */}
      {showAccountForm && (
        <Card>
          <p className="text-xs text-calm-muted font-medium uppercase mb-3">New Account</p>
          <div className="grid grid-cols-4 gap-3">
            <input placeholder="Institution" value={accountForm.institution_name}
              onChange={(e) => setAccountForm({ ...accountForm, institution_name: e.target.value })}
              className="px-3 py-1.5 text-sm border border-calm-border rounded bg-calm-surface" />
            <input placeholder="Account name" value={accountForm.account_name}
              onChange={(e) => setAccountForm({ ...accountForm, account_name: e.target.value })}
              className="px-3 py-1.5 text-sm border border-calm-border rounded bg-calm-surface" />
            <select value={accountForm.account_type}
              onChange={(e) => setAccountForm({ ...accountForm, account_type: e.target.value })}
              className="px-3 py-1.5 text-sm border border-calm-border rounded bg-calm-surface">
              <option value="taxable">Taxable</option>
              <option value="traditional_ira">Traditional IRA</option>
              <option value="roth_ira">Roth IRA</option>
              <option value="401k">401(k)</option>
              <option value="hsa">HSA</option>
              <option value="cash">Cash</option>
            </select>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={accountForm.is_tax_advantaged}
                onChange={(e) => setAccountForm({ ...accountForm, is_tax_advantaged: e.target.checked })} />
              Tax-advantaged
            </label>
          </div>
          <div className="flex gap-2 mt-3">
            <Button onClick={saveAccount}>Create</Button>
            <Button variant="ghost" onClick={() => setShowAccountForm(false)}>Cancel</Button>
          </div>
        </Card>
      )}

      {/* Account cards with holdings */}
      {accounts.map((acct) => {
        const acctHoldings = holdingsByAccount(acct.id);
        const acctTotal = acctHoldings.reduce((s, h) => s + h.market_value, 0);

        return (
          <Card key={acct.id}>
            <div className="flex justify-between items-center mb-3">
              <div>
                <h3 className="text-sm font-medium">{acct.account_name}</h3>
                <p className="text-xs text-calm-muted">
                  {acct.institution_name} &middot; {acct.account_type.replace('_', ' ')}
                  {acct.is_tax_advantaged && ' (tax-advantaged)'}
                </p>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-sm font-medium">{formatDollars(acctTotal)}</span>
                <Button variant="secondary" onClick={() => { setShowHoldingForm(acct.id); setHoldingForm({ ticker: '', quantity: 0, price: 0 }); }}>
                  Add Holding
                </Button>
                <Button variant="secondary" onClick={() => {
                  setCsvAccountId(acct.id);
                  fileInputRef.current?.click();
                }}>
                  Import CSV
                </Button>
                <Button variant="ghost" className="text-xs text-calm-red" onClick={() => deleteAccount(acct.id)}>
                  Delete
                </Button>
              </div>
            </div>

            {/* Holdings table */}
            {acctHoldings.length > 0 && (
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-calm-border text-left text-xs text-calm-muted uppercase tracking-wide">
                    <th className="pb-2 pr-4">Ticker</th>
                    <th className="pb-2 pr-4 text-right">Quantity</th>
                    <th className="pb-2 pr-4 text-right">Price</th>
                    <th className="pb-2 pr-4 text-right">Market Value</th>
                    <th className="pb-2 pr-4">As Of</th>
                    <th className="pb-2"></th>
                  </tr>
                </thead>
                <tbody>
                  {acctHoldings.map((h) => (
                    <tr key={h.id} className="border-b border-calm-border/50">
                      {editingHolding === h.id ? (
                        <>
                          <td className="py-2 pr-4 font-medium">{h.ticker}</td>
                          <td className="py-2 pr-4 text-right">
                            <input type="number" value={editForm.quantity}
                              onChange={(e) => setEditForm({ ...editForm, quantity: Number(e.target.value) })}
                              className="w-24 px-2 py-1 text-sm text-right border border-calm-border rounded bg-calm-surface" />
                          </td>
                          <td className="py-2 pr-4 text-right">
                            <input type="number" step="0.01" value={editForm.price}
                              onChange={(e) => setEditForm({ ...editForm, price: Number(e.target.value) })}
                              className="w-24 px-2 py-1 text-sm text-right border border-calm-border rounded bg-calm-surface" />
                          </td>
                          <td className="py-2 pr-4 text-right text-calm-muted">
                            {formatDollars(editForm.quantity * editForm.price)}
                          </td>
                          <td className="py-2 pr-4 text-calm-muted">{h.as_of_date}</td>
                          <td className="py-2 flex gap-1">
                            <Button variant="primary" className="text-xs" onClick={() => saveEditHolding(h.id)}>Save</Button>
                            <Button variant="ghost" className="text-xs" onClick={() => setEditingHolding(null)}>Cancel</Button>
                          </td>
                        </>
                      ) : (
                        <>
                          <td className="py-2 pr-4 font-medium">{h.ticker}</td>
                          <td className="py-2 pr-4 text-right">{h.quantity.toLocaleString()}</td>
                          <td className="py-2 pr-4 text-right">${h.price.toFixed(2)}</td>
                          <td className="py-2 pr-4 text-right">{formatDollars(h.market_value)}</td>
                          <td className="py-2 pr-4 text-calm-muted">{h.as_of_date}</td>
                          <td className="py-2 flex gap-1">
                            <Button variant="ghost" className="text-xs" onClick={() => {
                              setEditingHolding(h.id);
                              setEditForm({ quantity: h.quantity, price: h.price });
                            }}>Edit</Button>
                            <Button variant="ghost" className="text-xs text-calm-red" onClick={() => deleteHolding(h.id)}>
                              Delete
                            </Button>
                          </td>
                        </>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            )}

            {acctHoldings.length === 0 && (
              <p className="text-sm text-calm-muted">No holdings yet. Add manually or import a CSV.</p>
            )}

            {/* Add holding form */}
            {showHoldingForm === acct.id && (
              <div className="mt-3 p-3 bg-calm-bg rounded-lg">
                <div className="grid grid-cols-4 gap-3">
                  <input placeholder="Ticker" value={holdingForm.ticker}
                    onChange={(e) => setHoldingForm({ ...holdingForm, ticker: e.target.value.toUpperCase() })}
                    className="px-3 py-1.5 text-sm border border-calm-border rounded bg-calm-surface" />
                  <input type="number" placeholder="Quantity" value={holdingForm.quantity || ''}
                    onChange={(e) => setHoldingForm({ ...holdingForm, quantity: Number(e.target.value) })}
                    className="px-3 py-1.5 text-sm border border-calm-border rounded bg-calm-surface" />
                  <input type="number" step="0.01" placeholder="Price" value={holdingForm.price || ''}
                    onChange={(e) => setHoldingForm({ ...holdingForm, price: Number(e.target.value) })}
                    className="px-3 py-1.5 text-sm border border-calm-border rounded bg-calm-surface" />
                  <span className="flex items-center text-sm text-calm-muted">
                    = {formatDollars(holdingForm.quantity * holdingForm.price)}
                  </span>
                </div>
                <div className="flex gap-2 mt-3">
                  <Button onClick={() => saveHolding(acct.id)}>Add</Button>
                  <Button variant="ghost" onClick={() => setShowHoldingForm(null)}>Cancel</Button>
                </div>
              </div>
            )}
          </Card>
        );
      })}

      {accounts.length === 0 && (
        <Card>
          <p className="text-sm text-calm-muted">No accounts yet. Add an account to start entering holdings.</p>
        </Card>
      )}

      {/* CSV info */}
      <Card>
        <h3 className="text-sm font-medium text-calm-muted uppercase tracking-wide mb-2">CSV Import Format</h3>
        <p className="text-xs text-calm-muted mb-2">
          Upload a CSV with columns: <code className="bg-calm-bg px-1 rounded">ticker, quantity, price</code> or{' '}
          <code className="bg-calm-bg px-1 rounded">ticker, quantity, market_value</code>
        </p>
        <pre className="text-xs bg-calm-bg p-3 rounded text-calm-muted">
{`ticker,quantity,price
VTI,150,280.50
VXUS,300,58.20
VGIT,200,58.00`}
        </pre>
      </Card>

      {/* Hidden file input for CSV */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".csv"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file && csvAccountId) {
            handleCsvUpload(csvAccountId, file);
          }
          e.target.value = '';
        }}
      />
    </div>
  );
}
