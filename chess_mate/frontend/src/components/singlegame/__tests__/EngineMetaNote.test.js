import React from 'react';
import { render, screen } from '@testing-library/react';
import EngineMetaNote from '../EngineMetaNote';

jest.mock('../../../context/ThemeContext', () => ({
  useTheme: () => ({ isDarkMode: false }),
}));

describe('EngineMetaNote', () => {
  it('renders engine classification note', () => {
    render(
      <EngineMetaNote
        engineMeta={{ classification_note: 'Single-game uses depth-20 coach model; batch report uses depth-14.' }}
      />
    );

    expect(screen.getByText(/depth-20 coach model/i)).toBeInTheDocument();
  });

  it('renders nothing without a note', () => {
    const { container } = render(<EngineMetaNote />);
    expect(container).toBeEmptyDOMElement();
  });
});
