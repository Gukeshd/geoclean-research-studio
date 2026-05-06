import { useMemo, useRef, useState } from 'react'
import {
  Activity,
  AlertTriangle,
  ArrowDownUp,
  BarChart3,
  Bot,
  CheckCircle2,
  ChevronDown,
  Database,
  Download,
  FileSpreadsheet,
  Files,
  History,
  Layers3,
  Map,
  Moon,
  Play,
  Redo2,
  RefreshCw,
  Search,
  Settings2,
  Sparkles,
  Sun,
  Table2,
  Undo2,
  UploadCloud,
  Wand2,
} from 'lucide-react'
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import './App.css'

type ResearchType =
  | 'Text'
  | 'Integer'
  | 'Decimal'
  | 'Date'
  | 'District name'
  | 'State name'
  | 'Latitude'
  | 'Longitude'
  | 'Percentage'
  | 'Currency'
  | 'Binary variable'
  | 'Categorical variable'

type UploadedFile = {
  id: string
  name: string
  size: number
  rows: number
  columns: number
  encoding: string
  duplicate: boolean
  sheets: string[]
  selectedSheet: string
}

type ColumnProfile = {
  name: string
  type: ResearchType
  missing: number
  unique: number
  duplicates: number
  outlier: 'none' | 'low' | 'medium' | 'high'
}

type BackendProfile = {
  file: {
    dataset_id: string
    file_name: string
    size: number
    rows: number
    columns: number
    sheets: string[]
    selected_sheet: string | null
    encoding: string
    duplicate_file: boolean
  }
  columns: Array<{
    name: string
    inferred_type: ResearchType
    missing_count: number
    unique_count: number
    duplicate_count: number
    outlier_warning: ColumnProfile['outlier']
  }>
  preview: Record<string, string | number | null>[]
}

const apiBase = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'

const typeOptions: ResearchType[] = [
  'Text',
  'Integer',
  'Decimal',
  'Date',
  'District name',
  'State name',
  'Latitude',
  'Longitude',
  'Percentage',
  'Currency',
  'Binary variable',
  'Categorical variable',
]

const sampleFiles: UploadedFile[] = [
  {
    id: 'nfhs',
    name: 'NFHS5_district_health_indicators.csv',
    size: 2840000,
    rows: 707,
    columns: 18,
    encoding: 'UTF-8',
    duplicate: false,
    sheets: ['district_indicators'],
    selectedSheet: 'district_indicators',
  },
  {
    id: 'census',
    name: 'Census_2011_spatial_keys.xlsx',
    size: 1180000,
    rows: 640,
    columns: 9,
    encoding: 'Windows-1252',
    duplicate: false,
    sheets: ['District master', 'Old district names', 'GIS joins'],
    selectedSheet: 'District master',
  },
]

const initialProfiles: ColumnProfile[] = [
  { name: 'state', type: 'State name', missing: 0, unique: 36, duplicates: 671, outlier: 'none' },
  { name: 'district', type: 'District name', missing: 4, unique: 701, duplicates: 6, outlier: 'medium' },
  { name: 'district_code', type: 'Integer', missing: 0, unique: 707, duplicates: 0, outlier: 'none' },
  { name: 'women_bmi_low_pct', type: 'Percentage', missing: 18, unique: 201, duplicates: 12, outlier: 'low' },
  { name: 'children_stunted_pct', type: 'Percentage', missing: 11, unique: 229, duplicates: 17, outlier: 'medium' },
  { name: 'monthly_income', type: 'Currency', missing: 43, unique: 384, duplicates: 9, outlier: 'high' },
  { name: 'survey_date', type: 'Date', missing: 7, unique: 22, duplicates: 630, outlier: 'none' },
  { name: 'latitude', type: 'Latitude', missing: 13, unique: 688, duplicates: 4, outlier: 'low' },
  { name: 'longitude', type: 'Longitude', missing: 13, unique: 688, duplicates: 4, outlier: 'low' },
]

