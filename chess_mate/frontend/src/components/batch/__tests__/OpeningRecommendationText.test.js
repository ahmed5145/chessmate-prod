import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import OpeningRecommendationText from '../OpeningRecommendationText';

describe('OpeningRecommendationText', () => {
  it('bolds opening name and ECO in neutral recommendations', () => {
    render(
      <OpeningRecommendationText
        item={{
          opening_name: "Queen's Pawn Game: London System",
          eco_code: 'D02',
          recommendation:
            "As white in Queen's Pawn Game: London System (D02): 1W-0L-0D across 1 game(s). Opening phase: 92%.",
        }}
      />
    );

    const bold = screen.getByText("Queen's Pawn Game: London System (D02)");
    expect(bold).toBeInTheDocument();
    expect(bold.tagName).toBe('SPAN');
    expect(bold).toHaveStyle({ fontWeight: 700 });
  });
});
