import { useEffect } from 'react';

export const DEFAULT_SITE_TITLE = 'ChessMate';
export const DEFAULT_SITE_DESCRIPTION =
  'Import Chess.com or Lichess games and get Batch Coach reports — cross-game patterns, priorities, drills, and a training plan.';

const upsertMeta = (selector, attributes) => {
  if (typeof document === 'undefined') {
    return;
  }
  let element = document.head.querySelector(selector);
  if (!element) {
    element = document.createElement('meta');
    Object.entries(attributes).forEach(([key, value]) => {
      element.setAttribute(key, value);
    });
    document.head.appendChild(element);
  }
  return element;
};

const setMetaContent = (attrName, attrValue, content) => {
  if (!content) {
    return;
  }
  const element = upsertMeta(`meta[${attrName}="${attrValue}"]`, {
    [attrName]: attrValue,
  });
  if (element) {
    element.setAttribute('content', content);
  }
};

const setLinkHref = (rel, href) => {
  if (!href || typeof document === 'undefined') {
    return;
  }
  let element = document.head.querySelector(`link[rel="${rel}"]`);
  if (!element) {
    element = document.createElement('link');
    element.setAttribute('rel', rel);
    document.head.appendChild(element);
  }
  element.setAttribute('href', href);
};

export const buildCanonicalUrl = (path = '/') => {
  if (typeof window === 'undefined') {
    return path;
  }
  const normalized = path.startsWith('/') ? path : `/${path}`;
  return `${window.location.origin}${normalized}`;
};

export const setPageMeta = ({
  title,
  description = DEFAULT_SITE_DESCRIPTION,
  path = '/',
  type = 'website',
}) => {
  if (typeof document === 'undefined') {
    return;
  }

  const pageTitle = title ? `${title} · ${DEFAULT_SITE_TITLE}` : DEFAULT_SITE_TITLE;
  document.title = pageTitle;

  setMetaContent('name', 'description', description);
  setMetaContent('property', 'og:title', pageTitle);
  setMetaContent('property', 'og:description', description);
  setMetaContent('property', 'og:type', type);
  setMetaContent('property', 'og:url', buildCanonicalUrl(path));
  setMetaContent('name', 'twitter:card', 'summary_large_image');
  setMetaContent('name', 'twitter:title', pageTitle);
  setMetaContent('name', 'twitter:description', description);
  setLinkHref('canonical', buildCanonicalUrl(path));
};

export const usePageMeta = (config) => {
  const { title, description, path, type } = config;

  useEffect(() => {
    setPageMeta({ title, description, path, type });
    return () => setPageMeta({});
  }, [title, description, path, type]);
};

export const PAGE_META = {
  landing: {
    title: 'Batch Coach for your recent games',
    description:
      'ChessMate analyzes 5–30 Chess.com or Lichess games together — recurring mistakes, opening gaps, drills, and a coach-style action plan. First depth-20 single-game review is free.',
    path: '/',
  },
  exampleBatchReport: {
    title: 'Example Batch Coach report',
    description:
      'See a real Batch Coach report: priorities, phase breakdown, opening gaps, critical moments, and a week-by-week training plan from 8 games.',
    path: '/example/batch-report',
  },
  howItWorks: {
    title: 'How Batch Coach works',
    description:
      'Import from Chess.com or Lichess, pick 5–30 games, and get cross-game coaching — not one-game engine lines.',
    path: '/how-batch-coach-works',
  },
};
