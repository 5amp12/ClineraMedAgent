import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { FileText, Play, Loader2, AlertTriangle, Users, ClipboardList } from 'lucide-react'
import { listReports, runBoard, report } from '../../api/ReportCall.js'
import './ReportsIndex.css'

const POLL_MS = 2500

function formatWhen(value) {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString(undefined, {
    month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit',
  })
}

const STATUS_LABEL = {
  running: 'Running',
  ready: 'Ready',
  halted: 'Halted',
  failed: 'Failed',
}

function ReportsIndex() {
  const [boardId, setBoardId] = useState('')
  const [transcript, setTranscript] = useState('')
  const [runs, setRuns] = useState([])
  const [busy, setBusy] = useState(false)
  const [progress, setProgress] = useState(null)
  const [error, setError] = useState(null)
  const navigate = useNavigate()

  const refresh = useCallback(async () => {
    try {
      setRuns(await listReports())
    } catch (err) {
      setError(err.message)
    }
  }, [])

  // Load the list once on mount. The work is inlined rather than calling refresh() directly
  // because react-hooks flags a synchronous setState-producing call in an effect body, and
  // `cancelled` keeps a slow response from landing on an unmounted component.
  useEffect(() => {
    let cancelled = false

    async function load() {
      try {
        const data = await listReports()
        if (!cancelled) setRuns(data)
      } catch (err) {
        if (!cancelled) setError(err.message)
      }
    }
    load()

    return () => {
      cancelled = true
    }
  }, [])

  async function handleRun(event) {
    event.preventDefault()
    const id = boardId.trim()
    if (!id) return

    setBusy(true)
    setError(null)
    setProgress('Starting the run…')

    try {
      const { visit_id: visitId } = await runBoard(id, transcript)
      await refresh()

      // A full board is ~17 sequential model calls, so this polls rather than blocking on one
      // long request. The report page polls too, so navigating early is safe either way.
      setProgress('Processing the board. This takes a couple of minutes…')
      for (;;) {
        await new Promise((resolve) => setTimeout(resolve, POLL_MS))
        const payload = await report(visitId)

        if (payload.run_status === 'ready') {
          navigate(`/reports/${visitId}`)
          return
        }
        if (payload.run_status === 'failed') {
          throw new Error(payload.error || 'The pipeline run failed.')
        }
        if (payload.run_status === 'halted') {
          throw new Error(`Governance halted this board: ${payload.halt_reason}`)
        }
      }
    } catch (err) {
      setError(err.message)
      setProgress(null)
      refresh()
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="index-page">
      <header className="index-header">
        <h1 className="index-title">Board reports</h1>
        <p className="index-subtitle">
          Run the pipeline over a Clinera board. Paste the meeting transcript if you have one &mdash;
          without it the board record is summarized instead.
        </p>
      </header>

      <form className="index-form" onSubmit={handleRun}>
        <label className="index-label" htmlFor="board-id">Board ID</label>
        <input
          id="board-id"
          className="index-input"
          value={boardId}
          onChange={(e) => setBoardId(e.target.value)}
          placeholder="e.g. 892"
          inputMode="numeric"
          disabled={busy}
        />

        <label className="index-label" htmlFor="transcript">
          Meeting transcript <span className="index-optional">optional</span>
        </label>
        <textarea
          id="transcript"
          className="index-textarea"
          value={transcript}
          onChange={(e) => setTranscript(e.target.value)}
          placeholder={'Dr Jenkins: Moving to the next case…\nDr Botha: Imaging shows…'}
          rows={8}
          disabled={busy}
        />
        <p className="index-hint">
          One line per turn. A leading &ldquo;Name:&rdquo; is read as the speaker. Patient details,
          MRNs and diagnoses still come from Clinera, so recommendations stay tied to the real record.
        </p>

        <button type="submit" className="index-run-btn" disabled={busy || !boardId.trim()}>
          {busy ? <Loader2 size={15} className="index-spin" /> : <Play size={15} />}
          {busy ? 'Running…' : 'Run pipeline'}
        </button>

        {progress ? <p className="index-progress">{progress}</p> : null}
        {error ? (
          <p className="index-error">
            <AlertTriangle size={15} />
            {error}
          </p>
        ) : null}
      </form>

      <section className="index-runs">
        <h2 className="index-runs-title">Past runs</h2>
        {runs.length === 0 ? (
          <p className="index-empty">Nothing yet. Run a board above to produce your first report.</p>
        ) : (
          <ul className="index-run-list">
            {runs.map((run) => (
              <li key={run.visit_id}>
                <button
                  type="button"
                  className="index-run-row"
                  onClick={() => navigate(`/reports/${run.visit_id}`)}
                >
                  <span className="index-run-icon"><FileText size={16} /></span>
                  <span className="index-run-main">
                    <span className="index-run-name">
                      {run.board_title || `Board ${run.board_id}`}
                    </span>
                    <span className="index-run-meta">
                      {run.visit_id} &middot; {formatWhen(run.started_at)}
                    </span>
                  </span>
                  <span className="index-run-counts">
                    {run.patient_count ? (
                      <span title="patients"><Users size={13} /> {run.patient_count}</span>
                    ) : null}
                    {run.order_count ? (
                      <span title="proposed orders">
                        <ClipboardList size={13} /> {run.order_count}
                        {run.pending_count ? ` (${run.pending_count} pending)` : ''}
                      </span>
                    ) : null}
                  </span>
                  <span className={`index-run-status status-${run.status}`}>
                    {STATUS_LABEL[run.status] || run.status}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}

export default ReportsIndex
