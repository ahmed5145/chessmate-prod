import React from 'react';
import { render, screen } from '@testing-library/react';
import MetricInfoIcon from '../MetricInfoIcon';

describe('MetricInfoIcon', () => {
  it('renders accessible info control for a metric key', () => {
    render(<MetricInfoIcon metricKey="move_match" />);
    expect(screen.getByLabelText('Metric definition')).toBeInTheDocument();
  });

  it('renders nothing when no metric keys provided', () => {
    const { container } = render(<MetricInfoIcon />);
    expect(container).toBeEmptyDOMElement();
  });
});
