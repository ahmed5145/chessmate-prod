import React from 'react';
import { render, screen } from '@testing-library/react';
import CoachingUnavailableBanner from '../CoachingUnavailableBanner';

describe('CoachingUnavailableBanner', () => {
  it('renders when coaching is missing', () => {
    render(<CoachingUnavailableBanner coachingReport={null} />);
    expect(screen.getByText(/AI coaching narrative is unavailable/i)).toBeInTheDocument();
  });

  it('renders nothing when coaching exists', () => {
    const { container } = render(
      <CoachingUnavailableBanner coachingReport={{ executive_summary: 'ok' }} />
    );
    expect(container).toBeEmptyDOMElement();
  });
});
