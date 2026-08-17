
export type KpiItem = {
  id?: number
  templateName: string
  weight: number
  target?: string
}

type Props = {
  frameworkName?: string
  items?: KpiItem[]
}

export default function KpiFrameworkEditor({ frameworkName, items = [] }: Props) {
  if (!frameworkName) return <div>No framework selected</div>
  return (
    <div>
      <h2>{frameworkName}</h2>
      <table>
        <thead>
          <tr>
            <th>Template</th>
            <th>Weight</th>
            <th>Target</th>
          </tr>
        </thead>
        <tbody>
          {items.map((it, idx) => (
            <tr key={it.id ?? idx}>
              <td>{it.templateName}</td>
              <td>{it.weight}</td>
              <td>{it.target}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
