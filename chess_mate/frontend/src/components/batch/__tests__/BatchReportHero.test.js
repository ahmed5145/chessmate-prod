import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import BatchReportHero from '../BatchReportHero';

describe('BatchReportHero', () => {
  beforeEach(() => {
    document.body.innerHTML = '<div id="batch-section-priorities"></div>';
    Element.prototype.scrollIntoView = jest.fn();
  });

  it('shows takeaway and priority CTA when coaching exists', () => {
    render(
      <BatchReportHero
        batch_summary={{ games_analyzed: 10, date_range: 'May 2025' }}
        games_count={10}
        coaching_report={{
          executive_summary: 'You leak material in the middlegame. Focus on scans before captures.',
          top_3_priorities: [{ rank: 1, title: 'Tactics', why_it_matters: 'x', how_to_fix: 'y', specific_drill: 'z' }],
        }}
      />
    );

    expect(screen.getByText(/Batch coach report ready/i)).toBeInTheDocument();
    expect(screen.getByText(/10 games analyzed/i)).toBeInTheDocument();
    expect(screen.getByText(/leak material in the middlegame/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Start with priority #1/i })).toBeInTheDocument();
  });

  it('scrolls to priorities when CTA clicked', () => {
    render(
      <BatchReportHero
        batch_summary={{ games_analyzed: 5 }}
        coaching_report={{
          executive_summary: 'Opening play needs work across several games in this batch.',
          top_3_priorities: [{ rank: 1, title: 'Openings', why_it_matters: 'a', how_to_fix: 'b', specific_drill: 'c' }],
        }}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: /Start with priority #1/i }));
    expect(Element.prototype.scrollIntoView).toHaveBeenCalled();
  });

  it('falls back to phase CTA without priorities', () => {
    render(
      <BatchReportHero
        batch_summary={{ games_analyzed: 5 }}
        coaching_report={null}
      />
    );

    expect(screen.getByRole('button', { name: /View phase breakdown/i })).toBeInTheDocument();
  });
});
