import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import KpiFrameworkEditorForm from '../pages/KpiFrameworkEditorForm'
import axios from 'axios'

vi.mock('axios')

const mocked = axios as unknown as { get: any; post: any; delete: any }

test('renders editor and saves items', async () => {
  mocked.get.mockImplementation((url:string, opts:any) => {
    if (url.includes('/api/kpi-frameworks/')) return Promise.resolve({ data: { items: [] } })
    if (url.includes('/api/kpi-framework-items/')) return Promise.resolve({ data: [] })
    if (url.includes('/api/kpi-templates/')) return Promise.resolve({ data: [{ id: 1, uuid: 't1', name: 'Sales' }] })
    return Promise.resolve({ data: {} })
  })
  mocked.post = vi.fn().mockResolvedValue({ data: {} })
  mocked.delete = vi.fn().mockResolvedValue({})

  render(<KpiFrameworkEditorForm frameworkUuid="abc-123" />)
  expect(await screen.findByText('Framework Editor')).toBeInTheDocument()
  fireEvent.click(screen.getByText('Add'))
  const select = await screen.findByRole('combobox')
  // choose template id 1
  fireEvent.change(select, { target: { value: '1' } })
  // weight input is type=number so it's a spinbutton
  const weightInputs = await screen.findAllByRole('spinbutton')
  fireEvent.change(weightInputs[0], { target: { value: '50' } })
  fireEvent.click(screen.getByText('Save'))
  await waitFor(() => expect(screen.getByText(/Total weight must sum to 100/)).toBeInTheDocument())
  // now set weight to 100 and save
  fireEvent.change(weightInputs[0], { target: { value: '100' } })
  fireEvent.click(screen.getByText('Save'))
  await waitFor(() => expect(mocked.post).toHaveBeenCalled())
})
