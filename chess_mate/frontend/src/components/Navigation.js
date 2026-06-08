import { BarChart } from 'lucide-react';

const getNavigation = (pathname = '') => [
  {
    name: 'Batch Coach',
    href: '/batch-analysis',
    icon: BarChart,
    current: pathname === '/batch-analysis',
  },
];

export default getNavigation;
