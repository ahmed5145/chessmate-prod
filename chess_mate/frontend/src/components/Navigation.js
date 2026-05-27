import { BarChart } from 'lucide-react';

const getNavigation = (pathname = '') => [
  {
    name: 'Batch Analysis',
    href: '/batch-analysis',
    icon: BarChart,
    current: pathname === '/batch-analysis',
  },
];

export default getNavigation;
