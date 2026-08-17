import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import KpiTemplateForm from '../pages/KpiTemplateForm'
import { MemoryRouter } from 'react-router-dom'
import { ToastProvider } from '../contexts/ToastContext'

describe('KpiTemplateForm', () => {
  it('renders form fields', () => {
    render(<MemoryRouter><ToastProvider><KpiTemplateForm /></ToastProvider></MemoryRouter>)
    expect(screen.getByLabelText(/Name/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/Measurement Type/i)).toBeInTheDocument()
  })
})
