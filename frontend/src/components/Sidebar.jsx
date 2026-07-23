import { NavLink } from 'react-router-dom'
import {
  Sparkles,
  UserPlus,
  Wand2,
  FileText,
  Folder,
  Calendar,
  Plug,
  Star,
  GraduationCap,
  Lightbulb,
  ClipboardList,
  PlusCircle,
  ChevronRight,
} from 'lucide-react'
import './Sidebar.css'

const primaryNavItems = [
  { to: '/reports', label: 'Reports', icon: FileText },
  { to: '/folders', label: 'Folders', icon: Folder },
]

function NavItem({ to, label, icon: Icon }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) => `sidebar-nav-item${isActive ? ' active' : ''}`}
    >
      <Icon size={18} strokeWidth={1.75} />
      <span>{label}</span>
    </NavLink>
  )
}

function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar-top">
        <div className="sidebar-brand">
          <span className="sidebar-brand-mark">
            <Sparkles size={16} strokeWidth={2} />
          </span>
          <span className="sidebar-brand-name">Clinera</span>
        </div>

        <nav className="sidebar-nav">
          {primaryNavItems.map((item) => (
            <NavItem key={item.to} {...item} />
          ))}
        </nav>

        <div className="sidebar-divider" />

      </div>

      <div className="sidebar-bottom">

        <div className="sidebar-scheduler">
          <span className="sidebar-scheduler-label">Smart Scheduler Link</span>
          <div className="sidebar-scheduler-actions">
            <button type="button" className="sidebar-copy-link-btn">
              Copy link
            </button>
            <button type="button" className="sidebar-manage-btn">
              Manage
            </button>
          </div>
        </div>

        <button type="button" className="sidebar-profile">
          <span className="sidebar-avatar">SP</span>
          <span className="sidebar-profile-info">
            <span className="sidebar-profile-name">Samuel Passey</span>
            <span className="sidebar-profile-email">sampassey2@gmail.com</span>
          </span>
          <ChevronRight size={16} strokeWidth={1.75} />
        </button>
      </div>
    </aside>
  )
}

export default Sidebar
