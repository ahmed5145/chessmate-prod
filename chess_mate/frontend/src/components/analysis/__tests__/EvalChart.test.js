import React from 'react';
import { render, screen } from '@testing-library/react';
import EvalChart from '../EvalChart';

jest.mock('../../../context/ThemeContext', () => ({
  useTheme: () => ({ isDarkMode: false }),
}));

jest.mock('react-chartjs-2', () => ({
  Line: ({ data }) => (
    <div data-testid="eval-chart">{data?.labels?.length || 0} points</div>
  ),
}));

describe('EvalChart', () => {
  it('renders nothing when points are empty', () => {
    const { container } = render(<EvalChart points={[]} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('renders chart for eval points', () => {
    render(
      <EvalChart
        points={[
          { label: 1, value: 0.2 },
          { label: 2, value: -0.4 },
        ]}
        selectedIndex={1}
      />
    );

    expect(screen.getByTestId('eval-chart')).toHaveTextContent('2 points');
  });
});
