import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  ArrowLeft,
  Download,
  Share2,
  Check,
  Calendar,
  Clock,
  Users,
  ArrowUp,
} from 'lucide-react'
import { report } from '../../api/ReportCall.js'
import ClinicalNote from '../components/ClinicalNote.jsx'
import './Reports.css'

const tabs = ['Report']

// How often to re-check a run that is still in flight. A full board is ~17 sequential LLM calls,
// so this polls for a while — see app/api/routes_reports.py on why the run cannot be synchronous.
const POLL_MS = 2500

function formatDate(value) {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
}

function formatTime(value) {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })
}

// history/findings/plan are per-patient arrays of {patient_name, text}. Strings are still accepted
// so a report persisted before the schema change downloads as something readable rather than
// "[object Object]".
function sectionLines(entries) {
  if (!entries) return ['']
  if (typeof entries === 'string') return [entries]
  return entries.map((entry) => `${entry.patient_name}: ${entry.text}`)
}

function buildReportText(reportData) {
  const note = reportData.report || {}
  const lines = [
    reportData.board_title || 'Board Report',
    [formatDate(reportData.date), formatTime(reportData.start_time)].filter(Boolean).join(' · '),
    '',
    'Reason for Visit', note.reason_for_visit || '', '',
    'History', ...sectionLines(note.history), '',
    'Findings', ...sectionLines(note.findings), '',
    'Plan', ...sectionLines(note.plan),
  ]

  if (reportData.recommendations?.length) {
    lines.push('', 'Recommendations')
    reportData.recommendations.forEach((rec) => {
      const head = [rec.order_type, rec.details].filter(Boolean).join(': ')
      lines.push(`- [${rec.patient_name || 'unassigned'}] ${head}`)
      if (rec.rationale) lines.push(`    Rationale: ${rec.rationale}`)
      if (rec.status) lines.push(`    Status: ${rec.status}`)
    })
  }

  return lines.join('\n')
}

function Reports() {
  const [activeTab, setActiveTab] = useState('Report')
  const [reportData, setReportData] = useState(null)
  const [runState, setRunState] = useState('loading')
  const [error, setError] = useState(null)
  const [copied, setCopied] = useState(false)

  const params = useParams()
  const navigate = useNavigate()
  const visitId = params.id

  function handleBack() {
    // Step back through in-app history when there is any, so report -> report returns to the
    // previous report rather than jumping to the list. On a deep link (pasted URL, new tab) there
    // is nothing to go back to and history.back() would leave the app entirely, so fall back to
    // the reports list. React Router tracks its position in history.state.idx.
    if (window.history.state?.idx > 0) {
      navigate(-1)
    } else {
      navigate('/reports')
    }
  }

  // The dependency array matters more than it looks. Without one this effect re-ran after every
  // render, and setReportData causes a render — so one open tab fired several requests per second,
  // indefinitely, each a real authenticated call through to Clinera.
  useEffect(() => {
    let cancelled = false
    let timer = null

    async function load() {
      try {
        const payload = await report(visitId)
        if (cancelled) return

        setRunState(payload.run_status)
        if (payload.run_status === 'ready') {
          setReportData(payload.report)
        } else if (payload.run_status === 'failed') {
          setError(payload.error || 'The pipeline run failed.')
        } else if (payload.run_status === 'halted') {
          setError(`Governance halted this board: ${payload.halt_reason}`)
        } else {
          // still running — check back rather than leaving the page on a dead "Loading...".
          timer = setTimeout(load, POLL_MS)
        }
      } catch (err) {
        // report() throws on any non-2xx. Left unhandled, that rejection showed the user a
        // permanent "Loading..." with no hint that the backend was the problem.
        if (!cancelled) {
          setRunState('failed')
          setError(err.message)
        }
      }
    }
    load()

    return () => {
      cancelled = true
      if (timer) clearTimeout(timer)
    }
  }, [visitId])

  // Let ClinicalNote push an approved/rejected order back up without refetching the whole report.
  const handleOrderUpdated = useCallback((updated) => {
    setReportData((current) => {
      if (!current) return current
      return {
        ...current,
        recommendations: current.recommendations.map((rec) =>
          rec.id === updated.id ? { ...rec, ...updated } : rec,
        ),
      }
    })
  }, [])

  function handleDownload() {
    const blob = new Blob([buildReportText(reportData)], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${(reportData.board_title || 'report').replace(/[^a-z0-9]+/gi, '-')}.txt`
    link.click()
    URL.revokeObjectURL(url)
  }

  async function handleShare() {
    await navigator.clipboard.writeText(window.location.href)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const attendees = (reportData?.doctors_attended || []).map((d) => d.name).filter(Boolean)

  return (
    <div className="reports-page">
      <header className="reports-header">
        <div className="reports-header-left">
          <button type="button" className="icon-btn" aria-label="Back to reports" onClick={handleBack}>
            <ArrowLeft size={18} />
          </button>
          <h1 className="reports-title">{reportData?.board_title || visitId}</h1>
        </div>
        <div className="reports-header-right">
          <button type="button" className="pill-btn" onClick={handleDownload} disabled={!reportData}>
            <Download size={15} />
            Download
          </button>
          <button type="button" className="pill-btn primary" onClick={handleShare}>
            {copied ? <Check size={15} /> : <Share2 size={15} />}
            {copied ? 'Copied' : 'Share'}
          </button>
        </div>
      </header>

      <div className="reports-meta">
        <span className="reports-meta-item">
          <Calendar size={14} />
          {formatDate(reportData?.date)}
        </span>
        <span className="reports-meta-dot">&middot;</span>
        <span className="reports-meta-item">
          <Clock size={14} />
          {formatTime(reportData?.start_time)}
        </span>
        <span className="reports-meta-dot">&middot;</span>
        <span className="reports-meta-item">
          <Users size={14} />
          {attendees.length ? attendees.join(', ') : 'No attendees recorded'}
        </span>
      </div>

      <nav className="reports-tabs">
        {tabs.map((tab) => (
          <button
            key={tab}
            type="button"
            className={`reports-tab${activeTab === tab ? ' active' : ''}`}
            onClick={() => setActiveTab(tab)}
          >
            {tab}
          </button>
        ))}
      </nav>

       <div className="reports-body">
         <section className="reports-recap">
           {error ? (
             <p className="reports-error">{error}</p>
           ) : runState === 'running' ? (
             <p className="reports-pending">
               Running the pipeline for {visitId}. A full board is roughly 17 model calls, so this
               takes a couple of minutes &mdash; this page refreshes itself.
             </p>
           ) : reportData && reportData.report ? (
             <ClinicalNote
               note={reportData.report}
               patients={reportData.patients}
               recommendations={reportData.recommendations}
               visitId={reportData.id}
               onOrderUpdated={handleOrderUpdated}
             />
           ) : (
             <p>Loading...</p>
           )}
         </section>
       </div>

       <button type="button" className="reports-scroll-top" aria-label="Scroll to top">
         <ArrowUp size={16} />
       </button>
    </div>
  )
}

export default Reports
