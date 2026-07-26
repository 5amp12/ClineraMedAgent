import { useState } from 'react'
import { Stethoscope, ScrollText, Activity, ClipboardCheck, Quote } from 'lucide-react'
import './ClinicalNote.css'

const sectionConfig = [
  { key: 'history', label: 'History', icon: ScrollText },
  { key: 'findings', label: 'Findings', icon: Activity },
  { key: 'plan', label: 'Plan', icon: ClipboardCheck },
]

function ClinicalNote({ note, segments }) {
  const [openSegment, setOpenSegment] = useState(null)

  const segmentByIndex = new Map(segments.map((segment) => [segment.index, segment]))

  return (
    <div className="clinical-note">
      <div className="clinical-note-banner">
        <span className="clinical-note-banner-icon">
          <Stethoscope size={18} strokeWidth={1.75} />
        </span>
        <div>
          <span className="clinical-note-banner-label">Reason for Visit</span>
          <p className="clinical-note-banner-text">{note.reason_for_visit}</p>
        </div>
      </div>

      {sectionConfig.map(({ key, label, icon: Icon }) => (
        <section className="clinical-note-section" key={key}>
          <h3 className="clinical-note-section-title">
            <Icon size={16} strokeWidth={1.75} />
            {label}
          </h3>
          <p className="clinical-note-section-body">{note[key]}</p>
        </section>
      ))}

    </div>
  )
}

export default ClinicalNote
