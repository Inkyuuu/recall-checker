import React, { FormEvent, useEffect, useMemo, useState } from 'react';
import './App.css';

type SortKey = 'report_date_desc' | 'report_date_asc' | 'classification' | 'company_name' | 'relevance';

type RecallItem = {
  source: string | null;
  source_recall_id: string | null;
  product_description: string | null;
  brand_name: string | null;
  company_name: string | null;
  recall_reason: string | null;
  classification: string | null;
  status: string | null;
  report_date: string | null;
  state: string | null;
  country: string | null;
};

type RecallsResponse = {
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
  items: RecallItem[];
};

type Filters = {
  q: string;
  classification: string;
  ongoingOnly: boolean;
  state: string;
  start_date: string;
  end_date: string;
  sort: SortKey;
};

const initialFilters: Filters = {
  q: '',
  classification: '',
  ongoingOnly: false,
  state: '',
  start_date: '',
  end_date: '',
  sort: 'relevance',
};

const pageSize = 20;

function formatValue(value: string | null) {
  return value && value.trim() ? value : 'Unknown';
}

function formatDate(value: string | null) {
  if (!value) {
    return 'Unknown';
  }

  const date = new Date(`${value}T00:00:00`);
  return Number.isNaN(date.getTime())
    ? value
    : new Intl.DateTimeFormat('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      }).format(date);
}

function buildQuery(filters: Filters, page: number) {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
    sort: filters.sort,
  });

  Object.entries(filters).forEach(([key, value]) => {
    if (key === 'ongoingOnly') {
      if (value) {
        params.set('status', 'Ongoing');
      }
      return;
    }

    if (key !== 'sort' && typeof value === 'string' && value.trim()) {
      params.set(key, value.trim());
    }
  });

  return params.toString();
}

