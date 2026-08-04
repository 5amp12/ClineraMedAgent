import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import {
  ArrowLeft,
  FolderPlus,
  Download,
  Send,
  Share2,
  Check,
  MoreHorizontal,
  Calendar,
  Clock,
  Video,
  Users,
  Maximize2,
  Lock,
  ArrowUp,
  Sparkles,
} from 'lucide-react'
// import { report, chapters } from '../data/mockReport.js'
import { report } from "../../api/ReportCall.js"
import ClinicalNote from '../components/ClinicalNote.jsx'
import './Reports.css'

const tabs = ['Report']

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

function buildReportText(reportData) {
  const note = reportData.report || {}
  const lines = [
    reportData.board_title || 'Board Report',
    [formatDate(reportData.date), formatTime(reportData.start_time)].filter(Boolean).join(' · '),
    '',
    'Reason for Visit', note.reason_for_visit || '', '',
    'History', note.history || '', '',
    'Findings', note.findings || '', '',
    'Plan', note.plan || '',
  ]

  if (reportData.recommendations?.length) {
    lines.push('', 'Recommendations')
    reportData.recommendations.forEach((rec) => {
      lines.push(`- ${[rec.order_type, rec.details].filter(Boolean).join(': ')}`)
    })
  }

  return lines.join('\n')
}

function Reports() {
  const [activeTab, setActiveTab] = useState('Report')
  const [reportData, setReportData] = useState('')
  const [copied, setCopied] = useState(false)

  const params = useParams();
  useEffect(() => {

    async function load(){
      
      console.log(params.id)

      const data = await report(params.id);
      setReportData(data)
      console.log(data)
    }
    load()

  })

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

  return (
    <div className="reports-page">
      <header className="reports-header">
        <div className="reports-header-left">
          <button type="button" className="icon-btn" aria-label="Back">
            <ArrowLeft size={18} />
          </button>
          <h1 className="reports-title">{reportData.board_title}</h1>
        </div>
        <div className="reports-header-right">
          <button type="button" className="pill-btn" onClick={handleDownload}>
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
          {formatDate(reportData.date)}
        </span>
        <span className="reports-meta-dot">&middot;</span>
        <span className="reports-meta-item">
          <Clock size={14} />
          {formatTime(reportData.start_time)}
        </span>
        <span className="reports-meta-dot">&middot;</span>
        <span className="reports-meta-item">
          <Users size={14} />
          {/* {report.attendees.join(', ')}, +{report.extraAttendeeCount} more  --add attendees */}
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
           {reportData && reportData.report ? (
             <ClinicalNote note={reportData.report} segments={[]} patient={reportData.patient} recommendations={reportData.recommendations}/>
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
