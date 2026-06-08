import { notifySingleGameAnalysisComplete } from '../analysisNotifications';
import { toast } from 'react-hot-toast';

jest.mock('react-hot-toast', () => ({
  toast: {
    success: jest.fn(),
  },
}));

describe('notifySingleGameAnalysisComplete', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    Object.defineProperty(document, 'hidden', { configurable: true, value: false });
  });

  it('shows a toast with opponent label', () => {
    notifySingleGameAnalysisComplete(168, { opponent: 'Rival123' });
    expect(toast.success).toHaveBeenCalledWith(
      'Depth-20 review ready (vs Rival123)',
      { duration: 6000 }
    );
  });

  it('does not throw when Notification API is unavailable', () => {
    const original = global.Notification;
    // eslint-disable-next-line no-global-assign
    global.Notification = undefined;
    expect(() => notifySingleGameAnalysisComplete(42)).not.toThrow();
    global.Notification = original;
  });
});