function App() {
  const [filters, setFilters] = useState<Filters>(initialFilters);
  const [appliedFilters, setAppliedFilters] = useState<Filters>(initialFilters);
  const [page, setPage] = useState(1);
  const [data, setData] = useState<RecallsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const query = useMemo(() => buildQuery(appliedFilters, page), [appliedFilters, page]);

  useEffect(() => {
    const controller = new AbortController();

    async function loadRecalls() {
      setIsLoading(true);
      setError('');

      try {
        const response = await fetch(`/api/recalls?${query}`, {
          signal: controller.signal,
        });
        const payload = await response.json();

        if (!response.ok) {
          throw new Error(payload.error || 'Unable to load recalls.');
        }

        setData(payload);
      } catch (caught) {
        if ((caught as Error).name !== 'AbortError') {
          setError((caught as Error).message);
          setData(null);
        }
      } finally {
        if (!controller.signal.aborted) {
          setIsLoading(false);
        }
      }
    }

    loadRecalls();

    return () => controller.abort();
  }, [query]);

  function updateFilter(name: keyof Filters, value: string) {
    setFilters((current) => ({
      ...current,
      [name]: value,
    }));
  }

  function updateOngoingOnly(value: boolean) {
    setFilters((current) => ({
      ...current,
      ongoingOnly: value,
    }));
  }

  function submitSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPage(1);
    setAppliedFilters(filters);
  }

  function resetFilters() {
    setFilters(initialFilters);
    setAppliedFilters(initialFilters);
    setPage(1);
  }

  const totalPages = data?.total_pages ?? 0;
  const showingStart = data && data.total > 0 ? (data.page - 1) * data.page_size + 1 : 0;
  const showingEnd = data ? Math.min(data.page * data.page_size, data.total) : 0;

  return (
    <main className="app-shell">
      <section className="toolbar" aria-labelledby="page-title">
        <div>
          <p className="eyebrow">Recall Checker</p>
          <h1 id="page-title">Food Recall Search</h1>
          <p className="disclaimer">
            Recall data comes from the FDA and may not reflect the most recent updates.
          </p>
        </div>
        <div className="result-count" aria-live="polite">
          {data ? `${data.total.toLocaleString()} results` : 'Loading results'}
        </div>
      </section>

      <form className="filters" onSubmit={submitSearch}>
        <label className="field field-wide">
          <span>Search</span>
          <input
            type="search"
            value={filters.q}
            onChange={(event) => updateFilter('q', event.target.value)}
            placeholder="Product, brand, company, or reason"
          />
        </label>

        <label className="field">
          <span>Classification</span>
          <select
            value={filters.classification}
            onChange={(event) => updateFilter('classification', event.target.value)}
          >
            <option value="">All classes</option>
            <option value="Class I">Class I</option>
            <option value="Class II">Class II</option>
            <option value="Class III">Class III</option>
          </select>
        </label>

        <label className="field checkbox-field">
          <input
            type="checkbox"
            checked={filters.ongoingOnly}
            onChange={(event) => updateOngoingOnly(event.target.checked)}
          />
          <span>Ongoing recalls only</span>
        </label>

        <label className="field">
          <span>State</span>
          <input
            value={filters.state}
            onChange={(event) => updateFilter('state', event.target.value)}
            placeholder="CA"
            maxLength={32}
          />
        </label>

        <label className="field">
          <span>Start date</span>
          <input
            type="date"
            value={filters.start_date}
            onChange={(event) => updateFilter('start_date', event.target.value)}
          />
        </label>

        <label className="field">
          <span>End date</span>
          <input
            type="date"
            value={filters.end_date}
            onChange={(event) => updateFilter('end_date', event.target.value)}
          />
        </label>

        <label className="field">
          <span>Sort</span>
          <select value={filters.sort} onChange={(event) => updateFilter('sort', event.target.value as SortKey)}>
            <option value="report_date_desc">Newest report date</option>
            <option value="report_date_asc">Oldest report date</option>
            <option value="relevance">Best match</option>
            <option value="classification">Classification</option>
            <option value="company_name">Company name</option>
          </select>
        </label>

        <div className="filter-actions">
          <button type="submit">Search</button>
          <button type="button" className="button-secondary" onClick={resetFilters}>
            Reset
          </button>
        </div>
      </form>

      <section className="results" aria-label="Recall results">
        <div className="results-header">
          <div>
            <strong>Results</strong>
            <span>
              {data && data.total > 0
                ? `Showing ${showingStart.toLocaleString()}-${showingEnd.toLocaleString()}`
                : 'No rows to show'}
            </span>
          </div>
          <div className="pagination">
            <button type="button" onClick={() => setPage((current) => current - 1)} disabled={page <= 1 || isLoading}>
              Previous
            </button>
            <span>
              Page {data?.page ?? page} of {totalPages || 1}
            </span>
            <button
              type="button"
              onClick={() => setPage((current) => current + 1)}
              disabled={isLoading || totalPages === 0 || page >= totalPages}
            >
              Next
            </button>
          </div>
        </div>

        {error && <div className="alert">{error}</div>}
        {isLoading && <div className="state-message">Loading recalls...</div>}

        {!isLoading && !error && data?.items.length === 0 && (
          <div className="state-message">No recalls match the current search.</div>
        )}

        {!error && data && data.items.length > 0 && (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th scope="col">Report date</th>
                  <th scope="col">Product</th>
                  <th scope="col">Company</th>
                  <th scope="col">Class</th>
                  <th scope="col">Status</th>
                  <th scope="col">State</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((item) => (
                  <tr key={`${item.source}-${item.source_recall_id}`}>
                    <td>{formatDate(item.report_date)}</td>
                    <td>
                      <strong>{formatValue(item.product_description)}</strong>
                      <span>{formatValue(item.recall_reason)}</span>
                    </td>
                    <td>{formatValue(item.company_name || item.brand_name)}</td>
                    <td>{formatValue(item.classification)}</td>
                    <td>{formatValue(item.status)}</td>
                    <td>{formatValue(item.state || item.country)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </main>
  );
}

export default App;
