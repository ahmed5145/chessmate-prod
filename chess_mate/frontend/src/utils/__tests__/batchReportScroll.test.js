import { renderHook, act } from '@testing-library/react';
import { scrollToBatchSection, useBatchReportSectionSpy } from '../batchReportScroll';

describe('scrollToBatchSection', () => {
  beforeEach(() => {
    document.body.innerHTML = '';
  });

  it('scrolls when the section element exists', () => {
    const element = document.createElement('div');
    element.id = 'batch-section-summary';
    element.scrollIntoView = jest.fn();
    document.body.appendChild(element);

    scrollToBatchSection('batch-section-summary');

    expect(element.scrollIntoView).toHaveBeenCalledWith({
      behavior: 'smooth',
      block: 'start',
    });
  });

  it('no-ops when the section is missing', () => {
    expect(() => scrollToBatchSection('missing-section')).not.toThrow();
  });
});

describe('useBatchReportSectionSpy', () => {
  const sections = [
    { id: 'batch-section-summary', label: 'Summary' },
    { id: 'batch-section-games', label: 'Game breakdown' },
  ];

  beforeEach(() => {
    global.IntersectionObserver = class {
      observe() {}

      disconnect() {}

      unobserve() {}
    };
    document.body.innerHTML = '';
    Object.defineProperty(window, 'innerHeight', { configurable: true, value: 800 });
    Object.defineProperty(window, 'scrollY', { configurable: true, value: 0, writable: true });
    Object.defineProperty(document.documentElement, 'scrollHeight', {
      configurable: true,
      value: 2000,
    });
  });

  it('activates the last section when scrolled near the page bottom', () => {
    const summary = document.createElement('div');
    summary.id = 'batch-section-summary';
    const games = document.createElement('div');
    games.id = 'batch-section-games';
    document.body.append(summary, games);

    const { result } = renderHook(() => useBatchReportSectionSpy(sections));

    act(() => {
      window.scrollY = 1200;
      window.dispatchEvent(new Event('scroll'));
    });

    expect(result.current).toBe('batch-section-games');
  });
});
