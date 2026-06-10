import React from 'react';
import { render, screen } from '@testing-library/react';
import BatchReportLegend from '../BatchReportLegend';

describe('BatchReportLegend', () => {
  it('explains color key and header metrics', () => {
    render(<BatchReportLegend />);

    expect(screen.getByText(/Color key:/i)).toBeInTheDocument();
    expect(screen.getByText('green')).toBeInTheDocument();
    expect(screen.getByText('red')).toBeInTheDocument();
    expect(screen.getByText('amber')).toBeInTheDocument();
    expect(screen.getByText(/Hover/i)).toBeInTheDocument();
    expect(screen.getByText(/icons on metrics for definitions/i)).toBeInTheDocument();
  });
});