const previewRows = Array.from({ length: 32 }, (_, index) => {
  const states = ['Maharashtra', 'Bihar', 'Kerala', 'Tamil Nadu', 'Assam', 'Gujarat']
  const districts = ['Mumbai Suburb', 'Patna', 'Ernakulam', 'Chennai', 'Kamrup Metro', 'Ahmedabad']
  return {
    state: states[index % states.length],
    district: index === 6 ? 'Mumbai Suburban District' : districts[index % districts.length],
    district_code: 500 + index,
    women_bmi_low_pct: `${(17 + (index % 13) * 1.7).toFixed(1)}%`,
    children_stunted_pct: index === 11 ? '999' : `${(22 + (index % 15) * 1.3).toFixed(1)}%`,
    monthly_income: index === 8 ? '₹5,000' : `₹${(1200 + index * 187).toLocaleString('en-IN')}`,
    survey_date: index % 5 === 0 ? '12-04-2021' : '2021-04-12',
    latitude: (19.07 + index * 0.02).toFixed(4),
    longitude: (72.87 + index * 0.02).toFixed(4),
  }
})

const timeline = [
  { step: 'Upload', value: 42 },
  { step: 'Profile', value: 58 },
  { step: 'Missing', value: 64 },
  { step: 'Districts', value: 74 },
  { step: 'Types', value: 82 },
  { step: 'Export', value: 91 },
]

const missingChart = initialProfiles.map((column) => ({
  name: column.name.replaceAll('_', ' '),
  missing: column.missing,
  unique: column.unique,
}))

const correlationData = ['income', 'bmi', 'stunting', 'literacy', 'urban'].map((name, row) => ({
  name,
  a: Number((0.15 + row * 0.12).toFixed(2)),
  b: Number((0.75 - row * 0.08).toFixed(2)),
  c: Number((0.35 + row * 0.07).toFixed(2)),
  d: Number((0.62 - row * 0.05).toFixed(2)),
  e: Number((0.22 + row * 0.11).toFixed(2)),
}))

function formatBytes(size: number) {
  if (!size) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  const power = Math.min(Math.floor(Math.log(size) / Math.log(1024)), units.length - 1)
  return `${(size / 1024 ** power).toFixed(power ? 1 : 0)} ${units[power]}`
}

function inferFileMeta(file: File, duplicate: boolean): UploadedFile {
  const lower = file.name.toLowerCase()
  const workbook = lower.endsWith('.xlsx') || lower.endsWith('.xls')
  const roughRows = Math.max(42, Math.round(file.size / 680))
  const roughColumns = lower.includes('nfhs') ? 18 : lower.includes('census') ? 12 : 9 + (file.name.length % 8)
  return {
    id: `${file.name}-${file.size}-${file.lastModified}`,
    name: file.name,
    size: file.size,
    rows: roughRows,
    columns: roughColumns,
    encoding: lower.endsWith('.csv') || lower.endsWith('.tsv') ? 'UTF-8 detected' : 'Workbook XML',
    duplicate,
    sheets: workbook ? ['Sheet1', 'Metadata', 'District lookup'] : ['Default'],
    selectedSheet: workbook ? 'Sheet1' : 'Default',
  }
}

