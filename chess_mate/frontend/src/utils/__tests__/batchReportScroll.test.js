import { scrollToBatchSection } from '../batchReportScroll';

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
