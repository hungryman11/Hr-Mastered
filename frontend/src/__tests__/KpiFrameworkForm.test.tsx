import { render, screen, within, fireEvent } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import KpiFrameworkForm from '../pages/KpiFrameworkForm'
import { MemoryRouter } from 'react-router-dom'
import { ToastProvider } from '../contexts/ToastContext'

describe('KpiFrameworkForm', () => {
  it('renders framework editor and sample button', () => {
    render(<MemoryRouter><ToastProvider><KpiFrameworkForm /></ToastProvider></MemoryRouter>)
    expect(screen.getByText(/Configuration \(JSON\)/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Save/i })).toBeInTheDocument()
  })

  it('disables Save when JSON is invalid and shows an error', async () => {
    const { container } = render(<MemoryRouter><ToastProvider><KpiFrameworkForm /></ToastProvider></MemoryRouter>)
    const textarea = container.querySelector('textarea') as HTMLTextAreaElement
    const { getByRole } = within(container)
    const saveBtn = getByRole('button', { name: /Save/i }) as HTMLButtonElement

    // Enter invalid JSON
    await fireEvent.change(textarea!, { target: { value: '{ invalid: json,' } })
    expect(saveBtn).toBeDisabled()
    // Error message displayed
    expect(screen.getByText(/invalid|unexpected|Unexpected|Invalid JSON/i)).toBeTruthy()
  })

  it('inserts sample configuration and enables Save', async () => {
    render(<MemoryRouter><ToastProvider><KpiFrameworkForm /></ToastProvider></MemoryRouter>)
    const { container } = render(<MemoryRouter><ToastProvider><KpiFrameworkForm /></ToastProvider></MemoryRouter>)
    const { getByText, getByRole } = within(container)
    const insertBtn = getByText(/Insert sample/i)
    const saveBtn = getByRole('button', { name: /Save/i }) as HTMLButtonElement

    // Click Insert sample
    await fireEvent.click(insertBtn)

    // Save should be enabled (no json error)
    expect(saveBtn).not.toBeDisabled()

    // Textarea contains the sample template placeholder
    const textarea = container.querySelector('textarea') as HTMLTextAreaElement
    expect(textarea?.value).toMatch(/<template-uuid-1>/i)
  })
})