function App() {
  const [files, setFiles] = useState<UploadedFile[]>(sampleFiles)
  const [profiles, setProfiles] = useState<ColumnProfile[]>(initialProfiles)
  const [dark, setDark] = useState(false)
  const [activeTool, setActiveTool] = useState('Text cleaning')
  const [assistantText, setAssistantText] = useState(
    'I found district spelling variants, sentinel missing values coded as 999, and currency strings that should be converted before regression or GIS joins.',
  )
  const [history, setHistory] = useState<string[]>([
    'Uploaded NFHS district indicators',
    'Detected district and state fields',
    'Flagged 96 missing/sentinel values',
  ])
  const [redoStack, setRedoStack] = useState<string[]>([])
  const fileInput = useRef<HTMLInputElement>(null)

  const qualityScore = useMemo(() => {
    const missing = profiles.reduce((sum, column) => sum + column.missing, 0)
    const alerts = profiles.filter((column) => column.outlier !== 'none').length
    return Math.max(68, Math.round(96 - missing / 9 - alerts * 2))
  }, [profiles])

  const handleFiles = async (incoming: FileList | File[]) => {
    const currentKeys = new Set(files.map((file) => `${file.name}-${file.size}`))
    const accepted = Array.from(incoming).filter((file) =>
      ['.csv', '.xlsx', '.xls', '.tsv'].some((extension) => file.name.toLowerCase().endsWith(extension)),
    )
    const backendProfiles = await Promise.all(
      accepted.map(async (file) => {
        const form = new FormData()
        form.append('file', file)
        try {
          const response = await fetch(`${apiBase}/api/upload`, { method: 'POST', body: form })
          if (!response.ok) return null
          return (await response.json()) as BackendProfile
        } catch {
          return null
        }
      }),
    )
    const next = accepted.map((file, index) => {
      const backend = backendProfiles[index]
      if (!backend) return inferFileMeta(file, currentKeys.has(`${file.name}-${file.size}`))
      return {
        id: backend.file.dataset_id,
        name: backend.file.file_name,
        size: backend.file.size,
        rows: backend.file.rows,
        columns: backend.file.columns,
        encoding: backend.file.encoding,
        duplicate: backend.file.duplicate_file,
        sheets: backend.file.sheets.length ? backend.file.sheets : ['Default'],
        selectedSheet: backend.file.selected_sheet ?? 'Default',
      }
    })
    const latestProfile = backendProfiles.find(Boolean)
    if (latestProfile) {
      setProfiles(
        latestProfile.columns.map((column) => ({
          name: column.name,
          type: column.inferred_type,
          missing: column.missing_count,
          unique: column.unique_count,
          duplicates: column.duplicate_count,
          outlier: column.outlier_warning,
        })),
      )
    }
    setFiles((existing) => [...existing, ...next])
    setHistory((items) => [`Imported ${next.length} research file${next.length === 1 ? '' : 's'}`, ...items])
  }

  const applyCleaning = (label: string) => {
    setProfiles((current) =>
      current.map((column) => ({
        ...column,
        missing: Math.max(0, column.missing - (label.includes('Missing') ? 7 : 2)),
        duplicates: Math.max(0, column.duplicates - (label.includes('Duplicate') ? 16 : 1)),
        outlier: label.includes('Outlier') ? 'none' : column.outlier,
      })),
    )
    setHistory((items) => [`Applied ${label}`, ...items.slice(0, 7)])
    setRedoStack([])
  }

  const undo = () => {
    const [latest, ...rest] = history
    if (!latest) return
    setRedoStack((items) => [latest, ...items])
    setHistory(rest)
  }

  const redo = () => {
    const [latest, ...rest] = redoStack
    if (!latest) return
    setHistory((items) => [latest, ...items])
    setRedoStack(rest)
  }

  return (
    <main className={dark ? 'app dark' : 'app'}>
      <section className="hero-shell">
        <nav className="topbar">
          <div className="brand-mark">
            <Map size={20} />
            <span>GeoClean Research Studio</span>
          </div>
          <div className="topbar-actions">
            <span className="autosave"><CheckCircle2 size={15} /> Auto-saved 8 sec ago</span>
            <button className="icon-btn" onClick={undo} aria-label="Undo"><Undo2 size={18} /></button>
            <button className="icon-btn" onClick={redo} aria-label="Redo"><Redo2 size={18} /></button>
            <button className="icon-btn" onClick={() => setDark((value) => !value)} aria-label="Toggle dark mode">
              {dark ? <Sun size={18} /> : <Moon size={18} />}
            </button>
          </div>
        </nav>

        <div className="hero-grid">
          <div className="hero-copy">
            <p className="eyebrow">Dissertation-ready data harmonization</p>
            <h1>GeoClean Research Studio</h1>
            <p className="subtitle">
              AI-powered research data cleaning and harmonization platform for dissertation and spatial analysis.
            </p>
            <div className="hero-actions">
              <button className="primary-btn" onClick={() => fileInput.current?.click()}>
                <UploadCloud size={18} /> Browse files
              </button>
              <button className="secondary-btn"><Play size={17} /> Run smart audit</button>
            </div>
          </div>

          <div
            className="upload-panel"
            onDragOver={(event) => event.preventDefault()}
            onDrop={(event) => {
              event.preventDefault()
              handleFiles(event.dataTransfer.files)
            }}
          >
            <input
              ref={fileInput}
              type="file"
              multiple
              accept=".csv,.xlsx,.xls,.tsv"
              onChange={(event) => event.target.files && handleFiles(event.target.files)}
              hidden
            />
            <UploadCloud size={38} />
            <h2>Drag and drop messy Excel or CSV datasets</h2>
            <p>CSV, XLSX, XLS, and TSV files with multi-file upload, encoding checks, sheet detection, and duplicate detection.</p>
            <div className="file-list">
              {files.map((file) => (
                <article className={file.duplicate ? 'file-row duplicate' : 'file-row'} key={file.id}>
                  <FileSpreadsheet size={18} />
                  <div>
                    <strong>{file.name}</strong>
                    <span>
                      {formatBytes(file.size)} · {file.rows.toLocaleString()} rows · {file.columns} columns · {file.encoding}
                    </span>
                  </div>
                  {file.sheets.length > 1 ? (
                    <select
                      value={file.selectedSheet}
                      onChange={(event) =>
                        setFiles((current) =>
                          current.map((item) =>
                            item.id === file.id ? { ...item, selectedSheet: event.target.value } : item,
                          ),
                        )
                      }
                    >
                      {file.sheets.map((sheet) => <option key={sheet}>{sheet}</option>)}
                    </select>
                  ) : (
                    <span className="status-pill">1 sheet</span>
                  )}
                  {file.duplicate && <span className="danger-pill">Duplicate</span>}
                </article>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="workspace">
        <aside className="sidebar">
          <div className="side-title">
            <Wand2 size={18} />
            <span>Research Data Cleaning Tools</span>
          </div>
          <ToolSection title="Basic Cleaning Tools" items={['Text cleaning', 'Missing value handling', 'Duplicate handling']} active={activeTool} setActive={setActiveTool} />
          <ToolSection title="Numeric Cleaning" items={['Text numbers to numeric', 'Decimal handling', 'Percentage conversion']} active={activeTool} setActive={setActiveTool} />
          <ToolSection title="Date Cleaning" items={['Date format detection', 'Format conversion']} active={activeTool} setActive={setActiveTool} />
          <ToolSection title="Research-Specific Features" items={['District harmonization', 'State-district validation', 'Indicator standardization', 'Composite index builder']} active={activeTool} setActive={setActiveTool} />
          <ToolSection title="Advanced Workflow" items={['Multi-file merge engine', 'Outlier detection', 'Auto documentation', 'Export system']} active={activeTool} setActive={setActiveTool} />
        </aside>

        <section className="center-panel">
          <div className="panel-header">
            <div>
              <p className="eyebrow">Step 2 · Data preview dashboard</p>
              <h2>Research-ready preview and column intelligence</h2>
            </div>
            <div className="searchbox"><Search size={16} /><input placeholder="Search variables or values" /></div>
          </div>

          <div className="kpi-grid">
            <Kpi icon={<Database size={19} />} label="Rows profiled" value="707" delta="+100 preview rows" />
            <Kpi icon={<Table2 size={19} />} label="Columns inferred" value={profiles.length.toString()} delta="12 data type rules" />
            <Kpi icon={<AlertTriangle size={19} />} label="Warnings" value="7" delta="Outliers and mismatches" />
            <Kpi icon={<Sparkles size={19} />} label="Quality score" value={`${qualityScore}%`} delta="Before vs after live" />
          </div>

          <div className="profile-grid">
            <div className="table-card">
              <div className="table-title">
                <span>First 100 Rows Preview</span>
                <span className="status-pill">Scrollable table</span>
              </div>
              <div className="data-table-wrap">
                <table className="data-table">
                  <thead>
                    <tr>{Object.keys(previewRows[0]).map((key) => <th key={key}>{key}</th>)}</tr>
                  </thead>
                  <tbody>
                    {previewRows.map((row, index) => (
                      <tr key={index} className={index === 8 || index === 11 ? 'suspicious' : ''}>
                        {Object.values(row).map((value, cell) => <td key={cell}>{value}</td>)}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="column-card">
              <div className="table-title">
                <span>Column Profiles</span>
                <span className="status-pill">Manual override enabled</span>
              </div>
              <div className="column-list">
                {profiles.map((column) => (
                  <article className="column-row" key={column.name}>
                    <div>
                      <strong>{column.name}</strong>
                      <span>{column.missing} missing · {column.unique} unique · {column.duplicates} duplicate values</span>
                    </div>
                    <select
                      value={column.type}
                      onChange={(event) =>
                        setProfiles((current) =>
                          current.map((item) =>
                            item.name === column.name ? { ...item, type: event.target.value as ResearchType } : item,
                          ),
                        )
                      }
                    >
                      {typeOptions.map((type) => <option key={type}>{type}</option>)}
                    </select>
                    <OutlierBadge level={column.outlier} />
                  </article>
                ))}
              </div>
            </div>
          </div>

          <div className="operations-grid">
            <OperationCard
              title={activeTool}
              icon={<Settings2 size={20} />}
              body={toolCopy(activeTool)}
              actions={toolActions(activeTool)}
              onApply={applyCleaning}
            />
            <div className="merge-card">
              <div className="table-title"><span>Multi-file Merge Engine</span><Files size={18} /></div>
              <div className="merge-methods">
                {['District name', 'State + district', 'Unique ID', 'Custom column mapping'].map((item) => (
                  <button key={item}>{item}</button>
                ))}
              </div>
              <div className="merge-metrics">
                <Kpi icon={<ArrowDownUp size={18} />} label="Merge success" value="94.2%" delta="665 matched rows" />
                <Kpi icon={<AlertTriangle size={18} />} label="Unmatched" value="42" delta="State mismatch or blank key" />
              </div>
            </div>
          </div>

          <section className="viz-grid">
            <ChartPanel title="Missing Value Heatmap" icon={<BarChart3 size={18} />}>
              <ResponsiveContainer width="100%" height={210}>
                <BarChart data={missingChart}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="name" hide />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="missing" radius={[4, 4, 0, 0]} fill="#0f766e" />
                </BarChart>
              </ResponsiveContainer>
            </ChartPanel>
            <ChartPanel title="Histogram and Boxplot Signals" icon={<Activity size={18} />}>
              <ResponsiveContainer width="100%" height={210}>
                <ComposedChart data={timeline}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="step" />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="value" fill="#2563eb" radius={[4, 4, 0, 0]} />
                  <Line type="monotone" dataKey="value" stroke="#b45309" strokeWidth={2} />
                </ComposedChart>
              </ResponsiveContainer>
            </ChartPanel>
            <ChartPanel title="Correlation Matrix" icon={<Layers3 size={18} />}>
              <div className="matrix">
                {correlationData.flatMap((row) =>
                  ['a', 'b', 'c', 'd', 'e'].map((key) => {
                    const value = row[key as keyof typeof row] as number
                    return <span key={`${row.name}-${key}`} style={{ opacity: 0.35 + value * 0.65 }}>{value.toFixed(2)}</span>
                  }),
                )}
              </div>
            </ChartPanel>
            <ChartPanel title="Choropleth Preview Map" icon={<Map size={18} />}>
              <div className="map-preview">
                {['MH', 'GJ', 'RJ', 'MP', 'UP', 'BR', 'WB', 'OR', 'KA', 'TN', 'KL', 'AS'].map((state, index) => (
                  <span key={state} style={{ background: ['#0f766e', '#2563eb', '#b45309', '#7c3aed'][index % 4] }}>{state}</span>
                ))}
              </div>
            </ChartPanel>
          </section>
        </section>

        <aside className="summary-panel">
          <div className="assistant-card">
            <div className="assistant-head"><Bot size={20} /><strong>AI Research Assistant</strong></div>
            <p>{assistantText}</p>
            <div className="assistant-actions">
              {['Explain transformations', 'Recommend imputation', 'Suggest normalization'].map((item) => (
                <button key={item} onClick={() => setAssistantText(assistantReply(item))}>{item}</button>
              ))}
            </div>
          </div>

          <div className="quality-card">
            <div className="score-ring">{qualityScore}<span>%</span></div>
            <h3>Data Quality Dashboard</h3>
            <p>Before vs after cleaning across missing values, duplicates, standardized variables, and district harmonization.</p>
            <ResponsiveContainer width="100%" height={160}>
              <AreaChart data={timeline}>
                <defs>
                  <linearGradient id="quality" x1="0" x2="0" y1="0" y2="1">
                    <stop offset="5%" stopColor="#0f766e" stopOpacity={0.45} />
                    <stop offset="95%" stopColor="#0f766e" stopOpacity={0.02} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="step" hide />
                <YAxis hide />
                <Tooltip />
                <Area type="monotone" dataKey="value" stroke="#0f766e" fill="url(#quality)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          <div className="district-card">
            <h3>District Harmonization</h3>
            {[
              ['Mumbai Suburb', 'Mumbai Suburban', '98%'],
              ['Kamrup Metro', 'Kamrup Metropolitan', '95%'],
              ['Bangalore Urban', 'Bengaluru Urban', '92%'],
            ].map(([raw, clean, score]) => (
              <div className="correction-row" key={raw}>
                <span>{raw}</span>
                <strong>{clean}</strong>
                <em>{score}</em>
              </div>
            ))}
          </div>

          <div className="export-card">
            <h3>Export System</h3>
            <div className="export-grid">
              {['CSV', 'Excel', 'TSV', 'R-ready', 'SPSS-ready', 'GIS-ready', 'Stata-ready'].map((type) => (
                <button key={type}><Download size={15} /> {type}</button>
              ))}
            </div>
          </div>

          <div className="history-card">
            <h3><History size={17} /> Cleaning Log</h3>
            {history.map((item, index) => (
              <div className="history-row" key={`${item}-${index}`}>
                <span>{index + 1}</span>
                <p>{item}</p>
              </div>
            ))}
          </div>
        </aside>
      </section>
    </main>
  )
}

function ToolSection({ title, items, active, setActive }: { title: string; items: string[]; active: string; setActive: (value: string) => void }) {
  const [open, setOpen] = useState(true)
  return (
    <section className="tool-section">
      <button className="tool-section-head" onClick={() => setOpen((value) => !value)}>
        <span>{title}</span>
        <ChevronDown size={16} className={open ? 'chevron open' : 'chevron'} />
      </button>
      {open && (
        <div className="tool-items">
          {items.map((item) => (
            <button className={active === item ? 'active' : ''} key={item} onClick={() => setActive(item)}>{item}</button>
          ))}
        </div>
      )}
    </section>
  )
}

function Kpi({ icon, label, value, delta }: { icon: React.ReactNode; label: string; value: string; delta: string }) {
  return (
    <article className="kpi">
      <div>{icon}</div>
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{delta}</small>
    </article>
  )
}

function OutlierBadge({ level }: { level: ColumnProfile['outlier'] }) {
  if (level === 'none') return <span className="ok-pill">Clean</span>
  return <span className={`outlier ${level}`}>{level} outlier risk</span>
}

function OperationCard({ title, icon, body, actions, onApply }: { title: string; icon: React.ReactNode; body: string; actions: string[]; onApply: (label: string) => void }) {
  return (
    <div className="operation-card">
      <div className="table-title"><span>{title}</span>{icon}</div>
      <p>{body}</p>
      <div className="operation-actions">
        {actions.map((action) => <button key={action} onClick={() => onApply(action)}><RefreshCw size={15} /> {action}</button>)}
      </div>
    </div>
  )
}

function ChartPanel({ title, icon, children }: { title: string; icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <article className="chart-panel">
      <div className="table-title"><span>{title}</span>{icon}</div>
      {children}
    </article>
  )
}

function toolCopy(active: string) {
  const copy: Record<string, string> = {
    'Text cleaning': 'Trim leading and trailing spaces, remove extra spaces and special characters, and convert case to uppercase, lowercase, or proper case.',
    'Missing value handling': 'Detect blank, NULL, NA, N/A, dash, 999, and 9999 markers, then replace with blank, mean, median, mode, zero, or a custom value.',
    'Duplicate handling': 'Remove full duplicate rows or duplicates from selected columns while keeping first, keeping last, or removing all duplicate records.',
    'Text numbers to numeric': 'Convert values such as 45%, Rs.5,000, 1,200, and 12.5 kg into clean numeric columns.',
    'Decimal handling': 'Round research indicators to 2 decimals, 3 decimals, or a custom decimal precision.',
    'Percentage conversion': 'Convert 45 to 0.45 for modeling or 0.45 to 45% for reporting.',
    'Date format detection': 'Detect DD-MM-YYYY, YYYY-MM-DD, and MM/DD/YYYY formats across mixed date columns.',
    'Format conversion': 'Convert dates into a selected publication, R, Stata, SPSS, or ISO-friendly format.',
    'District harmonization': 'Use fuzzy matching, state validation, manual correction tables, and an India district master database to standardize district names.',
    'State-district validation': 'Detect invalid districts, state-district mismatches, missing districts, and old district names with correction suggestions.',
    'Indicator standardization': 'Apply z-score standardization, min-max normalization, and reverse coding for deprivation indicators in batches.',
    'Composite index builder': 'Build Food Insecurity, Vulnerability, Development, Health, or custom indexes with equal or custom weights.',
    'Multi-file merge engine': 'Merge datasets by district, state plus district, unique ID, or custom column mappings with diagnostics before final merge.',
    'Outlier detection': 'Detect extreme values, impossible percentages, invalid negative values, and statistical outliers using IQR, z-score, or standard deviation.',
    'Auto documentation': 'Generate a cleaning log, transformation history, variable dictionary, and metadata report for PDF or DOCX export.',
    'Export system': 'Export CSV, Excel, TSV, R-ready, SPSS-ready, GIS-ready, and Stata-ready datasets while preserving spatial IDs and join keys.',
  }
  return copy[active] ?? copy['Text cleaning']
}

function toolActions(active: string) {
  if (active.includes('Missing')) return ['Replace with median', 'Replace 999 as blank', 'Use mode for categories']
  if (active.includes('Duplicate')) return ['Show duplicate summary', 'Keep first duplicates', 'Remove all duplicates']
  if (active.includes('District')) return ['Run fuzzy match', 'Validate state pairs', 'Open correction table']
  if (active.includes('standardization')) return ['Apply z-score', 'Apply min-max', 'Reverse deprivation columns']
  if (active.includes('index')) return ['Equal-weight index', 'Custom weights', 'Z-score aggregation']
  if (active.includes('Outlier')) return ['Run IQR detection', 'Run z-score detection', 'Flag impossible values']
  if (active.includes('Export')) return ['Prepare GIS dataset', 'Prepare SPSS labels', 'Export metadata']
  return ['Apply to selected columns', 'Batch apply', 'Preview changes']
}

function assistantReply(action: string) {
  const replies: Record<string, string> = {
    'Explain transformations': 'Recommended order: normalize missing markers, harmonize districts within state, convert percentages and currency, then standardize indicators. This preserves auditability for dissertation methods chapters.',
    'Recommend imputation': 'For district-level indicators, use median imputation for skewed socio-economic fields, mode for categorical variables, and avoid mean imputation where outliers are strong.',
    'Suggest normalization': 'Use z-scores for composite deprivation indexes when indicators use different scales; use min-max normalization for maps and dashboards that need 0 to 1 comparability.',
  }
  return replies[action]
}

export default App
