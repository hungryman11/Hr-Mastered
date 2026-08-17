import React from 'react'
import { render, screen } from '@testing-library/react'
import KpiFrameworkEditor from '../pages/KpiFrameworkEditor'

test('renders no framework message when none provided', () => {
  render(<KpiFrameworkEditor />)
  expect(screen.getByText('No framework selected')).toBeInTheDocument()
})

test('renders framework name and items', () => {
  const items = [
    { id: 1, templateName: 'Sales', weight: 60, target: '100' },
    { id: 2, templateName: 'CSAT', weight: 40, target: '90' },
  ]
  render(<KpiFrameworkEditor frameworkName="Sales Framework" items={items} />)
  expect(screen.getByText('Sales Framework')).toBeInTheDocument()
  expect(screen.getByText('Sales')).toBeInTheDocument()
  expect(screen.getByText('CSAT')).toBeInTheDocument()
})
