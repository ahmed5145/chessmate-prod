import { BATCH_GAME_FOCUS_EVENT, scrollToBatchGame } from '../batchGameLinks';

describe('scrollToBatchGame', () => {
  beforeEach(() => {
    document.body.innerHTML = '<div id="batch-game-game_2"></div>';
    Element.prototype.scrollIntoView = jest.fn();
  });

  it('dispatches focus event and scrolls to the game accordion', async () => {
    const handler = jest.fn();
    window.addEventListener(BATCH_GAME_FOCUS_EVENT, handler);

    scrollToBatchGame('game_2');

    expect(handler).toHaveBeenCalled();
    expect(handler.mock.calls[0][0].detail.gameId).toBe('game_2');

    await new Promise((resolve) => requestAnimationFrame(resolve));
    expect(Element.prototype.scrollIntoView).toHaveBeenCalled();

    window.removeEventListener(BATCH_GAME_FOCUS_EVENT, handler);
  });
});
