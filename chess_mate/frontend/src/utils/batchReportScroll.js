import { useEffect, useState } from 'react';

/** Smooth-scroll to a batch report section by DOM id. */

export const scrollToBatchSection = (sectionId) => {
  const element = document.getElementById(sectionId);
  if (element) {
    element.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
};

const SCROLL_SPY_ROOT_MARGIN = '-20% 0px -55% 0px';
const BOTTOM_SCROLL_THRESHOLD_PX = 80;

const isNearPageBottom = () => (
  window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - BOTTOM_SCROLL_THRESHOLD_PX
);

/**
 * Track which batch report section is active for desktop/mobile nav.
 * Handles the last section (game breakdown) when the page bottom is reached.
 */
export const useBatchReportSectionSpy = (sections = []) => {
  const [activeId, setActiveId] = useState(sections[0]?.id || null);

  useEffect(() => {
    const sectionIds = sections.map((section) => section.id).filter(Boolean);
    const elements = sectionIds
      .map((sectionId) => document.getElementById(sectionId))
      .filter(Boolean);

    if (elements.length === 0) {
      return undefined;
    }

    const lastSectionId = sectionIds[sectionIds.length - 1];

    const activateLastSectionIfNearBottom = () => {
      if (isNearPageBottom() && lastSectionId) {
        setActiveId(lastSectionId);
        return true;
      }
      return false;
    };

    const observer = new IntersectionObserver(
      (entries) => {
        if (activateLastSectionIfNearBottom()) {
          return;
        }

        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio);

        if (visible[0]?.target?.id) {
          setActiveId(visible[0].target.id);
        }
      },
      { rootMargin: SCROLL_SPY_ROOT_MARGIN, threshold: [0, 0.1, 0.35, 0.6] }
    );

    elements.forEach((element) => observer.observe(element));

    const handleScroll = () => {
      activateLastSectionIfNearBottom();
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    activateLastSectionIfNearBottom();

    return () => {
      observer.disconnect();
      window.removeEventListener('scroll', handleScroll);
    };
  }, [sections]);

  return activeId;
};
