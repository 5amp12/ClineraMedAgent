import { useState } from 'react'
import {
  ArrowLeft,
  FolderPlus,
  Download,
  Send,
  Share2,
  MoreHorizontal,
  Calendar,
  Clock,
  Video,
  Users,
  Search,
  Copy,
  Maximize2,
  Lock,
  ArrowUp,
  Sparkles,
} from 'lucide-react'
import { report, chapters } from '../data/mockReport.js'
import './Reports.css'

const tabs = ['Report', 'Transcript']

function Reports() {
  const [activeTab, setActiveTab] = useState('Recap')
  const [search, setSearch] = useState('')

  const visibleChapters = chapters.filter((chapter) =>
    chapter.title.toLowerCase().includes(search.toLowerCase()) ||
    chapter.body.toLowerCase().includes(search.toLowerCase()),
  )

  return (
    <div className="reports-page">
      <header className="reports-header">
        <div className="reports-header-left">
          <button type="button" className="icon-btn" aria-label="Back">
            <ArrowLeft size={18} />
          </button>
          <h1 className="reports-title">{report.title}</h1>
        </div>
        <div className="reports-header-right">
          <button type="button" className="pill-btn">
            <Download size={15} />
            Download
          </button>
          <button type="button" className="pill-btn primary">
            <Share2 size={15} />
            Share
          </button>
        </div>
      </header>

      <div className="reports-meta">
        <span className="reports-meta-item">
          <Calendar size={14} />
          {report.date}
        </span>
        <span className="reports-meta-dot">&middot;</span>
        <span className="reports-meta-item">
          <Clock size={14} />
          {report.time}
        </span>
        <span className="reports-meta-dot">&middot;</span>
        <span className="reports-meta-item">
          <Users size={14} />
          {report.attendees.join(', ')}, +{report.extraAttendeeCount} more
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
          {activeTab === 'Transcript' ? (
            <>
              <div className="reports-search">
                <div className="reports-search-input">
                  <Search size={15} />
                  <input
                    type="text"
                    placeholder="Search recap..."
                    value={search}
                    onChange={(event) => setSearch(event.target.value)}
                  />
                </div>
                <button type="button" className="icon-btn" aria-label="Copy recap">
                  <Copy size={15} />
                </button>
              </div>

              <h2 className="reports-section-title">Key Discussion Points</h2>

              <div className="reports-discussion-list">
                {visibleChapters.map((chapter) => (
                  <div className="reports-discussion-item" key={chapter.time}>
                    <div className="reports-discussion-heading">
                      <span className="reports-discussion-time">{chapter.time}</span>
                      <span className="reports-discussion-title">{chapter.title}</span>
                    </div>
                    <p className="reports-discussion-body">{chapter.body}</p>
                  </div>
                ))}
                {visibleChapters.length === 0 ? (
                  <p className="reports-discussion-empty">No discussion points match your search.</p>
                ) : null}
              </div>
            </>
          ) : (
            <div className="reports-tab-placeholder">
              <p>{activeTab} content isn&apos;t wired up yet in this sample.</p>
            </div>
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
