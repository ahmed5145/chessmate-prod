import React from 'react';
import { render, screen } from '@testing-library/react';
import PwaInstallPrompt, { isMobileInstallContext, shouldShowPwaInstallPrompt } from '../PwaInstallPrompt';

describe('PwaInstallPrompt helpers', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('hides on desktop context', () => {
    window.matchMedia = jest.fn().mockImplementation((query) => ({
      matches: query.includes('max-width') ? false : false,
      addListener: jest.fn(),
      removeListener: jest.fn(),
    }));
    Object.defineProperty(window.navigator, 'maxTouchPoints', { value: 0, configurable: true });
    expect(shouldShowPwaInstallPrompt(1)).toBe(false);
  });

  it('shows on mobile after first batch when not dismissed', () => {
    window.matchMedia = jest.fn().mockImplementation((query) => ({
      matches: query.includes('max-width') || query.includes('pointer'),
      addListener: jest.fn(),
      removeListener: jest.fn(),
    }));
    Object.defineProperty(window.navigator, 'maxTouchPoints', { value: 2, configurable: true });
    expect(isMobileInstallContext()).toBe(true);
    expect(shouldShowPwaInstallPrompt(1)).toBe(true);
  });
});

describe('PwaInstallPrompt', () => {
  beforeEach(() => {
    localStorage.clear();
    window.matchMedia = jest.fn().mockImplementation((query) => ({
      matches: query.includes('max-width') || query.includes('pointer'),
      addListener: jest.fn(),
      removeListener: jest.fn(),
    }));
    Object.defineProperty(window.navigator, 'maxTouchPoints', { value: 2, configurable: true });
  });

  it('renders mobile install copy', () => {
    render(<PwaInstallPrompt batchesCompleted={1} />);
    expect(screen.getByText(/Add ChessMate to your home screen/i)).toBeInTheDocument();
  });

  it('does not render before first batch', () => {
    const { container } = render(<PwaInstallPrompt batchesCompleted={0} />);
    expect(container).toBeEmptyDOMElement();
  });
});
