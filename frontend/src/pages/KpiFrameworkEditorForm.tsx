import { useEffect, useState } from 'react'
import axios from 'axios'

export type Item = {
  id?: number
  templateId?: number
  templateName?: string
  weight: number
  target?: string
}

type Props = {
  frameworkUuid: string
}

export default function KpiFrameworkEditorForm({ frameworkUuid }: Props) {
  const [items, setItems] = useState<Item[]>([])
  const [templates, setTemplates] = useState<Array<any>>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!frameworkUuid) return
    setLoading(true)
    Promise.all([
      axios.get('/api/kpi-templates/'),
      axios.get(`/api/kpi-frameworks/${frameworkUuid}/`),
      axios.get('/api/kpi-framework-items/', { params: { framework: frameworkUuid } }),
    ]).then(([templatesRes, , itemsRes]) => {
      const templateRows: any[] = Array.isArray(templatesRes.data) ? templatesRes.data : []
      const itemRows: any[] = Array.isArray(itemsRes.data) ? itemsRes.data : []
      setTemplates(templateRows)
      const tplMap: Record<number, string> = {}
      templateRows.forEach((t:any) => { tplMap[t.id] = t.name })
      setItems(itemRows.map((it:any) => ({ id: it.id, templateId: it.template, templateName: tplMap[it.template] || String(it.template), weight: Number(it.weight), target: it.target })))
      setLoading(false)
    }).catch(() => { setError('Failed to load framework or templates'); setLoading(false) })
  }, [frameworkUuid])

  function addRow() {
    setItems(s => [...s, { templateId: undefined, templateName: '', weight: 0, target: '' }])
  }

  function update(idx: number, patch: Partial<Item>) {
    setItems(s => s.map((it, i) => i === idx ? { ...it, ...patch } : it))
  }

  function remove(idx: number) {
    setItems(s => s.filter((_, i) => i !== idx))
  }

  async function save() {
    setLoading(true)
    setError(null)
    try {
      const total = items.reduce((s, it) => s + Number(it.weight || 0), 0)
      if (Math.abs(total - 100) > 0.01) {
        setError(`Total weight must sum to 100. Current total: ${total}`)
        setLoading(false)
        return
      }

      const existingRes = await axios.get('/api/kpi-framework-items/', { params: { framework: frameworkUuid } })
      const existing: any[] = existingRes.data || []
      const existingMap: Record<number, any> = {}
      existing.forEach(e => existingMap[e.id] = e)

      // Determine deletes
      const currentIds = new Set(items.filter(it => it.id).map(it => it.id as number))
      const toDelete = existing.filter(e => !currentIds.has(e.id))

      // Determine creates and updates
      const toCreate: any[] = []
      const toUpdate: any[] = []
      items.forEach((it) => {
        const payload = { framework: frameworkUuid, template: it.templateId ?? it.templateName, weight: it.weight, target: it.target }
        if (it.id) {
          // compare with existing
          const orig = existingMap[it.id]
          if (!orig) return
          if (String(orig.template) !== String(it.templateId) || Number(orig.weight) !== Number(it.weight) || (orig.target || '') !== (it.target || '')) {
            toUpdate.push({ id: it.id, payload })
          }
        } else {
          toCreate.push(payload)
        }
      })

      // Apply deletes
      for (const d of toDelete) {
        await axios.delete(`/api/kpi-framework-items/${d.id}/`)
      }
      // Apply updates
      for (const u of toUpdate) {
        await axios.patch(`/api/kpi-framework-items/${u.id}/`, u.payload)
      }
      // Apply creates
      for (const c of toCreate) {
        await axios.post('/api/kpi-framework-items/', c)
      }
    } catch (e:any) {
      setError(e?.response?.data || 'Save failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h3>Framework Editor</h3>
      {error && <div style={{ color: 'red' }}>{String(error)}</div>}
      {loading && <div>Loading...</div>}
      <table>
        <thead>
          <tr><th>Template</th><th>Weight</th><th>Target</th><th></th></tr>
        </thead>
        <tbody>
          {items.map((it, idx) => (
            <tr key={idx}>
              <td>
                <select value={it.templateId ?? ''} onChange={e => update(idx, { templateId: e.target.value ? Number(e.target.value) : undefined, templateName: templates.find(t => String(t.id) === e.target.value)?.name })}>
                  <option value="">-- select template --</option>
                  {templates.map((t:any) => <option key={t.id} value={t.id}>{t.name}</option>)}
                </select>
              </td>
              <td><input type="number" value={it.weight} onChange={e => update(idx, { weight: Number(e.target.value) })} /></td>
              <td><input value={it.target || ''} onChange={e => update(idx, { target: e.target.value })} /></td>
              <td><button onClick={() => remove(idx)}>Remove</button></td>
            </tr>
          ))}
        </tbody>
      </table>
      <button onClick={addRow}>Add</button>
      <button onClick={save} disabled={loading}>Save</button>
    </div>
  )
}
